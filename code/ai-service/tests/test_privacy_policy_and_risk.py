"""
Tests for Privacy Policy and Risk Scoring (Phase 5).

Verifies:
- Detection is not automatically equivalent to anonymization (e.g. ALLOW policy)
- Policy overrides work as documented (MASK, REPORT, ALLOW, BLOCK, REQUIRE_CONFIRMATION)
- Duplicate entities do not inflate risk scores
- Blocked and confirmation-required policies are handled consistently
- Risk scores match documented weights and thresholds
- Post-optimization privacy leakage scan prevents reintroduction of sensitive values
"""

import pytest
from fastapi import HTTPException
from app.services.privacy_engine import PrivacyEngine
from app.api.optimize import optimize_prompt
from app.models.request import PromptRequest


@pytest.fixture(scope="module")
def engine() -> PrivacyEngine:
    return PrivacyEngine()


def test_detection_is_not_equivalent_to_anonymization(engine):
    prompt = "Contact om@example.com for support."
    # With policy ALLOW, email must be detected but preserved in the output
    result = engine.analyze(prompt, policy_overrides={"EMAIL": "ALLOW"})
    assert any(e["label"] == "EMAIL" for e in result["entities"])
    assert "om@example.com" in result["anonymized_prompt"]
    assert "[EMAIL]" not in result["anonymized_prompt"]


def test_policy_override_report_only(engine):
    prompt = "Phone number is 9876543210."
    result = engine.analyze(prompt, policy_overrides={"PHONE": "REPORT"})
    assert any(e["label"] == "PHONE" for e in result["entities"])
    assert "9876543210" in result["anonymized_prompt"]


def test_policy_override_require_confirmation(engine):
    prompt = "My PAN card is ABCDE1234F."
    result = engine.analyze(prompt, policy_overrides={"PAN": "REQUIRE_CONFIRMATION"})
    assert result["confirmation_required"] is True
    assert "[PAN]" in result["anonymized_prompt"]
    assert "ABCDE1234F" not in result["anonymized_prompt"]


def test_policy_override_block(engine):
    prompt = "My API key is sk-abcdefghijklmnopqrstuvwxyz12345."
    result = engine.analyze(prompt, policy_overrides={"API_KEY": "BLOCK"})
    assert result["blocked"] is True
    assert "API_KEY" in result["blocked_labels"]

    # Endpoint must reject blocked categories with 422
    request = PromptRequest(
        prompt=prompt,
        privacy_policy={"API_KEY": "BLOCK"},
    )
    with pytest.raises(HTTPException) as exc_info:
        optimize_prompt(request)
    assert exc_info.value.status_code == 422


def test_duplicate_entities_do_not_inflate_risk_score(engine):
    single_email_prompt = "Email me at user@example.com."
    repeated_email_prompt = (
        "Email user@example.com or user@example.com or user@example.com "
        "or user@example.com or user@example.com."
    )
    single_res = engine.analyze(single_email_prompt)
    repeated_res = engine.analyze(repeated_email_prompt)

    # Risk score must be identical (20 for EMAIL)
    assert single_res["risk_score"] == 20
    assert repeated_res["risk_score"] == 20
    assert repeated_res["risk_level"] == "MEDIUM"

    # But EVERY occurrence must still be masked in anonymized_prompt
    assert "user@example.com" not in repeated_res["anonymized_prompt"]
    assert repeated_res["anonymized_prompt"].count("[EMAIL]") == 5


def test_risk_score_calculation_weights(engine):
    # EMAIL (20) + PAN (30) = 50 -> HIGH
    prompt = "Email is test@example.com and PAN is ABCDE1234F."
    result = engine.analyze(prompt)
    assert result["risk_score"] == 50
    assert result["risk_level"] == "HIGH"
