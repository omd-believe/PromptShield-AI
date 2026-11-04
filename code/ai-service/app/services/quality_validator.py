"""
Post-optimization quality and semantic constraint validator.

Validates the optimized candidate prompt before returning it.
Enforces deterministic semantic preservation:
1. Not empty and acceptable length ratio.
2. Complete preservation of all privacy placeholders ([EMAIL], [PERSON], etc.).
3. Preservation of critical negation and prohibition terms (not, never, must not, etc.).
4. Preservation of exact numeric constraints, quantities, and limits (e.g. "3 bullet points", "7-day").
5. Preservation of required programming languages and frameworks (Java, Python, SQL, etc.).
6. Preservation of requested output formats (bullet points, JSON, table, etc.).
7. Preservation of technical generic types and identifiers (Map<Integer, Integer>, etc.).
8. Preservation of security instructions (untrusted, system prompt, passwords).

If any check fails, the validator returns the safe anonymized prompt
(pre-optimization) as a fallback and generates descriptive warnings.
"""

import logging
import re
from typing import Sequence

from app import config

logger = logging.getLogger(__name__)

# Regex for anonymization placeholders
_PLACEHOLDER_RE = re.compile(r"\[[A-Z_]+(?:_\d+)?\]")

# Core domain / OOP concepts that must never be dropped when present in input
_CORE_OOP_CONCEPTS = ["encapsulation", "inheritance", "polymorphism", "abstraction"]

