package com.promptshield.backend.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.Map;

@Data
public class PromptRequest {

    @NotBlank(message = "Prompt cannot be empty")
    // Keep in sync with MAX_PROMPT_LENGTH in the AI service (default 8000).
    @Size(max = 8000, message = "Prompt must not exceed 8000 characters")
    private String prompt;

    @Min(value = 1, message = "Target token budget must be at least 1")
    @Max(value = 100000, message = "Target token budget is too large")
    private Integer targetMaxTokens;

    @DecimalMin(value = "0.0", message = "Minimum semantic score cannot be negative")
    @DecimalMax(value = "100.0", message = "Minimum semantic score cannot exceed 100")
    private Double minimumSemanticScore;

    private Map<String, String> privacyPolicy;
}