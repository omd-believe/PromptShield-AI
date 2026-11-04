"""
Privacy risk scorer.

Calculates a numeric risk score and a qualitative risk level for a set of
detected entities.

Design:
- Risk weights are defined in app/config.py (RISK_WEIGHTS).
- Score is capped at RISK_MAX_SCORE (default 100).
- Each entity type contributes its weight exactly once per unique instance
  (deduplication must happen before this stage).
- The scorer is stateless and safe to share across requests.
"""

import logging

from app import config

logger = logging.getLogger(__name__)

# Risk level labels in descending order — used to determine which threshold applies
_RISK_LEVELS = [
    ("CRITICAL", config.RISK_THRESHOLDS["CRITICAL"]),
    ("HIGH",     config.RISK_THRESHOLDS["HIGH"]),
    ("MEDIUM",   config.RISK_THRESHOLDS["MEDIUM"]),
    ("LOW",      config.RISK_THRESHOLDS["LOW"]),
]


class PrivacyRiskScorer:
    """
    Calculates a risk score and level from a list of normalized entities.

    Input:
        Entities should already be deduplicated (via entity_normalizer).
        Passing duplicates will inflate the score.

    Output:
        dict with keys:
          score (int):  0–100 cumulative risk score
          level (str):  CRITICAL | HIGH | MEDIUM | LOW
    """

    def analyze(self, entities: list[dict]) -> dict:
        """
        Compute risk score for *entities*.

        Args:
            entities: list of entity dicts, each with at least a 'label' key.

        Returns:
            {"score": int, "level": str}
        """
        score = 0

        for entity in entities:
            label = entity.get("label", "")
            weight = config.RISK_WEIGHTS.get(label, 0)

            if weight == 0 and label:
                logger.debug(
                    "Entity label '%s' has no configured risk weight — scored 0.",
                    label,
                )

            score += weight

        # Cap at maximum
        score = min(score, config.RISK_MAX_SCORE)

        level = self._compute_level(score)

        return {"score": score, "level": level}

    @staticmethod
    def _compute_level(score: int) -> str:
        for level, threshold in _RISK_LEVELS:
            if score >= threshold:
                return level
        return "LOW"