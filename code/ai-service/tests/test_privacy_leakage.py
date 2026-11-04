from app.api.optimize import optimize_prompt
from app.models.request import PromptRequest


def test_optimization_reports_privacy_validity():
    result = optimize_prompt(
        PromptRequest(prompt="Please summarize the report from john@example.com.")
    )

    assert result.privacy_valid is True
    assert result.leakage_detected is False
    assert "john@example.com" not in result.optimized_prompt


def test_clean_prompt_has_no_privacy_leakage():
    result = optimize_prompt(PromptRequest(prompt="Summarize this report."))

    assert result.privacy_valid is True
    assert result.leakage_detected is False
