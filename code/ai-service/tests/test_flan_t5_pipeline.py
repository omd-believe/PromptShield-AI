"""
Unit and integration tests for FLAN-T5 candidate generation, validation, and API selection.

Tests candidate acceptance, constraint violations, safety rejections, and fallback semantics.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api.optimize import _evaluate_flan_t5_candidate, optimize_prompt
from app.main import app
from app.models.request import PromptRequest
from app.services.flan_t5_service import FlanT5TimeoutError, flan_t5_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_llmlingua_in_flan_tests(monkeypatch):
    """Disable LLMLingua-2 in dedicated FLAN-T5 pipeline tests so FLAN-T5 is tested directly."""
    monkeypatch.setattr(config, "LLMLINGUA_ENABLED", False)


def test_evaluate_candidate_accepts_valid_rewrite():
    """Valid concise rewrite preserving placeholders and meaning is accepted."""
    anon = "Please summarize this document for [PERSON] with email [EMAIL]."
    det = "summarize this document for [PERSON] with email [EMAIL]."
    cand = "Summarize this document for [PERSON] with email [EMAIL]."
    protected = [{"text": "Priya", "label": "PERSON"}, {"text": "priya@example.com", "label": "EMAIL"}]

    accepted, reason = _evaluate_flan_t5_candidate(
        anonymized_prompt=anon,
        deterministic_candidate=det,
        candidate=cand,
        privacy_policy=None,
        protected_entities=protected,
    )
    assert accepted is True
    assert reason is None


def test_evaluate_candidate_rejects_altered_placeholders():
    """Reject candidate that corrupts, drops, or alters privacy placeholders."""
    anon = "Contact [PERSON] at [EMAIL]."
    cand = "Contact the user at [EMAIL]."
    accepted, reason = _evaluate_flan_t5_candidate(
        anonymized_prompt=anon,
        deterministic_candidate=anon,
        candidate=cand,
        privacy_policy=None,
        protected_entities=[],
    )
    assert accepted is False
    assert "Altered privacy placeholders" in reason


def test_evaluate_candidate_rejects_removed_negation():
    """Reject candidate that drops critical negations (e.g. 'not', 'never')."""
    anon = "Review this code. Do not store passwords in [GENERIC_SECRET]."
    cand = "Review this code and store passwords in [GENERIC_SECRET]."
    accepted, reason = _evaluate_flan_t5_candidate(
        anonymized_prompt=anon,
        deterministic_candidate=anon,
        candidate=cand,
        privacy_policy=None,
        protected_entities=[],
    )
    assert accepted is False
    assert "critical negation" in reason.lower() or "failed quality" in reason.lower()


def test_evaluate_candidate_rejects_altered_plaintext_security():
    """Reject candidate that alters the protected term 'plaintext'."""
    anon = "Do not store passwords in plaintext."
    cand = "Do not store passwords in plain text format."
    accepted, reason = _evaluate_flan_t5_candidate(
        anonymized_prompt=anon,
        deterministic_candidate=anon,
        candidate=cand,
        privacy_policy=None,
        protected_entities=[],
    )
    assert accepted is False
    assert "security-critical instruction" in reason.lower() or "plaintext" in reason.lower()


def test_evaluate_candidate_rejects_altered_generic_types():
    """Reject candidate that mutates Map<Integer, Integer> or List<String>."""
    anon = "Write a method accepting Map<Integer, Integer> and returning List<String>."
    cand = "Write a method accepting a map of integers and returning a list of strings."
    accepted, reason = _evaluate_flan_t5_candidate(
        anonymized_prompt=anon,
        deterministic_candidate=anon,
        candidate=cand,
        privacy_policy=None,
        protected_entities=[],
    )
    assert accepted is False
    assert "generic type" in reason.lower() or "map<integer, integer>" in reason.lower()


def test_evaluate_candidate_rejects_dropped_numeric_constraints():
    """Reject candidate that drops exact numbers like '3 bullet points'."""
    anon = "Summarize the findings in 3 bullet points."
    cand = "Summarize the findings in bullet points."
    accepted, reason = _evaluate_flan_t5_candidate(
        anonymized_prompt=anon,
        deterministic_candidate=anon,
        candidate=cand,
        privacy_policy=None,
        protected_entities=[],
    )
    assert accepted is False
    assert "numeric constraint" in reason.lower()


def test_evaluate_candidate_rejects_sensitive_data_leakage():
    """Reject candidate that introduces sensitive entity values or unmasked PII."""
    anon = "User account [BANK_ACCOUNT] requested assistance."
    cand = "User account [BANK_ACCOUNT] with email leak@secret.com requested assistance."
    accepted, reason = _evaluate_flan_t5_candidate(
        anonymized_prompt=anon,
        deterministic_candidate=anon,
        candidate=cand,
        privacy_policy=None,
        protected_entities=[],
    )
    assert accepted is False
    assert "sensitive data leakage" in reason.lower() or "leakage" in reason.lower()


def test_evaluate_candidate_rejects_identical_to_input():
    """Reject candidate that did not perform any rewriting or optimization."""
    anon = "Review this function."
    accepted, reason = _evaluate_flan_t5_candidate(
        anonymized_prompt=anon,
        deterministic_candidate=anon,
        candidate=anon,
        privacy_policy=None,
        protected_entities=[],
    )
    assert accepted is False
    assert "identical" in reason.lower()


def test_api_deterministic_strategy_when_model_disabled(monkeypatch):
    """When FLAN_T5_ENABLED is False, optimization_strategy is deterministic and model_used is False."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", False)
    req = PromptRequest(prompt="Please kindly optimize this code query.")
    resp = optimize_prompt(req)

    assert resp.optimization_strategy == "deterministic"
    assert resp.model_used is False
    assert resp.model_candidate_accepted is False


