"""
Regex-based privacy detector.

Detects sensitive data using compiled regular expressions:
  - EMAIL
  - PHONE  (Indian mobile numbers)
  - PAN    (Indian Permanent Account Number)
  - AADHAAR (Indian 12-digit UID)
  - API_KEY (common key patterns)
  - DATE_OF_BIRTH (dates explicitly introduced as a birth date)
  - BANK_ACCOUNT (account numbers explicitly introduced as an account number)
  - CREDIT_CARD (Luhn-valid payment card numbers)
  - IP_ADDRESS (valid IPv4 addresses)
  - ADDRESS (context-labelled postal addresses)
  - PASSPORT (context-labelled passport numbers)
  - SSN, DRIVER_LICENSE, UK_NINO, CANADIAN_SIN, IBAN and EU_TAX_ID
    (context-labelled identifiers; common English, Spanish, French, German,
    Hindi and selected Russian labels are supported)
  - JWT, PRIVATE_KEY, DATABASE_URL, CLOUD_CREDENTIAL, WEBHOOK_SECRET
    and GENERIC_SECRET (credential and secret formats)

Design principles:
- Each pattern is word-boundary anchored to reduce false positives.
- Patterns are compiled once at class definition time.
- Detection and anonymization are separate methods.
- The class is stateless and safe to share across requests.
"""

import math
import re
from collections import Counter
from typing import NamedTuple


class RegexMatch(NamedTuple):
    text: str
    label: str
    start: int
    end: int


