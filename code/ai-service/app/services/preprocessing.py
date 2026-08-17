import re


class Preprocessor:

    def clean(self, prompt: str) -> str:
        prompt = self.normalize_whitespace(prompt)
        prompt = self.remove_repeated_punctuation(prompt)

        return prompt

    def normalize_whitespace(self, prompt: str) -> str:
        return re.sub(r"\s+", " ", prompt).strip()

    def remove_repeated_punctuation(self, prompt: str) -> str:
        return re.sub(r"([!?.,])\1+", r"\1", prompt)