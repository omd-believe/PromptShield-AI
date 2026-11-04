"""Model-aware token counting for prompt metrics."""

import logging

import tiktoken

from app import config

logger = logging.getLogger(__name__)


class TokenCounter:
    """Count tokens using the configured OpenAI-compatible encoding."""

    def __init__(self, model: str | None = None) -> None:
        model_name = model or config.TOKENIZER_MODEL
        try:
            self._encoding = tiktoken.encoding_for_model(model_name)
            self.encoding_name = self._encoding.name
        except KeyError:
            logger.warning(
                "Tokenizer model '%s' is unknown; using cl100k_base encoding.",
                model_name,
            )
            self._encoding = tiktoken.get_encoding("cl100k_base")
            self.encoding_name = self._encoding.name

    def count(self, text: str) -> int:
        """Return the number of tokens in *text*."""
        if not text or not text.strip():
            return 0
        return len(self._encoding.encode(text))

    def reduction_percentage(self, original: int, optimized: int) -> float:
        """Calculate token reduction percentage clamped to 0.0–100.0."""
        if original <= 0:
            return 0.0

        raw = ((original - optimized) / original) * 100
        return round(min(max(raw, 0.0), 100.0), 2)
