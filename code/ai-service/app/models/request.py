"""
Request model for POST /optimize.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app import config


class PromptRequest(BaseModel):
    """
    Request body for the prompt optimization endpoint.

    Fields:
        prompt: The raw user prompt to process.  Must be a non-empty string
                not exceeding the configured maximum length.
    """

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=config.MAX_PROMPT_LENGTH,
        description="The raw prompt to optimize and analyze for privacy.",
        examples=["Please kindly summarize this document for me."],
    )
    target_max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=100_000,
        description="Optional maximum token budget for the optimized prompt.",
    )
    minimum_semantic_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional minimum semantic score required for the result.",
    )
    privacy_policy: dict[str, Literal[
        "MASK", "REPORT", "ALLOW", "BLOCK", "REQUIRE_CONFIRMATION"
    ]] | None = Field(
        default=None,
        description=(
            "Optional per-category privacy actions. Categories omitted here "
            "use the secure default policy."
        ),
        examples=[{"EMAIL": "MASK", "ORG": "REPORT"}],
    )
    compression_engine: Literal["auto", "llmlingua", "flan-t5", "deterministic"] | None = Field(
        default=None,
        description="Optional engine override: 'auto', 'llmlingua', 'flan-t5', or 'deterministic'.",
    )
    compression_rate: float | None = Field(
        default=None,
        ge=0.01,
        le=1.0,
        description="Optional target retention rate for LLMLingua-2 (e.g. 0.6 preserves ~60% of tokens).",
    )

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Prompt must not be whitespace only.")
        return v

    @field_validator("privacy_policy")
    @classmethod
    def privacy_policy_must_use_supported_values(cls, policy):
        if policy is None:
            return policy
        supported_labels = (
            config.REGEX_ALWAYS_ANONYMIZE
            | config.NER_PRIVACY_TYPES
        )
        unknown_labels = sorted(set(policy) - supported_labels)
        if unknown_labels:
            raise ValueError(
                f"Unsupported privacy policy categories: {', '.join(unknown_labels)}"
            )
        return policy