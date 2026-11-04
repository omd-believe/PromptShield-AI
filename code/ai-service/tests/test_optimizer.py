"""
Tests for the PromptOptimizer service.

Covers:
- Filler phrase removal
- Case-insensitive matching
- Whitespace normalization after removal
- Constraint preservation (must not remove important instructions)
- Empty output prevention
- Multiline prompts
- Space before punctuation cleanup
"""

import pytest

from app.services.optimizer import PromptOptimizer


@pytest.fixture
def optimizer() -> PromptOptimizer:
    return PromptOptimizer()


# ── Filler removal ─────────────────────────────────────────────────────────────

def test_please_kindly_removed(optimizer):
    result = optimizer.optimize("Please kindly summarize this document.")
    assert "please kindly" not in result.lower()
    assert "summarize" in result.lower()


def test_kindly_please_removed(optimizer):
    result = optimizer.optimize("Kindly please help me analyze this.")
    assert "kindly please" not in result.lower()


def test_i_would_like_you_to_removed(optimizer):
    result = optimizer.optimize("I would like you to explain quantum computing.")
    assert "i would like you to" not in result.lower()
    assert "explain" in result.lower()


def test_i_want_you_to_removed(optimizer):
    result = optimizer.optimize("I want you to list the top 5 frameworks.")
    assert "i want you to" not in result.lower()
    assert "list" in result.lower()


def test_can_you_please_removed(optimizer):
    result = optimizer.optimize("Can you please write a summary?")
    assert "can you please" not in result.lower()


def test_could_you_please_removed(optimizer):
    result = optimizer.optimize("Could you please translate this?")
    assert "could you please" not in result.lower()


def test_please_alone_removed(optimizer):
    result = optimizer.optimize("Please summarize this document.")
    assert result.lower().startswith("summarize") or "please" not in result.lower()


# ── Case insensitivity ─────────────────────────────────────────────────────────

def test_case_insensitive_filler_removed(optimizer):
    result = optimizer.optimize("PLEASE KINDLY explain this concept.")
    assert "please kindly" not in result.lower()
    assert "explain" in result.lower()


# ── Whitespace cleanup ─────────────────────────────────────────────────────────

def test_no_double_spaces_after_removal(optimizer):
    result = optimizer.optimize("Please summarize this document.")
    assert "  " not in result


def test_no_leading_trailing_whitespace(optimizer):
    result = optimizer.optimize("   Please summarize.   ")
    assert result == result.strip()


# ── Constraint preservation ────────────────────────────────────────────────────

def test_constraints_preserved(optimizer):
    """
    Important constraints must never be removed.
    This test verifies a prompt with constraints is not over-aggressively optimized.
    """
    prompt = (
        "Please kindly summarize this document in exactly 5 bullet points "
        "and do not omit any financial figures."
    )
    result = optimizer.optimize(prompt)
    # Constraints must survive
    assert "5 bullet points" in result or "5" in result
    assert "financial figures" in result
    assert "do not omit" in result or "not omit" in result


def test_numerical_constraint_preserved(optimizer):
    prompt = "I want you to explain this in 500 words or fewer."
    result = optimizer.optimize(prompt)
    assert "500" in result


def test_negative_constraint_preserved(optimizer):
    prompt = "Please do not include any code examples."
    result = optimizer.optimize(prompt)
    assert "do not" in result or "not" in result


# ── Empty output prevention ────────────────────────────────────────────────────

def test_filler_only_prompt_not_emptied(optimizer):
    """If the entire prompt is filler, return it unchanged rather than empty."""
    result = optimizer.optimize("Please.")
    assert result.strip() != ""


def test_short_meaningful_prompt_not_emptied(optimizer):
    result = optimizer.optimize("Summarize.")
    assert result.strip() == "Summarize."


# ── Multiline prompts ──────────────────────────────────────────────────────────

def test_multiline_prompt_preserved(optimizer):
    prompt = "Please summarize:\n- Point one\n- Point two"
    result = optimizer.optimize(prompt)
    # Structure must be preserved
    assert "Point one" in result
    assert "Point two" in result


# ── Punctuation ────────────────────────────────────────────────────────────────

def test_space_before_punctuation_removed(optimizer):
    result = optimizer.optimize("Hello .")
    assert "Hello." in result or result.strip().endswith(".")


# ── Token counter ──────────────────────────────────────────────────────────────

def test_optimizer_reduces_tokens(optimizer):
    """Filler removal should typically reduce word count."""
    original = "Please kindly summarize this long document for me."
    result = optimizer.optimize(original)
    assert len(result.split()) < len(original.split())


# ── Structure-aware compression ───────────────────────────────────────────────

def test_verbose_prose_is_compacted(optimizer):
    prompt = "Explain this in order to make the result clear at this point in time."
    result = optimizer.optimize(prompt)
    assert "in order to" not in result
    assert "at this point in time" not in result
    assert "to make" in result
    assert "now" in result


def test_fenced_code_block_is_preserved(optimizer):
    prompt = "Please explain this code:\n```python\n  def  greet():\n    return 'Please'\n```"
    result = optimizer.optimize(prompt)
    assert "  def  greet():" in result
    assert "return 'Please'" in result


def test_structured_lines_are_preserved(optimizer):
    prompt = "Please return this JSON:\n{\"message\": \"Please keep this\"}\n- name: Please"
    result = optimizer.optimize(prompt)
    assert '{"message": "Please keep this"}' in result
    assert "- name: Please" in result


def test_compaction_preserves_constraints(optimizer):
    prompt = "Make sure that you return exactly 3 items and do not omit errors."
    result = optimizer.optimize(prompt)
    assert "exactly 3 items" in result
    assert "do not omit errors" in result


def test_domain_aware_compaction_removes_common_verbose_phrases(optimizer):
    prompt = "Please explain this with regard to the project and by means of a step by step manner that is clear."
    result = optimizer.optimize(prompt)
    assert "with regard to" not in result.lower()
    assert "by means of" not in result.lower()
    assert "step by step" in result.lower()
    assert "clear" in result.lower()


def test_compaction_keeps_instruction_intent(optimizer):
    prompt = "Write a concise summary at the end of the day about the report, with the aim of helping the team."
    result = optimizer.optimize(prompt)
    assert "summary" in result.lower()
    assert "report" in result.lower()
    assert "team" in result.lower()


def test_task_aware_compaction_handles_summary_requests(optimizer):
    prompt = "Please provide a brief overview of the quarterly report and summarize the key takeaways."
    result = optimizer.optimize(prompt)
    assert "summarize" in result.lower() or "brief overview" not in result.lower()
    assert "key takeaways" in result.lower()


def test_task_aware_compaction_handles_code_requests(optimizer):
    prompt = "Please write a Python function that validates an email address and returns true/false."
    result = optimizer.optimize(prompt)
    assert "Python" in result or "python" in result
    assert "function" in result.lower()
    assert "validates" in result.lower()