def test_api_flan_t5_strategy_when_candidate_accepted(monkeypatch):
    """When FLAN_T5_ENABLED is True and candidate is accepted, strategy is flan-t5."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_MIN_SEMANTIC_SCORE", 50.0)

    # Mock flan_t5_service to be available and return a clean rewrite
    monkeypatch.setattr(flan_t5_service, "_is_available", True)
    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value="Optimize this code query for execution speed.",
    ):
        req = PromptRequest(prompt="Please kindly optimize this code query.")
        resp = optimize_prompt(req)

        assert resp.model_used is True
        assert resp.model_candidate_accepted is True
        assert resp.optimization_strategy == "flan-t5"
        assert resp.optimized_prompt == "Optimize this code query for execution speed."


def test_api_fallback_to_deterministic_when_candidate_rejected(monkeypatch):
    """When candidate is rejected (e.g. lost constraint), deterministic fallback is used."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    # Candidate drops negation
    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value="Store passwords in plaintext.",
    ):
        req = PromptRequest(prompt="Do not store passwords in plaintext.")
        resp = optimize_prompt(req)

        assert resp.model_used is True
        assert resp.model_candidate_accepted is False
        assert resp.optimization_strategy == "deterministic"
        assert "FLAN-T5 candidate rejected" in " ".join(resp.optimization_warnings)
        assert "Do not store passwords in plaintext." in resp.optimized_prompt


