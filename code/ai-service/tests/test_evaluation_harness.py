import pytest

from app.services.grammar_corrector import GrammarCorrector
from app.services.optimizer import PromptOptimizer
from app.services.preprocessing import Preprocessor
from app.services.privacy_engine import PrivacyEngine
from app.services.quality_validator import QualityValidator
from app.services.semantic_validator import SemanticValidator
from app.services.token_counter import TokenCounter
from evaluate import evaluate_case


@pytest.fixture
def evaluation_dependencies():
    return {
        "preprocessor": Preprocessor(),
        "privacy_engine": PrivacyEngine(),
        "optimizer": PromptOptimizer(),
        "grammar_corrector": GrammarCorrector(),
        "validator": QualityValidator(),
        "semantic_validator": SemanticValidator(),
        "token_counter": TokenCounter(),
    }


def test_evaluation_harness_checks_constraint_preservation(evaluation_dependencies):
    item = {
        "id": "constraint-check",
        "category": "constraint_preserved",
        "prompt": "Please summarize this contract in exactly 3 sentences. Do not omit penalty clauses.",
        "expected": {
            "entities": [],
            "risk_level": "LOW",
            "constraint_preserved": ["exactly 3 sentences", "Do not omit penalty clauses"],
            "optimized_not_empty": True,
        },
    }

    result = evaluate_case(item, **evaluation_dependencies)

    assert not result["failures"]
    assert not result["risk_failures"]
    assert result["optimized_tokens"] > 0


def test_evaluation_harness_enforces_max_reduction(evaluation_dependencies):
    item = {
        "id": "max-reduction-check",
        "category": "reduction_limit",
        "prompt": "Please kindly summarize this long document for me. I want you to explain it in order to make it clear at this point in time.",
        "expected": {
            "entities": [],
            "risk_level": "LOW",
            "token_reduction_max_percent": 10,
            "optimized_not_empty": True,
        },
    }

    result = evaluate_case(item, **evaluation_dependencies)

    assert any("exceeds max" in failure for failure in result["failures"])
