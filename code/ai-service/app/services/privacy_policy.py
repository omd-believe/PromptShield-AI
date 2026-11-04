"""
Privacy policy — decides which detected entities should be anonymized.

This module separates DETECTION from ANONYMIZATION.

Detection answers: "What sensitive information is present?"
Policy answers:    "What should actually be replaced in the output?"

These are intentionally different questions.

Example:
  "Apple released a new iPhone."
  NER detects: ORG → "Apple"
  Policy decision: ORG is not anonymized by default (not personally identifying
                   in isolation). "Apple" stays as-is.

  "John's email is john@example.com"
  NER detects: PERSON → "John"
  Regex detects: EMAIL → "john@example.com"
  Policy decision: PERSON → anonymize (person names are PII).
                   EMAIL → anonymize (always).

The policy is configured in app/config.py:
  REGEX_ALWAYS_ANONYMIZE: types that are always anonymized
  NER_ANONYMIZE_TYPES:    NER types subject to anonymization
"""

from app import config

POLICY_ACTIONS = {
    "MASK",
    "REPORT",
    "ALLOW",
    "BLOCK",
    "REQUIRE_CONFIRMATION",
}


def action_for_entity(
    entity: dict,
    policy_overrides: dict[str, str] | None = None,
) -> str:
    """Resolve the effective action for an entity category."""
    label = entity.get("label", "")
    if policy_overrides and label in policy_overrides:
        return policy_overrides[label]
    if label in config.REGEX_ALWAYS_ANONYMIZE or label in config.NER_ANONYMIZE_TYPES:
        return "MASK"
    return "REPORT"


def should_anonymize(
    entity: dict,
    policy_overrides: dict[str, str] | None = None,
) -> bool:
    """
    Return True if *entity* should be replaced with a placeholder.

    Args:
        entity: dict with at least a 'label' key (str).

    Returns:
        True  — the entity should be anonymized.
        False — the entity should be kept in the output as-is.
    """
    return action_for_entity(entity, policy_overrides) in {
        "MASK",
        "REQUIRE_CONFIRMATION",
    }


def split_by_policy(
    entities: list[dict],
    policy_overrides: dict[str, str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Partition *entities* into (to_anonymize, to_keep).

    Returns:
        to_anonymize: entities that should be replaced in the output prompt.
        to_keep:      entities that are reported in the response but NOT
                      replaced (e.g. ORG entities like company names).
    """
    to_anonymize: list[dict] = []
    to_keep: list[dict] = []

    for entity in entities:
        if should_anonymize(entity, policy_overrides):
            to_anonymize.append(entity)
        else:
            to_keep.append(entity)

    return to_anonymize, to_keep