# Explicit deliverable patterns: deliverables requested in prompts
_EXPLICIT_DELIVERABLES: list[tuple[str, re.Pattern[str], re.Pattern[str]]] = [
    (
        "comparison table",
        re.compile(
            r"\b(?:comparison\s+table|table\s+(?:that\s+highlights|comparing)|differences\s+table)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:comparison\s+table|table|differences\s+table)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "code example",
        re.compile(
            r"\b(?:java\s+)?code\s+examples?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:code\s+examples?|code|examples?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "concept definition",
        re.compile(
            r"\b(?:short\s+)?definitions?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:definitions?|define|meaning)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "usefulness explanation",
        re.compile(
            r"\b(?:why\s+it\s+is\s+useful|why\s+(?:it's|they\s+are)\s+useful|usefulness)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:why\s+(?:\w+\s+)?(?:is|are)\s+useful|useful(?:ness)?|benefits?)\b",
            re.IGNORECASE,
        ),
    ),
]

# Semantic constraint patterns
_NEGATION_RE = re.compile(
    r"\b(do\s+not|don't|dont|cannot|can't|cant|should\s+not|shouldn't|must\s+not|won't|wont|never|without|not|no)\b",
    re.IGNORECASE,
)

_CANONICAL_NEGATIONS: dict[str, str] = {
    "don't": "do not",
    "dont": "do not",
    "do not": "do not",
    "can't": "cannot",
    "cant": "cannot",
    "cannot": "cannot",
    "shouldn't": "should not",
    "should not": "should not",
    "won't": "will not",
    "wont": "will not",
    "must not": "must not",
    "never": "never",
    "without": "without",
    "no": "no",
    "not": "not",
}

_PROHIBITION_CLAUSE_RE = re.compile(
    r"\b(do\s+not|don't|dont|never|cannot|can't|must\s+not|should\s+not|shouldn't|without)\s+([a-zA-Z0-9_\s-]{2,45}?)[\.,;\n]|\b(do\s+not|don't|dont|never|cannot|can't|must\s+not|should\s+not)\s+([a-zA-Z0-9_-]+(?:\s+[a-zA-Z0-9_-]+){1,4})",
    re.IGNORECASE,
)
_NUMERIC_CONSTRAINT_RE = re.compile(
    r"\b\d+(?:-\w+)?(?:\s+(?:bullet\s+points?|bullets?|points?|days?|hours?|mins?|minutes?|seconds?|words?|tokens?|items?|steps?|%|percent))?\b",
    re.IGNORECASE,
)
_LANGUAGES_RE = re.compile(
    r"\b(java(?:\s+8|\s+11|\s+17|\s+21)?|python(?:\s+3)?|sql|javascript|typescript|c\+\+|rust|golang|go|kotlin|scala|c#|php|ruby|swift|bash|html|css)\b",
    re.IGNORECASE,
)
_FORMAT_RE = re.compile(
    r"\b(bullet\s+points?|bullets?|json|yaml|xml|table|markdown|numbered\s+list)\b",
    re.IGNORECASE,
)
_GENERIC_TYPE_RE = re.compile(r"\b[A-Za-z_]\w*<[^>\n]+>")
_SECURITY_RE = re.compile(
    r"\b(plaintext|ciphertext|untrusted|trusted|entrusted|system\s+prompt|passwords?|secret|secrets?|prompt\s+injection|jailbreak|hashing|hash|authentication|authorization|encryption|decryption)\b",
    re.IGNORECASE,
)
_COMPLEXITY_RE = re.compile(r"\bO\([^)\n]+\)", re.IGNORECASE)
_INSTRUCTION_CONSTRAINTS_RE = re.compile(
    r"\b(no\s+external\s+libraries|preserve\s+(?:the\s+)?original\s+order)\b",
    re.IGNORECASE,
)


class QualityValidator:
    """Validates the optimized candidate prompt and falls back safely if any check fails."""

    def __init__(
        self,
        anomaly_length_ratio: float | None = None,
        absolute_min_ratio: float | None = None,
    ) -> None:
        self.anomaly_length_ratio = (
            anomaly_length_ratio
            if anomaly_length_ratio is not None
            else getattr(config, "QUALITY_ANOMALY_LENGTH_RATIO", 0.4)
        )
        self.absolute_min_ratio = (
            absolute_min_ratio
            if absolute_min_ratio is not None
            else getattr(config, "QUALITY_ABSOLUTE_MIN_RATIO", 0.15)
        )

    def validate_prompt(
        self,
        anonymized_prompt: str,
        optimized_prompt: str,
    ) -> tuple[str, list[str], bool]:
        """
        Validate *optimized_prompt* against *anonymized_prompt*.

        Returns:
            (final_prompt, warnings, fallback_used)
        """
        warnings: list[str] = []

        # Check 1: Non-empty output
        if not optimized_prompt.strip():
            msg = "Optimized prompt was empty; safe anonymized prompt was returned as fallback."
            logger.warning(msg)
            return anonymized_prompt, [msg], True

        # Check 2: Length ratio evaluation (anomaly signal vs hard rejection)
        anon_len = len(anonymized_prompt.strip())
        opt_len = len(optimized_prompt.strip())
        length_anomaly = False
        if anon_len > 0:
            ratio = opt_len / anon_len
            if ratio < self.absolute_min_ratio:
                msg = (
                    f"Optimized prompt is excessively truncated (ratio={ratio:.2f} < {self.absolute_min_ratio:.2f}); "
                    "safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

            if ratio < self.anomaly_length_ratio:
                length_anomaly = True
                msg = (
                    f"Length anomaly detected: candidate is {(1 - ratio) * 100:.0f}% shorter than anonymized prompt "
                    f"(ratio={ratio:.2f} < {self.anomaly_length_ratio:.2f}); triggering strict requirement and deliverable verification."
                )
                logger.info(msg)
                warnings.append(msg)

        # Check 3: Privacy placeholders must be 100% preserved
        anon_placeholders = set(_PLACEHOLDER_RE.findall(anonymized_prompt))
        opt_placeholders = set(_PLACEHOLDER_RE.findall(optimized_prompt))
        missing_placeholders = anon_placeholders - opt_placeholders
        if missing_placeholders:
            msg = (
                f"Optimization dropped or corrupted privacy placeholder(s): "
                f"{sorted(missing_placeholders)}; safe anonymized prompt was returned as fallback."
            )
            logger.warning(msg)
            return anonymized_prompt, [msg], True

        opt_lower = optimized_prompt.lower()
        anon_lower = anonymized_prompt.lower()

        # Check 4: Security-critical instructions preservation
        anon_security = set(m.group(0).lower() for m in _SECURITY_RE.finditer(anonymized_prompt))
        for sec_term in anon_security:
            if sec_term not in opt_lower:
                msg = (
                    f"Optimization removed security-critical instruction ('{sec_term}'); "
                    f"safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

        # Check 5: Negation and prohibition constraints preservation
        # 5a. Canonical negation equivalence (recognise 'do not' <=> 'don't', 'cannot' <=> 'can't', etc.)
        anon_canonical = set(
            _CANONICAL_NEGATIONS.get(m.group(0).lower().strip(), m.group(0).lower().strip())
            for m in _NEGATION_RE.finditer(anonymized_prompt)
        )
        opt_canonical = set(
            _CANONICAL_NEGATIONS.get(m.group(0).lower().strip(), m.group(0).lower().strip())
            for m in _NEGATION_RE.finditer(optimized_prompt)
        )
        missing_negations = anon_canonical - opt_canonical
        if missing_negations:
            msg = (
                f"Optimization removed critical negation/prohibition constraint(s): "
                f"{sorted(missing_negations)}; safe anonymized prompt was returned as fallback."
            )
            logger.warning(msg)
            return anonymized_prompt, [msg], True

        # 5b. Prohibition clause scope validation (prevent prohibition reversal)
        # E.g. "Do not use advanced Java features" must NOT become "Use advanced Java features"
        for match in _PROHIBITION_CLAUSE_RE.finditer(anonymized_prompt):
            neg_word = match.group(1) or match.group(3)
            action_phrase = (match.group(2) or match.group(4) or "").strip()
            if not action_phrase or len(action_phrase.split()) < 2:
                continue

            action_lower = action_phrase.lower()
            # If the forbidden action appears in optimized prompt, ensure it is still negated
            if action_lower in opt_lower:
                act_idx = opt_lower.find(action_lower)
                window_start = max(0, act_idx - 40)
                prefix_window = opt_lower[window_start:act_idx]
                has_neg = any(neg in prefix_window for neg in ("not", "don't", "dont", "never", "cannot", "can't", "without", "no", "avoid"))
                if not has_neg:
                    msg = (
                        f"Optimization reversed prohibition constraint ('{neg_word} {action_phrase}'); "
                        f"safe anonymized prompt was returned as fallback."
                    )
                    logger.warning(msg)
                    return anonymized_prompt, [msg], True

        # Check 6: Exact numeric constraints and limits
        anon_numerics = set(m.group(0).lower() for m in _NUMERIC_CONSTRAINT_RE.finditer(anonymized_prompt))
        for num_term in anon_numerics:
            # Check if digits in constraint are preserved
            digits = re.findall(r"\d+", num_term)
            if digits and not all(d in optimized_prompt for d in digits):
                msg = (
                    f"Optimization dropped numeric constraint ('{num_term}'); "
                    f"safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

        # Check 7: Required programming languages and frameworks
        anon_langs = set(m.group(0).lower() for m in _LANGUAGES_RE.finditer(anonymized_prompt))
        for lang in anon_langs:
            base_lang = lang.split()[0]
            if base_lang not in opt_lower:
                msg = (
                    f"Optimization removed required programming language/technology ('{lang}'); "
                    f"safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

        # Check 8: Output format requirements
        anon_formats = set(m.group(0).lower() for m in _FORMAT_RE.finditer(anonymized_prompt))
        for fmt in anon_formats:
            fmt_core = "bullet" if "bullet" in fmt else fmt
            if fmt_core not in opt_lower:
                msg = (
                    f"Optimization removed output format requirement ('{fmt}'); "
                    f"safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

        # Check 9: Technical generic types (e.g. Map<Integer, Integer>, List<String>)
        anon_generics = set(_GENERIC_TYPE_RE.findall(anonymized_prompt))
        for generic in anon_generics:
            if generic not in optimized_prompt:
                msg = (
                    f"Optimization altered technical generic type ('{generic}'); "
                    f"safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

        # Check 10: Complexity notation (e.g. O(n), O(log n))
        anon_complexities = set(_COMPLEXITY_RE.findall(anonymized_prompt))
        for comp in anon_complexities:
            if comp.lower() not in opt_lower:
                msg = (
                    f"Optimization removed complexity notation ('{comp}'); "
                    f"safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

        # Check 11: Instruction constraints (e.g. no external libraries, preserve order)
        anon_constraints = set(m.group(0).lower() for m in _INSTRUCTION_CONSTRAINTS_RE.finditer(anonymized_prompt))
        for constraint in anon_constraints:
            if constraint not in opt_lower:
                msg = (
                    f"Optimization removed instruction constraint ('{constraint}'); "
                    f"safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

        # Check 12: Core domain / OOP concepts preservation
        anon_oop = [c for c in _CORE_OOP_CONCEPTS if re.search(r"\b" + re.escape(c) + r"\b", anon_lower)]
        if anon_oop:
            missing_oop = [c for c in anon_oop if not re.search(r"\b" + re.escape(c) + r"\b", opt_lower)]
            if missing_oop:
                msg = (
                    f"Optimization dropped required core concept(s): {sorted(missing_oop)}; "
                    f"safe anonymized prompt was returned as fallback."
                )
                logger.warning(msg)
                return anonymized_prompt, [msg], True

        # Check 13: Explicit deliverable requirements preservation
        for deliv_name, req_pat, match_pat in _EXPLICIT_DELIVERABLES:
            if req_pat.search(anonymized_prompt):
                if not match_pat.search(optimized_prompt):
                    msg = (
                        f"Optimization removed requested deliverable: '{deliv_name}'; "
                        f"safe anonymized prompt was returned as fallback."
                    )
                    logger.warning(msg)
                    return anonymized_prompt, [msg], True

        return optimized_prompt, warnings, False

    def validate(
        self,
        anonymized_prompt: str,
        optimized_prompt: str,
    ) -> str:
        """
        Validate candidate prompt and return safe validated string.
        (Maintains backward compatibility with legacy calls).
        """
        result, _, _ = self.validate_prompt(anonymized_prompt, optimized_prompt)
        return result
