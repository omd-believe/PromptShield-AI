package com.promptshield.backend.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

@Data
public class PrivacyAuditRequest {

    @NotBlank
    @Size(max = 40)
    private String eventType;

    @Size(max = 40)
    private String riskLevel;

    private Integer riskScore;
    private Long promptId;
    private List<@Size(max = 40) String> categories;
}
