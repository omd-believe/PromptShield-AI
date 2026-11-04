"""
candidate_evaluator.py — Candidate evaluation logic for PromptShield-AI.

Contains pure-Python evaluation functions for LLMLingua-2 and FLAN-T5 candidates.
Kept separate from app.api.optimize so unit tests can import these functions
without pulling in spaCy/numpy (which cannot be re-imported in the same process).
"""

import logging
import re

from app import config

logger = logging.getLogger(__name__)

_PLACEHOLDER_PATTERN = re.compile(r"\[[A-Z_]+(?:_\d+)?\]")


def _has_measurable_clarity_improvement(
    grammar_corrector,
    anonymized_prompt: str,
    candidate: str,
    deterministic_candidate: str,
    filler_patterns,
    compact_patterns,
) -> tuple[bool, str | None]:
    """
    Evaluate whether a candidate provides a defensible clarity improvement
    when token reduction is zero or negative.
    """
    input_grammar = grammar_corrector.correct(anonymized_prompt)
    cand_grammar = grammar_corrector.correct(candidate)
    if input_grammar.get("changed") and not cand_grammar.get("changed"):
        return True, "Candidate repairs spelling or grammatical defects present in baseline"

    input_has_fillers = any(p.search(anonymized_prompt) for p in filler_patterns)
    cand_has_fillers = any(p.search(candidate) for p in filler_patterns)
    if input_has_fillers and not cand_has_fillers:
        return True, "Candidate eliminates polite filler phrases present in baseline"

    input_has_compact = any(p[0].search(anonymized_prompt) for p in compact_patterns)
    cand_has_compact = any(p[0].search(candidate) for p in compact_patterns)
    if input_has_compact and not cand_has_compact:
        return True, "Candidate compacts verbose connective phrases present in baseline"

    return False, "Candidate provides no measurable token reduction or quality improvement over baseline"


def _is_leakage(entity: dict, candidate: str, anonymized_prompt: str) -> bool:
    """
    Check if a detected entity represents genuine newly introduced sensitive data leakage.
    Returns True if it is a leak, False if it is a false positive (placeholder or pre-existing).
    """
    text = entity.get("text", "").strip()
    if not text:
        return False

    # 1. Exact bracketed placeholder: e.g. [PERSON_1], [EMAIL]
    if text.startswith("[") and text.endswith("]"):
        return False

    # 2. Text matches placeholder syntax (e.g. EMAIL_3, PERSON_1, EMAIL, PERSON)
    if re.fullmatch(r"\[?[A-Z]+(?:_\d+)?\]?", text):
        return False

    # 3. Span in candidate is enclosed in brackets: e.g. [EMAIL_3]
    start = entity.get("start", -1)
    end = entity.get("end", -1)
    if 0 < start and end < len(candidate):
        if candidate[start - 1] == "[" and candidate[end] == "]":
            return False

    # 4. Span falls within any bracketed placeholder in candidate
    for m in _PLACEHOLDER_PATTERN.finditer(candidate):
        if m.start() <= start and end <= m.end():
            return False

    # 5. Entity text was already present in the anonymized input prompt (exact or case-insensitive)
    if text in anonymized_prompt or text.lower() in anonymized_prompt.lower():
        return False

    # 6. All individual words in the entity text were already present in the anonymized input prompt
    # Compression can juxtapose pre-existing non-sensitive words (e.g. "No" + "Frequent" -> "No Frequent")
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", text)]
    if words:
        anon_lower = anonymized_prompt.lower()
        if all(re.search(r"\b" + re.escape(w) + r"\b", anon_lower) for w in words):
            return False

    return True



