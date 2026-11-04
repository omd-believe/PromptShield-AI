"""
Tests for the TokenCounter service.

Covers:
- Normal text counting
- Empty/whitespace-only input
- Single word
- Division-by-zero protection in reduction_percentage
- Reduction percentage calculation
- Negative reduction (optimized longer than original)
"""

import pytest

from app.services.token_counter import TokenCounter


@pytest.fixture
def counter() -> TokenCounter:
    return TokenCounter()


# ── count() ────────────────────────────────────────────────────────────────────

def test_normal_sentence(counter):
    assert counter.count("Hello world how are you") == len(
        counter._encoding.encode("Hello world how are you")
    )


def test_single_word(counter):
    assert counter.count("Hello") == len(counter._encoding.encode("Hello"))


def test_empty_string_returns_zero(counter):
    assert counter.count("") == 0


def test_whitespace_only_returns_zero(counter):
    assert counter.count("     ") == 0


def test_newline_only_returns_zero(counter):
    assert counter.count("\n\n") == 0


def test_multiline_counted(counter):
    assert counter.count("Hello\nworld") == len(
        counter._encoding.encode("Hello\nworld")
    )


def test_multiple_spaces_counted_as_single(counter):
    assert counter.count("Hello  world") == len(
        counter._encoding.encode("Hello  world")
    )


# ── reduction_percentage() ─────────────────────────────────────────────────────

def test_no_reduction(counter):
    assert counter.reduction_percentage(10, 10) == 0.0


def test_full_reduction_impossible():
    # Can't be 100% without original=0 edge
    c = TokenCounter()
    result = c.reduction_percentage(10, 0)
    assert result == 100.0


def test_zero_original_returns_zero(counter):
    """Division by zero protection."""
    assert counter.reduction_percentage(0, 5) == 0.0


def test_normal_reduction(counter):
    # 10 → 8 words = 20% reduction
    result = counter.reduction_percentage(10, 8)
    assert result == 20.0


def test_reduction_rounded_to_2dp(counter):
    # 3 → 2 = 33.33...%
    result = counter.reduction_percentage(3, 2)
    assert result == 33.33


def test_negative_original_returns_zero(counter):
    """Negative original count treated as invalid."""
    assert counter.reduction_percentage(-1, 5) == 0.0
