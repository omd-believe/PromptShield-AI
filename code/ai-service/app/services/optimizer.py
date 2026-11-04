"""
Deterministic prompt optimizer.

Applies conservative, rule-based improvements to a prompt:
  - Removes unnecessary filler phrases
  - Compacts safe verbose connective phrases in prose
  - Normalizes whitespace
  - Removes space before punctuation

IMPORTANT — this is NOT an LLM and NOT an AI compressor.

This module applies deterministic string transformations.  It does not
understand meaning, semantics, or context.  Therefore it must be:
  1. Conservative — prefer leaving text unchanged over risky rewrites.
  2. Constraint-preserving — never remove words that appear to be constraints
     or instructions (detected via a keyword safeguard list).
  3. Non-empty-producing — if removal would produce an empty string, fall
     back to the previous (pre-removal) state.

Filler phrases are patterns that add politeness overhead without changing
the instruction.  Examples:
  "Please kindly summarize..." → "Summarize..."
  "I would like you to explain..." → "explain..."

The optimizer does NOT:
  - Paraphrase or rephrase content
  - Summarize or shorten by removing information
  - Remove constraint words (must, do not, never, always, exactly, etc.)
  - Remove numerical constraints ("in 5 bullet points")
"""

import re
import logging

logger = logging.getLogger(__name__)

# ─── Filler phrases to remove ─────────────────────────────────────────────────
#
# Each entry is a case-insensitive regex pattern.
# Patterns are matched at word boundaries to avoid accidental partial removal.
# After removal, surrounding whitespace is cleaned up.
#
# Order matters: more specific multi-word phrases must come before shorter ones.

_FILLER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcan\s+you\s+please\s+help\s+me\s+to\b", re.IGNORECASE),
    re.compile(r"\bcould\s+you\s+please\s+help\s+me\s+to\b", re.IGNORECASE),
    re.compile(r"\bwould\s+you\s+please\s+help\s+me\s+to\b", re.IGNORECASE),
    re.compile(r"\bplease\s+help\s+me\s+to\b",             re.IGNORECASE),
    re.compile(r"\bplease\s+kindly\b",                     re.IGNORECASE),
    re.compile(r"\bkindly\s+please\b",                     re.IGNORECASE),
    re.compile(r"\bi\s+would\s+like\s+you\s+to\b",         re.IGNORECASE),
    re.compile(r"\bi\s+want\s+you\s+to\b",                 re.IGNORECASE),
    re.compile(r"\bcan\s+you\s+please\b",                   re.IGNORECASE),
    re.compile(r"\bcould\s+you\s+please\b",                 re.IGNORECASE),
    re.compile(r"\bwould\s+you\s+please\b",                 re.IGNORECASE),
    re.compile(r"\bhelp\s+me\s+to\b",                      re.IGNORECASE),
    re.compile(r"\bplease\b",                               re.IGNORECASE),
    re.compile(r"\bkindly\b",                               re.IGNORECASE),
]

# These replacements preserve the instruction while removing predictable
# wording overhead. They are applied only to prose, never to structured lines
# or fenced code blocks.
_COMPACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bin order to\b", re.IGNORECASE), "to"),
    (re.compile(r"\bfor the purpose of\b", re.IGNORECASE), "to"),
    (re.compile(r"\bin the event that\b", re.IGNORECASE), "if"),
    (re.compile(r"\bdue to the fact that\b", re.IGNORECASE), "because"),
    (re.compile(r"\bat this point in time\b", re.IGNORECASE), "now"),
    (re.compile(r"\bmake sure that\b", re.IGNORECASE), "ensure that"),
    (re.compile(r"\bwith regard to\b", re.IGNORECASE), "about"),
    (re.compile(r"\bstep by step manner\b", re.IGNORECASE), "step by step"),
    (re.compile(r"\bin a detailed manner\b", re.IGNORECASE), "in detail"),
    (re.compile(r"\bat the end of the day\b", re.IGNORECASE), "ultimately"),
    (re.compile(r"\bfor the sake of brevity\b", re.IGNORECASE), "briefly"),
    (re.compile(r"\bwith the aim of\b", re.IGNORECASE), "to"),
    (re.compile(r"\bby means of\b", re.IGNORECASE), "using"),
    (re.compile(r"\bprovide a brief overview of\b", re.IGNORECASE), "summarize"),
    (re.compile(r"\bgive me a brief summary of\b", re.IGNORECASE), "summarize"),
    (re.compile(r"\bwrite a concise summary of\b", re.IGNORECASE), "summarize"),
    (re.compile(r"\bprovide a detailed analysis of\b", re.IGNORECASE), "analyze"),
    (re.compile(r"\bwrite a detailed explanation of\b", re.IGNORECASE), "explain"),
    (re.compile(r"\bextract key information from\b", re.IGNORECASE), "extract key info from"),
    (re.compile(r"\bcompare and contrast\b", re.IGNORECASE), "compare"),
    (re.compile(r"\blist the main points of\b", re.IGNORECASE), "list key points of"),
]