class PrivacyDetector:
    """
    Detects and anonymizes regex-defined sensitive data categories.

    This class is intentionally conservative:
    - It prefers avoiding false positives over exhaustive coverage.
    - It does NOT claim to detect every possible secret format.
    """

    # ── Pattern definitions ────────────────────────────────────────────────────
    #
    # EMAIL
    #   Standard RFC-5321 simplified form.  Word-boundary anchor prevents
    #   matching inside URLs that already contain @.
    #
    # PHONE (Indian)
    #   Matches:
    #     9876543210          (bare 10-digit starting with 6-9)
    #     +91 9876543210      (ISD prefix with space)
    #     +91-9876543210      (ISD prefix with hyphen)
    #     +919876543210       (ISD prefix no separator)
    #   \b anchors prevent matching digits that are part of longer numbers.
    #
    # PAN (Indian)
    #   Exactly: AAAAA9999A — 5 uppercase letters, 4 digits, 1 uppercase letter.
    #   \b anchors ensure we don't match substrings of longer tokens.
    #
    # AADHAAR
    #   12-digit number in groups of 4, separated by space or hyphen,
    #   or written contiguously (Aadhaar never starts with 0 or 1).
    #   Format: 1234 5678 9012  or  1234-5678-9012  or  234567890123
    #   Anchored to avoid matching longer digit strings.
    #
    # API_KEY
    #   Conservative: only well-known prefixed patterns.
    #     sk-<20+ alphanum/dash/underscore>   (OpenAI-style)
    #     AIza<20+ alphanum/dash/underscore>  (Google API key style)
    #   Deliberately NOT a catch-all for arbitrary long hex strings, which
    #   would produce too many false positives.

    _PATTERNS: dict[str, re.Pattern[str]] = {
        "EMAIL": re.compile(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
        ),
        "PHONE": re.compile(
            r"(?<!\d)"
            r"(?:\+91[\s\-]?)?"
            r"[6-9]\d{9}"
            r"(?!\d)"
        ),
        "PAN": re.compile(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
        ),
        "AADHAAR": re.compile(
            r"\b(?:\d{4}[\s\-]\d{4}[\s\-]\d{4}|[2-9]\d{11})\b"
            r"(?![\s\-]\d)"
        ),
        "API_KEY": re.compile(
            r"\b(?:sk-[A-Za-z0-9_\-]{20,}|AIza[A-Za-z0-9_\-]{20,})\b"
        ),
        "CREDIT_CARD": re.compile(
            r"(?<!\d)(?:\d{4}(?:[ -]?\d{4}){2,4})(?!\d)"
        ),
        "IP_ADDRESS": re.compile(
            r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"
        ),
        "JWT": re.compile(
            r"\beyJ[A-Za-z0-9_-]{8,}\."
            r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
        ),
        "PRIVATE_KEY": re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
            r"[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        ),
        "DATABASE_URL": re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
            r"[^\s\"'<>]+",
            re.IGNORECASE,
        ),
        "CLOUD_CREDENTIAL": re.compile(
            r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
            r"|\b(?:ghp|github_pat|glpat)-[A-Za-z0-9_]{20,}\b"
            r"|\bxox[baprs]-[A-Za-z0-9-]{20,}\b"
        ),
    }

    # Context is required for these formats because dates and long numbers
    # commonly occur in harmless prompts.
    _CONTEXT_PATTERNS: dict[str, re.Pattern[str]] = {
        "DATE_OF_BIRTH": re.compile(
            r"(?i)(?:\b(?:dob|date\s+of\s+birth|birth\s+date)|"
            r"\bfecha\s+de\s+nacimiento|"
            r"\bdate\s+de\s+naissance|"
            r"\bgeburtsdatum|"
            r"\bfecha\s+de\s+nacimiento|"
            r"\bजन्म\s+तिथि|जन्मदिन)\s*"
            r"(?:is|:|-)?\s*"
            r"(?P<value>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
            r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|"
            r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b"
        ),
        "BANK_ACCOUNT": re.compile(
            r"(?i)(?:\b(?:bank\s+)?(?:account|a/c)|"
            r"\bcuenta\s+bancaria|\bcompte\s+bancaire|"
            r"\bbankverbindung|\bबैंक\s+खाता)\s*"
            r"(?:number|no\.?|#|número|numero|numéro|nummer|संख्या)?\s*"
            r"(?:is|:|-)?\s*(?P<value>\d{9,18})\b"
        ),
        "ADDRESS": re.compile(
            r"(?i)(?:\b(?:home|postal|mailing|residential)?\s*address|"
            r"\bdirección|adresse|anschrift|पता)\s*"
            r"(?:is|:|-)\s*(?P<value>\d{1,5}[A-Za-z]?\s+"
            r"[A-Za-z0-9][A-Za-z0-9 .,'/#-]{4,79}?)(?=\s*(?:[,;.]|$))"
        ),
        "PASSPORT": re.compile(
            r"(?i)(?:\bpassport|\bpasaporte|\bпаспорта|\bपासपोर्ट)\s*"
            r"(?:number|no\.?|#|número|numero|numéro|номер|संख्या)?\s*"
            r"(?:is|:|-)?\s*"
            r"(?P<value>[A-Z]\d{7})\b"
        ),
        "SSN": re.compile(
            r"(?i)(?:\b(?:social\s+security|ssn)|"
            r"\bseguro\s+social|\bsécurité\s+sociale|\bсоциального\s+страхования)\s*"
            r"(?:number|no\.?|#)?\s*(?:is|:|-)?\s*"
            r"(?P<value>(?!000|666|9\d{2})\d{3}[- ]\d{2}[- ]\d{4})\b"
        ),
        "DRIVER_LICENSE": re.compile(
            r"(?i)(?:\b(?:driver'?s?|driving)\s+licen[cs]e|"
            r"\blicencia\s+de\s+conducir|\bpermis\s+de\s+conduire|"
            r"\bführerschein|\bड्राइविंग\s+लाइसेंस)\s*"
            r"(?:number|no\.?|#|id)?\s*(?:is|:|-)?\s*"
            r"(?P<value>[A-Z0-9][A-Z0-9-]{4,13})\b"
        ),
        "UK_NINO": re.compile(
            r"(?i)\b(?:national\s+insurance|nino)\s*"
            r"(?:number|no\.?|#)?\s*(?:is|:|-)?\s*"
            r"(?P<value>[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]"
            r"\d{6}[A-D])\b"
        ),
        "CANADIAN_SIN": re.compile(
            r"(?i)\b(?:canadian\s+)?(?:sin|social\s+insurance)\s*"
            r"(?:number|no\.?|#)?\s*(?:is|:|-)?\s*"
            r"(?P<value>\d{3}[- ]\d{3}[- ]\d{3})\b"
        ),
        "IBAN": re.compile(
            r"(?i)\b(?:iban|international\s+bank\s+account)\s*"
            r"(?:number|no\.?|#)?\s*(?:is|:|-)?\s*"
            r"(?P<value>[A-Z]{2}\d{2}(?:[\s-]?[A-Z0-9]){11,30})\b"
        ),
        "EU_TAX_ID": re.compile(
            r"(?i)\b(?:vat|tax)\s*(?:identification|id|number|no\.?)?\s*"
            r"(?:is|:|-)?\s*(?P<value>"
            r"(?:ATU\d{8}|BE0?\d{9,10}|BG\d{9,10}|CY\d{8}[A-Z]|"
            r"CZ\d{8,10}|DE\d{9}|DK\d{8}|EE\d{9}|EL\d{9}|ES[A-Z0-9]\d{7}[A-Z0-9]|"
            r"FI\d{8}|FR[A-Z0-9]{2}\d{9}|GB\d{9}|HU\d{8}|IE\d{7}[A-Z]{1,2}|"
            r"IT\d{11}|LT\d{9,12}|LU\d{8}|LV\d{11}|MT\d{8}|NL\d{9}B\d{2}|"
            r"PL\d{10}|PT\d{9}|RO\d{2,10}|SE\d{12}|SI\d{8}|SK\d{10}))\b"
        ),
        "WEBHOOK_SECRET": re.compile(
            r"(?i)\b(?:webhook|signing)\s+(?:secret|token)\s*"
            r"(?:is|:|=|-)?\s*(?P<value>[A-Za-z0-9_\-]{20,})\b"
        ),
        "GENERIC_SECRET": re.compile(
            r"(?i)\b(?:api\s+)?(?:key|token|secret|password)\s*"
            r"(?:is|:|=|-)\s*(?P<value>[A-Za-z0-9_./+=\-]{20,})\b"
        ),
    }

    def detect(self, prompt: str) -> list[RegexMatch]:
        """
        Return all regex matches found in *prompt*.

        Returns a list of RegexMatch named tuples containing:
          - text:  the matched string
          - label: the category (EMAIL, PHONE, etc.)
          - start: character start offset in prompt
          - end:   character end offset in prompt

        Matches are returned in the order they appear in the text.
        """
        matches: list[RegexMatch] = []

        for label, pattern in self._PATTERNS.items():
            for m in pattern.finditer(prompt):
                value = m.group()
                if label == "CREDIT_CARD" and not self._is_luhn_valid(value):
                    continue
                if label == "IP_ADDRESS" and not self._is_valid_ipv4(value):
                    continue
                matches.append(
                    RegexMatch(
                        text=value,
                        label=label,
                        start=m.start(),
                        end=m.end(),
                    )
                )

        for label, pattern in self._CONTEXT_PATTERNS.items():
            if label == "GENERIC_SECRET":
                continue
            for m in pattern.finditer(prompt):
                value = m.group("value")
                if label == "CANADIAN_SIN" and not self._is_valid_canadian_sin(value):
                    continue
                if label == "IBAN" and not self._is_valid_iban(value):
                    continue
                start = m.start("value")
                matches.append(
                    RegexMatch(
                        text=value,
                        label=label,
                        start=start,
                        end=start + len(value),
                    )
                )

        # Generic secret detection is deliberately gated by entropy so normal
        # words and identifiers are not classified as credentials.
        for match in self._CONTEXT_PATTERNS["GENERIC_SECRET"].finditer(prompt):
            value = match.group("value")
            if self._shannon_entropy(value) < 3.0:
                continue
            matches.append(
                RegexMatch(
                    text=value,
                    label="GENERIC_SECRET",
                    start=match.start("value"),
                    end=match.end("value"),
                )
            )

        # Sort by position so callers get a predictable ordered list
        matches.sort(key=lambda x: x.start)
        return matches

    @staticmethod
    def _is_luhn_valid(value: str) -> bool:
        digits = [int(char) for char in value if char.isdigit()]
        if not 13 <= len(digits) <= 19:
            return False
        checksum = 0
        parity = len(digits) % 2
        for index, digit in enumerate(digits):
            if index % 2 == parity:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0

    @staticmethod
    def _is_valid_ipv4(value: str) -> bool:
        octets = value.split(".")
        return len(octets) == 4 and all(
            octet.isdigit() and 0 <= int(octet) <= 255
            for octet in octets
        )

    @staticmethod
    def _is_valid_canadian_sin(value: str) -> bool:
        digits = [int(char) for char in value if char.isdigit()]
        if len(digits) != 9 or len(set(digits)) == 1:
            return False
        total = 0
        for index, digit in enumerate(digits):
            if index % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0

    @staticmethod
    def _is_valid_iban(value: str) -> bool:
        compact = re.sub(r"[\s-]", "", value).upper()
        if not 15 <= len(compact) <= 34 or not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", compact):
            return False
        rearranged = compact[4:] + compact[:4]
        numeric = "".join(
            str(ord(char) - ord("A") + 10) if char.isalpha() else char
            for char in rearranged
        )
        return int(numeric) % 97 == 1

    @staticmethod
    def _shannon_entropy(value: str) -> float:
        """Return character entropy used to filter generic secret candidates."""
        if not value:
            return 0.0
        counts = Counter(value)
        length = len(value)
        return -sum(
            (count / length) * math.log2(count / length)
            for count in counts.values()
        )

    def detect_as_dicts(self, prompt: str) -> list[dict]:
        """
        Convenience wrapper returning matches as plain dicts.
        """
        return [
            {
                "text": m.text,
                "label": m.label,
                "confidence": 0.99,
                "start": m.start,
                "end": m.end,
            }
            for m in self.detect(prompt)
        ]