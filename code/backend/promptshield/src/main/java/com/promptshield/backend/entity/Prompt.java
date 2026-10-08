package com.promptshield.backend.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;


import java.time.LocalDateTime;

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

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;


    private Double reductionPercentage;

    private Boolean sensitiveDataDetected;

}