def evaluate_llmlingua_candidate(
    anonymized_prompt: str,
    deterministic_candidate: str,
    candidate: str,
    privacy_policy,
    protected_entities: list[dict],
    token_counter,
    privacy_engine,
    should_anonymize_fn,
    quality_validator,
    semantic_validator,
    grammar_corrector,
    filler_patterns,
    compact_patterns,
) -> tuple[bool, str | None]:
    """
    Validate LLMLingua-2 candidate against safety, constraint, and quality requirements.
    Returns (accepted, rejection_reason).
    """
    if not candidate or not candidate.strip():
        return False, "LLMLingua-2 candidate was empty or whitespace only"

    anon_tokens = token_counter.count(anonymized_prompt)
    cand_tokens = token_counter.count(candidate)

    # Reject pathologically short outputs (> 67% shorter than anonymized)
    if anon_tokens > 0 and (cand_tokens / anon_tokens) < 0.33:
        ratio = cand_tokens / anon_tokens
        return False, (
            f"LLMLingua-2 candidate is {(1 - ratio) * 100:.0f}% shorter than anonymized "
            f"prompt (ratio={ratio:.2f}); output may be truncated"
        )

    # Placeholder preservation
    anon_placeholders = sorted(_PLACEHOLDER_PATTERN.findall(anonymized_prompt))
    cand_placeholders = sorted(_PLACEHOLDER_PATTERN.findall(candidate))
    if anon_placeholders != cand_placeholders:
        return False, (
            f"LLMLingua-2 altered privacy placeholders: expected {anon_placeholders}, "
            f"got {cand_placeholders}"
        )

    # Privacy leakage scan
    if any(e["text"] in candidate for e in protected_entities):
        return False, "LLMLingua-2 candidate contains protected sensitive entity values"

    cand_scan = privacy_engine.analyze(candidate, privacy_policy)
    cand_leaks = [
        e
        for e in cand_scan["entities"]
        if should_anonymize_fn(e, privacy_policy) and _is_leakage(e, candidate, anonymized_prompt)
    ]
    if cand_leaks:
        labels = sorted({e["label"] for e in cand_leaks})
        return False, f"LLMLingua-2 candidate introduced sensitive data leakage: {labels}"

    # Quality validation
    _, val_warnings, fallback_used = quality_validator.validate_prompt(anonymized_prompt, candidate)
    if fallback_used:
        reason = "; ".join(val_warnings) if val_warnings else "Failed quality constraint validation"
        return False, f"LLMLingua-2 candidate failed quality validation: {reason}"

    # Semantic similarity
    sem_score = semantic_validator.score(anonymized_prompt, candidate)
    if sem_score < config.LLMLINGUA_MIN_SEMANTIC_SCORE:
        return False, (
            f"LLMLingua-2 semantic similarity score ({sem_score:.2f}%) below required threshold "
            f"({config.LLMLINGUA_MIN_SEMANTIC_SCORE:.2f}%)"
        )

    # Exact equivalence / no-op checks
    if candidate.strip() == anonymized_prompt.strip():
        return False, "LLMLingua-2 candidate is identical to anonymized input (no compression occurred)"

    if candidate.strip() == deterministic_candidate.strip():
        return False, "LLMLingua-2 candidate is identical to deterministic candidate (no additional improvement)"

    # Measurable benefit
    has_token_reduction = cand_tokens < anon_tokens

    if not has_token_reduction:
        has_clarity, _ = _has_measurable_clarity_improvement(
            grammar_corrector=grammar_corrector,
            anonymized_prompt=anonymized_prompt,
            candidate=candidate,
            deterministic_candidate=deterministic_candidate,
            filler_patterns=filler_patterns,
            compact_patterns=compact_patterns,
        )
        if not has_clarity:
            return False, (
                f"LLMLingua-2 candidate provides no measurable token reduction "
                f"({cand_tokens} >= {anon_tokens} tokens) or quality improvement over baseline"
            )

    return True, None


