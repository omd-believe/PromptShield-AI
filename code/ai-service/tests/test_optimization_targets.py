from app.api.optimize import optimize_prompt
from app.models.request import PromptRequest


def test_optional_targets_are_reported():
    result = optimize_prompt(
        PromptRequest(
            prompt="Please kindly summarize this document.",
            target_max_tokens=100,
            minimum_semantic_score=50,
            compression_engine="deterministic",
        )
    )

    assert result.target_max_tokens == 100
    assert result.minimum_semantic_score == 50
    assert result.token_budget_met is True
    assert result.semantic_valid is True
    assert result.optimization_warnings == []


def test_unmet_budget_is_reported_without_unsafe_truncation():
    result = optimize_prompt(
        PromptRequest(
            prompt="Explain the complete history of machine learning in detail.",
            target_max_tokens=1,
        )
    )

    assert result.token_budget_met is False
    assert result.optimization_warnings
    assert result.optimized_prompt
