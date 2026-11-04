package com.promptshield.backend.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.promptshield.backend.dto.request.PromptRequest;
import com.promptshield.backend.dto.response.AiOptimizeResponse;
import com.promptshield.backend.dto.response.PromptResponse;
import com.promptshield.backend.dto.response.PromptStatsResponse;
import com.promptshield.backend.dto.response.PrivacyReport;
import com.promptshield.backend.entity.Prompt;
import com.promptshield.backend.entity.User;
import com.promptshield.backend.exception.ResourceNotFoundException;
import com.promptshield.backend.repository.PromptRepository;
import com.promptshield.backend.repository.UserRepository;
import com.promptshield.backend.service.AiService;
import com.promptshield.backend.service.PromptService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;

@Service
@RequiredArgsConstructor
public class PromptServiceImpl implements PromptService {

    private final PromptRepository promptRepository;
    private final UserRepository userRepository;
    private final AiService aiService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public PromptResponse optimizePrompt(
            String email,
            PromptRequest request) {

        User user = userRepository.findByEmail(email)
                .orElseThrow(() ->
                        new ResourceNotFoundException("User not found"));

        // Send prompt to Python AI service
        AiOptimizeResponse aiResponse =
                aiService.optimizePrompt(
                        request.getPrompt(),
                        request.getTargetMaxTokens(),
                        request.getMinimumSemanticScore(),
                        request.getPrivacyPolicy());

        Prompt prompt = new Prompt();
        prompt.setOriginalPrompt(request.getPrompt());
        prompt.setOptimizedPrompt(aiResponse.getOptimizedPrompt());
        prompt.setUser(user);

        // Populate token, risk, and sensitivity fields from AI response
        prompt.setOriginalTokens(aiResponse.getOriginalTokens());
        prompt.setOptimizedTokens(aiResponse.getOptimizedTokens());
        prompt.setReductionPercentage(aiResponse.getReductionPercentage());
        prompt.setRiskScore(aiResponse.getRiskScore());
        prompt.setRiskLevel(aiResponse.getRiskLevel());
        prompt.setTargetMaxTokens(aiResponse.getTargetMaxTokens());
        prompt.setMinimumSemanticScore(aiResponse.getMinimumSemanticScore());
        prompt.setTokenBudgetMet(aiResponse.getTokenBudgetMet());
        prompt.setPrivacyValid(aiResponse.getPrivacyValid());
        prompt.setLeakageDetected(aiResponse.getLeakageDetected());
        try {
            prompt.setPrivacyReportJson(aiResponse.getPrivacyReport() == null
                    ? null
                    : objectMapper.writeValueAsString(aiResponse.getPrivacyReport()));
            prompt.setPrivacyPolicyJson(request.getPrivacyPolicy() == null
                    ? null
                    : objectMapper.writeValueAsString(request.getPrivacyPolicy()));
            prompt.setOptimizationWarningsJson(aiResponse.getOptimizationWarnings() == null
                    ? null
                    : objectMapper.writeValueAsString(aiResponse.getOptimizationWarnings()));
        } catch (JsonProcessingException e) {
            prompt.setPrivacyReportJson(null);
            prompt.setPrivacyPolicyJson(null);
            prompt.setOptimizationWarningsJson(null);
        }
        prompt.setSemanticSimilarityScore(aiResponse.getSemanticSimilarityScore());
        prompt.setSemanticValid(aiResponse.getSemanticValid());
        prompt.setGrammarCorrectionCount(aiResponse.getGrammarCorrections() == null
                ? 0
                : aiResponse.getGrammarCorrections().size());
        boolean hasSensitiveData = false;
        if (aiResponse.getEntities() != null && !aiResponse.getEntities().isEmpty()) {
            hasSensitiveData = aiResponse.getEntities().stream().anyMatch(e -> {
                String action = e.getPolicyAction();
                if (action == null && aiResponse.getPolicyActions() != null) {
                    action = aiResponse.getPolicyActions().get(e.getLabel());
                }
                return action == null || !"ALLOW".equalsIgnoreCase(action);
            });
        }
        prompt.setSensitiveDataDetected(hasSensitiveData);

        Prompt savedPrompt = promptRepository.save(prompt);

        return PromptResponse.builder()
                .promptId(savedPrompt.getPromptId())
                .originalPrompt(savedPrompt.getOriginalPrompt())
                .optimizedPrompt(savedPrompt.getOptimizedPrompt())
                .createdAt(savedPrompt.getCreatedAt())
                .entities(aiResponse.getEntities())
                .privacyReport(aiResponse.getPrivacyReport())
                .riskScore(aiResponse.getRiskScore())
                .riskLevel(aiResponse.getRiskLevel())
                .privacyReportJson(savedPrompt.getPrivacyReportJson())
                .privacyPolicy(request.getPrivacyPolicy())
                .policyActions(aiResponse.getPolicyActions())
                .confirmationRequired(aiResponse.getConfirmationRequired())
                .blocked(aiResponse.getBlocked())
                .blockedLabels(aiResponse.getBlockedLabels())
                .semanticSimilarityScore(aiResponse.getSemanticSimilarityScore())
                .semanticValid(aiResponse.getSemanticValid())
                .grammarCorrections(aiResponse.getGrammarCorrections())
                .grammarCorrected(aiResponse.getGrammarCorrected())
                .grammarCorrectionCount(savedPrompt.getGrammarCorrectionCount())
                .originalTokens(savedPrompt.getOriginalTokens())
                .anonymizedTokens(aiResponse.getAnonymizedTokens())
                .optimizedTokens(savedPrompt.getOptimizedTokens())
                .reductionPercentage(savedPrompt.getReductionPercentage())
                .compressionPercentage(aiResponse.getCompressionPercentage())
                .anonymizationTokenDelta(aiResponse.getAnonymizationTokenDelta())
                .targetMaxTokens(savedPrompt.getTargetMaxTokens())
                .minimumSemanticScore(savedPrompt.getMinimumSemanticScore())
                .tokenBudgetMet(savedPrompt.getTokenBudgetMet())
                .optimizationWarnings(aiResponse.getOptimizationWarnings())
                .privacyValid(savedPrompt.getPrivacyValid())
                .leakageDetected(savedPrompt.getLeakageDetected())
                .sensitiveDataDetected(savedPrompt.getSensitiveDataDetected())
                .optimizationStrategy(aiResponse.getOptimizationStrategy())
                .modelUsed(aiResponse.getModelUsed())
                .modelCandidateAccepted(aiResponse.getModelCandidateAccepted())
                .modelRejectionReason(aiResponse.getModelRejectionReason())
                .build();
    }

