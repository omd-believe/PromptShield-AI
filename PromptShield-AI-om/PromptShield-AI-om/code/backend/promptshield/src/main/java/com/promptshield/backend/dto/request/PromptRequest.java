package com.promptshield.backend.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class PromptRequest {

    @NotNull
    private Long userId;

    @NotBlank
    private String prompt;

}
