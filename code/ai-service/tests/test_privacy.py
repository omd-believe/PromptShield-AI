"""
Tests for the PrivacyDetector (regex-based detection).

Covers:
- Detection of all seven categories: EMAIL, PHONE, PAN, AADHAAR, API_KEY,
  DATE_OF_BIRTH, BANK_ACCOUNT
- Common formatting variations for each category
- False positive resistance
- Multiple entities in one prompt
- Character offsets returned correctly
"""

import pytest

from app.services.privacy import PrivacyDetector


@pytest.fixture
def detector() -> PrivacyDetector:
    return PrivacyDetector()


# ── EMAIL detection ────────────────────────────────────────────────────────────

def test_email_detected(detector):
    matches = detector.detect("Contact me at om@example.com")
    labels = [m.label for m in matches]
    assert "EMAIL" in labels


def test_email_text(detector):
    matches = detector.detect("Contact me at om@example.com")
    texts = [m.text for m in matches if m.label == "EMAIL"]
    assert "om@example.com" in texts


def test_email_with_plus(detector):
    matches = detector.detect("Email: user+tag@domain.co.in")
    assert any(m.label == "EMAIL" for m in matches)


def test_email_subdomain(detector):
    matches = detector.detect("user@mail.example.org")
    assert any(m.label == "EMAIL" for m in matches)


def test_no_email_false_positive(detector):
    # Plain word without @ should not match
    matches = detector.detect("Summarize this document clearly")
    assert not any(m.label == "EMAIL" for m in matches)


# ── PHONE detection ────────────────────────────────────────────────────────────

def test_phone_bare_10_digit(detector):
    matches = detector.detect("My phone is 9876543210")
    assert any(m.label == "PHONE" for m in matches)


def test_phone_with_isd_space(detector):
    matches = detector.detect("Call me at +91 9876543210")
    assert any(m.label == "PHONE" for m in matches)


def test_phone_with_isd_hyphen(detector):
    matches = detector.detect("Call +91-9876543210 for help")
    assert any(m.label == "PHONE" for m in matches)


def test_phone_with_isd_no_separator(detector):
    matches = detector.detect("Reach me: +919876543210")
    assert any(m.label == "PHONE" for m in matches)


def test_phone_invalid_start_digit_not_matched(detector):
    # Indian mobile must start with 6-9; 1234567890 should not match
    matches = detector.detect("Number: 1234567890")
    assert not any(m.label == "PHONE" for m in matches)


# ── PAN detection ──────────────────────────────────────────────────────────────

def test_pan_detected(detector):
    matches = detector.detect("My PAN is ABCDE1234F")
    assert any(m.label == "PAN" for m in matches)


def test_pan_text(detector):
    matches = detector.detect("PAN: ABCDE1234F")
    texts = [m.text for m in matches if m.label == "PAN"]
    assert "ABCDE1234F" in texts


def test_pan_lowercase_not_matched(detector):
    # PAN must be uppercase
    matches = detector.detect("pan: abcde1234f")
    assert not any(m.label == "PAN" for m in matches)


def test_pan_partial_not_matched(detector):
    # Too short — should not match
    matches = detector.detect("Code: ABCDE123")
    assert not any(m.label == "PAN" for m in matches)


# ── AADHAAR detection ──────────────────────────────────────────────────────────

def test_aadhaar_with_space(detector):
    matches = detector.detect("Aadhaar: 1234 5678 9012")
    assert any(m.label == "AADHAAR" for m in matches)


def test_aadhaar_with_hyphen(detector):
    matches = detector.detect("UID: 1234-5678-9012")
    assert any(m.label == "AADHAAR" for m in matches)


def test_aadhaar_text(detector):
    matches = detector.detect("My Aadhaar is 1234-5678-9012")
    texts = [m.text for m in matches if m.label == "AADHAAR"]
    assert "1234-5678-9012" in texts


def test_aadhaar_16_digits_not_matched(detector):
    # 16 digits is too many — should not match
    matches = detector.detect("1234 5678 9012 3456")
    # May or may not match first 12 digits; key: no 16-digit match
    for m in matches:
        if m.label == "AADHAAR":
            assert len(m.text.replace(" ", "").replace("-", "")) == 12


# ── API_KEY detection ──────────────────────────────────────────────────────────

def test_openai_style_key_detected(detector):
    matches = detector.detect("Key: sk-abcdefghijklmnopqrstu123456")
    assert any(m.label == "API_KEY" for m in matches)


def test_google_style_key_detected(detector):
    matches = detector.detect("Use AIzaAbcDefGhIjKlMnOpQrStUvWxYz12")
    assert any(m.label == "API_KEY" for m in matches)


def test_short_sk_not_matched(detector):
    # sk- followed by fewer than 20 chars — should not match
    matches = detector.detect("sk-short")
    assert not any(m.label == "API_KEY" for m in matches)