    @Override
    public List<PromptResponse> getPromptHistory(String email) {

        User user = userRepository.findByEmail(email)
                .orElseThrow(() ->
                        new ResourceNotFoundException("User not found"));

        return promptRepository
                .findByUserOrderByCreatedAtDesc(user)
                .stream()
                .map(p -> {
                    PrivacyReport privacyReport = null;
                    if (p.getPrivacyReportJson() != null && !p.getPrivacyReportJson().isBlank()) {
                        try {
                            privacyReport = objectMapper.readValue(p.getPrivacyReportJson(), PrivacyReport.class);
                        } catch (JsonProcessingException ignored) {
                            // Ignore malformed legacy entries and leave the report null.
                        }
                    }

                    Map<String, String> privacyPolicy = null;
                    if (p.getPrivacyPolicyJson() != null && !p.getPrivacyPolicyJson().isBlank()) {
                        try {
                            privacyPolicy = objectMapper.readValue(p.getPrivacyPolicyJson(), Map.class);
                        } catch (JsonProcessingException ignored) {
                            // Ignore malformed legacy entries and leave the policy null.
                        }
                    }

                    List<String> optimizationWarnings = null;
                    if (p.getOptimizationWarningsJson() != null && !p.getOptimizationWarningsJson().isBlank()) {
                        try {
                            optimizationWarnings = objectMapper.readValue(
                                    p.getOptimizationWarningsJson(),
                                    objectMapper.getTypeFactory().constructCollectionType(List.class, String.class));
                        } catch (JsonProcessingException ignored) {
                            // Ignore malformed legacy entries and leave warnings null.
                        }
                    }

                    List<com.promptshield.backend.entity.AiEntity> entities = new java.util.ArrayList<>();
                    if (privacyReport != null && privacyReport.getEntityTypes() != null) {
                        for (com.promptshield.backend.dto.response.EntityTypeSummary summary : privacyReport.getEntityTypes()) {
                            int count = summary.getCount() != null ? summary.getCount() : 1;
                            for (int i = 0; i < count; i++) {
                                com.promptshield.backend.entity.AiEntity entity = new com.promptshield.backend.entity.AiEntity();
                                entity.setLabel(summary.getLabel());
                                entity.setText(summary.getMaskedAs() != null ? summary.getMaskedAs() : "[" + summary.getLabel() + "]");
                                entity.setPolicyAction("MASK");
                                entities.add(entity);
                            }
                        }
                    }

                    return PromptResponse.builder()
                            .promptId(p.getPromptId())
                            .originalPrompt(p.getOriginalPrompt())
                            .optimizedPrompt(p.getOptimizedPrompt())
                            .createdAt(p.getCreatedAt())
                            .entities(entities)
                            .privacyReport(privacyReport)
                            .riskScore(p.getRiskScore())
                            .riskLevel(p.getRiskLevel())
                            .privacyReportJson(p.getPrivacyReportJson())
                            .privacyPolicy(privacyPolicy)
                            .semanticSimilarityScore(p.getSemanticSimilarityScore())
                            .semanticValid(p.getSemanticValid())
                            .grammarCorrections(null)
                            .grammarCorrected(p.getGrammarCorrectionCount() != null && p.getGrammarCorrectionCount() > 0)
                            .grammarCorrectionCount(p.getGrammarCorrectionCount())
                            .originalTokens(p.getOriginalTokens())
                            .optimizedTokens(p.getOptimizedTokens())
                            .reductionPercentage(p.getReductionPercentage())
                            .targetMaxTokens(p.getTargetMaxTokens())
                            .minimumSemanticScore(p.getMinimumSemanticScore())
                            .tokenBudgetMet(p.getTokenBudgetMet())
                            .optimizationWarnings(optimizationWarnings)
                            .privacyValid(p.getPrivacyValid())
                            .leakageDetected(p.getLeakageDetected())
                            .sensitiveDataDetected(p.getSensitiveDataDetected())
                            .build();
                })
                .toList();
    }

