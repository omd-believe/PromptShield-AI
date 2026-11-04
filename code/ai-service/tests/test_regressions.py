"""
Regression tests for bugs found in review.

1. Repeated PII must be masked at EVERY occurrence (previously only the first
   occurrence of each distinct value was anonymized and the rest leaked).
2. Contiguous 12-digit Aadhaar numbers must be detected.
3. reduction_percentage must never be negative or above 100.
"""

import pytest

from app.services.privacy import PrivacyDetector
from app.services.privacy_engine import PrivacyEngine
from app.services.token_counter import TokenCounter


@pytest.fixture(scope="module")
def engine():
    return PrivacyEngine()


def test_repeated_email_is_masked_everywhere(engine):
    result = engine.analyze("Mail a@example.com, then again a@example.com, or A@Example.com.")
    assert "example.com" not in result["anonymized_prompt"]
    assert result["anonymized_prompt"].count("[EMAIL]") == 3


def test_repeated_phone_is_masked_everywhere(engine):
    result = engine.analyze("Call 9876543210 now. Call 9876543210 later.")
    assert "9876543210" not in result["anonymized_prompt"]
    assert result["anonymized_prompt"].count("[PHONE]") == 2


def test_repeated_entities_reported_once_and_scored_once(engine):
    result = engine.analyze("Mail a@example.com or a@example.com")
    assert [e["label"] for e in result["entities"]] == ["EMAIL"]
    assert result["risk_score"] == 20


def test_contiguous_aadhaar_detected():
    matches = PrivacyDetector().detect("My Aadhaar is 234567890123 ok")
    assert any(m.label == "AADHAAR" and m.text == "234567890123" for m in matches)


def test_contiguous_aadhaar_masked(engine):
    result = engine.analyze("My Aadhaar is 234567890123")
    assert "234567890123" not in result["anonymized_prompt"]


def test_reduction_percentage_never_negative():
    counter = TokenCounter()
    assert counter.reduction_percentage(5, 9) == 0.0


def test_reduction_percentage_never_above_100():
    assert TokenCounter().reduction_percentage(5, -3) == 100.0