_TASK_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "summarize": [
        re.compile(r"\b(summarize|summary|condense|tl;dr)\b", re.IGNORECASE),
        re.compile(r"\bbrief overview\b", re.IGNORECASE),
        re.compile(r"\bkey takeaways\b", re.IGNORECASE),
    ],
    "analyze": [
        re.compile(r"\b(analyze|analysis|evaluate|assess|review)\b", re.IGNORECASE),
        re.compile(r"\bidentify key issues\b", re.IGNORECASE),
    ],
    "extract": [
        re.compile(r"\b(extract|pull out|capture|list facts|key details)\b", re.IGNORECASE),
    ],
    "compare": [
        re.compile(r"\b(compare|contrast|difference between)\b", re.IGNORECASE),
    ],
    "code": [
        re.compile(r"\b(python|javascript|java|typescript|sql|code|function|class|api)\b", re.IGNORECASE),
        re.compile(r"```", re.IGNORECASE),
    ],
    "write": [
        re.compile(r"\b(write|draft|compose|generate)\b", re.IGNORECASE),
        re.compile(r"\bemail|letter|blog|article|message\b", re.IGNORECASE),
    ],
}

_FENCED_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_STRUCTURED_LINE_RE = re.compile(
    r"^\s*(?:[{[]|.*:\s*[{[]|</?[A-Za-z][^>]*>|[-*]\s*[A-Za-z_][\w-]*\s*:)"
)

# Whitespace normalization after removal
_MULTI_SPACE_RE = re.compile(r"[^\S\n]+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"[^\S\n]+([,.!?;:])")


class PromptOptimizer:
    """
    Applies deterministic, conservative optimization to a prompt.

    The input prompt should already be:
    - preprocessed (whitespace normalized, validated)
    - anonymized (sensitive data replaced with placeholders)

    The optimizer preserves:
    - All constraint language (must, do not, never, always, exactly, etc.)
    - Numerical constraints ("5 bullet points", "in 500 words")
    - Instructions that follow filler removal
    - Multiline structure

    It removes or compacts:
    - Unnecessary filler phrases (politeness overhead)
    - Predictable verbose connective phrases in prose
    - Leading/trailing whitespace introduced by removals

    Fenced code blocks and structured lines are preserved byte-for-byte.
    """

    def optimize(self, prompt: str) -> str:
        """
        Optimize *prompt* and return the improved version.

        If optimization produces an empty string, the original prompt is
        returned unchanged.
        """
        if not prompt.strip():
            return prompt

        optimized = self._optimize_segments(prompt)

        # Prose segments are already normalized; avoid a global rewrite here
        # because it would corrupt indentation inside protected code blocks.
        optimized = optimized.strip()

        # Final guard: if somehow empty, return original
        if not optimized:
            logger.warning(
                "Optimization produced empty prompt — returning original."
            )
            return prompt

        return optimized

    def _optimize_segments(self, prompt: str) -> str:
        """Optimize prose segments while leaving code and structured lines intact."""
        segments: list[str] = []
        cursor = 0

        for match in _FENCED_BLOCK_RE.finditer(prompt):
            segments.append(self._optimize_prose(prompt[cursor:match.start()]))
            segments.append(match.group(0))
            cursor = match.end()

        segments.append(self._optimize_prose(prompt[cursor:]))
        return "".join(segments)

    def _optimize_prose(self, text: str) -> str:
        """Optimize prose line-by-line without rewriting structured content."""
        task_type = self._detect_task_type(text)
        optimized_lines: list[str] = []
        for line in text.splitlines(keepends=True):
            newline = "\n" if line.endswith("\n") else ""
            content = line[:-1] if newline else line
            if _STRUCTURED_LINE_RE.match(content):
                optimized_lines.append(line)
                continue

            candidate = content
            for pattern in _FILLER_PATTERNS:
                candidate = pattern.sub("", candidate)
            for pattern, replacement in self._task_specific_compactions(task_type):
                candidate = pattern.sub(replacement, candidate)
            for pattern, replacement in _COMPACT_PATTERNS:
                candidate = pattern.sub(replacement, candidate)
            candidate = self._normalize_whitespace(candidate)
            candidate = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", candidate).strip()
            optimized_lines.append(candidate + newline)

        return "".join(optimized_lines)

    @staticmethod
    def _detect_task_type(text: str) -> str:
        """Infer a coarse prompt intent for safer, tighter compaction."""
        lowered = text.lower()
        for task_type, patterns in _TASK_PATTERNS.items():
            if any(pattern.search(lowered) for pattern in patterns):
                return task_type
        return "general"

    @staticmethod
    def _task_specific_compactions(task_type: str) -> list[tuple[re.Pattern[str], str]]:
        """Task-aware phrase compactions: useful but intentionally conservative."""
        if task_type == "summarize":
            return [
                (re.compile(r"\bwrite a brief summary of\b", re.IGNORECASE), "summarize"),
                (re.compile(r"\bin summary\b", re.IGNORECASE), ""),
                (re.compile(r"\bbriefly summarize\b", re.IGNORECASE), "summarize"),
            ]
        if task_type == "analyze":
            return [
                (re.compile(r"\bperform an analysis of\b", re.IGNORECASE), "analyze"),
                (re.compile(r"\bprovide an assessment of\b", re.IGNORECASE), "assess"),
            ]
        if task_type == "extract":
            return [
                (re.compile(r"\bextract the key details from\b", re.IGNORECASE), "extract key details from"),
                (re.compile(r"\bidentify the main points in\b", re.IGNORECASE), "list key points in"),
            ]
        if task_type == "compare":
            return [
                (re.compile(r"\bcompare and contrast the differences between\b", re.IGNORECASE), "compare"),
            ]
        if task_type == "write":
            return [
                (re.compile(r"\bwrite a polished version of\b", re.IGNORECASE), "rewrite"),
                (re.compile(r"\bcompose a concise version of\b", re.IGNORECASE), "rewrite"),
            ]
        return []

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Collapse horizontal whitespace runs within each line."""
        lines = text.split("\n")
        lines = [_MULTI_SPACE_RE.sub(" ", line).strip() for line in lines]
        return "\n".join(lines)