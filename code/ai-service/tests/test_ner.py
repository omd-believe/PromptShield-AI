from app.services.ner import NERDetector


def test_person_detection():

    detector = NERDetector()

    result = detector.detect(
        "Barack Obama was the president of the United States."
    )

    assert any(
        entity["text"] == "Barack Obama"
        and entity["label"] == "PERSON"
        for entity in result
    )


def test_location_detection():

    detector = NERDetector()

    result = detector.detect(
        "I live in Sangli."
    )

    assert any(
        entity["text"] == "Sangli"
        and entity["label"] == "GPE"
        for entity in result
    )


def test_organization_detection():

    detector = NERDetector()

    result = detector.detect(
        "I study at Walchand College of Engineering."
    )

    assert any(
        entity["text"] == "Walchand College of Engineering"
        and entity["label"] == "ORG"
        for entity in result
    )