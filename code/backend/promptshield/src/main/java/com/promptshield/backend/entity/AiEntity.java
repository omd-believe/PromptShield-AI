package com.promptshield.backend.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class AiEntity {

    private String text;
    private String label;
    private Double confidence;

    @JsonProperty("policy_action")
    private String policyAction;
}
