"""
Evaluation and Comparison Runner: Deterministic Baseline vs. FLAN-T5.

Runs representative synthetic benchmark cases through both the deterministic baseline
and the FLAN-T5 candidate generation pipeline, recording:
- Original token count
- Deterministic candidate token count
- FLAN-T5 candidate token count
- Final selected token count
- Token reduction percentage
- Semantic preservation
- Constraint preservation
- Privacy leakage
- Candidate acceptance / rejection reason
- Inference latency
- Selected optimization strategy
"""

import argparse
import statistics
import time
from typing import Any

from app import config
from app.api.optimize import _evaluate_flan_t5_candidate
from app.services.flan_t5_service import flan_t5_service
from app.services.grammar_corrector import GrammarCorrector
from app.services.optimizer import PromptOptimizer
from app.services.preprocessing import Preprocessor
from app.services.privacy_engine import PrivacyEngine
from app.services.privacy_policy import should_anonymize
from app.services.quality_validator import QualityValidator
from app.services.semantic_validator import SemanticValidator
from app.services.token_counter import TokenCounter

# Documented representative prompts covering general, technical, constraints, security, and privacy
EVAL_CASES = [
    {
        "id": "CASE-01",
        "category": "filler_politeness",
        "prompt": "Could you please kindly go ahead and provide a concise summary of this quarterly report for me?",
        "constraints": ["summary", "quarterly report"],
    },
    {
        "id": "CASE-02",
        "category": "technical_java_generics",
        "prompt": "Write a Java method accepting Map<Integer, Integer> and returning a List<String>. Use Java 8 streams only.",
        "constraints": ["Map<Integer, Integer>", "List<String>", "Java 8 streams only"],
    },
    {
        "id": "CASE-03",
        "category": "security_negation",
        "prompt": "Review this login function. Critical security instruction: do not store passwords in plaintext and recommend secure password hashing.",
        "constraints": ["do not store passwords in plaintext", "recommend secure password hashing"],
    },
    {
        "id": "CASE-04",
        "category": "numeric_constraints",
        "prompt": "List the top 3 recommendations for securing a Spring Boot REST API in bullet points.",
        "constraints": ["3", "bullet points", "Spring Boot", "REST API"],
    },
    {
        "id": "CASE-05",
        "category": "pii_anonymized",
        "prompt": "Customer Priya Patil with email priya.test@example.com reported an issue with account 123456789012.",
        "constraints": ["Customer [PERSON]", "[EMAIL]", "[BANK_ACCOUNT]"],
    },
    {
        "id": "CASE-06",
        "category": "algorithmic_complexity",
        "prompt": "Implement binary search in Python with O(log n) time complexity and O(1) space complexity.",
        "constraints": ["binary search", "Python", "O(log n)", "O(1)"],
    },
    {
        "id": "CASE-07",
        "category": "strict_negation",
        "prompt": "Explain dependency injection in Spring Boot without using XML configuration or deprecated annotations.",
        "constraints": ["without using XML configuration", "deprecated annotations"],
    },
    {
        "id": "CASE-08",
        "category": "sql_query_tuning",
        "prompt": "Please optimize this PostgreSQL query in order to improve execution performance and eliminate sequential scans.",
        "constraints": ["PostgreSQL", "sequential scans", "optimize"],
    },
]


