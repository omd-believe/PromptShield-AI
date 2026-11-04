"""
Regression tests for FLAN-T5 length safeguards, deliverable preservation,
and candidate selection in PromptShield-AI.

Tests the 10 required scenarios from the debugging specification:
1. A shorter candidate that preserves all required concepts and deliverables.
2. A shorter candidate that omits one OOP concept.
3. A candidate that preserves concepts but omits the comparison table.
4. A candidate that preserves meaning but triggers the existing length threshold.
5. A candidate that introduces a privacy leak.
6. A candidate that removes a mandatory negation.
7. A candidate that is shorter but offers no meaningful improvement.
8. A valid candidate that is selected over a less effective deterministic result.
9. A rejected candidate that correctly falls back to the deterministic or safe anonymized output.
10. Correct final token counts, reduction percentage, strategy metadata and rejection reasons.
"""

from unittest.mock import patch
import pytest

from app import config
from app.api.optimize import _evaluate_flan_t5_candidate, optimize_prompt
from app.models.request import PromptRequest
from app.services.flan_t5_service import flan_t5_service
from app.services.optimizer import PromptOptimizer
from app.services.quality_validator import QualityValidator
from app.services.token_counter import TokenCounter


@pytest.fixture(autouse=True)
def disable_llmlingua_in_flan_tests(monkeypatch):
    """Disable LLMLingua-2 in dedicated FLAN-T5 length safeguards tests so FLAN-T5 is tested directly."""
    monkeypatch.setattr(config, "LLMLINGUA_ENABLED", False)


OOP_TEST_PROMPT = (
    "Can you please explain the four main concepts of object-oriented programming in Java, "
    "which are encapsulation, inheritance, polymorphism, and abstraction, in a very simple way "
    "that is suitable for someone who has only recently started learning Java programming? "
    "For each concept, provide a short definition, explain why it is useful, and give a small "
    "Java code example that demonstrates how it works. At the end, provide a comparison table "
    "that highlights the main differences between these four concepts."
)


def test_1_shorter_candidate_preserves_all_concepts_and_deliverables(monkeypatch):
    """Case 1: A shorter candidate that preserves all required concepts and deliverables is accepted."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    concise_candidate = (
        "Explain Java OOP (encapsulation, inheritance, polymorphism, abstraction) simply for beginners. "
        "Give a definition, why it is useful, and a code example for each. End with a comparison table."
    )

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=concise_candidate,
    ):
        resp = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp.optimization_strategy == "flan-t5"
        assert resp.model_candidate_accepted is True
        assert resp.model_rejection_reason is None
        assert resp.optimized_tokens < resp.original_tokens
        assert resp.reduction_percentage > 0.0
        assert "encapsulation" in resp.optimized_prompt.lower()
        assert "inheritance" in resp.optimized_prompt.lower()
        assert "polymorphism" in resp.optimized_prompt.lower()
        assert "abstraction" in resp.optimized_prompt.lower()
        assert "comparison table" in resp.optimized_prompt.lower()


def test_2_shorter_candidate_omits_one_oop_concept(monkeypatch):
    """Case 2: A shorter candidate that omits one OOP concept (e.g. abstraction) is rejected."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    candidate_missing_abstraction = (
        "Explain Java OOP (encapsulation, inheritance, polymorphism) simply for beginners. "
        "Give a definition, why it is useful, and a code example for each. End with a comparison table."
    )

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=candidate_missing_abstraction,
    ):
        resp = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_candidate_accepted is False
        assert resp.model_rejection_reason is not None
        assert "abstraction" in resp.model_rejection_reason.lower()
        assert "dropped required core concept" in resp.model_rejection_reason.lower()
        # Fallback retained
        assert "abstraction" in resp.optimized_prompt.lower()


def test_3_candidate_preserves_concepts_but_omits_comparison_table(monkeypatch):
    """Case 3: A candidate that preserves concepts but omits the comparison table is rejected."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    candidate_missing_table = (
        "Explain Java OOP (encapsulation, inheritance, polymorphism, abstraction) simply for beginners. "
        "Give a definition, why it is useful, and a code example for each."
    )

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=candidate_missing_table,
    ):
        resp = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_candidate_accepted is False
        assert resp.model_rejection_reason is not None
        assert "table" in resp.model_rejection_reason.lower()


def test_4_candidate_preserves_meaning_but_triggers_length_threshold(monkeypatch):
    """Case 4: A candidate triggering the length threshold (ratio < 0.40) is accepted if concepts & deliverables survive."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    # 187 chars / 505 chars = 0.370 ratio (triggers the 0.40 length threshold)
    concise_candidate = (
        "Explain Java OOP (encapsulation, inheritance, polymorphism, abstraction) simply for beginners. "
        "Give a definition, why it is useful, and a code example for each. End with a comparison table."
    )
    assert len(concise_candidate) / len(OOP_TEST_PROMPT) < 0.40

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=concise_candidate,
    ):
        resp = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        # Length anomaly triggered additional verification, but candidate is accepted because deliverables survived
        assert resp.optimization_strategy == "flan-t5"
        assert resp.model_candidate_accepted is True
        assert resp.model_rejection_reason is None
        assert resp.optimized_tokens < resp.original_tokens


