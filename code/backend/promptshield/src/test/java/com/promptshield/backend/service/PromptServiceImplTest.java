package com.promptshield.backend.service;

import com.promptshield.backend.dto.request.PromptRequest;
import com.promptshield.backend.dto.response.AiOptimizeResponse;
import com.promptshield.backend.dto.response.PromptResponse;
import com.promptshield.backend.entity.AiEntity;
import com.promptshield.backend.entity.Prompt;
import com.promptshield.backend.entity.User;
import com.promptshield.backend.repository.PromptRepository;
import com.promptshield.backend.repository.UserRepository;
import com.promptshield.backend.service.impl.PromptServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class PromptServiceImplTest {

    @Mock
    private PromptRepository promptRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private AiService aiService;

    @InjectMocks
    private PromptServiceImpl promptService;

    private User testUser;

    @BeforeEach
    void setUp() {
        testUser = new User();
        testUser.setUserId(1L);
        testUser.setEmail("test@example.com");
    }

    @Test
    void optimizePrompt_ShouldPopulateTokensAndSensitiveFlag() {
        PromptRequest request = new PromptRequest();
        request.setPrompt("Please contact john@example.com for info");
        request.setTargetMaxTokens(250);
        request.setMinimumSemanticScore(92.5);
        request.setPrivacyPolicy(Map.of("EMAIL", "MASK", "API_KEY", "BLOCK"));

        AiOptimizeResponse aiResp = new AiOptimizeResponse();
        aiResp.setOriginalPrompt("Please contact john@example.com for info");
        aiResp.setOptimizedPrompt("contact [EMAIL] for info");
        aiResp.setRiskScore(60);
        aiResp.setRiskLevel("MEDIUM");
        aiResp.setOriginalTokens(6);
        aiResp.setOptimizedTokens(4);
        aiResp.setReductionPercentage(33.3);
        aiResp.setTargetMaxTokens(250);
        aiResp.setMinimumSemanticScore(92.5);
        aiResp.setTokenBudgetMet(true);
        aiResp.setPrivacyValid(true);
        aiResp.setLeakageDetected(false);

        AiEntity entity = new AiEntity();
        entity.setText("john@example.com");
        entity.setLabel("EMAIL");
        aiResp.setEntities(List.of(entity));

        when(userRepository.findByEmail("test@example.com")).thenReturn(Optional.of(testUser));
        when(aiService.optimizePrompt(
                request.getPrompt(),
                request.getTargetMaxTokens(),
                request.getMinimumSemanticScore(),
                request.getPrivacyPolicy())).thenReturn(aiResp);
        when(promptRepository.save(any(Prompt.class))).thenAnswer(invocation -> {
            Prompt p = invocation.getArgument(0);
            p.setPromptId(100L);
            p.setCreatedAt(LocalDateTime.now());
            return p;
        });

        PromptResponse result = promptService.optimizePrompt("test@example.com", request);

        assertNotNull(result);
        assertEquals(100L, result.getPromptId());
        assertEquals("contact [EMAIL] for info", result.getOptimizedPrompt());
        assertEquals(6, result.getOriginalTokens());
        assertEquals(4, result.getOptimizedTokens());
        assertEquals(33.3, result.getReductionPercentage());
        assertTrue(result.getSensitiveDataDetected());
        assertEquals(1, result.getEntities().size());
        assertEquals(60, result.getRiskScore());
        assertEquals("MEDIUM", result.getRiskLevel());
        assertEquals(250, result.getTargetMaxTokens());
        assertEquals(92.5, result.getMinimumSemanticScore());
        assertTrue(result.getTokenBudgetMet());
        assertTrue(result.getPrivacyValid());
        assertFalse(result.getLeakageDetected());
        assertEquals("MASK", result.getPrivacyPolicy().get("EMAIL"));

        verify(promptRepository, times(1)).save(argThat(p ->
                p.getOriginalTokens() == 6 &&
                p.getOptimizedTokens() == 4 &&
                p.getReductionPercentage() == 33.3 &&
                Boolean.TRUE.equals(p.getSensitiveDataDetected()) &&
                p.getTargetMaxTokens() == 250 &&
                p.getMinimumSemanticScore() == 92.5 &&
                p.getTokenBudgetMet() &&
                Boolean.TRUE.equals(p.getPrivacyValid()) &&
                Boolean.FALSE.equals(p.getLeakageDetected())
        ));
    }

    @Test
    void getPromptHistory_ShouldIncludeTokenMetrics() {
        Prompt p1 = new Prompt();
        p1.setPromptId(10L);
        p1.setOriginalPrompt("My text");
        p1.setOptimizedPrompt("text");
        p1.setOriginalTokens(2);
        p1.setOptimizedTokens(1);
        p1.setReductionPercentage(50.0);
        p1.setSensitiveDataDetected(false);
        p1.setCreatedAt(LocalDateTime.now());

        when(userRepository.findByEmail("test@example.com")).thenReturn(Optional.of(testUser));
        when(promptRepository.findByUserOrderByCreatedAtDesc(testUser)).thenReturn(List.of(p1));

        List<PromptResponse> history = promptService.getPromptHistory("test@example.com");

        assertEquals(1, history.size());
        PromptResponse item = history.get(0);
        assertEquals(10L, item.getPromptId());
        assertEquals(2, item.getOriginalTokens());
        assertEquals(1, item.getOptimizedTokens());
        assertEquals(50.0, item.getReductionPercentage());
        assertFalse(item.getSensitiveDataDetected());
    }

    @Test
    void getPromptHistory_ShouldDeserializePrivacyReportFromJson() {
        Prompt p1 = new Prompt();
        p1.setPromptId(11L);
        p1.setOriginalPrompt("Call john@example.com");
        p1.setOptimizedPrompt("Call [EMAIL]");
        p1.setPrivacyReportJson("{\"total_entities\":1,\"entity_types\":[{\"label\":\"EMAIL\",\"count\":1,\"masked_as\":\"[EMAIL]\"}]}");
        p1.setPrivacyPolicyJson("{\"EMAIL\":\"MASK\",\"API_KEY\":\"BLOCK\"}");
        p1.setTargetMaxTokens(300);
        p1.setMinimumSemanticScore(88.0);
        p1.setTokenBudgetMet(true);
        p1.setPrivacyValid(true);
        p1.setLeakageDetected(false);
        p1.setOptimizationWarningsJson("[\"Shortened safely\"]");
        p1.setSensitiveDataDetected(true);
        p1.setCreatedAt(LocalDateTime.now());

        when(userRepository.findByEmail("test@example.com")).thenReturn(Optional.of(testUser));
        when(promptRepository.findByUserOrderByCreatedAtDesc(testUser)).thenReturn(List.of(p1));

        List<PromptResponse> history = promptService.getPromptHistory("test@example.com");

        assertEquals(1, history.size());
        assertNotNull(history.get(0).getPrivacyReport());
        assertEquals(1, history.get(0).getPrivacyReport().getTotalEntities());
        assertEquals(1, history.get(0).getPrivacyReport().getEntityTypes().size());
        assertEquals("EMAIL", history.get(0).getPrivacyReport().getEntityTypes().get(0).getLabel());
        assertEquals("[EMAIL]", history.get(0).getPrivacyReport().getEntityTypes().get(0).getMaskedAs());
        assertEquals("MASK", history.get(0).getPrivacyPolicy().get("EMAIL"));
        assertEquals(300, history.get(0).getTargetMaxTokens());
        assertEquals(88.0, history.get(0).getMinimumSemanticScore());
        assertTrue(history.get(0).getTokenBudgetMet());
        assertTrue(history.get(0).getPrivacyValid());
        assertFalse(history.get(0).getLeakageDetected());
        assertEquals("Shortened safely", history.get(0).getOptimizationWarnings().get(0));
    }

    @Test
    void getPromptStats_ShouldReturnAggregateMetricsWithoutPromptContent() {
        Prompt prompt = new Prompt();
        prompt.setOriginalTokens(10);
        prompt.setOptimizedTokens(7);
        prompt.setReductionPercentage(30.0);
        prompt.setSensitiveDataDetected(true);
        prompt.setRiskLevel("HIGH");
        prompt.setSemanticValid(true);
        prompt.setPrivacyReportJson(
                "{\"total_entities\":2,\"entity_types\":["
                        + "{\"label\":\"EMAIL\",\"count\":1,\"masked_as\":\"[EMAIL]\"},"
                        + "{\"label\":\"PHONE\",\"count\":1,\"masked_as\":\"[PHONE]\"}]}"
        );

        when(userRepository.findByEmail("test@example.com")).thenReturn(Optional.of(testUser));
        when(promptRepository.findByUser(testUser)).thenReturn(List.of(prompt));

        var stats = promptService.getPromptStats("test@example.com");

        assertEquals(1, stats.getTotalPrompts());
        assertEquals(30.0, stats.getAverageTokenReduction());
        assertEquals(1, stats.getPromptsWithSensitiveData());
        assertEquals(2, stats.getTotalEntitiesDetected());
        assertEquals(3, stats.getTotalTokensSaved());
        assertEquals(1L, stats.getPrivacyCategories().get("EMAIL"));
        assertEquals(1L, stats.getPrivacyCategories().get("PHONE"));
        assertEquals(1L, stats.getRiskLevels().get("HIGH"));
        assertEquals(100.0, stats.getSemanticAcceptanceRate());
    }
}
