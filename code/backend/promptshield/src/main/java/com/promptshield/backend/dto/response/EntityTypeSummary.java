package com.promptshield.backend.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class EntityTypeSummary {

    private String label;
    private Integer count;

    @JsonProperty("masked_as")
    private String maskedAs;
}
