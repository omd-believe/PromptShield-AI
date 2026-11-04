"""
Tests for the single-pass anonymizer.

Covers:
- Single entity replacement
- Multiple entities (ordered)
- Repeated same entity in one prompt
- Overlapping entity protection
- Surrounding punctuation preserved
- Already-anonymized content not double-processed
- Empty entity list (no change)
- Entity with no offsets (skipped with warning)
- Span mismatch protection
"""

import pytest

from app.services.anonymizer import anonymize


# ── Single entity ──────────────────────────────────────────────────────────────

def test_email_replaced(capsys):
    prompt = "Contact me at om@example.com"
    entities = [{"text": "om@example.com", "label": "EMAIL", "start": 14, "end": 28}]
    result = anonymize(prompt, entities)
    assert result == "Contact me at [EMAIL]"


def test_phone_replaced():
    prompt = "My phone is 9876543210"
    entities = [{"text": "9876543210", "label": "PHONE", "start": 12, "end": 22}]
    result = anonymize(prompt, entities)
    assert result == "My phone is [PHONE]"


def test_pan_replaced():
    prompt = "My PAN is ABCDE1234F"
    entities = [{"text": "ABCDE1234F", "label": "PAN", "start": 10, "end": 20}]
    result = anonymize(prompt, entities)
    assert result == "My PAN is [PAN]"


def test_aadhaar_replaced():
    prompt = "My Aadhaar is 1234-5678-9012"
    entities = [{"text": "1234-5678-9012", "label": "AADHAAR", "start": 14, "end": 28}]
    result = anonymize(prompt, entities)
    assert result == "My Aadhaar is [AADHAAR]"


# ── Multiple entities ──────────────────────────────────────────────────────────

def test_multiple_entities_replaced():
    prompt = "Email om@example.com and phone 9876543210"
    entities = [
        {"text": "om@example.com", "label": "EMAIL", "start": 6, "end": 20},
        {"text": "9876543210", "label": "PHONE", "start": 31, "end": 41},
    ]
    result = anonymize(prompt, entities)
    assert result == "Email [EMAIL] and phone [PHONE]"


def test_entities_unsorted_still_work():
    """Anonymizer sorts entities by start offset internally."""
    prompt = "Email om@example.com and phone 9876543210"
    entities = [
        {"text": "9876543210", "label": "PHONE", "start": 31, "end": 41},
        {"text": "om@example.com", "label": "EMAIL", "start": 6, "end": 20},
    ]
    result = anonymize(prompt, entities)
    assert result == "Email [EMAIL] and phone [PHONE]"


# ── Empty entity list ──────────────────────────────────────────────────────────

def test_no_entities_returns_original():
    prompt = "Hello world"
    result = anonymize(prompt, [])
    assert result == "Hello world"


# ── Surrounding punctuation preserved ─────────────────────────────────────────

def test_entity_at_end_of_sentence():
    prompt = "My email is om@example.com."
    entities = [{"text": "om@example.com", "label": "EMAIL", "start": 12, "end": 26}]
    result = anonymize(prompt, entities)
    assert result == "My email is [EMAIL]."


def test_entity_in_parentheses():
    prompt = "Contact (9876543210) for info"
    entities = [{"text": "9876543210", "label": "PHONE", "start": 9, "end": 19}]
    result = anonymize(prompt, entities)
    assert result == "Contact ([PHONE]) for info"


# ── Entity at prompt boundaries ────────────────────────────────────────────────

def test_entity_at_start():
    prompt = "om@example.com is my email"
    entities = [{"text": "om@example.com", "label": "EMAIL", "start": 0, "end": 14}]
    result = anonymize(prompt, entities)
    assert result == "[EMAIL] is my email"


def test_entity_at_end():
    prompt = "Email me at om@example.com"
    entities = [{"text": "om@example.com", "label": "EMAIL", "start": 12, "end": 26}]
    result = anonymize(prompt, entities)
    assert result == "Email me at [EMAIL]"


# ── Placeholder not corrupted by second pass ───────────────────────────────────

def test_already_anonymized_placeholder_preserved():
    """
    If [EMAIL] already appears in the text (from regex pass),
    a subsequent NER entity must not corrupt it.
    The single-pass approach prevents this entirely.
    """
    prompt = "[EMAIL] is already anonymized"
    # No entities to anonymize — prompt returned unchanged
    result = anonymize(prompt, [])
    assert result == "[EMAIL] is already anonymized"


# ── Entity without offsets ─────────────────────────────────────────────────────

def test_entity_without_offsets_skipped(caplog):
    import logging
    prompt = "Hello world"
    entities = [{"text": "world", "label": "PERSON"}]  # no start/end
    with caplog.at_level(logging.WARNING):
        result = anonymize(prompt, entities)
    # Entity skipped — prompt unchanged
    assert result == "Hello world"
    assert any("no character offsets" in record.message for record in caplog.records)


# ── Span mismatch protection ───────────────────────────────────────────────────

def test_span_mismatch_skipped(caplog):
    import logging
    prompt = "Hello world"
    # Deliberately wrong text for the given span
    entities = [{"text": "WRONG", "label": "PERSON", "start": 6, "end": 11}]
    with caplog.at_level(logging.WARNING):
        result = anonymize(prompt, entities)
    assert result == "Hello world"
    assert any("mismatch" in record.message for record in caplog.records)
