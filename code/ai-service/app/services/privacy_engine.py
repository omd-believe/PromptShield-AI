"""
Privacy Engine — orchestrates the privacy detection pipeline.

Pipeline stages (in order):
  1. Regex detection   — PrivacyDetector  → regex entities with offsets
  2. NER detection     — NERDetector      → NER entities with offsets
  3. Entity normalization — normalize_entities() → merged, deduplicated list
  4. Privacy policy    — split_by_policy() → partition into anonymize / keep
  5. Risk scoring      — PrivacyRiskScorer → score + level
  6. Anonymization     — anonymize()       → single-pass, offset-based

This class does NOT perform preprocessing or prompt optimization.
Those are separate pipeline stages handled by the route handler.

The privacy engine is stateless with respect to individual requests.
All service objects (NER, regex detector, risk scorer) are created once
and reused.
"""

import logging
from collections import Counter

from app.services.privacy import PrivacyDetector
from app.services.ner import NERDetector
from app.services.entity_normalizer import normalize_entities, deduplicate_for_report
from app.services.privacy_policy import action_for_entity, split_by_policy
from app.services.risk import PrivacyRiskScorer
from app.services.anonymizer import anonymize

logger = logging.getLogger(__name__)


class PrivacyEngine:
    """
    Orchestrates the complete privacy detection and anonymization pipeline.

    Usage:
        engine = PrivacyEngine()  # created once, shared across requests
        result = engine.analyze("My email is foo@example.com")

    Returns a dict:
        {
          "entities":         list[dict],  # all detected entities (for response)
          "risk_score":       int,         # 0–100
          "risk_level":       str,         # CRITICAL | HIGH | MEDIUM | LOW
          "anonymized_prompt": str,        # prompt with sensitive values replaced
        }
    """

    def __init__(self) -> None:
        self._regex_detector = PrivacyDetector()
        self._ner_detector = NERDetector()
        self._risk_scorer = PrivacyRiskScorer()

    def analyze(
        self,
        prompt: str,
        policy_overrides: dict[str, str] | None = None,
    ) -> dict:
        """
        Run the full privacy pipeline on *prompt*.

        Args:
            prompt: Pre-processed prompt text.

        Returns:
            dict with keys: entities, risk_score, risk_level, anonymized_prompt.
        """
        logger.debug("Privacy pipeline: starting analysis (prompt length=%d)", len(prompt))

        # Stage 1: Regex detection
        regex_entities = self._regex_detector.detect_as_dicts(prompt)
        logger.debug("Regex entities detected: %d", len(regex_entities))

        # Stage 2: NER detection
        ner_entities = self._ner_detector.detect(prompt)
        logger.debug("NER entities detected: %d", len(ner_entities))

        # Stage 3: Entity normalization — merge, deduplicate, resolve overlaps
        all_entities = normalize_entities(regex_entities, ner_entities)
        logger.debug("Normalized entities: %d", len(all_entities))

        # Stage 4: Privacy policy — decide what to anonymize.
        # all_entities holds EVERY occurrence so repeated PII is masked everywhere.
        to_anonymize, to_keep = split_by_policy(all_entities, policy_overrides)
        logger.debug(
            "Entities to anonymize: %d, to keep: %d",
            len(to_anonymize),
            len(to_keep),
        )

        # Stage 5: Risk scoring — unique entities only (including kept ones),
        # so repeating the same value does not inflate the score.
        unique_entities = deduplicate_for_report(all_entities)
        risk = self._risk_scorer.analyze(unique_entities)

        # Stage 6: Safe single-pass anonymization
        anonymized_prompt = anonymize(prompt, to_anonymize)

        # The response entity list contains each unique entity once.
        # Only text and label are exposed to the API consumer (not internal offsets).
        detected_actions = {
            entity["label"]: action_for_entity(entity, policy_overrides)
            for entity in unique_entities
        }
        response_entities = [
            {
                "text": e["text"],
                "label": e["label"],
                "confidence": round(float(e.get("confidence", 1.0)), 2),
                "policy_action": detected_actions[e["label"]],
            }
            for e in unique_entities
        ]
        counts = Counter(e["label"] for e in unique_entities)
        privacy_report = {
            "total_entities": len(unique_entities),
            "entity_types": [
                {
                    "label": label,
                    "count": count,
                    "masked_as": f"[{label}]",
                }
                for label, count in sorted(counts.items())
            ],
        }
        blocked_labels = sorted(
            label for label, action in detected_actions.items() if action == "BLOCK"
        )
        confirmation_required = any(
            action == "REQUIRE_CONFIRMATION"
            for action in detected_actions.values()
        )

        return {
            "entities": response_entities,
            "privacy_report": privacy_report,
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "anonymized_prompt": anonymized_prompt,
            "policy_actions": detected_actions,
            "confirmation_required": confirmation_required,
            "blocked": bool(blocked_labels),
            "blocked_labels": blocked_labels,
        }