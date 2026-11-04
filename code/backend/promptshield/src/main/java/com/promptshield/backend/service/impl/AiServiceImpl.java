package com.promptshield.backend.service.impl;


import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.promptshield.backend.dto.response.AiOptimizeResponse;
import com.promptshield.backend.dto.response.PrivacyAnalysisResponse;
import com.promptshield.backend.exception.AiServiceException;
import com.promptshield.backend.exception.PolicyBlockedException;
import com.promptshield.backend.service.AiService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.Map;

@Service
public class AiServiceImpl implements AiService {

    private static final Logger log = LoggerFactory.getLogger(AiServiceImpl.class);

    private final WebClient webClient;
    private final int timeoutSeconds;
    private final String apiKey;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AiServiceImpl(
            WebClient webClient,
            @Value("${ai.service.timeout-seconds:60}") int timeoutSeconds,
            @Value("${ai.service.api-key:}") String apiKey) {
        this.webClient = webClient;
        this.timeoutSeconds = timeoutSeconds;
        this.apiKey = apiKey;
    }

    @Override
    public AiOptimizeResponse optimizePrompt(String prompt, Integer targetMaxTokens, Double minimumSemanticScore,
                                              Map<String, String> privacyPolicy) {
        return callAiService("/optimize", prompt, targetMaxTokens, minimumSemanticScore,
                privacyPolicy, AiOptimizeResponse.class);
    }

    @Override
    public PrivacyAnalysisResponse analyzePrompt(String prompt, Map<String, String> privacyPolicy) {
        return callAiService("/analyze", prompt, null, null, privacyPolicy, PrivacyAnalysisResponse.class);
    }

    private <T> T callAiService(
            String path,
            String prompt,
            Integer targetMaxTokens,
            Double minimumSemanticScore,
            Map<String, String> privacyPolicy,
            Class<T> responseType) {
        String requestId = java.util.UUID.randomUUID().toString();
        log.info("[{}] Dispatching AI service call to {} (promptLength={})",
                requestId, path, prompt != null ? prompt.length() : 0);
        T response;
        try {
            var requestSpec = webClient.post()
                    .uri(path)
                    .header("X-Request-ID", requestId);

            if (apiKey != null && !apiKey.isBlank()) {
                requestSpec.header("X-API-Key", apiKey);
                requestSpec.header("X-AI-Service-Key", apiKey);
            }

            response = requestSpec
                    .bodyValue(new PromptRequest(prompt, targetMaxTokens, minimumSemanticScore, privacyPolicy))
                    .retrieve()
                    .onStatus(HttpStatusCode::is4xxClientError, resp ->
                            resp.bodyToMono(String.class)
                                    .defaultIfEmpty("")
                                    .map(body -> {
                                        log.warn("[{}] AI service returned client error HTTP {}: {}",
                                                requestId, resp.statusCode().value(), body);
                                        if (resp.statusCode().value() == HttpStatus.UNPROCESSABLE_ENTITY.value()) {
                                            String msg = "Prompt contains a category blocked by the privacy policy.";
                                            try {
                                                JsonNode node = objectMapper.readTree(body);
                                                if (node.has("detail")) {
                                                    JsonNode detail = node.get("detail");
                                                    if (detail.isObject() && detail.has("message")) {
                                                        msg = detail.get("message").asText();
                                                    } else if (detail.isTextual()) {
                                                        msg = detail.asText();
                                                    }
                                                }
                                            } catch (Exception ignored) {}
                                            return new PolicyBlockedException(msg);
                                        }
                                        if (resp.statusCode().value() == HttpStatus.BAD_REQUEST.value()) {
                                            String msg = "Invalid prompt input";
                                            try {
                                                JsonNode node = objectMapper.readTree(body);
                                                if (node.has("detail") && node.get("detail").isTextual()) {
                                                    msg = node.get("detail").asText();
                                                }
                                            } catch (Exception ignored) {}
                                            return new IllegalArgumentException(msg);
                                        }
                                        return new AiServiceException(
                                                "AI service rejected the request (HTTP "
                                                        + resp.statusCode().value() + ")");
                                    }))
                    .onStatus(HttpStatusCode::is5xxServerError, resp ->
                            resp.bodyToMono(String.class)
                                    .defaultIfEmpty("")
                                    .map(body -> {
                                        log.error("[{}] AI service returned server error HTTP {}", requestId, resp.statusCode().value());
                                        return new AiServiceException("AI service failed to process the request.");
                                    }))
                    .bodyToMono(responseType)
                    .timeout(Duration.ofSeconds(timeoutSeconds))
                    .block();
        } catch (PolicyBlockedException | IllegalArgumentException | AiServiceException ex) {
            throw ex;
        } catch (Exception ex) {
            // Connection refused, DNS failure, timeout, bad JSON ...
            log.error("[{}] AI service call failed: {}", requestId, ex.toString());
            throw new AiServiceException("AI service is unavailable or timed out. Please try again.");
        }

        if (response == null) {
            throw new AiServiceException("AI service returned an empty response.");
        }
        return response;
    }

    private record PromptRequest(
            String prompt,
            Integer target_max_tokens,
            Double minimum_semantic_score,
            Map<String, String> privacy_policy) {
    }
}