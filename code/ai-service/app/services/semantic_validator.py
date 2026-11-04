"""
Lexical similarity validation for deterministic prompt optimization.

NOTE: This score is a lexical overlap heuristic (combining Jaccard token set
overlap and SequenceMatcher sequence ratio). It does NOT claim deep natural
language semantic understanding or true semantic equivalence.
"""

import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Stopwords are removed when measuring semantic drift so filler words and
# repeated politeness phrases do not artificially reduce the score.
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "he",
    "i",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "should",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "was",
    "we",
    "with",
    "you",
    "your",
}

_PLACEHOLDER_RE = re.compile(r"\[[A-Z_]+(?:_\d+)?\]")


class SemanticValidator:
    """Scores how much an optimized prompt preserves the original meaning."""

    @staticmethod
    def _normalize(text: str) -> list[str]:
        if not text:
            return []

        normalized = text.lower()
        normalized = _PLACEHOLDER_RE.sub(" [placeholder] ", normalized)
        normalized = re.sub(r"[^a-z0-9\s\[\]]+", " ", normalized)

        tokens = [token for token in normalized.split() if len(token) > 1 and token not in _STOPWORDS]
        return tokens

    def score(self, original_prompt: str, optimized_prompt: str) -> float:
        """Return semantic similarity on a 0–100 scale."""
        if not original_prompt and not optimized_prompt:
            return 100.0
        if not original_prompt or not optimized_prompt:
            return 0.0

        original_tokens = self._normalize(original_prompt)
        optimized_tokens = self._normalize(optimized_prompt)

        if not original_tokens and not optimized_tokens:
            return 100.0
        if not original_tokens or not optimized_tokens:
            return 0.0

        original_set = set(original_tokens)
        optimized_set = set(optimized_tokens)
        common_tokens = original_set & optimized_set

        # Asymmetric precision (fidelity: proportion of candidate tokens rooted in original)
        precision = len(common_tokens) / len(optimized_set) if optimized_set else 1.0
        # Recall (coverage: proportion of key original tokens retained)
        recall = len(common_tokens) / len(original_set) if original_set else 1.0

        original_text = " ".join(original_tokens)
        optimized_text = " ".join(optimized_tokens)
        sequence_ratio = SequenceMatcher(None, original_text, optimized_text).ratio()

        # Weighted combination: 40% precision (hallucination guard), 35% recall (instruction retention), 25% sequence order
        similarity = (0.40 * precision) + (0.35 * recall) + (0.25 * sequence_ratio)
        score = max(0.0, min(1.0, similarity)) * 100.0
        return round(score, 2)

    def validate(self, original_prompt: str, optimized_prompt: str, minimum_score: float = 50.0) -> bool:
        """Return True when the optimized prompt preserves enough meaning."""
        score = self.score(original_prompt, optimized_prompt)
        if score >= minimum_score:
            return True

        logger.warning(
            "Semantic similarity check failed: score=%.2f < %.2f",
            score,
            minimum_score,
        )
        return False
