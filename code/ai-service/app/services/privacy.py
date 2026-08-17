import re


class PrivacyDetector:

    PATTERNS = {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",

        "PHONE": r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b",

        "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",

        "AADHAAR": r"\b\d{4}[-\s]\d{4}[-\s]\d{4}\b",

        "API_KEY": r"\b(?:sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,})\b"
    }

    def detect(self, prompt: str) -> dict:

        detected = {}

        for data_type, pattern in self.PATTERNS.items():

            matches = re.findall(pattern, prompt)

            if matches:
                detected[data_type] = matches

        return detected

    def anonymize(self, prompt: str) -> str:

        anonymized_prompt = prompt

        for data_type, pattern in self.PATTERNS.items():

            anonymized_prompt = re.sub(
                pattern,
                f"[{data_type}]",
                anonymized_prompt
            )

        return anonymized_prompt