def test_api_fallback_when_inference_times_out(monkeypatch):
    """When model inference times out, fallback to deterministic candidate with warning."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        side_effect=FlanT5TimeoutError("Timed out"),
    ):
        req = PromptRequest(prompt="Please kindly analyze this data.")
        resp = optimize_prompt(req)

        assert resp.model_used is True
        assert resp.model_candidate_accepted is False
        assert resp.optimization_strategy == "deterministic"
        assert "failed" in " ".join(resp.optimization_warnings).lower() or "timed out" in " ".join(resp.optimization_warnings).lower()


def test_api_policy_blocked_does_not_call_model(monkeypatch):
    """When prompt is blocked by policy, returns 422 immediately without invoking model."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    mock_gen = patch.object(flan_t5_service, "generate_candidate_with_timeout")
    with mock_gen as mocked:
        response = client.post(
            "/optimize",
            json={
                "prompt": "My API key is sk-abcdefghijklmnopqrstuvwxyz12345.",
                "privacy_policy": {"API_KEY": "BLOCK"},
            },
        )
        assert response.status_code == 422
        mocked.assert_not_called()


def test_api_flan_t5_returns_input_unchanged_handled_as_noop(monkeypatch):
    """When FLAN-T5 returns the input unchanged, it is handled as a no-op and falls back to deterministic."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    prompt_text = "Explain binary search in Java for a beginner."
    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=prompt_text,
    ):
        req = PromptRequest(prompt=prompt_text)
        resp = optimize_prompt(req)

        assert resp.model_used is True
        assert resp.model_candidate_accepted is False
        assert resp.optimization_strategy == "deterministic"
        assert "identical" in (resp.model_rejection_reason or "").lower()
        assert resp.optimized_prompt == prompt_text


def test_api_serializes_correct_optimized_prompt_field(monkeypatch):
    """The API response model serializes the actual accepted candidate, not the original prompt."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_MIN_SEMANTIC_SCORE", 50.0)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    original_input = "Could you please kindly explain binary search in Java?"
    accepted_rewrite = "Explain binary search in Java clearly."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=accepted_rewrite,
    ):
        response = client.post("/optimize", json={"prompt": original_input})
        assert response.status_code == 200
        data = response.json()

        assert data["original_prompt"] == original_input
        assert data["optimized_prompt"] == accepted_rewrite
        assert data["optimization_strategy"] == "flan-t5"
        assert data["model_used"] is True
        assert data["model_candidate_accepted"] is True


def test_candidate_selection_valid_reduces_tokens_without_losing_constraints(monkeypatch):
    """A valid candidate that reduces tokens without losing constraints is accepted."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_MIN_SEMANTIC_SCORE", 50.0)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    input_prompt = "Please kindly summarize this technical report in 3 bullet points for Java developers."
    # Valid rewrite that removes filler and preserves "3 bullet points" and "Java"
    candidate_rewrite = "Summarize this report in 3 bullet points for Java developers."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=candidate_rewrite,
    ):
        req = PromptRequest(prompt=input_prompt)
        resp = optimize_prompt(req)

        assert resp.optimization_strategy == "flan-t5"
        assert resp.model_used is True
        assert resp.model_candidate_accepted is True
        assert resp.model_rejection_reason is None
        assert resp.optimized_tokens < resp.original_tokens
        assert resp.reduction_percentage > 0.0
        assert "3 bullet points" in resp.optimized_prompt
        assert "Java" in resp.optimized_prompt


def test_candidate_selection_unchanged_tokens_no_measurable_quality_improvement(monkeypatch):
    """A candidate with unchanged token count and no measurable quality improvement is rejected as a no-op."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_MIN_SEMANTIC_SCORE", 50.0)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    input_prompt = "Explain binary search in Java for a beginner. Include a simple example and time complexity."
    # Synonym substitution ("Explain" -> "Describe") with 17 tokens -> 17 tokens and no quality benefit
    candidate_rewrite = "Describe binary search in Java for a beginner. Include a simple example and time complexity."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=candidate_rewrite,
    ):
        req = PromptRequest(prompt=input_prompt)
        resp = optimize_prompt(req)

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_used is True
        assert resp.model_candidate_accepted is False
        assert resp.model_rejection_reason is not None
        assert "no measurable token reduction" in resp.model_rejection_reason.lower()
        assert resp.original_tokens == resp.optimized_tokens
        assert resp.reduction_percentage == 0.0
        # Safe deterministic/baseline returned unchanged
        assert resp.optimized_prompt == input_prompt


