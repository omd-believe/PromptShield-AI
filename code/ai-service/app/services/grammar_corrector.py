"""Conservative grammar and spelling cleanup for optimized prompts."""

import re
from spellchecker import SpellChecker

from app.services.technical_filter import TECHNICAL_VOCABULARY

# ── High-confidence explicit word corrections ─────────────────────────────────
_WORD_CORRECTIONS = {
    "hlleo": "hello",
    "teh": "the",
    "recieve": "receive",
    "seperate": "separate",
    "occured": "occurred",
    "becuase": "because",
    "dont": "don't",
    "cant": "can't",
    "wont": "won't",
    "doesnt": "doesn't",
    "isnt": "isn't",
    "shouldnt": "shouldn't",
}

# ── Protected vocabulary that must NEVER be modified by spell check ───────────
# 1. Negations, prohibitions, and strict constraint keywords
_PROTECTED_NEGATIONS_CONSTRAINTS = {
    "not", "never", "no", "none", "must", "exactly", "only", "cannot",
    "without", "stop", "halt", "refuse", "deny", "disallow", "prohibit",
    "prohibited", "prohibition", "prohibitions", "forbidden", "neither",
    "nor", "always", "avoid", "prevent", "reject", "exclude",
    "dont", "cant", "wont", "doesnt", "isnt", "shouldnt",
}

# 2. Security, authentication, cryptography, and prompt-injection instructions
_PROTECTED_SECURITY_TERMS = {
    "plaintext", "ciphertext", "untrusted", "trusted", "entrusted",
    "password", "passwords", "hash", "hashing", "hashed", "hashes",
    "authentication", "auth", "authorization", "authz", "encryption",
    "encrypted", "encrypt", "decryption", "decrypted", "decrypt",
    "secret", "secrets", "token", "tokens", "credential", "credentials",
    "key", "keys", "certificate", "certificates", "privilege", "privileges",
    "permission", "permissions", "vulnerability", "vulnerabilities",
    "exploit", "exploits", "payload", "payloads", "injection", "jailbreak",
    "bypass", "override", "sanitize", "sanitization", "safety", "breach",
    "leak", "leakage", "malicious", "unauthorized", "attacker", "attackers",
    "threat", "threats", "ignore", "reveal", "hidden", "system", "prompt",
    "prompts", "instruction", "instructions",
}

# 3. Common domain, programming, and technical keywords
_ADDITIONAL_TECHNICAL_TERMS = {
    "docstring", "docstrings", "aadhaar", "pan", "sha256", "jwt", "uuid",
    "regex", "postgresql", "postgres", "fastapi", "springdoc", "pydantic",
    "tiktoken", "endpoint", "endpoints", "dto", "dao", "entity", "repo",
    "repository", "json", "yaml", "yml", "xml", "csv", "url", "urls",
    "uri", "uris", "oauth", "bcrypt", "boolean", "integer", "hashmap",
    "treemap", "arraylist", "linkedlist", "api", "apis", "config",
    "datasource", "null", "undefined", "stream", "streams", "list", "map",
    "set", "queue", "stack", "generics", "generic", "string", "char",
    "byte", "short", "long", "float", "double", "class", "interface",
    "record", "enum", "complexity", "algorithm", "algorithms",
}

# Combine all protected words and include all individual tokens from TECHNICAL_VOCABULARY
_ALL_PROTECTED_WORDS = (
    _PROTECTED_NEGATIONS_CONSTRAINTS
    | _PROTECTED_SECURITY_TERMS
    | _ADDITIONAL_TECHNICAL_TERMS
)
for _term in TECHNICAL_VOCABULARY:
    _ALL_PROTECTED_WORDS.add(_term.lower())
    for _token in re.findall(r"[a-zA-Z]+", _term.lower()):
        _ALL_PROTECTED_WORDS.add(_token)

# ── Syntax preservation regexes ───────────────────────────────────────────────
_FENCED_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_QUOTED_TEXT_RE = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'')
_URL_RE = re.compile(r"\b(?:https?|ftp|file)://[^\s<>\"']+|\b/[\w\-./]+(?:\?[\w=&-]*)?")
_PLACEHOLDER_RE = re.compile(r"\[[A-Z_]+(?:_\d+)?\]")
_GENERIC_TYPE_RE = re.compile(r"\b[A-Za-z_]\w*<[^>\n]+>")
_COMPLEXITY_RE = re.compile(r"\bO\([^)\n]+\)", re.IGNORECASE)
_VERSION_RE = re.compile(r"\b[A-Za-z]+\s+\d+(?:\.\d+)*\b")
_METHOD_CALL_RE = re.compile(r"\b[A-Za-z_]\w*\s*\([^\)\n]*\)")
_DOT_NOTATION_RE = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b")
_STRUCTURED_LINE_RE = re.compile(
    r"^\s*(?:[{[]|.*:\s*[{[]|</?[A-Za-z][^>]*>|[-*]\s*[A-Za-z_][\w-]*\s*:)"
)
_WORD_RE = re.compile(r"\b[a-zA-Z]+\b")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"[ \t]+([,.!?;:])")
_PROTECTED_WORD_RE = re.compile(r"^[A-Z][A-Za-z]+$")


