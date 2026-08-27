from app.services.risk import PrivacyRiskScorer


def test_low_risk():

    scorer = PrivacyRiskScorer()

    entities = [
        {
            "text": "Google",
            "label": "ORG"
        }
    ]

    result = scorer.analyze(entities)

    assert result["score"] == 5
    assert result["level"] == "LOW"


def test_medium_risk():

    scorer = PrivacyRiskScorer()

    entities = [
        {
            "text": "rahul@gmail.com",
            "label": "EMAIL"
        }
    ]

    result = scorer.analyze(entities)

    assert result["score"] == 20
    assert result["level"] == "MEDIUM"


def test_high_risk():

    scorer = PrivacyRiskScorer()

    entities = [
        {
            "text": "Rahul",
            "label": "PERSON"
        },
        {
            "text": "9876543210",
            "label": "PHONE"
        },
        {
            "text": "rahul@gmail.com",
            "label": "EMAIL"
        }
    ]

    result = scorer.analyze(entities)

    assert result["score"] == 55
    assert result["level"] == "HIGH"


def test_critical_risk():

    scorer = PrivacyRiskScorer()

    entities = [
        {
            "text": "ABCDE1234F",
            "label": "PAN"
        },
        {
            "text": "1234-5678-9012",
            "label": "AADHAAR"
        },
        {
            "text": "sk-very-secret-api-key",
            "label": "API_KEY"
        }
    ]

    result = scorer.analyze(entities)

    assert result["score"] == 100
    assert result["level"] == "CRITICAL"