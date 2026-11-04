package com.promptshield.backend.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.promptshield.backend.entity.AiEntity;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class PrivacyAnalysisResponse {

    @JsonProperty("original_prompt")
    private String originalPrompt;

    @JsonProperty("anonymized_prompt")
    private String anonymizedPrompt;

    private List<AiEntity> entities;

    @JsonProperty("privacy_report")
    private PrivacyReport privacyReport;

    @JsonProperty("risk_score")
    private Integer riskScore;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("policy_actions")
    private Map<String, String> policyActions;
    @JsonProperty("confirmation_required")
    private boolean confirmationRequired;
    private boolean blocked;
    @JsonProperty("blocked_labels")
    private List<String> blockedLabels;
}
