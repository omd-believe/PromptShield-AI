package com.promptshield.backend.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@AllArgsConstructor
public class PromptResponse {

    private Long promptId;

    private String originalPrompt;

    private String optimizedPrompt;

    private LocalDateTime createdAt;

}
