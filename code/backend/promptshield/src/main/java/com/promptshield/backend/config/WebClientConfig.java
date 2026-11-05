package com.promptshield.backend.config;

import io.netty.channel.ChannelOption;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.Http11SslContextSpec;
import reactor.netty.http.client.HttpClient;
import reactor.netty.resources.ConnectionProvider;

import java.time.Duration;

/**
 * WebClient configuration for the AI microservice.
 *
 * <p>Configures a reliable Reactor Netty HTTP client with:
 * <ul>
 *   <li>Connection timeout applied at socket level for fast failure on unreachable networks</li>
 *   <li>Response timeout tuned for deep learning GPU inference (e.g. Flan-T5, LLMLingua-2)</li>
 *   <li>Sensible connection pooling with proactive idle eviction to avoid stale tunnel/proxy sockets</li>
 *   <li>Standard TLS certificate verification preserved intact</li>
 * </ul>
 */
@Configuration
public class WebClientConfig {

    @Value("${ai.service.base-url}")
    private String aiServiceBaseUrl;

    @Value("${ai.service.api-key:}")
    private String aiServiceApiKey;

    @Value("${ai.service.timeout-seconds:90}")
    private int timeoutSeconds;

    @Value("${ai.service.connect-timeout-seconds:15}")
    private int connectTimeoutSeconds;

    @Bean
    public WebClient webClient() {
        // Connection pool tuned for external/tunneled microservices (e.g., Tailscale Funnel / Cloudflare Tunnel)
        // Stale connections are proactively evicted before remote gateways close them.
        ConnectionProvider connectionProvider = ConnectionProvider.builder("ai-service-pool")
                .maxConnections(50)
                .maxIdleTime(Duration.ofSeconds(30))
                .maxLifeTime(Duration.ofMinutes(5))
                .pendingAcquireTimeout(Duration.ofSeconds(10))
                .evictInBackground(Duration.ofSeconds(30))
                .build();

        HttpClient httpClient = HttpClient.create(connectionProvider)
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, connectTimeoutSeconds * 1000)
                .responseTimeout(Duration.ofSeconds(timeoutSeconds))
                .secure(ssl -> ssl.sslContext(Http11SslContextSpec.forClient())
                        .handshakeTimeout(Duration.ofSeconds(30)));

        WebClient.Builder builder = WebClient.builder()
                .baseUrl(aiServiceBaseUrl)
                .clientConnector(new ReactorClientHttpConnector(httpClient));

        // Attach authentication headers if configured
        if (aiServiceApiKey != null && !aiServiceApiKey.isBlank()) {
            builder.defaultHeader("X-API-Key", aiServiceApiKey);
            builder.defaultHeader("X-AI-Service-Key", aiServiceApiKey);
        }

        return builder.build();
    }
}
