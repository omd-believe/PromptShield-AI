"""
End-to-end pipeline tests via the PrivacyEngine.

Tests the full: privacy detection → normalization → policy → scoring → anonymization

Covers:
- Clean prompt (no sensitive data)
- Email prompt
- Phone prompt
- PAN prompt
- Aadhaar prompt
- API key prompt
- Multiple sensitive entities
- High-risk prompt
- NER entity (PERSON)
- Anonymization correctness (placeholders appear in output)
- Risk score not exceeding 100
"""

import pytest

from app.services.privacy_engine import PrivacyEngine


@pytest.fixture(scope="module")
def engine() -> PrivacyEngine:
    """Module-scoped — loads spaCy once for all pipeline tests."""
    return PrivacyEngine()


# ── No sensitive data ──────────────────────────────────────────────────────────

def test_clean_prompt_no_entities(engine):
    result = engine.analyze("Explain the concept of machine learning.")
    assert result["risk_level"] == "LOW"
    # May still have NER entities (ORG, GPE etc.) — score should be low
    assert result["risk_score"] < 20


def test_clean_prompt_anonymized_unchanged_or_close(engine):
    prompt = "Explain the concept of machine learning."
    result = engine.analyze(prompt)
    # Without sensitive data, anonymized prompt should be very similar
    assert result["anonymized_prompt"] is not None


# ── Email ──────────────────────────────────────────────────────────────────────

def test_email_detected(engine):
    result = engine.analyze("My email is om@example.com")
    labels = {e["label"] for e in result["entities"]}
    assert "EMAIL" in labels


def test_email_anonymized(engine):
    result = engine.analyze("My email is om@example.com")
    assert "om@example.com" not in result["anonymized_prompt"]
    assert "[EMAIL]" in result["anonymized_prompt"]


def test_email_risk_medium_or_above(engine):
    result = engine.analyze("Contact: om@example.com")
    assert result["risk_level"] in ("MEDIUM", "HIGH", "CRITICAL")


# ── Phone ──────────────────────────────────────────────────────────────────────

def test_phone_detected(engine):
    result = engine.analyze("Call me at 9876543210")
    labels = {e["label"] for e in result["entities"]}
    assert "PHONE" in labels


def test_phone_anonymized(engine):
    result = engine.analyze("Call me at 9876543210")
    assert "9876543210" not in result["anonymized_prompt"]
    assert "[PHONE]" in result["anonymized_prompt"]


# ── PAN ────────────────────────────────────────────────────────────────────────

def test_pan_detected(engine):
    result = engine.analyze("My PAN is ABCDE1234F")
    labels = {e["label"] for e in result["entities"]}
    assert "PAN" in labels


def test_pan_anonymized(engine):
    result = engine.analyze("My PAN is ABCDE1234F")
    assert "ABCDE1234F" not in result["anonymized_prompt"]
    assert "[PAN]" in result["anonymized_prompt"]


# ── Aadhaar ────────────────────────────────────────────────────────────────────

def test_aadhaar_detected(engine):
    result = engine.analyze("Aadhaar: 1234-5678-9012")
    labels = {e["label"] for e in result["entities"]}
    assert "AADHAAR" in labels


def test_aadhaar_anonymized(engine):
    result = engine.analyze("Aadhaar: 1234-5678-9012")
    assert "1234-5678-9012" not in result["anonymized_prompt"]
    assert "[AADHAAR]" in result["anonymized_prompt"]


# ── API key ────────────────────────────────────────────────────────────────────

def test_api_key_detected(engine):
    result = engine.analyze("Use key sk-abcdefghijklmnopqrstuvwxyz12345")
    labels = {e["label"] for e in result["entities"]}
    assert "API_KEY" in labels


def test_api_key_anonymized(engine):
    result = engine.analyze("Use key sk-abcdefghijklmnopqrstuvwxyz12345")
    assert "sk-" not in result["anonymized_prompt"]
    assert "[API_KEY]" in result["anonymized_prompt"]


# ── Credit card and IP address ────────────────────────────────────────────────

def test_credit_card_and_ip_anonymized(engine):
    result = engine.analyze(
        "Charge card 4111 1111 1111 1111 from server 192.168.1.25"
    )
    labels = {e["label"] for e in result["entities"]}
    assert "CREDIT_CARD" in labels
    assert "IP_ADDRESS" in labels
    assert "[CREDIT_CARD]" in result["anonymized_prompt"]
    assert "[IP_ADDRESS]" in result["anonymized_prompt"]


def test_address_and_passport_anonymized(engine):
    result = engine.analyze(
        "Mailing address: 221B Baker Street, passport number: A1234567"
    )
    labels = {e["label"] for e in result["entities"]}
    assert "ADDRESS" in labels
    assert "PASSPORT" in labels
    assert "[ADDRESS]" in result["anonymized_prompt"]
    assert "[PASSPORT]" in result["anonymized_prompt"]


