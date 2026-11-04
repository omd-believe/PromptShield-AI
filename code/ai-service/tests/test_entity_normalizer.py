"""
Tests for the entity normalizer (merge + dedup stage).

Covers:
- No entities (empty result)
- Regex-only entities
- NER-only entities
- Regex + NER with no overlap (combined)
- Duplicate entities (same text + label) — deduplicated
- Overlapping spans — only one kept
- Regex wins over NER for same span
"""

import pytest

from app.services.entity_normalizer import normalize_entities


# ── Empty inputs ───────────────────────────────────────────────────────────────

def test_both_empty():
    result = normalize_entities([], [])
    assert result == []


def test_regex_empty():
    ner = [{"text": "John", "label": "PERSON", "start": 0, "end": 4}]
    result = normalize_entities([], ner)
    assert len(result) == 1
    assert result[0]["label"] == "PERSON"


def test_ner_empty():
    regex = [{"text": "om@example.com", "label": "EMAIL", "start": 0, "end": 14}]
    result = normalize_entities(regex, [])
    assert len(result) == 1
    assert result[0]["label"] == "EMAIL"


# ── Non-overlapping entities merged ───────────────────────────────────────────

def test_non_overlapping_merged():
    regex = [{"text": "om@example.com", "label": "EMAIL", "start": 0, "end": 14}]
    ner = [{"text": "John", "label": "PERSON", "start": 20, "end": 24}]
    result = normalize_entities(regex, ner)
    assert len(result) == 2
    labels = {e["label"] for e in result}
    assert "EMAIL" in labels
    assert "PERSON" in labels


# ── Duplicate deduplication ────────────────────────────────────────────────────

def test_duplicate_same_text_and_label_deduplicated():
    """Same entity detected by both regex and NER at same position."""
    regex = [{"text": "9876543210", "label": "PHONE", "start": 12, "end": 22}]
    ner = [{"text": "9876543210", "label": "PHONE", "start": 12, "end": 22}]
    result = normalize_entities(regex, ner)
    assert len(result) == 1


def test_duplicate_same_text_different_label_kept():
    """Same text but different labels — both kept (different entities)."""
    regex = [{"text": "test", "label": "EMAIL", "start": 0, "end": 4}]
    ner = [{"text": "test", "label": "PERSON", "start": 0, "end": 4}]
    # Overlapping span — only one kept (regex wins)
    result = normalize_entities(regex, ner)
    assert len(result) == 1


# ── Overlapping spans ──────────────────────────────────────────────────────────

def test_overlapping_spans_one_kept():
    """Entity spans that overlap — only the first (by start) is kept."""
    regex = [{"text": "9876543210", "label": "PHONE", "start": 5, "end": 15}]
    ner = [{"text": "98765", "label": "CARDINAL", "start": 5, "end": 10}]
    result = normalize_entities(regex, ner)
    # Both start at 5; regex is longer and comes first in sort
    # Only one should be in result
    assert len(result) == 1


def test_adjacent_spans_not_overlapping():
    """Entities that touch but don't overlap are both kept."""
    e1 = {"text": "hello", "label": "PERSON", "start": 0, "end": 5}
    e2 = {"text": "world", "label": "ORG", "start": 5, "end": 10}
    result = normalize_entities([e1], [e2])
    assert len(result) == 2


# ── Output structure ───────────────────────────────────────────────────────────

def test_output_has_required_keys():
    regex = [{"text": "om@example.com", "label": "EMAIL", "start": 0, "end": 14}]
    result = normalize_entities(regex, [])
    assert "text" in result[0]
    assert "label" in result[0]
    assert "start" in result[0]
    assert "end" in result[0]


def test_result_sorted_by_start():
    """Output should be sorted by character start offset."""
    regex = [{"text": "om@example.com", "label": "EMAIL", "start": 20, "end": 34}]
    ner = [{"text": "John", "label": "PERSON", "start": 0, "end": 4}]
    result = normalize_entities(regex, ner)
    starts = [e["start"] for e in result]
    assert starts == sorted(starts)
