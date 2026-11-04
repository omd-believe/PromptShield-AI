"""
Preprocessing service — normalizes raw prompt text before NLP processing.

Purpose: safe normalization only.
This stage does NOT rewrite meaning, remove instructions, or compress content.
"""

import re
import unicodedata

from app import config


class Preprocessor:
    """
    Cleans and normalizes a raw prompt string.

    Stages applied (in order):
    1. Validate input (empty, oversized)
    2. Unicode normalization (NFC)
    3. Normalize line endings
    4. Normalize whitespace (collapse runs, strip edges)
    5. Remove repeated punctuation (e.g. "!!!" → "!")

    Returns the cleaned string.  Raises ValueError for invalid input.
    """

    # Punctuation characters where consecutive repetition is meaningless
    _REPEATED_PUNCT_RE = re.compile(r"([!?.,;])\1+")
    _FENCED_BLOCK_RE = re.compile(r"```[\s\S]*?```")
    _STRUCTURED_LINE_RE = re.compile(
        r"^\s*(?:[{[]|.*:\s*[{[]|</?[A-Za-z][^>]*>|[-*]\s*[A-Za-z_][\w-]*\s*:)"
    )

    def clean(self, prompt: str) -> str:
        """
        Normalize *prompt* and return the cleaned string.

        Raises:
            ValueError: if prompt is empty or exceeds the configured max length.
        """
        if not isinstance(prompt, str):
            raise ValueError("Prompt must be a string.")

        # 1. Reject empty input
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        # 2. Reject oversized input before running any NLP
        if len(prompt) > config.MAX_PROMPT_LENGTH:
            raise ValueError(
                f"Prompt exceeds maximum allowed length of "
                f"{config.MAX_PROMPT_LENGTH} characters "
                f"(received {len(prompt)})."
            )

        # 3. Unicode NFC normalization — ensures consistent codepoint representation
        prompt = unicodedata.normalize("NFC", prompt)

        # 4. Normalize line endings to \n
        prompt = prompt.replace("\r\n", "\n").replace("\r", "\n")

        # 5–7. Normalize prose while preserving code and structured content.
        return self._clean_segments(prompt).strip()

    def _clean_segments(self, prompt: str) -> str:
        segments: list[str] = []
        cursor = 0
        for fenced in self._FENCED_BLOCK_RE.finditer(prompt):
            segments.append(self._clean_prose(prompt[cursor:fenced.start()]))
            segments.append(fenced.group(0))
            cursor = fenced.end()
        segments.append(self._clean_prose(prompt[cursor:]))
        return "".join(segments)

    def _clean_prose(self, text: str) -> str:
        """Normalize prose lines while preserving structured lines."""
        lines: list[str] = []
        blank_count = 0
        for line in text.split("\n"):
            if self._STRUCTURED_LINE_RE.match(line):
                lines.append(line)
                blank_count = 0
                continue
            normalized = re.sub(r"[^\S\n]+", " ", line).strip()
            if normalized == "":
                blank_count += 1
                if blank_count <= 1:
                    lines.append(normalized)
            else:
                blank_count = 0
                lines.append(self._REPEATED_PUNCT_RE.sub(r"\1", normalized))
        return "\n".join(lines)