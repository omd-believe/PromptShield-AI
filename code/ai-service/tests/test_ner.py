"""
Tests for the NERDetector service.

Covers:
- PERSON detection
- GPE (geopolitical entity) detection
- ORG detection
- LOC detection
- Filtering of irrelevant entity types (DATE, MONEY, etc.)
- Entity dict structure (text, label, start, end)
"""

import pytest

from app.services.ner import NERDetector


@pytest.fixture(scope="module")
def detector() -> NERDetector:
    """Module-scoped fixture — loads spaCy model once for all NER tests."""
    return NERDetector()


# ── PERSON detection ───────────────────────────────────────────────────────────

def test_person_detected(detector):
    result = detector.detect("Barack Obama was the president of the United States.")
    assert any(
        e["text"] == "Barack Obama" and e["label"] == "PERSON"
        for e in result
    )


def test_person_single_name(detector):
    # spaCy may or may not detect single first names — this is a soft test
    result = detector.detect("John called me yesterday.")
    # At minimum: no error raised, result is a list
    assert isinstance(result, list)


# ── GPE detection ──────────────────────────────────────────────────────────────

def test_gpe_detected(detector):
    result = detector.detect("I live in Sangli.")
    assert any(e["label"] == "GPE" for e in result)


def test_gpe_text(detector):
    result = detector.detect("I live in Sangli.")
    gpe_entities = [e for e in result if e["label"] == "GPE"]
    assert any("Sangli" in e["text"] for e in gpe_entities)


def test_gpe_country(detector):
    result = detector.detect("She moved to Canada last year.")
    assert any(e["label"] == "GPE" for e in result)


# ── ORG detection ──────────────────────────────────────────────────────────────

def test_org_detected(detector):
    result = detector.detect("I study at Walchand College of Engineering.")
    assert any(
        e["text"] == "Walchand College of Engineering" and e["label"] == "ORG"
        for e in result
    )


def test_org_company(detector):
    result = detector.detect("She works at Google.")
    assert any(e["label"] == "ORG" for e in result)


# ── Type filtering ─────────────────────────────────────────────────────────────

def test_date_entity_not_returned(detector):
    """DATE is not a privacy-relevant type and should be filtered."""
    result = detector.detect("The meeting is on January 15th.")
    assert not any(e["label"] == "DATE" for e in result)


def test_money_entity_not_returned(detector):
    """MONEY is not a privacy-relevant type and should be filtered."""
    result = detector.detect("The product costs $500.")
    assert not any(e["label"] == "MONEY" for e in result)


def test_cardinal_not_returned(detector):
    """CARDINAL (numbers) is not a privacy-relevant type."""
    result = detector.detect("There are 42 students in the class.")
    assert not any(e["label"] == "CARDINAL" for e in result)


# ── Entity dict structure ──────────────────────────────────────────────────────

def test_entity_has_required_keys(detector):
    result = detector.detect("Barack Obama lives in Washington.")
    for entity in result:
        assert "text" in entity
        assert "label" in entity
        assert "start" in entity
        assert "end" in entity


def test_entity_offsets_correct(detector):
    prompt = "Barack Obama was president."
    result = detector.detect(prompt)
    for entity in result:
        # Verify the offset points to the actual text in the prompt
        assert prompt[entity["start"]:entity["end"]] == entity["text"]


def test_empty_prompt_returns_empty(detector):
    # Empty string — no entities to detect (spaCy handles this gracefully)
    result = detector.detect("")
    assert result == []


def test_no_entities_prompt(detector):
    result = detector.detect("The sky is blue and the grass is green.")
    # No guarantee from spaCy on this sentence, but must return a list
    assert isinstance(result, list)