def evaluate_flan_t5_candidate(
    anonymized_prompt: str,
    deterministic_candidate: str,
    candidate: str,
    privacy_policy,
    protected_entities: list[dict],
    token_counter,
    privacy_engine,
    should_anonymize_fn,
    quality_validator,
    semantic_validator,
    grammar_corrector,
    filler_patterns,
    compact_patterns,
) -> tuple[bool, str | None]:
    """
    Validate FLAN-T5 candidate against safety, constraint, and quality requirements.
    Returns (accepted, rejection_reason).
    """
    if not candidate or not candidate.strip():
        return False, "Candidate was empty or whitespace only"

    # Placeholder preservation
    anon_placeholders = sorted(_PLACEHOLDER_PATTERN.findall(anonymized_prompt))
    cand_placeholders = sorted(_PLACEHOLDER_PATTERN.findall(candidate))
    if anon_placeholders != cand_placeholders:
        return False, (
            f"Altered privacy placeholders: expected {anon_placeholders}, "
            f"got {cand_placeholders}"
        )

    # Privacy leakage scan
    if any(e["text"] in candidate for e in protected_entities):
        return False, "Candidate contains protected sensitive entity values"

    cand_scan = privacy_engine.analyze(candidate, privacy_policy)
    cand_leaks = [
        e
        for e in cand_scan["entities"]
        if should_anonymize_fn(e, privacy_policy) and _is_leakage(e, candidate, anonymized_prompt)
    ]
    if cand_leaks:
        labels = sorted({e["label"] for e in cand_leaks})
        return False, f"Candidate introduced sensitive data leakage: {labels}"

    # Quality validation
    _, val_warnings, fallback_used = quality_validator.validate_prompt(anonymized_prompt, candidate)
    if fallback_used:
        reason = "; ".join(val_warnings) if val_warnings else "Failed quality constraint validation"
        return False, reason

    # Semantic similarity
    sem_score = semantic_validator.score(anonymized_prompt, candidate)
    if sem_score < config.FLAN_T5_MIN_SEMANTIC_SCORE:
        is_length_anomaly = any("Length anomaly detected" in w for w in val_warnings)
        if is_length_anomaly:
            p_toks = set(semantic_validator._normalize(anonymized_prompt))
            c_toks = set(semantic_validator._normalize(candidate))
            grounded_ratio = (len(p_toks & c_toks) / len(c_toks)) if c_toks else 0.0
            if grounded_ratio < 0.65 or sem_score < 25.0:
                return False, (
                    f"Semantic similarity score ({sem_score:.2f}%) below required threshold "
                    f"({config.FLAN_T5_MIN_SEMANTIC_SCORE:.2f}%)"
                )
        else:
            return False, (
                f"Semantic similarity score ({sem_score:.2f}%) below required threshold "
                f"({config.FLAN_T5_MIN_SEMANTIC_SCORE:.2f}%)"
            )

    # Exact equivalence / no-op checks
    if candidate.strip() == anonymized_prompt.strip():
        return False, "Candidate is identical to anonymized input (no rewriting occurred)"

    if candidate.strip() == deterministic_candidate.strip():
        return False, "Candidate is identical to deterministic candidate (no additional improvement)"

    # Measurable benefit
    anon_tokens = token_counter.count(anonymized_prompt)
    det_tokens = token_counter.count(deterministic_candidate)
    cand_tokens = token_counter.count(candidate)

    has_token_reduction = cand_tokens < anon_tokens
    has_clarity, _ = _has_measurable_clarity_improvement(
        grammar_corrector=grammar_corrector,
        anonymized_prompt=anonymized_prompt,
        candidate=candidate,
        deterministic_candidate=deterministic_candidate,
        filler_patterns=filler_patterns,
        compact_patterns=compact_patterns,
    )

    if not has_token_reduction and not has_clarity:
        return False, (
            f"Candidate provides no measurable token reduction "
            f"({cand_tokens} >= {anon_tokens} tokens) or quality improvement over baseline"
        )

    if has_token_reduction and not has_clarity and (det_tokens < cand_tokens):
        return False, (
            f"Deterministic candidate provides superior token reduction "
            f"({det_tokens} < {cand_tokens} tokens)"
        )

    return True, None
