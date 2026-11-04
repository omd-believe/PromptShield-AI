import pytest
from pydantic import ValidationError

from app.models.request import PromptRequest


def test_privacy_policy_accepts_supported_category_and_action():
    request = PromptRequest(
        prompt="Contact me at person@example.com",
        privacy_policy={"EMAIL": "REQUIRE_CONFIRMATION"},
    )

    assert request.privacy_policy == {"EMAIL": "REQUIRE_CONFIRMATION"}


def test_privacy_policy_rejects_unknown_category():
    with pytest.raises(ValidationError, match="Unsupported privacy policy categories"):
        PromptRequest(
            prompt="Review this",
            privacy_policy={"UNKNOWN_CATEGORY": "MASK"},
        )
