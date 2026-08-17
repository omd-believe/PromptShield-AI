from app.services.preprocessing import Preprocessor


def test_normalize_whitespace():

    preprocessor = Preprocessor()

    result = preprocessor.clean(
        "   Explain    Java    Streams   "
    )

    assert result == "Explain Java Streams"


def test_remove_repeated_punctuation():

    preprocessor = Preprocessor()

    result = preprocessor.clean(
        "Explain Java Streams!!!!"
    )

    assert result == "Explain Java Streams!"