def test_candidate_selection_reduces_tokens_but_removes_mandatory_constraint(monkeypatch):
    """A candidate that reduces tokens but removes a mandatory constraint is rejected."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    input_prompt = "Summarize this technical document in 3 bullet points."
    # Drops mandatory numeric constraint "3 bullet points"
    candidate_rewrite = "Summarize this document."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=candidate_rewrite,
    ):
        req = PromptRequest(prompt=input_prompt)
        resp = optimize_prompt(req)

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_used is True
        assert resp.model_candidate_accepted is False
        assert resp.model_rejection_reason is not None
        assert "numeric constraint" in resp.model_rejection_reason.lower() or "3 bullet points" in resp.model_rejection_reason.lower()
        assert "3 bullet points" in resp.optimized_prompt


def test_candidate_selection_improves_clarity_without_reducing_tokens(monkeypatch):
    """A candidate that improves clarity without reducing tokens is accepted with accurate 0.0% reduction."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_MIN_SEMANTIC_SCORE", 50.0)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    # Input contains spelling defect "occured" (10 tokens in tiktoken)
    input_prompt = "An error occured while executing this query in Java."
    # Candidate fixes spelling "occurred" (also exactly 10 tokens in tiktoken)
    candidate_rewrite = "An error occurred while executing this query in Java."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=candidate_rewrite,
    ):
        req = PromptRequest(prompt=input_prompt)
        resp = optimize_prompt(req)

        assert resp.optimization_strategy == "flan-t5"
        assert resp.model_used is True
        assert resp.model_candidate_accepted is True
        assert resp.model_rejection_reason is None
        assert resp.original_tokens == resp.optimized_tokens
        assert resp.reduction_percentage == 0.0
        assert resp.optimized_prompt == candidate_rewrite


def test_candidate_selection_fails_validation_triggers_fallback(monkeypatch):
    """A candidate that fails semantic or negation constraints triggers safe fallback."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    input_prompt = "Do not store user passwords in plaintext format."
    # Inverts safety constraint by dropping negation
    candidate_rewrite = "Store user passwords in plaintext format."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=candidate_rewrite,
    ):
        req = PromptRequest(prompt=input_prompt)
        resp = optimize_prompt(req)

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_used is True
        assert resp.model_candidate_accepted is False
        assert "negation" in (resp.model_rejection_reason or "").lower()
        assert "Do not store" in resp.optimized_prompt


def test_candidate_selection_correct_metadata_and_token_metrics_every_outcome(monkeypatch):
    """Metadata, strategy, model_candidate_accepted, and token metrics are truthful across all outcomes."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_MIN_SEMANTIC_SCORE", 50.0)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    # Outcome A: Valid candidate with reduction (9 tokens -> 7 tokens)
    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value="Summarize this technical document.",
    ):
        resp_a = optimize_prompt(PromptRequest(prompt="Could you please kindly summarize this technical document."))
        assert resp_a.optimization_strategy == "flan-t5"
        assert resp_a.model_candidate_accepted is True
        assert resp_a.model_rejection_reason is None
        assert resp_a.reduction_percentage > 0.0
        assert resp_a.optimized_tokens < resp_a.original_tokens

    # Outcome B: No-op candidate with zero token reduction and zero quality benefit
    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value="Describe binary search in Java for a beginner. Include a simple example and time complexity.",
    ):
        resp_b = optimize_prompt(PromptRequest(prompt="Explain binary search in Java for a beginner. Include a simple example and time complexity."))
        assert resp_b.optimization_strategy == "deterministic"
        assert resp_b.model_candidate_accepted is False
        assert resp_b.model_rejection_reason is not None
        assert resp_b.reduction_percentage == 0.0
        assert resp_b.optimized_tokens == resp_b.original_tokens



