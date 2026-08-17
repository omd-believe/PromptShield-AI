from app.services.privacy import PrivacyDetector


def test_email_detection():

    detector = PrivacyDetector()

    result = detector.detect(
        "Contact me at omd@gmail.com"
    )

    assert "EMAIL" in result
    assert "omd@gmail.com" in result["EMAIL"]


def test_phone_detection():

    detector = PrivacyDetector()

    result = detector.detect(
        "My phone number is 9876543210"
    )

    assert "PHONE" in result


def test_no_sensitive_data():

    detector = PrivacyDetector()

    result = detector.detect(
        "Explain Java Streams"
    )

    assert result == {}


def test_email_anonymization():

    detector = PrivacyDetector()

    result = detector.anonymize(
        "My email is omd@gmail.com"
    )

    assert result == "My email is [EMAIL]"