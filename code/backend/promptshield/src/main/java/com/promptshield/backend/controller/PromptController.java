package com.promptshield.backend.controller;


import com.promptshield.backend.dto.request.PromptRequest;
import com.promptshield.backend.dto.request.PrivacyAuditRequest;
import com.promptshield.backend.dto.response.PromptResponse;
import com.promptshield.backend.dto.response.PrivacyAnalysisResponse;
import com.promptshield.backend.dto.response.PromptStatsResponse;
import com.promptshield.backend.service.AiService;
import com.promptshield.backend.service.PromptService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.promptshield.backend.entity.PrivacyAuditEvent;
import com.promptshield.backend.entity.User;
import com.promptshield.backend.exception.ResourceNotFoundException;
import com.promptshield.backend.repository.PrivacyAuditEventRepository;
import com.promptshield.backend.repository.UserRepository;

@RestController
@RequestMapping("/api/v1/prompts")
@RequiredArgsConstructor
public class PromptController {

    private final PromptService promptService;
    private final AiService aiService;
    private final UserRepository userRepository;
    private final PrivacyAuditEventRepository auditRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @PostMapping
    public ResponseEntity<PromptResponse> optimizePrompt(
            @Valid @RequestBody PromptRequest request,
            @AuthenticationPrincipal Jwt jwt) {

        String email = jwt.getSubject();

        return ResponseEntity.ok(
                promptService.optimizePrompt(email, request)
        );
    }

    @PostMapping("/analyze")
    public ResponseEntity<PrivacyAnalysisResponse> analyzePrompt(
            @Valid @RequestBody PromptRequest request,
            @AuthenticationPrincipal Jwt jwt) {

        return ResponseEntity.ok(aiService.analyzePrompt(
                request.getPrompt(), request.getPrivacyPolicy()));
    }

    @GetMapping("/user")
    public ResponseEntity<List<PromptResponse>> getPromptHistory(
            @AuthenticationPrincipal Jwt jwt) {

        String email = jwt.getSubject();

        return ResponseEntity.ok(
                promptService.getPromptHistory(email)
        );
    }

    @GetMapping("/stats")
    public ResponseEntity<PromptStatsResponse> getPromptStats(
            @AuthenticationPrincipal Jwt jwt) {

        return ResponseEntity.ok(
                promptService.getPromptStats(jwt.getSubject())
        );
    }

    @PostMapping("/audit")
    public ResponseEntity<Void> recordAuditEvent(
            @Valid @RequestBody PrivacyAuditRequest request,
            @AuthenticationPrincipal Jwt jwt) {
        User user = userRepository.findByEmail(jwt.getSubject())
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));
        PrivacyAuditEvent event = new PrivacyAuditEvent();
        event.setUser(user);
        event.setPromptId(request.getPromptId());
        event.setEventType(request.getEventType());
        event.setRiskLevel(request.getRiskLevel());
        event.setRiskScore(request.getRiskScore());
        try {
            event.setCategoriesJson(objectMapper.writeValueAsString(
                    request.getCategories() == null ? List.of() : request.getCategories()));
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("Could not record audit categories", ex);
        }
        auditRepository.save(event);
        return ResponseEntity.noContent().build();
    }


    @DeleteMapping("/{promptId}")
    public ResponseEntity<Void> deletePrompt(
            @PathVariable Long promptId,
            @AuthenticationPrincipal Jwt jwt) {

        String email = jwt.getSubject();

        promptService.deletePrompt(email, promptId);

        return ResponseEntity.noContent().build();
    }

}
