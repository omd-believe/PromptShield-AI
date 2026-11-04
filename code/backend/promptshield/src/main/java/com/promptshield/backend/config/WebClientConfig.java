package com.promptshield.backend.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

/**
 * WebClient configuration for the AI microservice.
 *
 * <p>All requests to the AI service include an {@code X-API-Key} header
 * populated from the {@code AI_SERVICE_API_KEY} environment variable.
 * When the variable is empty (local dev without authentication), the header
 * is omitted to avoid sending an empty string as a credential.
 */
@Configuration
public class WebClientConfig {

    @Value("${ai.service.base-url}")
    private String aiServiceBaseUrl;

    /**
     * API key shared between this backend and the FastAPI AI service.
     * Set via AI_SERVICE_API_KEY environment variable.
     * Leave empty to disable authentication (local development only).
     */
    @Value("${ai.service.api-key:}")
    private String aiServiceApiKey;

    @Bean
    public WebClient webClient() {
        WebClient.Builder builder = WebClient.builder()
                .baseUrl(aiServiceBaseUrl);

        // Attach both X-API-Key and X-AI-Service-Key when a key is configured
        if (aiServiceApiKey != null && !aiServiceApiKey.isBlank()) {
            builder.defaultHeader("X-API-Key", aiServiceApiKey);
            builder.defaultHeader("X-AI-Service-Key", aiServiceApiKey);
        }

        return builder.build();
    }
}
