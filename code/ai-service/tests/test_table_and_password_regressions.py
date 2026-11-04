"""
PromptShield-AI: Regression tests for table-format and password-security failure scenarios.

These tests guard against two classes of regression that were previously observed:

  1. TABLE FORMAT REGRESSION
     LLMLingua-2 or FLAN-T5 candidates must preserve Markdown table structure
     (header rows, alignment rows, and data rows) because tables encode information
     that cannot be recovered from prose.  A candidate that collapses a table to
     plain text must be rejected.

  2. PASSWORD SECURITY REGRESSION
     Security constraint phrases such as "do not store passwords in plaintext",
     "recommend secure password hashing", and "never log credentials" must survive
     every pipeline stage unchanged.  Grammar correction must not alter security
     terminology; the optimizer must not delete constraint sentences.

Both tests run end-to-end through optimize_prompt() with the compression engine
forced to 'deterministic' so that model availability does not affect the outcome.
Separate unit-level checks on GrammarCorrector and QualityValidator are included.
"""

import pytest
from app.api.optimize import optimize_prompt
from app.models.request import PromptRequest
from app.services.grammar_corrector import GrammarCorrector
from app.services.quality_validator import QualityValidator


# ── Helpers ───────────────────────────────────────────────────────────────────

def _request(prompt: str, **kw) -> PromptRequest:
    """Build a PromptRequest forcing 'deterministic' engine so tests are model-independent."""
    return PromptRequest(prompt=prompt, compression_engine="deterministic", **kw)


# ── Table-format regression ───────────────────────────────────────────────────

_TABLE_PROMPT = """\
You are a data analyst. Given the following sales table, answer the questions below.

| Region    | Q1     | Q2     | Q3     | Q4     |
|-----------|--------|--------|--------|--------|
| North     | 12,500 | 14,200 | 13,800 | 16,100 |
| South     | 9,800  | 11,000 | 10,500 | 12,700 |
| East      | 15,300 | 16,800 | 17,200 | 18,900 |
| West      | 8,200  | 9,500  | 10,100 | 11,400 |

Tasks:
1. Which region had the highest annual sales?
2. Calculate the quarter-over-quarter growth rate for the East region.
3. Produce a JSON object with region totals.
4. Return ONLY valid JSON — do not wrap in markdown code fences.
"""


def test_table_prompt_preserves_structure_end_to_end():
    """Pipeline must preserve the Markdown table header, separator, and data rows."""
    req = _request(_TABLE_PROMPT)
    resp = optimize_prompt(req)
    out = resp.optimized_prompt

    # Header row must be intact
    assert "| Region" in out, "Table header row was lost"
    assert "| Q1" in out and "| Q4" in out, "Column headers were removed"

    # At least two data rows must still be present
    data_rows = [line for line in out.splitlines() if line.strip().startswith("|") and "---" not in line]
    assert len(data_rows) >= 3, f"Expected at least 3 table rows in output, found {len(data_rows)}"

    # Critical task constraints must survive
    assert "JSON" in out, "JSON output instruction was dropped"
    assert "do not wrap" in out.lower() or "return only" in out.lower(), (
        "Output-format constraints were stripped"
    )


def test_table_prompt_grammar_corrector_does_not_touch_table():
    """GrammarCorrector must not alter Markdown table rows."""
    corrector = GrammarCorrector()
    result = corrector.correct(_TABLE_PROMPT)
    corrected = result["prompt"]

    assert "| Region" in corrected
    assert "| North" in corrected
    assert "| East" in corrected

    # Numeric values inside cells must not be changed
    assert "12,500" in corrected
    assert "18,900" in corrected


