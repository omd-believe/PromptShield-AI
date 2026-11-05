package com.promptshield.backend.config;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Programmatic Resilience4j circuit breaker configuration for the AI microservice.
 *
 * <p>All thresholds and durations are externally configurable via {@code application.properties}
 * or environment variables. No AOP, Actuator, or Spring-Boot auto-config is required.
 *
 * <p>Circuit states:
 * <ul>
 *   <li><b>CLOSED</b> — normal operation; failures are counted.</li>
 *   <li><b>OPEN</b> — all calls immediately fail-fast with {@code CallNotPermittedException}.
 *       After {@code waitDurationSeconds} the circuit moves to HALF-OPEN.</li>
 *   <li><b>HALF-OPEN</b> — {@code halfOpenCalls} probe requests are sent.
 *       Success closes the circuit; continued failure re-opens it.</li>
 * </ul>
 *
 * <p>Exceptions that do <em>not</em> count as failures (client errors that should not trip
 * the breaker):
 * <ul>
 *   <li>{@link com.promptshield.backend.exception.PolicyBlockedException} (HTTP 422)</li>
 *   <li>{@link IllegalArgumentException} (HTTP 400)</li>
 * </ul>
 */
@Configuration
public class AiCircuitBreakerConfig {

    @Value("${ai.service.circuit-breaker.minimum-calls:5}")
    private int minimumCalls;

    @Value("${ai.service.circuit-breaker.failure-rate-threshold:50}")
    private float failureRateThreshold;

    @Value("${ai.service.circuit-breaker.wait-duration-seconds:30}")
    private int waitDurationSeconds;

    @Value("${ai.service.circuit-breaker.half-open-calls:2}")
    private int halfOpenCalls;

    @Value("${ai.service.circuit-breaker.sliding-window-size:10}")
    private int slidingWindowSize;

    /** Named constant used to look up the circuit breaker from the registry. */
    public static final String AI_SERVICE_CB = "aiService";

    @Bean
    public CircuitBreakerRegistry circuitBreakerRegistry() {
        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
                .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(slidingWindowSize)
                .minimumNumberOfCalls(minimumCalls)
                .failureRateThreshold(failureRateThreshold)
                .waitDurationInOpenState(Duration.ofSeconds(waitDurationSeconds))
                .permittedNumberOfCallsInHalfOpenState(halfOpenCalls)
                // Client-side errors must NOT trip the circuit breaker.
                .ignoreExceptions(
                        com.promptshield.backend.exception.PolicyBlockedException.class,
                        IllegalArgumentException.class
                )
                .build();

        return CircuitBreakerRegistry.of(config);
    }

    @Bean
    public CircuitBreaker aiServiceCircuitBreaker(CircuitBreakerRegistry registry) {
        return registry.circuitBreaker(AI_SERVICE_CB);
    }
}

