package com.promptshield.backend.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;
import lombok.ToString;
import org.hibernate.annotations.CreationTimestamp;


import java.time.LocalDateTime;
import java.util.Map;

@Entity
@NoArgsConstructor
@AllArgsConstructor
@Data
@Table(name = "prompts")
public class Prompt {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long promptId;

    @Column(columnDefinition = "TEXT")
    private String originalPrompt;

    @Column(columnDefinition = "TEXT")
    private String optimizedPrompt;

    private Integer originalTokens;

    private Integer optimizedTokens;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @ToString.Exclude
    @EqualsAndHashCode.Exclude
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;


    private Double reductionPercentage;

    private Boolean sensitiveDataDetected;

    private Integer riskScore;

    private String riskLevel;

    @Column(columnDefinition = "TEXT")
    private String privacyReportJson;

    @Column(columnDefinition = "TEXT")
    private String privacyPolicyJson;

    private Integer targetMaxTokens;

    private Double minimumSemanticScore;

    private Boolean tokenBudgetMet;

    private Boolean privacyValid;

    private Boolean leakageDetected;

    @Column(columnDefinition = "TEXT")
    private String optimizationWarningsJson;

    private Double semanticSimilarityScore;

    private Boolean semanticValid;

    private Integer grammarCorrectionCount;
}