class GrammarCorrector:
    """Apply only high-confidence, meaning-preserving text corrections."""

    def __init__(self) -> None:
        self._spell_checker = SpellChecker(distance=2)
        # Register technical and security terms as valid words so they are never flagged as unknown
        self._spell_checker.word_frequency.load_words(_ALL_PROTECTED_WORDS)

    def correct(self, prompt: str) -> dict[str, object]:
        corrections: list[str] = []

        def replace_word(match: re.Match[str]) -> str:
            original = match.group(0)
            original_lower = original.lower()

            # Guard 1: Never modify protected words (security, negation, constraints, tech)
            if original_lower in _ALL_PROTECTED_WORDS:
                return original

            # Guard 2: High-confidence explicit correction
            replacement = _WORD_CORRECTIONS.get(original_lower)
            if replacement is None:
                replacement = self._spell_correction(original)
            if replacement is None:
                return original

            # Guard 3: Double-check candidate doesn't violate protected vocabulary
            if replacement.lower() in _ALL_PROTECTED_WORDS and original_lower != replacement.lower():
                # E.g., don't let any typo mutate into a security keyword unless explicitly mapped
                pass

            if original[0].isupper():
                replacement = replacement.capitalize()
            corrections.append(f"{original} → {replacement}")
            return replacement

        # Segment prompt into protected regions (code, quotes, URLs, placeholders,
        # generics, complexity notation, method calls, versions)
        # and unquoted prose lines that can be checked safely.
        protected_intervals: list[tuple[int, int]] = []
        for regex in (
            _FENCED_BLOCK_RE,
            _INLINE_CODE_RE,
            _QUOTED_TEXT_RE,
            _URL_RE,
            _PLACEHOLDER_RE,
            _GENERIC_TYPE_RE,
            _COMPLEXITY_RE,
            _VERSION_RE,
            _METHOD_CALL_RE,
            _DOT_NOTATION_RE,
        ):
            for match in regex.finditer(prompt):
                protected_intervals.append((match.start(), match.end()))

        # Merge overlapping/adjacent intervals
        protected_intervals.sort()
        merged_intervals: list[tuple[int, int]] = []
        for start, end in protected_intervals:
            if not merged_intervals:
                merged_intervals.append((start, end))
            else:
                last_start, last_end = merged_intervals[-1]
                if start <= last_end:
                    merged_intervals[-1] = (last_start, max(last_end, end))
                else:
                    merged_intervals.append((start, end))

        segments: list[str] = []
        cursor = 0
        for p_start, p_end in merged_intervals:
            if p_start > cursor:
                segments.append(
                    self._correct_prose(prompt[cursor:p_start], replace_word)
                )
            segments.append(prompt[p_start:p_end])
            cursor = p_end

        if cursor < len(prompt):
            segments.append(self._correct_prose(prompt[cursor:], replace_word))

        corrected = "".join(segments)

        # ── Post-correction validation step ────────────────────────────────────
        # Detect critical-term changes or damaged constraints and reject unsafe corrections
        def extract_critical_tokens(text: str) -> list[str]:
            tokens = []
            for m in _WORD_RE.finditer(text):
                w = m.group(0).lower()
                if w in _ALL_PROTECTED_WORDS:
                    tokens.append(w)
            return tokens

        orig_critical = extract_critical_tokens(prompt)
        corrected_critical = extract_critical_tokens(corrected)

        unsafe_correction = False
        if orig_critical != corrected_critical:
            unsafe_correction = True

        if not unsafe_correction:
            for regex in (
                _GENERIC_TYPE_RE,
                _COMPLEXITY_RE,
                _PLACEHOLDER_RE,
            ):
                if regex.findall(prompt) != regex.findall(corrected):
                    unsafe_correction = True
                    break

        if unsafe_correction:
            # Safely fall back to the last safe version (original input prompt)
            return {
                "prompt": prompt,
                "corrections": [],
                "changed": False,
                "safety_reverted": True,
            }

        return {
            "prompt": corrected,
            "corrections": corrections,
            "changed": corrected != prompt,
        }

    @staticmethod
    def _correct_prose(text: str, replace_word) -> str:
        """Correct prose lines while preserving structured content exactly."""
        lines: list[str] = []
        for line in text.splitlines(keepends=True):
            newline = "\n" if line.endswith("\n") else ""
            content = line[:-1] if newline else line
            if _STRUCTURED_LINE_RE.match(content):
                lines.append(line)
                continue
            corrected = _WORD_RE.sub(replace_word, content)
            corrected = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", corrected)
            lines.append(corrected + newline)
        return "".join(lines)

    def _spell_correction(self, word: str) -> str | None:
        """Return a safe dictionary correction, or None when uncertain."""
        if len(word) < 4 or _PROTECTED_WORD_RE.fullmatch(word):
            return None

        normalized = word.lower()
        if normalized in _ALL_PROTECTED_WORDS:
            return None

        if normalized not in self._spell_checker.unknown([normalized]):
            return None

        candidate = self._spell_checker.correction(normalized)
        if not candidate or candidate == normalized:
            return None

        candidate_lower = candidate.lower()
        # Never allow spell correction to flip to or from a security or negation word
        if candidate_lower in _ALL_PROTECTED_WORDS:
            return None

        # Only accept very close edits (distance <= 2 and similar length)
        if abs(len(candidate) - len(normalized)) > 2:
            return None
        return candidate
