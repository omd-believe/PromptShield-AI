class PrivacyRiskScorer:

    RISK_SCORES = {
        "EMAIL": 20,
        "PHONE": 20,
        "PERSON": 15,
        "GPE": 10,
        "ORG": 5,
        "PAN": 30,
        "AADHAAR": 30,
        "API_KEY": 40
    }

    def calculate_score(self, entities: list[dict]) -> int:
        score = 0

        for entity in entities:
            label = entity["label"]
            score += self.RISK_SCORES.get(label, 0)

        return min(score, 100)

    def get_risk_level(self, score: int) -> str:

        if score >= 70:
            return "CRITICAL"

        if score >= 40:
            return "HIGH"

        if score >= 20:
            return "MEDIUM"

        return "LOW"

    def analyze(self, entities: list[dict]) -> dict:

        score = self.calculate_score(entities)

        return {
            "score": score,
            "level": self.get_risk_level(score)
        }