"""Response models for privacy analysis and prompt optimization."""

from pydantic import BaseModel, Field


class EntityItem(BaseModel):
    """A single detected entity."""

    text: str = Field(..., description="Surface form of the detected entity.")
    label: str = Field(..., description="Entity category (e.g. EMAIL, PERSON, PAN).")
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Detection confidence from 0.0 to 1.0.",
    )
    policy_action: str = Field(
        "REPORT",
        description="Effective privacy action for this entity category.",
    )


class EntityTypeSummary(BaseModel):
    """Summary of one detected entity category."""

    label: str = Field(..., description="Entity category.")
    count: int = Field(..., ge=1, description="Number of unique entities in this category.")
    masked_as: str = Field(..., description="Placeholder used for anonymization.")


class PrivacyReport(BaseModel):
    """Structured summary of privacy-relevant entities in a prompt."""

    total_entities: int = Field(..., ge=0, description="Number of unique detected entities.")
    entity_types: list[EntityTypeSummary] = Field(
        default_factory=list,
        description="Counts grouped by entity category.",
    )


class PrivacyResponse(BaseModel):
    """Response model for POST /analyze."""

    original_prompt: str = Field(..., description="The prompt as received.")
    anonymized_prompt: str = Field(..., description="The prompt with sensitive values masked.")
    entities: list[EntityItem] = Field(
        default_factory=list,
        description="All privacy-relevant entities detected in the prompt.",
    )
    privacy_report: PrivacyReport = Field(..., description="Structured privacy summary.")
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL.")
    policy_actions: dict[str, str] = Field(default_factory=dict)
    confirmation_required: bool = False
    blocked: bool = False
    blocked_labels: list[str] = Field(default_factory=list)


class PromptResponse(BaseModel):
    """
    Full response from the prompt optimization pipeline.

    Token counts use the configured model tokenizer.
    """

    original_prompt: str = Field(
        ...,
        description="The original prompt as received (before any processing).",
    )
    optimized_prompt: str = Field(
        ...,
        description="The final prompt after anonymization and optimization.",
    )
    entities: list[EntityItem] = Field(
        default_factory=list,
        description="All privacy-relevant entities detected in the prompt.",
    )
    privacy_report: PrivacyReport = Field(
        ...,
        description="Structured summary of detected privacy-relevant entities.",
    )
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Cumulative privacy risk score (0–100).",
    )
    risk_level: str = Field(
        ...,
        description="Qualitative risk level: LOW | MEDIUM | HIGH | CRITICAL.",
    )
    semantic_similarity_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Semantic preservation score between original and optimized prompts.",
    )
    semantic_valid: bool = Field(
        ...,
        description="Whether the optimized prompt preserves enough meaning to be accepted.",
    )
    grammar_corrections: list[str] = Field(
        default_factory=list,
        description="High-confidence grammar or spelling corrections applied.",
    )
    grammar_corrected: bool = Field(
        ...,
        description="Whether grammar or spelling corrections changed the prompt.",
    )
    original_tokens: int = Field(
        ...,
        ge=0,
        description="Token count of the original prompt using the configured tokenizer.",
    )
    optimized_tokens: int = Field(
        ...,
        ge=0,
        description="Token count of the optimized prompt using the configured tokenizer.",
    )
    anonymized_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Token count of the anonymized prompt baseline before optimizer/compression.",
    )
    reduction_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Total token reduction percentage from original to optimized prompt (0.00–100.00). "
            "Includes both anonymization and optimizer compression. Clamped to 0.0 when tokens increase."
        ),
    )
    anonymization_token_delta: int = Field(
        default=0,
        description=(
            "Signed change in token count caused by anonymization alone "
            "(anonymized_tokens − original_tokens). Negative = anonymization shortened the prompt; "
            "positive = placeholders added tokens."
        ),
    )
    compression_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description=(
            "Token reduction percentage attributable only to the optimizer or model compression stage, "
            "measured from the anonymized baseline to the final optimized output "
            "(excludes anonymization-driven token changes)."
        ),
    )
    target_max_tokens: int | None = Field(
        default=None,
        description="Requested maximum token budget, if supplied.",
    )
    minimum_semantic_score: float | None = Field(
        default=None,
        description="Requested minimum semantic score, if supplied.",
    )
    token_budget_met: bool | None = Field(
        default=None,
        description="Whether the optimized prompt meets the requested token budget.",
    )
    optimization_warnings: list[str] = Field(
        default_factory=list,
        description="Non-blocking warnings about optimization targets.",
    )
    privacy_valid: bool = Field(
        ...,
        description="Whether protected entities remained masked after optimization.",
    )
    leakage_detected: bool = Field(
        ...,
        description="Whether a protected entity value was found after optimization.",
    )
    policy_actions: dict[str, str] = Field(default_factory=dict)
    confirmation_required: bool = False
    blocked: bool = False
    optimization_strategy: str = Field(
        default="deterministic",
        description="Selected optimization strategy: 'deterministic', 'llmlingua-2', or 'flan-t5'.",
    )
    model_used: bool = Field(
        default=False,
        description="Whether an AI model (LLMLingua-2 or FLAN-T5) was invoked for compression/rewriting.",
    )
    model_candidate_accepted: bool = Field(
        default=False,
        description="Whether the model candidate was accepted.",
    )
    model_rejection_reason: str | None = Field(
        default=None,
        description="Detailed reason if the model candidate was rejected.",
    )