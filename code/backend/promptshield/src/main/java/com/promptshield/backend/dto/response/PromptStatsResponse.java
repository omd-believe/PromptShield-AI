package com.promptshield.backend.dto.response;

import lombok.Builder;
import lombok.Value;

import java.util.Map;

@Value
@Builder
public class PromptStatsResponse {

    long totalPrompts;
    double averageTokenReduction;
    long promptsWithSensitiveData;
    long totalEntitiesDetected;
    long totalTokensSaved;
    Map<String, Long> privacyCategories;
    Map<String, Long> riskLevels;
    Double semanticAcceptanceRate;
}
