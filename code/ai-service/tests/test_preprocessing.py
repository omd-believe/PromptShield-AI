"""
Tests for the Preprocessor service.

Covers:
- Normal whitespace normalization
- Repeated punctuation removal
- Empty/whitespace-only input (should raise ValueError)
- Oversized input (should raise ValueError)
- Multiline input
- Unicode normalization
- Blank line collapsing
"""

import pytest

from app.services.preprocessing import Preprocessor


@pytest.fixture
def preprocessor() -> Preprocessor:
    return Preprocessor()


# ── Whitespace normalization ───────────────────────────────────────────────────

def test_normalize_leading_trailing_whitespace(preprocessor):
    assert preprocessor.clean("   hello world   ") == "hello world"


def test_normalize_internal_whitespace(preprocessor):
    assert preprocessor.clean("Explain    Java    Streams") == "Explain Java Streams"


def test_normalize_tabs_and_spaces(preprocessor):
    assert preprocessor.clean("hello\t\tworld") == "hello world"


def test_normalize_mixed_whitespace(preprocessor):
    result = preprocessor.clean("   Explain    Java    Streams   ")
    assert result == "Explain Java Streams"


# ── Repeated punctuation ───────────────────────────────────────────────────────

def test_remove_repeated_exclamation(preprocessor):
    assert preprocessor.clean("Explain Java Streams!!!!") == "Explain Java Streams!"


def test_remove_repeated_question_marks(preprocessor):
    assert preprocessor.clean("What is Java???") == "What is Java?"


def test_remove_repeated_commas(preprocessor):
    assert preprocessor.clean("Hello,,, world") == "Hello, world"


def test_single_punctuation_preserved(preprocessor):
    assert preprocessor.clean("Hello world!") == "Hello world!"


# ── Multiline input ────────────────────────────────────────────────────────────

def test_multiline_whitespace_per_line(preprocessor):
    result = preprocessor.clean("  Line one  \n  Line two  ")
    assert result == "Line one\nLine two"


def test_collapse_multiple_blank_lines(preprocessor):
    result = preprocessor.clean("First\n\n\n\nSecond")
    assert result == "First\n\nSecond"


def test_preserve_single_blank_line(preprocessor):
    result = preprocessor.clean("First\n\nSecond")
    assert result == "First\n\nSecond"


# ── Empty / invalid input ──────────────────────────────────────────────────────

def test_empty_string_raises(preprocessor):
    with pytest.raises(ValueError, match="empty"):
        preprocessor.clean("")


def test_whitespace_only_raises(preprocessor):
    with pytest.raises(ValueError, match="empty"):
        preprocessor.clean("     ")


def test_newline_only_raises(preprocessor):
    with pytest.raises(ValueError, match="empty"):
        preprocessor.clean("\n\n\n")


def test_none_raises(preprocessor):
    with pytest.raises((ValueError, AttributeError)):
        preprocessor.clean(None)  # type: ignore[arg-type]


# ── Oversized input ────────────────────────────────────────────────────────────

def test_oversized_prompt_raises(preprocessor):
    long_prompt = "a" * 9000  # exceeds default 8000 limit
    with pytest.raises(ValueError, match="maximum allowed length"):
        preprocessor.clean(long_prompt)


def test_max_length_boundary_accepted(preprocessor):
    # Exactly at the limit — should not raise
    prompt = "a" * 8000
    result = preprocessor.clean(prompt)
    assert len(result) == 8000


# ── Unicode normalization ──────────────────────────────────────────────────────

def test_unicode_text_preserved(preprocessor):
    result = preprocessor.clean("नमस्ते")
    assert result == "नमस्ते"


def test_unicode_with_whitespace(preprocessor):
    result = preprocessor.clean("   नमस्ते   ")
    assert result == "नमस्ते"


def test_preserve_code_fence_formatting(preprocessor):
    prompt = "Please explain:\n```python\n  def  greet():\n    return 'Please'\n```"
    result = preprocessor.clean(prompt)
    assert "  def  greet():" in result
    assert "return 'Please'" in result


def test_preserve_structured_json_line(preprocessor):
    prompt = 'Return JSON: {"message": "Please keep this"}'
    assert preprocessor.clean(prompt) == prompt