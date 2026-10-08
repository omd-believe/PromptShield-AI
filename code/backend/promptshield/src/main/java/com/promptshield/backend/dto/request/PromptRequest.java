package com.promptshield.backend.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class PromptRequest {

    @NotBlank(message = "Prompt cannot be empty")
    private String prompt;
}