def test_5_candidate_introduces_privacy_leak(monkeypatch):
    """Case 5: A candidate that introduces a privacy leak is rejected."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    anon_prompt = "Process transaction for user [PERSON]."
    leaking_candidate = "Process transaction for user [PERSON] with email leaked_admin@company.com."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=leaking_candidate,
    ):
        resp = optimize_prompt(PromptRequest(prompt=anon_prompt))

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_candidate_accepted is False
        assert resp.privacy_valid is True
        assert "leaked_admin@company.com" not in resp.optimized_prompt


def test_6_candidate_removes_mandatory_negation(monkeypatch):
    """Case 6: A candidate that removes a mandatory negation is rejected."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    prompt = "Do not expose secret API keys in version control."
    candidate_inverted = "Expose secret API keys in version control."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=candidate_inverted,
    ):
        resp = optimize_prompt(PromptRequest(prompt=prompt))

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_candidate_accepted is False
        assert "negation" in (resp.model_rejection_reason or "").lower()
        assert "Do not expose" in resp.optimized_prompt


def test_7_candidate_shorter_but_offers_no_meaningful_improvement(monkeypatch):
    """Case 7: A candidate that truncates randomly without preserving deliverables is rejected."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    # Shorter prompt, but dropped all required OOP concepts and deliverables
    poor_candidate = "Explain the concepts in Java."

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=poor_candidate,
    ):
        resp = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_candidate_accepted is False
        assert resp.model_rejection_reason is not None


def test_8_valid_candidate_selected_over_less_effective_deterministic(monkeypatch):
    """Case 8: A valid concise candidate is selected over a less effective deterministic result."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    # Deterministic only removes "Can you please" (93 -> 91 tokens, 2.15% reduction)
    # FLAN-T5 candidate provides a concise, valid rewrite (93 -> 35 tokens, ~62% reduction)
    concise_candidate = (
        "Explain Java OOP (encapsulation, inheritance, polymorphism, abstraction) simply for beginners. "
        "Give a definition, why it is useful, and a code example for each. End with a comparison table."
    )

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=concise_candidate,
    ):
        resp = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp.optimization_strategy == "flan-t5"
        assert resp.model_candidate_accepted is True
        assert resp.optimized_tokens < 50
        assert resp.reduction_percentage > 50.0


def test_9_rejected_candidate_falls_back_to_deterministic_output(monkeypatch):
    """Case 9: The actual FLAN-T5 candidate (missing OOP concepts and table) falls back to deterministic output."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    # The actual output produced by FLAN-T5 for this prompt
    actual_flan_output = (
        "For each concept, provide a short definition, explain why it is useful, "
        "and provide java code examples that illustrate the main differences between these four concepts."
    )

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=actual_flan_output,
    ):
        resp = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp.optimization_strategy == "deterministic"
        assert resp.model_candidate_accepted is False
        assert resp.model_rejection_reason is not None
        # Verify rejection distinguished semantic/concept failure rather than uninformative length ratio
        assert (
            "concept" in resp.model_rejection_reason.lower()
            or "table" in resp.model_rejection_reason.lower()
        )
        # Deterministic candidate was returned
        assert "encapsulation" in resp.optimized_prompt.lower()
        assert "inheritance" in resp.optimized_prompt.lower()
        assert "polymorphism" in resp.optimized_prompt.lower()
        assert "abstraction" in resp.optimized_prompt.lower()


def test_10_correct_final_token_counts_reduction_percentage_and_metadata(monkeypatch):
    """Case 10: Token counts, reduction percentages, strategy metadata and rejection reasons are strictly verified."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    tc = TokenCounter()
    expected_original_tokens = tc.count(OOP_TEST_PROMPT)
    assert expected_original_tokens == 93

    # Subcase A: Rejected candidate falls back to deterministic
    actual_flan_output = (
        "For each concept, provide a short definition, explain why it is useful, "
        "and provide java code examples that illustrate the main differences between these four concepts."
    )
    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=actual_flan_output,
    ):
        resp_fallback = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp_fallback.original_tokens == 93
        assert resp_fallback.optimized_tokens == 91
        expected_reduction = round(((93 - 91) / 93) * 100, 2)
        assert resp_fallback.reduction_percentage == expected_reduction
        assert resp_fallback.optimization_strategy == "deterministic"
        assert resp_fallback.model_candidate_accepted is False
        assert resp_fallback.model_used is True
        assert resp_fallback.model_rejection_reason is not None

    # Subcase B: Accepted concise candidate
    concise_candidate = (
        "Explain Java OOP (encapsulation, inheritance, polymorphism, abstraction) simply for beginners. "
        "Give a definition, why it is useful, and a code example for each. End with a comparison table."
    )
    expected_cand_tokens = tc.count(concise_candidate)

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=concise_candidate,
    ):
        resp_accepted = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp_accepted.original_tokens == 93
        assert resp_accepted.optimized_tokens == expected_cand_tokens
        expected_reduction_b = round(((93 - expected_cand_tokens) / 93) * 100, 2)
        assert resp_accepted.reduction_percentage == expected_reduction_b
        assert resp_accepted.optimization_strategy == "flan-t5"
        assert resp_accepted.model_candidate_accepted is True
        assert resp_accepted.model_rejection_reason is None


def test_11_candidate_not_rejected_for_beginner_friendly_phrasing(monkeypatch):
    """Case 11: A rewrite preserving all concepts and deliverables without verbatim 'beginner' words is accepted."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(flan_t5_service, "_is_available", True)

    # Valid rewrite that preserves concepts & tangible deliverables but tightens wording
    concise_candidate = (
        "Explain Java OOP concepts: encapsulation, inheritance, polymorphism, and abstraction. "
        "Provide a definition, explain why each is useful, provide a code example, and finish with a comparison table."
    )

    with patch.object(
        flan_t5_service,
        "generate_candidate_with_timeout",
        return_value=concise_candidate,
    ):
        resp = optimize_prompt(PromptRequest(prompt=OOP_TEST_PROMPT))

        assert resp.optimization_strategy == "flan-t5"
        assert resp.model_candidate_accepted is True
        assert resp.model_rejection_reason is None
        assert "beginner" not in resp.model_rejection_reason if resp.model_rejection_reason else True