def run_evaluation(device: str = "auto") -> dict[str, Any]:
    """Execute evaluation across test prompts and return detailed metrics."""
    # Ensure FLAN-T5 is enabled for evaluation
    config.FLAN_T5_ENABLED = True
    config.FLAN_T5_DEVICE = device
    config.FLAN_T5_USE_ONLINE_DOWNLOAD = True

    preprocessor = Preprocessor()
    privacy_engine = PrivacyEngine()
    optimizer = PromptOptimizer()
    grammar_corrector = GrammarCorrector()
    validator = QualityValidator()
    semantic_validator = SemanticValidator()
    token_counter = TokenCounter()

    # Load model
    print("=" * 105)
    print(f"PROMPTSHIELD FLAN-T5 INTEGRATION EVALUATION BENCHMARK (Device: {device})")
    print("=" * 105)
    start_load = time.perf_counter()
    loaded = flan_t5_service.load_model()
    load_time_ms = (time.perf_counter() - start_load) * 1000
    print(f"Model loaded: {loaded} in {load_time_ms:.1f} ms on device '{flan_t5_service._device}'\n")

    results = []
    latencies = []

    for item in EVAL_CASES:
        case_id = item["id"]
        prompt = item["prompt"]
        constraints = item["constraints"]

        # Stage 1: Preprocessing & Privacy
        cleaned = preprocessor.clean(prompt)
        privacy_res = privacy_engine.analyze(cleaned)
        anonymized = privacy_res["anonymized_prompt"]
        orig_tokens = token_counter.count(cleaned)

        protected_entities = [
            e for e in privacy_res["entities"] if should_anonymize(e)
        ]

        # Stage 2: Deterministic Baseline Candidate
        det_raw = optimizer.optimize(anonymized)
        det_grammar = grammar_corrector.correct(det_raw)["prompt"]
        det_validated, _, _ = validator.validate_prompt(anonymized, det_grammar)
        det_tokens = token_counter.count(det_validated)
        det_sem = semantic_validator.score(anonymized, det_validated)

        # Stage 3: FLAN-T5 Candidate Generation
        t0 = time.perf_counter()
        try:
            flan_raw = flan_t5_service.generate_candidate(anonymized)
            infer_ms = (time.perf_counter() - t0) * 1000
        except Exception as exc:
            flan_raw = ""
            infer_ms = 0.0

        latencies.append(infer_ms)
        flan_tokens = token_counter.count(flan_raw) if flan_raw else 0

        # Stage 4: Candidate Validation & Selection
        accepted, reject_reason = _evaluate_flan_t5_candidate(
            anonymized_prompt=anonymized,
            deterministic_candidate=det_validated,
            candidate=flan_raw,
            privacy_policy=None,
            protected_entities=protected_entities,
        )

        if accepted:
            strategy = "flan-t5"
            selected = flan_raw
        else:
            strategy = "deterministic"
            selected = det_validated

        # Stage 5: Final Validation & Metrics
        selected_grammar = grammar_corrector.correct(selected)["prompt"]
        final_prompt, _, _ = validator.validate_prompt(anonymized, selected_grammar)
        final_tokens = token_counter.count(final_prompt)
        reduction_pct = token_counter.reduction_percentage(orig_tokens, final_tokens)
        final_sem = semantic_validator.score(anonymized, final_prompt)

        # Leakage verification on final output
        final_scan = privacy_engine.analyze(final_prompt)
        leakage = any(
            should_anonymize(e) and not e["text"].startswith("[")
            for e in final_scan["entities"]
        ) or any(e["text"] in final_prompt for e in protected_entities)

        # Constraint check
        constraints_preserved = all(
            c.lower() in final_prompt.lower() or c in final_prompt
            for c in constraints
        )

        status_str = "ACCEPTED" if accepted else "REJECTED"
        print(
            f"[{case_id}] {item['category']:<26} | Tokens: {orig_tokens:2d} -> Det:{det_tokens:2d} FLAN:{flan_tokens:2d} Final:{final_tokens:2d} "
            f"({reduction_pct:4.1f}%) | Sem:{final_sem:5.1f} | Latency:{infer_ms:6.1f}ms | {status_str:<8} -> {strategy}"
        )
        if not accepted and reject_reason:
            print(f"        └─ Safety/Quality Rejection: {reject_reason}")

        results.append({
            "case_id": case_id,
            "category": item["category"],
            "orig_tokens": orig_tokens,
            "det_tokens": det_tokens,
            "flan_tokens": flan_tokens,
            "final_tokens": final_tokens,
            "reduction_pct": reduction_pct,
            "semantic_score": final_sem,
            "constraints_preserved": constraints_preserved,
            "leakage": leakage,
            "accepted": accepted,
            "reject_reason": reject_reason,
            "strategy": strategy,
            "latency_ms": infer_ms,
        })

    # Summary Statistics
    total_cases = len(results)
    accepted_count = sum(1 for r in results if r["accepted"])
    rejected_count = total_cases - accepted_count
    accept_rate = (accepted_count / total_cases) * 100
    reject_rate = (rejected_count / total_cases) * 100
    avg_reduction = statistics.mean(r["reduction_pct"] for r in results)
    avg_semantic = statistics.mean(r["semantic_score"] for r in results)
    constraint_rate = (sum(1 for r in results if r["constraints_preserved"]) / total_cases) * 100
    leakage_count = sum(1 for r in results if r["leakage"])

    valid_latencies = [l for l in latencies if l > 0]
    median_lat = statistics.median(valid_latencies) if valid_latencies else 0.0
    p95_lat = sorted(valid_latencies)[int(len(valid_latencies) * 0.95)] if valid_latencies else 0.0

    print("\n" + "=" * 105)
    print("EVALUATION & COMPARISON SUMMARY METRICS")
    print("=" * 105)
    print(f"Total Benchmark Cases Evaluated : {total_cases}")
    print(f"FLAN-T5 Candidates Accepted     : {accepted_count} ({accept_rate:.1f}%)")
    print(f"FLAN-T5 Candidates Rejected     : {rejected_count} ({reject_rate:.1f}%)")
    print(f"Constraint Preservation Rate    : {constraint_rate:.1f}%")
    print(f"Privacy Leakage Regressions     : {leakage_count}")
    print(f"Average Token Reduction (Final) : {avg_reduction:.2f}%")
    print(f"Average Semantic Similarity     : {avg_semantic:.2f}%")
    print(f"Model Inference Latency (Median): {median_lat:.1f} ms")
    print(f"Model Inference Latency (p95)   : {p95_lat:.1f} ms")
    print("=" * 105)

    return {
        "device": flan_t5_service._device,
        "total_cases": total_cases,
        "accepted_count": accepted_count,
        "accept_rate": accept_rate,
        "rejected_count": rejected_count,
        "reject_rate": reject_rate,
        "constraint_rate": constraint_rate,
        "leakage_count": leakage_count,
        "avg_reduction": avg_reduction,
        "avg_semantic": avg_semantic,
        "median_latency_ms": median_lat,
        "p95_latency_ms": p95_lat,
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate PromptShield with FLAN-T5")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    args = parser.parse_args()
    run_evaluation(device=args.device)
