package com.promptshield.backend.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
public class PrivacyReport {

    @JsonProperty("total_entities")
    private Integer totalEntities;

    @JsonProperty("entity_types")
    private List<EntityTypeSummary> entityTypes;
}
