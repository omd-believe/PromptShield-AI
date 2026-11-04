package com.promptshield.backend.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Data
@NoArgsConstructor
@Table(name = "privacy_audit_events")
public class PrivacyAuditEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id")
    private User user;

    private Long promptId;
    private String eventType;
    private String riskLevel;
    private Integer riskScore;

    @Column(columnDefinition = "TEXT")
    private String categoriesJson;

    @CreationTimestamp
    private LocalDateTime createdAt;
}
