package com.promptshield.backend.dto.response;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.promptshield.backend.entity.AiEntity;
import lombok.Data;

import java.util.List;

/**
 * Response DTO mapping the Python AI service's JSON response.
 *
 * The Python service uses snake_case; Jackson @JsonProperty handles the mapping.
 *
 * Token fields (originalTokens, optimizedTokens, reductionPercentage) are
 * APPROXIMATE word counts, not actual LLM tokenizer counts.
 */
@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class AiOptimizeResponse {

    @JsonProperty("original_prompt")
    private String originalPrompt;

    @JsonProperty("optimized_prompt")
    private String optimizedPrompt;

    private List<AiEntity> entities;

    @JsonProperty("privacy_report")
    private PrivacyReport privacyReport;

    @JsonProperty("risk_score")
    private Integer riskScore;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("semantic_similarity_score")
    private Double semanticSimilarityScore;

    @JsonProperty("semantic_valid")
    private Boolean semanticValid;

    @JsonProperty("grammar_corrections")
    private List<String> grammarCorrections;

    @JsonProperty("grammar_corrected")
    private Boolean grammarCorrected;

    /** Approximate word count of the original prompt (before optimization). */
    @JsonProperty("original_tokens")
    private Integer originalTokens;

    /** Approximate word count of the optimized prompt. */
    @JsonProperty("optimized_tokens")
    private Integer optimizedTokens;

    @JsonProperty("reduction_percentage")
    private Double reductionPercentage;

    @JsonProperty("anonymized_tokens")
    private Integer anonymizedTokens;

    @JsonProperty("compression_percentage")
    private Double compressionPercentage;

    @JsonProperty("anonymization_token_delta")
    private Integer anonymizationTokenDelta;

    @JsonProperty("target_max_tokens")
    private Integer targetMaxTokens;

    @JsonProperty("minimum_semantic_score")
    private Double minimumSemanticScore;

    @JsonProperty("token_budget_met")
    private Boolean tokenBudgetMet;

    @JsonProperty("optimization_warnings")
    private List<String> optimizationWarnings;

    @JsonProperty("privacy_valid")
    private Boolean privacyValid;

    @JsonProperty("leakage_detected")
    private Boolean leakageDetected;

    @JsonProperty("policy_actions")
    private java.util.Map<String, String> policyActions;

    @JsonProperty("confirmation_required")
    private Boolean confirmationRequired;

    @JsonProperty("blocked")
    private Boolean blocked;

    @JsonProperty("blocked_labels")
    private List<String> blockedLabels;

    @JsonProperty("optimization_strategy")
    private String optimizationStrategy;

    @JsonProperty("model_used")
    private Boolean modelUsed;

    @JsonProperty("model_candidate_accepted")
    private Boolean modelCandidateAccepted;

    @JsonProperty("model_rejection_reason")
    private String modelRejectionReason;
}