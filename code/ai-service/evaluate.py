"""PromptShield baseline evaluation runner.

Runs the same deterministic stages used by the optimization endpoint against
the checked-in benchmark dataset. The harness measures:

* required privacy-label detection and anonymization
* post-optimization privacy leakage
* semantic preservation
* token reduction
* grammar-correction behavior
* pipeline latency

Use ``python evaluate.py`` for a human-readable report or
``python evaluate.py --json`` for machine-readable output.
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from app.services.grammar_corrector import GrammarCorrector
from app.services.optimizer import PromptOptimizer
from app.services.preprocessing import Preprocessor
from app.services.privacy_engine import PrivacyEngine
from app.services.privacy_policy import should_anonymize
from app.services.quality_validator import QualityValidator
from app.services.semantic_validator import SemanticValidator
from app.services.token_counter import TokenCounter


def _required_labels(expected: dict[str, Any]) -> list[str]:
    """Return list of labels explicitly required by a dataset case."""
    labels = list(expected.get("entities_labels", []))
    labels.extend(expected.get("entities_labels_contains", []))
    for entity in expected.get("entities", []):
        if isinstance(entity, str):
            labels.append(entity)
        elif isinstance(entity, dict) and entity.get("label"):
            labels.append(entity["label"])
    return [label for label in labels if label]


def evaluate_case(
    item: dict[str, Any],
    *,
    preprocessor: Preprocessor,
    privacy_engine: PrivacyEngine,
    optimizer: PromptOptimizer,
    grammar_corrector: GrammarCorrector,
    validator: QualityValidator,
    semantic_validator: SemanticValidator,
    token_counter: TokenCounter,
) -> dict[str, Any]:
    """Evaluate one benchmark case and return serializable metrics."""
    prompt = item["prompt"]
    expected = item.get("expected", {})
    started = time.perf_counter()

    cleaned = preprocessor.clean(prompt)
    privacy_result = privacy_engine.analyze(cleaned)
    anonymized = privacy_result["anonymized_prompt"]
    optimized_candidate = optimizer.optimize(anonymized)
    grammar_result = grammar_corrector.correct(optimized_candidate)
    optimized = validator.validate(anonymized, str(grammar_result["prompt"]))

    semantic_score = semantic_validator.score(anonymized, optimized)
    semantic_valid = semantic_validator.validate(anonymized, optimized)
    original_tokens = token_counter.count(cleaned)
    optimized_tokens = token_counter.count(optimized)
    reduction = token_counter.reduction_percentage(original_tokens, optimized_tokens)

    original_entities = privacy_result["entities"]
    protected_entities = [
        entity for entity in original_entities if should_anonymize(entity)
    ]
    post_privacy = privacy_engine.analyze(optimized)

    detected_labels = [entity["label"] for entity in original_entities]
    exp_labels = _required_labels(expected)
    missing_labels = sorted(set(exp_labels) - set(detected_labels))

    # Calculate TP, FP, FN for entity detection
    allowed_labels = set(expected.get("entities_labels_allowed", [])) | set(expected.get("entities_labels_may_contain", []))
    rem_exp = list(exp_labels)
    tp = 0
    fp = 0
    for d in detected_labels:
        if d in rem_exp:
            tp += 1
            rem_exp.remove(d)
        elif d in allowed_labels:
            continue
        else:
            fp += 1
    fn = len(rem_exp)

    # Anonymization success and leakage checks
    anonymized_success_count = sum(
        1 for entity in protected_entities
        if entity["text"] not in anonymized and entity["text"] not in optimized
    )
    has_leakage = any(
        entity["text"] in anonymized or entity["text"] in optimized
        for entity in protected_entities
    )

    # Constraint preservation checks
    expected_constraints = expected.get("constraint_preserved", [])
    constraints_expected = len(expected_constraints)
    constraints_preserved = sum(1 for phrase in expected_constraints if phrase in optimized)

    leakage_labels = sorted(
        {
            entity["label"]
            for entity in protected_entities
            if entity["text"] in optimized
        }
    )
    post_sensitive_labels = sorted(
        {
            entity["label"]
            for entity in post_privacy["entities"]
            if should_anonymize(entity) and not entity["text"].startswith("[")
        }
    )

    failures: list[str] = []
    risk_failures: list[str] = []
    expected_risk = expected.get("risk_level")
    if expected_risk and privacy_result["risk_level"] != expected_risk:
        risk_failures.append(
            f"risk level {privacy_result['risk_level']} != expected {expected_risk}"
        )
    if privacy_result["risk_level"] not in expected.get("risk_level_in", [privacy_result["risk_level"]]):
        risk_failures.append(
            f"risk level {privacy_result['risk_level']} not in {expected['risk_level_in']}"
        )
    if privacy_result["risk_score"] < expected.get("risk_score_min", 0):
        risk_failures.append(
            f"risk score {privacy_result['risk_score']} < {expected['risk_score_min']}"
        )
    if privacy_result["risk_score"] > expected.get("risk_score_max", 100):
        risk_failures.append(
            f"risk score {privacy_result['risk_score']} > {expected['risk_score_max']}"
        )

    if missing_labels:
        failures.append(f"missing entity labels {missing_labels}")
    for needle in expected.get("anonymized_contains", []):
        if needle not in anonymized:
            failures.append(f"anonymized prompt is missing {needle!r}")
    for needle in expected.get("anonymized_not_contains", []):
        if needle in anonymized:
            failures.append(f"PII leak during anonymization: {needle!r}")
    if expected.get("anonymized_contains_placeholders") is False:
        placeholder_like = re.search(r"\[[A-Z_]+\]", anonymized)
        if placeholder_like:
            failures.append("anonymized prompt unexpectedly contains placeholders")
    for needle in expected.get("optimized_contains", []):
        if needle not in optimized:
            failures.append(f"optimized prompt is missing {needle!r}")
    for needle in expected.get("optimized_not_contains", []):
        if needle in optimized:
            failures.append(f"optimized prompt still contains {needle!r}")
    for phrase in expected_constraints:
        if phrase not in optimized:
            failures.append(f"constraint not preserved: {phrase!r}")
    for phrase in expected.get("filler_removed", []):
        if phrase.lower() in optimized.lower():
            failures.append(f"filler phrase still present: {phrase!r}")
    if expected.get("optimized_not_empty") is True and not optimized.strip():
        failures.append("optimized prompt is empty")
    if expected.get("token_reduction_max_percent") is not None:
        max_reduction = float(expected["token_reduction_max_percent"])
        if reduction > max_reduction:
            failures.append(
                f"token reduction {reduction:.1f}% exceeds max {max_reduction:.1f}%"
            )
    for label in expected.get("entities_labels_may_contain", []):
        if label not in detected_labels and label not in {e.get("label") for e in post_privacy["entities"]}:
            failures.append(f"expected optional label {label!r} not detected")
    if expected.get("org_not_anonymized") is True:
        if "ORG" not in detected_labels and "ORG" not in {e.get("label") for e in post_privacy["entities"]}:
            failures.append("ORG entity expected but not detected")
    if leakage_labels:
        failures.append(
            f"protected entity categories leaked after optimization: {leakage_labels}"
        )
    if post_sensitive_labels:
        failures.append(
            f"post-optimization scan found protected categories: {post_sensitive_labels}"
        )
    if not optimized.strip():
        failures.append("optimized prompt is empty")

    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "id": item["id"],
        "category": item["category"],
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "tokens_saved": max(0, original_tokens - optimized_tokens),
        "reduction_percentage": reduction,
        "semantic_similarity_score": semantic_score,
        "semantic_valid": semantic_valid,
        "grammar_corrected": bool(grammar_result["changed"]),
        "entities_detected": len(original_entities),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "protected_entities_count": len(protected_entities),
        "anonymized_success_count": anonymized_success_count,
        "has_leakage": has_leakage,
        "constraints_expected": constraints_expected,
        "constraints_preserved": constraints_preserved,
        "privacy_valid": not leakage_labels and not post_sensitive_labels,
        "risk_score": privacy_result["risk_score"],
        "risk_level": privacy_result["risk_level"],
        "latency_ms": round(elapsed_ms, 2),
        "failures": failures,
        "risk_failures": risk_failures,
    }


def run_evaluation(json_output: bool = False) -> dict[str, Any]:
    """Run the benchmark and return aggregate and per-case results."""
    dataset_path = Path(__file__).parent / "datasets" / "evaluation_dataset.json"
    with dataset_path.open(encoding="utf-8") as dataset_file:
        dataset = json.load(dataset_file)

    services = {
        "preprocessor": Preprocessor(),
        "privacy_engine": PrivacyEngine(),
        "optimizer": PromptOptimizer(),
        "grammar_corrector": GrammarCorrector(),
        "validator": QualityValidator(),
        "semantic_validator": SemanticValidator(),
        "token_counter": TokenCounter(),
    }
    results = [evaluate_case(item, **services) for item in dataset]

    total = len(results)
    passed = sum(not result["failures"] and not result["risk_failures"] for result in results)
    failed = total - passed
    privacy_valid = sum(result["privacy_valid"] for result in results)
    semantic_valid = sum(result["semantic_valid"] for result in results)

    # Entity detection classification metrics
    total_tp = sum(r["tp"] for r in results)
    total_fp = sum(r["fp"] for r in results)
    total_fn = sum(r["fn"] for r in results)
    precision = round(total_tp / (total_tp + total_fp) * 100, 2) if (total_tp + total_fp) > 0 else 100.0
    recall = round(total_tp / (total_tp + total_fn) * 100, 2) if (total_tp + total_fn) > 0 else 100.0
    f1 = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0

    # Privacy and anonymization metrics
    total_protected = sum(r["protected_entities_count"] for r in results)
    total_anonymized = sum(r["anonymized_success_count"] for r in results)
    anonymization_success_rate = (
        round(total_anonymized / total_protected * 100, 2) if total_protected > 0 else 100.0
    )
    leakage_cases = sum(1 for r in results if r["has_leakage"])
    privacy_leakage_rate = round(leakage_cases / total * 100, 2) if total else 0.0

    # Constraint preservation metrics
    total_constraints = sum(r["constraints_expected"] for r in results)
    preserved_constraints = sum(r["constraints_preserved"] for r in results)
    constraint_preservation_rate = (
        round(preserved_constraints / total_constraints * 100, 2) if total_constraints > 0 else 100.0
    )

    # Latencies
    latencies = [r["latency_ms"] for r in results]
    latencies_sorted = sorted(latencies)
    p95_idx = min(len(latencies_sorted) - 1, int(len(latencies_sorted) * 0.95))

    summary = {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "pass_rate": round(passed / total * 100, 2) if total else 0.0,
        "failure_rate": round(failed / total * 100, 2) if total else 0.0,
        "entity_precision": precision,
        "entity_recall": recall,
        "entity_f1": f1,
        "false_positives": total_fp,
        "true_positives": total_tp,
        "false_negatives": total_fn,
        "anonymization_success_rate": anonymization_success_rate,
        "privacy_leakage_rate": privacy_leakage_rate,
        "constraint_preservation_rate": constraint_preservation_rate,
        "privacy_valid_rate": round(privacy_valid / total * 100, 2) if total else 0.0,
        "semantic_valid_rate": round(semantic_valid / total * 100, 2) if total else 0.0,
        "average_token_reduction": round(
            sum(result["reduction_percentage"] for result in results) / total, 2
        ) if total else 0.0,
        "average_semantic_similarity": round(
            sum(result["semantic_similarity_score"] for result in results) / total, 2
        ) if total else 0.0,
        "average_latency_ms": round(sum(latencies) / total, 2) if total else 0.0,
        "min_latency_ms": min(latencies) if latencies else 0.0,
        "max_latency_ms": max(latencies) if latencies else 0.0,
        "p95_latency_ms": latencies_sorted[p95_idx] if latencies else 0.0,
    }
    report = {"summary": summary, "results": results}

    if json_output:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 104)
        print("PROMPTSHIELD BASELINE V1 EVALUATION BENCHMARK")
        print("=" * 104)
        for result in results:
            status = "PASS" if not result["failures"] and not result["risk_failures"] else "FAIL"
            print(
                f"[{status}] {result['id']:02d} {result['category']:<32} "
                f"{result['original_tokens']:3d} -> {result['optimized_tokens']:3d} "
                f"(-{result['reduction_percentage']:5.1f}%) "
                f"semantic={result['semantic_similarity_score']:5.1f} "
                f"privacy={'OK' if result['privacy_valid'] else 'LEAK'} "
                f"{result['latency_ms']:6.1f}ms"
            )
            for failure in result["failures"] + result["risk_failures"]:
                print(f"      - {failure}")
        print("=" * 104)
        print("EVALUATION METRICS & BASELINE SUMMARY")
        print("=" * 104)
        print(f"Benchmark Cases             : {summary['total_cases']} (Pass: {summary['passed_cases']}, Fail: {summary['failed_cases']})")
        print(f"Pass Rate                   : {summary['pass_rate']}%")
        print(f"Failure Rate                : {summary['failure_rate']}%")
        print(f"Entity Detection Precision  : {summary['entity_precision']}%")
        print(f"Entity Detection Recall     : {summary['entity_recall']}%")
        print(f"Entity Detection F1 Score   : {summary['entity_f1']}%")
        print(f"False Positives Count       : {summary['false_positives']}")
        print(f"Anonymization Success Rate  : {summary['anonymization_success_rate']}%")
        print(f"Privacy Leakage Rate        : {summary['privacy_leakage_rate']}%")
        print(f"Constraint Preservation Rate: {summary['constraint_preservation_rate']}%")
        print(f"Average Token Reduction     : {summary['average_token_reduction']}%")
        print(f"Average Semantic Similarity : {summary['average_semantic_similarity']}")
        print(f"Average Latency             : {summary['average_latency_ms']} ms (min: {summary['min_latency_ms']} ms, p95: {summary['p95_latency_ms']} ms)")
        print("=" * 104)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full benchmark report as JSON.",
    )
    args = parser.parse_args()
    run_evaluation(json_output=args.json)
