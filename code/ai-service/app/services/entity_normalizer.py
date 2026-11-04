"""
Entity normalization stage.

Merges regex-detected entities and NER-detected entities into a single,
deduplicated, overlap-free list with clear priority rules.

Problems solved:
1. Duplicate entities — the same text/label pair detected by both regex and NER.
2. Overlapping spans — regex matches and NER spans that cover the same characters.
3. NER containing regex — spaCy sometimes wraps a regex-detectable token
   inside a broader span (e.g. "PAN ABCDE1234F" detected as ORG, while
   regex precisely detects "ABCDE1234F" as PAN).  In such cases the regex
   detection must win.
4. Label normalization — ensures consistent label strings.

Priority rule: regex-detected entities always win over NER entities for
overlapping spans. Regex patterns are explicit, high-precision detectors
(PAN, EMAIL, PHONE, etc.); NER is probabilistic and may misclassify
structured data tokens as ORG/PERSON.

Each normalized entity contains:
  - text:  original surface form
  - label: category label (EMAIL, PERSON, etc.)
  - start: character start offset in the (preprocessed) prompt
  - end:   character end offset in the (preprocessed) prompt
"""

import logging

logger = logging.getLogger(__name__)

# Source priority constants (lower = higher priority in conflict resolution)
_REGEX_SOURCE = 0
_NER_SOURCE = 1


def normalize_entities(
    regex_entities: list[dict],
    ner_entities: list[dict],
) -> list[dict]:
    """
    Merge regex and NER entities into a deduplicated, overlap-free list.

    Algorithm:
    1. Tag each entity with its source priority (_source=0 for regex, 1 for NER).
    2. Remove NER entities that overlap with ANY regex entity (regex wins
       regardless of span position — this handles containment cases).
    3. Combine the remaining NER entities with all regex entities.
    4. Sort by start offset.
    5. Apply greedy interval selection to remove any remaining overlaps
       (should be rare after step 2).
    6. Return EVERY occurrence. Text-level deduplication is deliberately NOT
       done here: the anonymizer replaces spans by offset, so dropping a
       repeated occurrence would leave that PII in the output prompt.
       Use deduplicate_for_report() for the API entity list and risk score.

    Args:
        regex_entities: list of dicts from PrivacyDetector.detect_as_dicts()
                        — must have keys: text, label, start, end
        ner_entities:   list of dicts from NERDetector.detect()
                        — must have keys: text, label, start, end

    Returns:
        Sorted list of non-overlapping entity dicts.
    """
    if not regex_entities and not ner_entities:
        return []

    # Step 1: Build set of regex-covered intervals for fast lookup
    regex_intervals: list[tuple[int, int]] = [
        (e["start"], e["end"]) for e in regex_entities
    ]

    def overlaps_any_regex(ner_start: int, ner_end: int) -> bool:
        """Return True if a NER entity's span overlaps with any regex entity."""
        for r_start, r_end in regex_intervals:
            # Overlap condition: not (ner_end <= r_start or ner_start >= r_end)
            if not (ner_end <= r_start or ner_start >= r_end):
                return True
        return False

    # Step 2: Filter out NER entities that conflict with regex entities
    filtered_ner: list[dict] = []
    for ner_ent in ner_entities:
        if overlaps_any_regex(ner_ent["start"], ner_ent["end"]):
            logger.debug(
                "NER entity '%s' (%s) at [%d,%d] removed — conflicts with regex entity.",
                ner_ent["text"],
                ner_ent["label"],
                ner_ent["start"],
                ner_ent["end"],
            )
        else:
            filtered_ner.append(ner_ent)

    # Step 3: Combine all regex entities with non-conflicting NER entities
    combined = list(regex_entities) + filtered_ner

    if not combined:
        return []

    # Step 4: Sort by start offset
    combined.sort(key=lambda e: e["start"])

    # Step 5: Greedy interval selection (removes any residual overlaps)
    accepted: list[dict] = []
    last_end = -1

    for entity in combined:
        start = entity.get("start", 0)
        end = entity.get("end", 0)

        if start >= last_end:
            accepted.append(entity)
            last_end = end
        else:
            logger.debug(
                "Greedy: skipping overlapping entity '%s' (%s) at [%d,%d].",
                entity["text"],
                entity["label"],
                start,
                end,
            )

    return accepted


def deduplicate_for_report(entities: list[dict]) -> list[dict]:
    """
    Collapse repeated (text, label) pairs, keeping the first occurrence.

    Intended ONLY for what is reported to the API consumer and for risk
    scoring. Never feed the result to the anonymizer — it needs every
    occurrence so that repeated PII is masked everywhere it appears.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []

    for entity in entities:
        key = (entity["text"].strip().lower(), entity["label"])
        if key not in seen:
            seen.add(key)
            unique.append(entity)

    return unique
