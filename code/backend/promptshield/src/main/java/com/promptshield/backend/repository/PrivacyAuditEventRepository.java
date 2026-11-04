package com.promptshield.backend.repository;

import com.promptshield.backend.entity.PrivacyAuditEvent;
import com.promptshield.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface PrivacyAuditEventRepository extends JpaRepository<PrivacyAuditEvent, Long> {
    List<PrivacyAuditEvent> findByUserOrderByCreatedAtDesc(User user);
}
