package com.promptshield.backend.dto.response;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.promptshield.backend.entity.AiEntity;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@JsonIgnoreProperties(ignoreUnknown = true)
public class PromptResponse {

    private Long promptId;

    private String originalPrompt;

    private String optimizedPrompt;

    private LocalDateTime createdAt;

    private List<AiEntity> entities;
    private PrivacyReport privacyReport;
    private Integer riskScore;
    private String riskLevel;
    private String privacyReportJson;
    private Map<String, String> privacyPolicy;

    private Double semanticSimilarityScore;
    private Boolean semanticValid;
    private List<String> grammarCorrections;
    private Boolean grammarCorrected;
    private Integer grammarCorrectionCount;

    /** Approximate word count of the original prompt */
    private Integer originalTokens;

    /** Approximate word count of the optimized prompt */
    private Integer optimizedTokens;

    /** Approximate percentage reduction in word count */
    private Double reductionPercentage;

    private Integer anonymizedTokens;
    private Double compressionPercentage;
    private Integer anonymizationTokenDelta;

    private Integer targetMaxTokens;
    private Double minimumSemanticScore;
    private Boolean tokenBudgetMet;
    private List<String> optimizationWarnings;
    private Boolean privacyValid;
    private Boolean leakageDetected;
    @JsonProperty("policy_actions")
    private Map<String, String> policyActions;
    @JsonProperty("confirmation_required")
    private Boolean confirmationRequired;
    @JsonProperty("blocked")
    private Boolean blocked;
    @JsonProperty("blocked_labels")
    private List<String> blockedLabels;

    /** Flag indicating whether sensitive PII/entities were detected */
    private Boolean sensitiveDataDetected;

    @JsonProperty("optimization_strategy")
    private String optimizationStrategy;

    @JsonProperty("model_used")
    private Boolean modelUsed;

    @JsonProperty("model_candidate_accepted")
    private Boolean modelCandidateAccepted;

    @JsonProperty("model_rejection_reason")
    private String modelRejectionReason;
}