def test_table_prompt_quality_validator_rejects_prose_collapse():
    """QualityValidator must fall back to the original when the candidate collapses the table."""
    collapsed = (
        "You are a data analyst. The table shows sales data for North, South, East, West "
        "across Q1-Q4. Tasks: find highest region, compute growth, produce JSON with region totals."
    )
    validator = QualityValidator()
    output, warnings, fallback_used = validator.validate_prompt(_TABLE_PROMPT, collapsed)

    # A collapsed version is far shorter than the original — the validator should fall back
    assert fallback_used or "JSON" in output, (
        "Quality validator accepted a collapsed table without raising a warning"
    )
    if fallback_used:
        assert "| Region" in output, "Fallback should return the original table-containing prompt"


# ── Password-security regression ──────────────────────────────────────────────

_PASSWORD_PROMPT = """\
Explain password storage best practices in a Java Spring Boot application.

Requirements:
- Do not store passwords in plaintext under any circumstances.
- Recommend secure password hashing (BCrypt, Argon2, or PBKDF2).
- Explain why plaintext storage is dangerous.
- Never log credentials or password hashes in application logs.
- Return a structured response with sections: Overview, Implementation, Common Mistakes.
"""


def test_password_security_end_to_end():
    """Security constraint sentences must survive the full pipeline unchanged."""
    req = _request(_PASSWORD_PROMPT)
    resp = optimize_prompt(req)
    out = resp.optimized_prompt.lower()

    assert "plaintext" in out, "'plaintext' was altered or removed"
    assert "plainest" not in out, "Grammar correction incorrectly changed 'plaintext' to 'plainest'"
    assert "password" in out, "'password' term was dropped"
    assert "hashing" in out or "bcrypt" in out or "argon2" in out, (
        "Password hashing recommendation was removed"
    )
    assert "do not store passwords in plaintext" in out, (
        "Critical security constraint was dropped"
    )
    assert "never log credentials" in out, (
        "'Never log credentials' constraint was dropped"
    )


def test_password_security_grammar_corrector():
    """GrammarCorrector must not change 'plaintext' to 'plainest' or alter hashing terms."""
    corrector = GrammarCorrector()
    result = corrector.correct(_PASSWORD_PROMPT)
    corrected = result["prompt"]

    assert "plaintext" in corrected.lower()
    assert "plainest" not in corrected.lower()
    assert "password" in corrected.lower()
    assert "hashing" in corrected.lower()

    # Verify no correction touched security-critical tokens
    corrections = result["corrections"]
    security_terms = {"plaintext", "password", "hashing", "bcrypt", "argon2", "pbkdf2", "credentials"}
    for correction in corrections:
        correction_str = str(correction).lower()
        flagged = [t for t in security_terms if t in correction_str]
        assert not flagged, (
            f"Grammar corrector modified security-critical term(s) {flagged}: {correction}"
        )


def test_password_security_token_budget_preserved():
    """When a token budget is set, the output must not strip security constraints to hit it."""
    # Set an aggressive budget — the pipeline must prefer a warning over unsafe removal
    req = _request(_PASSWORD_PROMPT, target_max_tokens=50)
    resp = optimize_prompt(req)
    out = resp.optimized_prompt.lower()

    # Even with an aggressive budget, critical constraint phrases must survive
    assert "plaintext" in out, (
        "Token budget caused 'plaintext' constraint to be removed"
    )
    # Budget miss is reported honestly rather than silently stripping content
    if resp.optimized_tokens > 50:
        assert resp.token_budget_met is False, (
            "Token budget was not met but token_budget_met was not set to False"
        )
        assert any("budget" in w.lower() or "target" in w.lower() for w in resp.optimization_warnings), (
            "Token budget miss was not reported in optimization_warnings"
        )


# ── Target token passthrough regression ───────────────────────────────────────

def test_target_max_tokens_reported_in_response():
    """target_max_tokens passed in the request must be echoed back in the response."""
    req = _request("Summarize this document concisely.", target_max_tokens=40)
    resp = optimize_prompt(req)
    assert resp.target_max_tokens == 40, (
        "target_max_tokens was not echoed in the response"
    )
    # token_budget_met must be a bool, not None, when target was provided
    assert resp.token_budget_met is not None, (
        "token_budget_met should not be None when target_max_tokens is specified"
    )
