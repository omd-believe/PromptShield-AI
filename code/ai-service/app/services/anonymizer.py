"""
Safe single-pass anonymizer.

Replaces sensitive entity spans with stable placeholder tokens (e.g. [EMAIL]).
When multiple distinct values share a label, indexed placeholders such as
[EMAIL_1] and [EMAIL_2] preserve their identity without exposing the values.
in a single, sorted pass over the prompt text.

Why a single pass?
  The previous implementation used two passes:
    1. re.sub() for regex patterns
    2. str.replace() for NER entities

  This caused two critical bugs:
    a. str.replace() replaces ALL occurrences of a substring, including
       occurrences inside unrelated words.
       Example: "John" in "Johnson" → "[PERSON]son"
    b. The NER pass could corrupt placeholders already inserted by the
       regex pass.
       Example: "[EMAIL]" might contain a substring that NER matches.

  A single sorted pass over character offsets avoids both problems entirely.

How it works:
  1. Receive a list of entity dicts, each with (start, end, label).
  2. Sort entities by start offset.
  3. Walk through the prompt once, copying unchanged segments and inserting
     placeholders at entity positions.
  4. Return the reconstructed string.
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def anonymize(prompt: str, entities_to_anonymize: list[dict]) -> str:
    """
    Replace entity spans in *prompt* with [LABEL] placeholders.

    Args:
        prompt:                The preprocessed prompt string.
        entities_to_anonymize: List of entity dicts, each with keys:
                               'text', 'label', 'start', 'end'.
                               Only entities with valid start/end offsets are
                               processed.  Entities without offsets are skipped
                               with a warning.

    Returns:
        The anonymized prompt string.

    Design guarantees:
      - A single forward pass — no entity corrupts another's placeholder.
      - Only the exact character span is replaced — no substring matching.
      - Overlapping spans are skipped (normalization should have removed them).
      - If entities_to_anonymize is empty, returns prompt unchanged.
    """
    if not entities_to_anonymize:
        return prompt

    # Filter out entities that lack offset information
    valid_entities: list[dict] = []
    for entity in entities_to_anonymize:
        if "start" not in entity or "end" not in entity:
            logger.warning(
                "Entity '%s' (%s) has no character offsets — skipping.",
                entity.get("text", "?"),
                entity.get("label", "?"),
            )
            continue
        valid_entities.append(entity)

    if not valid_entities:
        return prompt

    # Assign indexes by first appearance. A single distinct value keeps the
    # legacy [LABEL] form; multiple values receive stable indexed placeholders.
    values_by_label: dict[str, list[str]] = defaultdict(list)
    for entity in valid_entities:
        label = entity["label"]
        value_key = entity.get("text", "").casefold()
        if value_key not in values_by_label[label]:
            values_by_label[label].append(value_key)

    placeholders: dict[tuple[str, str], str] = {}
    for label, values in values_by_label.items():
        for index, value in enumerate(values, start=1):
            placeholders[(label, value)] = (
                f"[{label}]" if len(values) == 1 else f"[{label}_{index}]"
            )

    # Sort by start offset to process left-to-right
    valid_entities.sort(key=lambda e: e["start"])

    parts: list[str] = []
    cursor = 0

    for entity in valid_entities:
        start: int = entity["start"]
        end: int = entity["end"]
        label: str = entity["label"]

        # Skip if this entity's span was already consumed (overlapping spans)
        if start < cursor:
            logger.debug(
                "Skipping overlapping entity '%s' at [%d, %d] (cursor=%d)",
                entity.get("text", "?"),
                start,
                end,
                cursor,
            )
            continue

        # Validate that the span matches the expected text (sanity check)
        actual_text = prompt[start:end]
        expected_text = entity.get("text", "")
        if actual_text != expected_text:
            logger.warning(
                "Entity span mismatch: expected '%s' at [%d,%d] but found '%s'. "
                "Skipping to avoid corruption.",
                expected_text,
                start,
                end,
                actual_text,
            )
            continue

        # Append the unchanged segment before this entity
        parts.append(prompt[cursor:start])

        # Append the stable placeholder
        value_key = entity.get("text", "").casefold()
        parts.append(placeholders[(label, value_key)])

        cursor = end

    # Append any remaining text after the last entity
    parts.append(prompt[cursor:])

    return "".join(parts)
