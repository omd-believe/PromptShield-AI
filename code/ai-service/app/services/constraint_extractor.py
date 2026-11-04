"""
Deterministic constraint and critical token extractor for PromptShield AI.

Identifies security requirements, prohibitions/negations, required output formats,
technical identifiers, numeric constraints, and privacy placeholders before compression.
Extracted keywords are fed to LLMLingua-2's force_tokens mechanism to ensure they are
never pruned during compression.
"""

import re
from typing import Sequence

from app.services.quality_validator import (
    _PLACEHOLDER_RE,
    _SECURITY_RE,
    _NEGATION_RE,
    _NUMERIC_CONSTRAINT_RE,
    _LANGUAGES_RE,
    _FORMAT_RE,
    _GENERIC_TYPE_RE,
    _COMPLEXITY_RE,
    _INSTRUCTION_CONSTRAINTS_RE,
    _CORE_OOP_CONCEPTS,
    _EXPLICIT_DELIVERABLES,
    _PROHIBITION_CLAUSE_RE,
)


class ConstraintExtractor:
    """Extracts critical constraint tokens from a prompt to protect during compression."""

    @staticmethod
    def extract_critical_tokens(prompt: str, max_tokens: int = 100) -> list[str]:
        """
        Extract tokens and phrases that must be forcibly preserved during compression.

        Returns:
            A deduplicated list of tokens suitable for LLMLingua-2's force_tokens parameter.
        """
        if not prompt or not prompt.strip():
            return []

        forced: list[str] = []
        seen: set[str] = set()

        def _add(token: str) -> None:
            clean = token.strip()
            if not clean:
                return
            clean_lower = clean.lower()
            if clean_lower not in seen and len(forced) < max_tokens:
                seen.add(clean_lower)
                forced.append(clean)

        # 1. Privacy placeholders ([PERSON], [EMAIL], [PERSON_1], etc.)
        for ph in _PLACEHOLDER_RE.findall(prompt):
            _add(ph)

        # 2. Security-critical instructions
        for match in _SECURITY_RE.finditer(prompt):
            _add(match.group(0))

        # 3. Negations, prohibitions, and complete prohibition clauses
        for match in _NEGATION_RE.finditer(prompt):
            _add(match.group(0))

        for match in _PROHIBITION_CLAUSE_RE.finditer(prompt):
            # Add full clause if concise
            full_clause = match.group(0).strip(" .,;\n")
            if len(full_clause.split()) <= 4:
                _add(full_clause)
            action = (match.group(2) or match.group(4) or "").strip()
            if action:
                for w in action.split():
                    if len(w) > 2 and w.lower() not in {"the", "and", "for", "with"}:
                        _add(w)

        # 4. Programming languages & frameworks
        for match in _LANGUAGES_RE.finditer(prompt):
            _add(match.group(0))

        # 5. Output format requirements (JSON, table, markdown, etc.)
        for match in _FORMAT_RE.finditer(prompt):
            _add(match.group(0))

        # 6. Generic types (Map, Integer, List, String, etc.)
        for match in _GENERIC_TYPE_RE.finditer(prompt):
            _add(match.group(0))
            # Also add individual words inside generic type
            for word in re.findall(r"[A-Za-z_]\w*", match.group(0)):
                _add(word)

        # 7. Complexity notation (O(n), O(1), etc.)
        for match in _COMPLEXITY_RE.finditer(prompt):
            _add(match.group(0))

        # 8. Core OOP concepts
        prompt_lower = prompt.lower()
        for concept in _CORE_OOP_CONCEPTS:
            if re.search(r"\b" + re.escape(concept) + r"\b", prompt_lower):
                _add(concept)

        # 9. Instruction constraints (no external libraries, etc.)
        for match in _INSTRUCTION_CONSTRAINTS_RE.finditer(prompt):
            _add(match.group(0))

        # 10. Deliverable key terms
        for deliv_name, req_pat, _ in _EXPLICIT_DELIVERABLES:
            if req_pat.search(prompt):
                # Add deliverable keywords
                for word in deliv_name.split():
                    _add(word)

        # 11. Numeric constraint tokens (e.g. "3", "5 examples", "200 words")
        for match in _NUMERIC_CONSTRAINT_RE.finditer(prompt):
            full = match.group(0).strip()
            _add(full)
            # Also add the bare digit to ensure it survives token classification
            import re as _re
            digit = _re.match(r"\d+", full)
            if digit:
                _add(digit.group(0))

        return forced[:max_tokens]


constraint_extractor = ConstraintExtractor()
