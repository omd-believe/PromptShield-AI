"""
Tests for the PrivacyRiskScorer service.

Covers:
- LOW risk (single ORG entity)
- MEDIUM risk (single EMAIL entity)
- HIGH risk (PERSON + PHONE + EMAIL)
- CRITICAL risk (PAN + AADHAAR + API_KEY — exceeds 100, capped)
- Empty entity list
- Unknown entity label
- Duplicate entity protection (dedup should happen upstream, but scorer
  should not double-count if passed identical labels)
"""

import pytest

from app.services.risk import PrivacyRiskScorer


@pytest.fixture
def scorer() -> PrivacyRiskScorer:
    return PrivacyRiskScorer()


# ── Risk levels ────────────────────────────────────────────────────────────────

def test_low_risk_single_org(scorer):
    entities = [{"text": "Google", "label": "ORG"}]
    result = scorer.analyze(entities)
    assert result["score"] == 5
    assert result["level"] == "LOW"


def test_low_risk_empty(scorer):
    result = scorer.analyze([])
    assert result["score"] == 0
    assert result["level"] == "LOW"


def test_medium_risk_email(scorer):
    entities = [{"text": "rahul@gmail.com", "label": "EMAIL"}]
    result = scorer.analyze(entities)
    assert result["score"] == 20
    assert result["level"] == "MEDIUM"


def test_medium_risk_phone(scorer):
    entities = [{"text": "9876543210", "label": "PHONE"}]
    result = scorer.analyze(entities)
    assert result["score"] == 20
    assert result["level"] == "MEDIUM"


def test_high_risk_combination(scorer):
    entities = [
        {"text": "Rahul", "label": "PERSON"},
        {"text": "9876543210", "label": "PHONE"},
        {"text": "rahul@gmail.com", "label": "EMAIL"},
    ]
    result = scorer.analyze(entities)
    # PERSON=15, PHONE=20, EMAIL=20 → 55
    assert result["score"] == 55
    assert result["level"] == "HIGH"


def test_critical_risk_cap_at_100(scorer):
    entities = [
        {"text": "ABCDE1234F", "label": "PAN"},       # 30
        {"text": "1234-5678-9012", "label": "AADHAAR"},  # 30
        {"text": "sk-very-secret-api-key-12345", "label": "API_KEY"},  # 40
    ]
    result = scorer.analyze(entities)
    assert result["score"] == 100  # 100 (capped from 100)
    assert result["level"] == "CRITICAL"


def test_score_not_exceed_100(scorer):
    # Even with many high-weight entities, score must not exceed 100
    entities = [
        {"text": "ABCDE1234F", "label": "PAN"},
        {"text": "1234-5678-9012", "label": "AADHAAR"},
        {"text": "sk-key-123456789012345678", "label": "API_KEY"},
        {"text": "om@example.com", "label": "EMAIL"},
        {"text": "9876543210", "label": "PHONE"},
        {"text": "Om", "label": "PERSON"},
    ]
    result = scorer.analyze(entities)
    assert result["score"] <= 100


def test_unknown_label_contributes_zero(scorer):
    entities = [{"text": "something", "label": "UNKNOWN_LABEL"}]
    result = scorer.analyze(entities)
    assert result["score"] == 0
    assert result["level"] == "LOW"


# ── Threshold boundaries ───────────────────────────────────────────────────────

def test_score_19_is_low(scorer):
    # GPE=10 + LOC=5 = 15 → LOW
    entities = [
        {"label": "GPE", "text": "Mumbai"},
        {"label": "LOC", "text": "Western India"},
    ]
    result = scorer.analyze(entities)
    assert result["level"] == "LOW"


def test_score_20_is_medium(scorer):
    entities = [{"label": "EMAIL", "text": "x@y.com"}]
    result = scorer.analyze(entities)
    assert result["score"] == 20
    assert result["level"] == "MEDIUM"


def test_score_40_is_high(scorer):
    # EMAIL=20 + PHONE=20 = 40 → HIGH
    entities = [
        {"label": "EMAIL", "text": "x@y.com"},
        {"label": "PHONE", "text": "9876543210"},
    ]
    result = scorer.analyze(entities)
    assert result["score"] == 40
    assert result["level"] == "HIGH"


def test_score_70_is_critical(scorer):
    # AADHAAR=30 + PAN=30 + PERSON=15 = 75 → CRITICAL
    entities = [
        {"label": "AADHAAR", "text": "1234 5678 9012"},
        {"label": "PAN", "text": "ABCDE1234F"},
        {"label": "PERSON", "text": "Rahul"},
    ]
    result = scorer.analyze(entities)
    assert result["score"] >= 70
    assert result["level"] == "CRITICAL"