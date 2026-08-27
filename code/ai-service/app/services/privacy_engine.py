from app.services.privacy import PrivacyDetector
from app.services.ner import NERDetector
from app.services.risk import PrivacyRiskScorer


class PrivacyEngine:

    def __init__(self):
        self.regex_detector = PrivacyDetector()
        self.ner_detector = NERDetector()
        self.risk_scorer = PrivacyRiskScorer()

    def analyze(self, prompt: str) -> dict:

        regex_entities = self.regex_detector.detect(prompt)

        ner_entities = self.ner_detector.detect(prompt)

        entities = []

        for label, values in regex_entities.items():
            for value in values:
                entities.append({
                    "text": value,
                    "label": label
                })

        entities.extend(ner_entities)

        risk = self.risk_scorer.analyze(entities)

        anonymized_prompt = self.regex_detector.anonymize(prompt)

        return {
            "entities": entities,
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "anonymized_prompt": anonymized_prompt
        }