    @Override
    public PromptStatsResponse getPromptStats(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        List<Prompt> prompts = promptRepository.findByUser(user);
        Map<String, Long> privacyCategories = new LinkedHashMap<>();
        Map<String, Long> riskLevels = new LinkedHashMap<>();
        long totalEntities = 0;
        long totalTokensSaved = 0;
        double totalReduction = 0;
        int reductionSamples = 0;
        int semanticSamples = 0;
        int semanticAccepted = 0;
        long promptsWithSensitiveData = 0;

        for (Prompt prompt : prompts) {
            if (Boolean.TRUE.equals(prompt.getSensitiveDataDetected())) {
                promptsWithSensitiveData++;
            }
            if (prompt.getOriginalTokens() != null && prompt.getOptimizedTokens() != null) {
                totalTokensSaved += Math.max(
                        0,
                        prompt.getOriginalTokens() - prompt.getOptimizedTokens());
            }
            if (prompt.getReductionPercentage() != null) {
                totalReduction += prompt.getReductionPercentage();
                reductionSamples++;
            }
            if (prompt.getSemanticValid() != null) {
                semanticSamples++;
                if (Boolean.TRUE.equals(prompt.getSemanticValid())) {
                    semanticAccepted++;
                }
            }
            if (prompt.getRiskLevel() != null) {
                riskLevels.merge(prompt.getRiskLevel(), 1L, Long::sum);
            }

            PrivacyReport report = readPrivacyReport(prompt.getPrivacyReportJson());
            if (report != null && report.getEntityTypes() != null) {
                report.getEntityTypes().forEach(entity -> {
                    privacyCategories.merge(
                            entity.getLabel(),
                            (long) entity.getCount(),
                            Long::sum);
                });
                totalEntities += report.getTotalEntities();
            }
        }

        return PromptStatsResponse.builder()
                .totalPrompts(prompts.size())
                .averageTokenReduction(reductionSamples == 0
                        ? 0
                        : totalReduction / reductionSamples)
                .promptsWithSensitiveData(promptsWithSensitiveData)
                .totalEntitiesDetected(totalEntities)
                .totalTokensSaved(totalTokensSaved)
                .privacyCategories(privacyCategories)
                .riskLevels(riskLevels)
                .semanticAcceptanceRate(semanticSamples == 0
                        ? null
                        : (double) semanticAccepted / semanticSamples * 100)
                .build();
    }

    private PrivacyReport readPrivacyReport(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, PrivacyReport.class);
        } catch (JsonProcessingException ignored) {
            return null;
        }
    }

    @Override
    public void deletePrompt(String email, Long promptId) {

        User user = userRepository.findByEmail(email)
                .orElseThrow(() ->
                        new ResourceNotFoundException("User not found"));

        Prompt prompt = promptRepository
                .findByPromptIdAndUser(promptId, user)
                .orElseThrow(() ->
                        new ResourceNotFoundException("Prompt not found"));

        promptRepository.delete(prompt);
    }
}