# ── Secret and credential detection ────────────────────────────────────────────

def test_jwt_detected(detector):
    value = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.signaturevalue123"
    matches = detector.detect(f"Authorization: Bearer {value}")
    assert any(m.label == "JWT" for m in matches)


def test_private_key_detected(detector):
    value = "-----BEGIN PRIVATE KEY-----\nMIIEfakekeymaterial\n-----END PRIVATE KEY-----"
    matches = detector.detect(value)
    assert any(m.label == "PRIVATE_KEY" for m in matches)


def test_database_url_detected(detector):
    matches = detector.detect("DATABASE_URL=postgresql://user:pass@db.example/app")
    assert any(m.label == "DATABASE_URL" for m in matches)


def test_cloud_credential_detected(detector):
    matches = detector.detect("AWS key: AKIAIOSFODNN7EXAMPLE")
    assert any(m.label == "CLOUD_CREDENTIAL" for m in matches)


def test_webhook_secret_detected(detector):
    matches = detector.detect(
        "webhook secret: whsec_7f3e9a1b2c4d5e6f7a8b9c0d1e2f3a4b"
    )
    assert any(m.label == "WEBHOOK_SECRET" for m in matches)


def test_generic_low_entropy_token_not_detected(detector):
    matches = detector.detect("token: aaaaaaaaaaaaaaaaaaaaaaaa")
    assert not any(m.label == "GENERIC_SECRET" for m in matches)


# ── Context-sensitive PII detection ───────────────────────────────────────────

def test_date_of_birth_detected_only_with_context(detector):
    matches = detector.detect("DOB: 12/04/1990")
    assert any(m.label == "DATE_OF_BIRTH" and m.text == "12/04/1990" for m in matches)


def test_unlabelled_date_not_treated_as_date_of_birth(detector):
    matches = detector.detect("The report was created on 12/04/1990")
    assert not any(m.label == "DATE_OF_BIRTH" for m in matches)


def test_bank_account_detected_with_context(detector):
    matches = detector.detect("Bank account number: 123456789012")
    assert any(
        m.label == "BANK_ACCOUNT" and m.text == "123456789012"
        for m in matches
    )


def test_unlabelled_long_number_not_treated_as_bank_account(detector):
    matches = detector.detect("Order reference: 123456789012")
    assert not any(m.label == "BANK_ACCOUNT" for m in matches)


# ── Multilingual contextual detection ──────────────────────────────────────────

@pytest.mark.parametrize(
    ("prompt", "label", "value"),
    [
        ("Fecha de nacimiento: 12/04/1990", "DATE_OF_BIRTH", "12/04/1990"),
        ("Date de naissance: 12/04/1990", "DATE_OF_BIRTH", "12/04/1990"),
        ("जन्म तिथि: 12/04/1990", "DATE_OF_BIRTH", "12/04/1990"),
        ("Cuenta bancaria: 123456789012", "BANK_ACCOUNT", "123456789012"),
        ("Compte bancaire: 123456789012", "BANK_ACCOUNT", "123456789012"),
        ("बैंक खाता: 123456789012", "BANK_ACCOUNT", "123456789012"),
        ("Dirección: 221B Baker Street", "ADDRESS", "221B Baker Street"),
        ("Adresse: 221B Baker Street", "ADDRESS", "221B Baker Street"),
        ("पता: 221B Baker Street", "ADDRESS", "221B Baker Street"),
        ("Pasaporte número: A1234567", "PASSPORT", "A1234567"),
        ("पासपोर्ट संख्या: A1234567", "PASSPORT", "A1234567"),
        ("Licencia de conducir: DL12345", "DRIVER_LICENSE", "DL12345"),
        ("ड्राइविंग लाइसेंस: DL12345", "DRIVER_LICENSE", "DL12345"),
    ],
)
def test_multilingual_context_detected(detector, prompt, label, value):
    matches = detector.detect(prompt)
    assert any(
        match.label == label and match.text == value
        for match in matches
    )


# ── Credit card and network identity detection ────────────────────────────────

def test_luhn_valid_credit_card_detected(detector):
    matches = detector.detect("Card: 4111 1111 1111 1111")
    assert any(
        m.label == "CREDIT_CARD" and m.text == "4111 1111 1111 1111"
        for m in matches
    )


def test_invalid_credit_card_not_detected(detector):
    matches = detector.detect("Card: 4111 1111 1111 1112")
    assert not any(m.label == "CREDIT_CARD" for m in matches)


def test_valid_ipv4_detected(detector):
    matches = detector.detect("Server address: 192.168.1.25")
    assert any(m.label == "IP_ADDRESS" and m.text == "192.168.1.25" for m in matches)