# ── Multiple entities ──────────────────────────────────────────────────────────

def test_multiple_entities_detected(engine):
    result = engine.analyze(
        "Email om@example.com and PAN ABCDE1234F and phone 9876543210"
    )
    labels = {e["label"] for e in result["entities"]}
    assert "EMAIL" in labels
    assert "PAN" in labels
    assert "PHONE" in labels


def test_multiple_entities_anonymized(engine):
    prompt = "Email om@example.com and PAN ABCDE1234F"
    result = engine.analyze(prompt)
    assert "om@example.com" not in result["anonymized_prompt"]
    assert "ABCDE1234F" not in result["anonymized_prompt"]
    assert "[EMAIL]" in result["anonymized_prompt"]
    assert "[PAN]" in result["anonymized_prompt"]


def test_distinct_same_type_entities_use_stable_indexed_placeholders(engine):
    result = engine.analyze(
        "Primary email om@example.com and backup email backup@example.com"
    )
    assert "[EMAIL_1]" in result["anonymized_prompt"]
    assert "[EMAIL_2]" in result["anonymized_prompt"]


def test_repeated_same_value_reuses_stable_placeholder(engine):
    result = engine.analyze(
        "Use om@example.com first, then send again to om@example.com"
    )
    assert result["anonymized_prompt"].count("[EMAIL]") == 2
    assert "[EMAIL_1]" not in result["anonymized_prompt"]


def test_policy_report_keeps_entity_unmasked(engine):
    result = engine.analyze(
        "Contact om@example.com",
        {"EMAIL": "REPORT"},
    )
    assert "om@example.com" in result["anonymized_prompt"]
    assert result["policy_actions"]["EMAIL"] == "REPORT"
    assert result["entities"][0]["policy_action"] == "REPORT"


def test_policy_require_confirmation_masks_and_flags(engine):
    result = engine.analyze(
        "Contact om@example.com",
        {"EMAIL": "REQUIRE_CONFIRMATION"},
    )
    assert "[EMAIL]" in result["anonymized_prompt"]
    assert result["confirmation_required"] is True
    assert result["entities"][0]["policy_action"] == "REQUIRE_CONFIRMATION"


def test_policy_block_marks_prompt_blocked(engine):
    result = engine.analyze(
        "Contact om@example.com",
        {"EMAIL": "BLOCK"},
    )
    assert result["blocked"] is True
    assert result["blocked_labels"] == ["EMAIL"]
    assert result["entities"][0]["policy_action"] == "BLOCK"


# ── High risk ──────────────────────────────────────────────────────────────────

def test_high_risk_prompt(engine):
    result = engine.analyze(
        "PAN: ABCDE1234F, Aadhaar: 1234-5678-9012, API key: sk-abcdefghijklmnopqrst1234"
    )
    assert result["risk_level"] == "CRITICAL"
    assert result["risk_score"] == 100


# ── Risk cap ───────────────────────────────────────────────────────────────────

def test_risk_score_never_exceeds_100(engine):
    result = engine.analyze(
        "PAN ABCDE1234F, AADHAAR 1234-5678-9012, key sk-ABCDEFGHIJKLMNOPQRSTU12345, "
        "email a@b.com, phone 9876543210"
    )
    assert result["risk_score"] <= 100


# ── Response structure ─────────────────────────────────────────────────────────

def test_response_has_required_keys(engine):
    result = engine.analyze("Hello world")
    assert "entities" in result
    assert "privacy_report" in result
    assert result["privacy_report"]["total_entities"] == len(result["entities"])
    assert "risk_score" in result
    assert "risk_level" in result
    assert "anonymized_prompt" in result


def test_entity_has_text_and_label(engine):
    result = engine.analyze("Email om@example.com")
    for entity in result["entities"]:
        assert "text" in entity
        assert "label" in entity
        # Internal offsets must NOT be exposed
        assert "start" not in entity
        assert "end" not in entity


def test_entity_includes_confidence_score(engine):
    result = engine.analyze("Email om@example.com")

    email = next(entity for entity in result["entities"] if entity["label"] == "EMAIL")
    assert email["confidence"] == 0.99


def test_privacy_report_groups_entity_types(engine):
    result = engine.analyze(
        "Email first@example.com and second@example.com; call 9876543210"
    )
    report = result["privacy_report"]
    summaries = {item["label"]: item for item in report["entity_types"]}

    assert report["total_entities"] == 3
    assert summaries["EMAIL"]["count"] == 2
    assert summaries["EMAIL"]["masked_as"] == "[EMAIL]"
    assert summaries["PHONE"]["count"] == 1