def test_invalid_ipv4_not_detected(detector):
    matches = detector.detect("Version: 999.1.1.1")
    assert not any(m.label == "IP_ADDRESS" for m in matches)


def test_contextual_address_detected(detector):
    matches = detector.detect("Mailing address: 221B Baker Street, London")
    assert any(
        m.label == "ADDRESS" and m.text == "221B Baker Street"
        for m in matches
    )


def test_unlabelled_street_text_not_detected_as_address(detector):
    matches = detector.detect("The office is at 221B Baker Street")
    assert not any(m.label == "ADDRESS" for m in matches)


def test_contextual_passport_detected(detector):
    matches = detector.detect("Passport number: A1234567")
    assert any(m.label == "PASSPORT" and m.text == "A1234567" for m in matches)


def test_unlabelled_passport_like_value_not_detected(detector):
    matches = detector.detect("Reference: A1234567")
    assert not any(m.label == "PASSPORT" for m in matches)


def test_ssn_detected_with_context(detector):
    matches = detector.detect("Social Security number: 123-45-6789")
    assert any(
        m.label == "SSN" and m.text == "123-45-6789"
        for m in matches
    )


def test_invalid_ssn_not_detected(detector):
    matches = detector.detect("SSN: 000-12-3456")
    assert not any(m.label == "SSN" for m in matches)


def test_unlabelled_ssn_not_detected(detector):
    matches = detector.detect("Reference: 123-45-6789")
    assert not any(m.label == "SSN" for m in matches)


def test_driver_license_detected_with_context(detector):
    matches = detector.detect("Driver license number: D1234-5678")
    assert any(
        m.label == "DRIVER_LICENSE" and m.text == "D1234-5678"
        for m in matches
    )


def test_unlabelled_driver_license_not_detected(detector):
    matches = detector.detect("Reference: D1234-5678")
    assert not any(m.label == "DRIVER_LICENSE" for m in matches)


def test_uk_nino_detected_with_context(detector):
    matches = detector.detect("National Insurance number: AB123456C")
    assert any(
        m.label == "UK_NINO" and m.text == "AB123456C"
        for m in matches
    )


def test_unlabelled_uk_nino_not_detected(detector):
    matches = detector.detect("Reference: AB123456C")
    assert not any(m.label == "UK_NINO" for m in matches)


def test_canadian_sin_detected_with_context(detector):
    matches = detector.detect("Canadian SIN: 046-454-286")
    assert any(
        m.label == "CANADIAN_SIN" and m.text == "046-454-286"
        for m in matches
    )


def test_invalid_canadian_sin_not_detected(detector):
    matches = detector.detect("SIN: 123-456-789")
    assert not any(m.label == "CANADIAN_SIN" for m in matches)


def test_valid_iban_detected_with_context(detector):
    matches = detector.detect("IBAN: GB82 WEST 1234 5698 7654 32")
    assert any(
        m.label == "IBAN" and m.text == "GB82 WEST 1234 5698 7654 32"
        for m in matches
    )


def test_invalid_iban_not_detected(detector):
    matches = detector.detect("IBAN: GB82 WEST 1234 5698 7654 31")
    assert not any(m.label == "IBAN" for m in matches)


def test_unlabelled_iban_not_detected(detector):
    matches = detector.detect("Reference: GB82 WEST 1234 5698 7654 32")
    assert not any(m.label == "IBAN" for m in matches)


def test_eu_tax_id_detected_with_context(detector):
    matches = detector.detect("VAT number: DE136695976")
    assert any(
        m.label == "EU_TAX_ID" and m.text == "DE136695976"
        for m in matches
    )


def test_unlabelled_eu_tax_id_not_detected(detector):
    matches = detector.detect("Reference: DE136695976")
    assert not any(m.label == "EU_TAX_ID" for m in matches)


# ── Multiple entities ──────────────────────────────────────────────────────────

def test_multiple_entities_in_one_prompt(detector):
    prompt = "Email om@example.com and phone 9876543210"
    matches = detector.detect(prompt)
    labels = {m.label for m in matches}
    assert "EMAIL" in labels
    assert "PHONE" in labels


def test_detect_as_dicts_returns_dicts(detector):
    result = detector.detect_as_dicts("Email om@example.com")
    assert isinstance(result, list)
    assert all(isinstance(d, dict) for d in result)
    assert all("text" in d and "label" in d and "start" in d and "end" in d
               for d in result)


# ── Offsets ────────────────────────────────────────────────────────────────────

def test_email_offsets_correct(detector):
    prompt = "Contact me at om@example.com"
    matches = detector.detect(prompt)
    email_matches = [m for m in matches if m.label == "EMAIL"]
    assert len(email_matches) == 1
    m = email_matches[0]
    assert prompt[m.start:m.end] == "om@example.com"