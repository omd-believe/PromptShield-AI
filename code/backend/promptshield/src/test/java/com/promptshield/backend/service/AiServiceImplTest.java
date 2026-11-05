package com.promptshield.backend.service;

import com.promptshield.backend.dto.response.AiOptimizeResponse;
import com.promptshield.backend.dto.response.PrivacyAnalysisResponse;
import com.promptshield.backend.exception.AiCircuitBreakerOpenException;
import com.promptshield.backend.exception.AiServiceException;
import com.promptshield.backend.exception.PolicyBlockedException;
import com.promptshield.backend.service.impl.AiServiceImpl;
import com.promptshield.backend.service.impl.AiServiceImpl.AiServiceErrorCategory;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.netty.channel.ConnectTimeoutException;
import io.netty.handler.ssl.SslHandshakeTimeoutException;
import io.netty.handler.timeout.ReadTimeoutException;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.ClientRequest;
import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.ExchangeFunction;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import reactor.core.publisher.Mono;

import javax.net.ssl.SSLHandshakeException;
import javax.net.ssl.SSLPeerUnverifiedException;
import java.net.ConnectException;
import java.net.SocketException;
import java.net.URI;
import java.net.UnknownHostException;
import java.security.cert.CertificateException;
import java.security.cert.CertificateExpiredException;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

class AiServiceImplTest {

    // ── Helpers ───────────────────────────────────────────────────────────────

    /** No-op circuit breaker (always CLOSED, effectively never trips) for deterministic unit tests. */
    private static CircuitBreaker noOpCircuitBreaker() {
        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
                .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(100)
                .minimumNumberOfCalls(1000)       // effectively never reaches threshold in a unit test
                .failureRateThreshold(100.0f)
                .waitDurationInOpenState(Duration.ofHours(1))
                .build();
        return CircuitBreakerRegistry.of(config).circuitBreaker("test-noop");
    }

    /** Circuit breaker configured to open after 1 failure (for circuit-breaker tests). */
    private static CircuitBreaker sensitiveCircuitBreaker() {
        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
                .minimumNumberOfCalls(1)
                .slidingWindowSize(1)
                .failureRateThreshold(100.0f)       // open after 100 % failure rate
                .waitDurationInOpenState(Duration.ofSeconds(60))
                .permittedNumberOfCallsInHalfOpenState(1)
                .ignoreExceptions(
                        PolicyBlockedException.class,
                        IllegalArgumentException.class)
                .build();
        return CircuitBreakerRegistry.of(config).circuitBreaker("test-sensitive");
    }

    /** Circuit breaker configured with a fast wait duration for HALF-OPEN state transition tests. */
    private static CircuitBreaker fastTransitionCircuitBreaker(Duration waitInOpen, int halfOpenCalls) {
        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
                .minimumNumberOfCalls(1)
                .slidingWindowSize(1)
                .failureRateThreshold(100.0f)
                .waitDurationInOpenState(waitInOpen)
                .permittedNumberOfCallsInHalfOpenState(halfOpenCalls)
                .ignoreExceptions(
                        PolicyBlockedException.class,
                        IllegalArgumentException.class)
                .build();
        return CircuitBreakerRegistry.of(config).circuitBreaker("test-fast-transition-" + System.nanoTime());
    }

    private AiServiceImpl createServiceWithResponse(HttpStatus status, String jsonBody,
                                                    AtomicReference<ClientRequest> requestRef) {
        ExchangeFunction exchangeFunction = request -> {
            if (requestRef != null) requestRef.set(request);
            return Mono.just(ClientResponse.create(status)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body(jsonBody)
                    .build());
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        // retryMaxAttempts=0 → no retries in simple happy-path / HTTP-error tests
        return new AiServiceImpl(webClient, noOpCircuitBreaker(), 5, "test-secret-api-key",
                0, 100L, 500L, 0.0);
    }

    private AiServiceImpl createServiceWithError(Throwable error, AtomicReference<ClientRequest> requestRef) {
        ExchangeFunction exchangeFunction = request -> {
            if (requestRef != null) requestRef.set(request);
            return Mono.error(error);
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        // retryMaxAttempts=0 → no retries in simple error-classification tests
        return new AiServiceImpl(webClient, noOpCircuitBreaker(), 5, "test-secret-api-key",
                0, 100L, 500L, 0.0);
    }

    // ─── 1. Successful Prompt Optimization ───────────────────────────────────

    @Test
    @DisplayName("1. Should successfully execute prompt optimization and deserialize response DTO")
    void shouldSuccessfullyOptimizePrompt() {
        String json = """
            {
              "original_prompt": "Please contact test@example.com",
              "optimized_prompt": "Contact [EMAIL]",
              "original_tokens": 4,
              "optimized_tokens": 2,
              "reduction_percentage": 50.0,
              "risk_score": 15,
              "risk_level": "LOW",
              "semantic_valid": true,
              "entities": []
            }
            """;
        AtomicReference<ClientRequest> capturedReq = new AtomicReference<>();
        AiServiceImpl service = createServiceWithResponse(HttpStatus.OK, json, capturedReq);

        AiOptimizeResponse resp = service.optimizePrompt("Please contact test@example.com", 100, 85.0, Map.of("EMAIL", "MASK"));

        assertNotNull(resp);
        assertEquals("Contact [EMAIL]", resp.getOptimizedPrompt());
        assertEquals(4, resp.getOriginalTokens());
        assertEquals(2, resp.getOptimizedTokens());
        assertEquals(50.0, resp.getReductionPercentage());
        assertTrue(resp.getSemanticValid());
    }

    // ─── 2. Successful Privacy Analysis ──────────────────────────────────────

    @Test
    @DisplayName("2. Should successfully execute privacy analysis and deserialize response DTO")
    void shouldSuccessfullyAnalyzePrompt() {
        String json = """
            {
              "original_prompt": "My phone is 555-0199",
              "anonymized_prompt": "My phone is [PHONE]",
              "risk_score": 40,
              "risk_level": "MEDIUM",
              "blocked": false,
              "entities": []
            }
            """;
        AtomicReference<ClientRequest> capturedReq = new AtomicReference<>();
        AiServiceImpl service = createServiceWithResponse(HttpStatus.OK, json, capturedReq);

        PrivacyAnalysisResponse resp = service.analyzePrompt("My phone is 555-0199", Map.of("PHONE", "MASK"));

        assertNotNull(resp);
        assertEquals("My phone is [PHONE]", resp.getAnonymizedPrompt());
        assertEquals(40, resp.getRiskScore());
        assertEquals("MEDIUM", resp.getRiskLevel());
        assertFalse(resp.isBlocked());
    }

    // ─── 3. Authentication Headers ───────────────────────────────────────────

    @Test
    @DisplayName("3. Should attach both X-API-Key and X-AI-Service-Key and correlation ID headers")
    void shouldAttachAuthenticationHeaders() {
        String json = "{\"original_prompt\":\"a\",\"optimized_prompt\":\"a\"}";
        AtomicReference<ClientRequest> capturedReq = new AtomicReference<>();
        AiServiceImpl service = createServiceWithResponse(HttpStatus.OK, json, capturedReq);

        service.optimizePrompt("Test prompt", null, null, null);

        ClientRequest request = capturedReq.get();
        assertNotNull(request);
        assertEquals(HttpMethod.POST, request.method());
        assertEquals("http://localhost:8000/optimize", request.url().toString());
        assertEquals("test-secret-api-key", request.headers().getFirst("X-API-Key"));
        assertEquals("test-secret-api-key", request.headers().getFirst("X-AI-Service-Key"));
        assertNotNull(request.headers().getFirst("X-Request-ID"));
    }

    // ─── 4. HTTP 401 and 403 Responses ───────────────────────────────────────

    @Test
    @DisplayName("4a. Should handle HTTP 401 Unauthorized with dedicated configuration message")
    void shouldHandleHttp401Unauthorized() {
        String json = "{\"detail\":\"Invalid API key\"}";
        AiServiceImpl service = createServiceWithResponse(HttpStatus.UNAUTHORIZED, json, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Hello", null, null, null));

        assertTrue(ex.getMessage().contains("authentication"));
        assertTrue(ex.getMessage().contains("API key configuration"));
    }

    @Test
    @DisplayName("4b. Should handle HTTP 403 Forbidden with dedicated access message")
    void shouldHandleHttp403Forbidden() {
        String json = "{\"detail\":\"Forbidden access\"}";
        AiServiceImpl service = createServiceWithResponse(HttpStatus.FORBIDDEN, json, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.analyzePrompt("Hello", null));

        assertTrue(ex.getMessage().contains("forbidden"));
    }

    // ─── 5. Other HTTP 4xx and 5xx Responses ─────────────────────────────────

    @Test
    @DisplayName("5a. Should handle HTTP 422 Unprocessable Entity by throwing PolicyBlockedException")
    void shouldHandleHttp422PolicyBlocked() {
        String json = "{\"detail\":{\"message\":\"PAN card category is blocked by organization policy\"}}";
        AiServiceImpl service = createServiceWithResponse(HttpStatus.UNPROCESSABLE_ENTITY, json, null);

        PolicyBlockedException ex = assertThrows(PolicyBlockedException.class, () ->
                service.optimizePrompt("My PAN is ABCDE1234F", null, null, null));

        assertEquals("PAN card category is blocked by organization policy", ex.getMessage());
    }

    @Test
    @DisplayName("5b. Should handle HTTP 400 Bad Request by throwing IllegalArgumentException")
    void shouldHandleHttp400BadRequest() {
        String json = "{\"detail\":\"Prompt text cannot be empty or whitespace only\"}";
        AiServiceImpl service = createServiceWithResponse(HttpStatus.BAD_REQUEST, json, null);

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class, () ->
                service.optimizePrompt(" ", null, null, null));

        assertEquals("Prompt text cannot be empty or whitespace only", ex.getMessage());
    }

    @Test
    @DisplayName("5c. Should handle HTTP 429 Too Many Requests")
    void shouldHandleHttp429RateLimit() {
        String json = "{\"detail\":\"Rate limit exceeded\"}";
        AiServiceImpl service = createServiceWithResponse(HttpStatus.TOO_MANY_REQUESTS, json, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Prompt", null, null, null));

        assertTrue(ex.getMessage().contains("rate limit exceeded"));
    }

    @Test
    @DisplayName("5d. Should handle HTTP 500 Internal Server Error")
    void shouldHandleHttp500ServerError() {
        String json = "{\"detail\":\"Model inference failure\"}";
        AiServiceImpl service = createServiceWithResponse(HttpStatus.INTERNAL_SERVER_ERROR, json, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Prompt", null, null, null));

        assertTrue(ex.getMessage().contains("failed to process the request"));
        assertTrue(ex.getMessage().contains("500"));
    }

    @Test
    @DisplayName("5e. Should handle HTTP 503 Service Unavailable")
    void shouldHandleHttp503ServiceUnavailable() {
        String json = "{\"detail\":\"GPU worker queue overloaded\"}";
        AiServiceImpl service = createServiceWithResponse(HttpStatus.SERVICE_UNAVAILABLE, json, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Prompt", null, null, null));

        assertTrue(ex.getMessage().contains("temporarily unavailable"));
        assertTrue(ex.getMessage().contains("503"));
    }

    // ─── 6. Connection Failures ──────────────────────────────────────────────

    @Test
    @DisplayName("6a. Should distinguish DNS resolution failure and return helpful message")
    void shouldHandleDnsFailure() {
        UnknownHostException dnsEx = new UnknownHostException("fedora.tail1f8405.ts.net: Name or service not known");
        AiServiceImpl service = createServiceWithError(dnsEx, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.analyzePrompt("Sensitive prompt", null));

        assertTrue(ex.getMessage().contains("DNS resolution failure"));
        assertNotNull(ex.getCause());
    }

    @Test
    @DisplayName("6b. Should distinguish connection refused and return helpful message")
    void shouldHandleConnectionRefused() {
        ConnectException refused = new ConnectException("Connection refused");
        AiServiceImpl service = createServiceWithError(refused, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Prompt", null, null, null));

        assertTrue(ex.getMessage().contains("connection refused"));
        assertNotNull(ex.getCause());
    }

    @Test
    @DisplayName("6c. Should distinguish connection timeout during TCP handshake")
    void shouldHandleConnectTimeout() {
        ConnectTimeoutException timeout = new ConnectTimeoutException("connection timed out: fedora.tail1f8405.ts.net/100.80.90.100:443");
        AiServiceImpl service = createServiceWithError(timeout, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Prompt", null, null, null));

        assertTrue(ex.getMessage().contains("timed out"));
        assertNotNull(ex.getCause());
    }

    @Test
    @DisplayName("6d. Should distinguish connection reset by peer")
    void shouldHandleConnectionReset() {
        SocketException reset = new SocketException("Connection reset by peer");
        AiServiceImpl service = createServiceWithError(reset, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Prompt", null, null, null));

        assertTrue(ex.getMessage().contains("interrupted"));
        assertNotNull(ex.getCause());
    }

    @Test
    @DisplayName("6e. Should distinguish TLS handshake failure")
    void shouldHandleTlsHandshakeFailure() {
        SSLHandshakeException sslEx = new SSLHandshakeException("PKIX path building failed");
        AiServiceImpl service = createServiceWithError(sslEx, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Prompt", null, null, null));

        assertTrue(ex.getMessage().contains("TLS handshake failure"));
        assertNotNull(ex.getCause());
    }

    // ─── 7. Timeout Handling ─────────────────────────────────────────────────

    @Test
    @DisplayName("7. Should distinguish request inference timeout and provide actionable message")
    void shouldHandleInferenceTimeout() {
        TimeoutException timeout = new TimeoutException("Response timeout after 45000ms");
        AiServiceImpl service = createServiceWithError(timeout, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("Large prompt", null, null, null));

        assertTrue(ex.getMessage().contains("timed out during processing"));
        assertTrue(ex.getMessage().contains("shorter prompt"));
        assertNotNull(ex.getCause());
    }

    // ─── 8. Preservation of Original Exception Causes & Security Safeguards ──

    @Test
    @DisplayName("8a. Should preserve original exception as cause without leaking secrets or prompt text")
    void shouldPreserveOriginalCauseAndPreventLeakage() {
        ConnectException originalError = new ConnectException("Connection refused");
        AiServiceImpl service = createServiceWithError(originalError, null);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.analyzePrompt("Confidential prompt with PAN ABCDE1234F", null));

        // Cause chain preserved
        assertNotNull(ex.getCause());
        // No confidential prompt content in user-facing exception message
        assertFalse(ex.getMessage().contains("Confidential"));
        assertFalse(ex.getMessage().contains("ABCDE1234F"));
        // No secrets in user-facing exception message
        assertFalse(ex.getMessage().contains("test-secret-api-key"));
    }

    // ─── 9. Retry Behaviour & Conservative Policy ────────────────────────────

    @Test
    @DisplayName("9a. Should retry on transient TLS timeout and succeed on second attempt")
    void shouldRetryOnTlsTimeoutAndSucceedOnSecondAttempt() {
        String successJson = """
            {
              "original_prompt": "prompt",
              "optimized_prompt": "p",
              "original_tokens": 1,
              "optimized_tokens": 1,
              "reduction_percentage": 0.0,
              "risk_score": 5,
              "risk_level": "LOW",
              "semantic_valid": true,
              "entities": []
            }
            """;
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            if (callCount.incrementAndGet() == 1) {
                // First call: TLS timeout (pre-request retryable)
                return Mono.error(new javax.net.ssl.SSLHandshakeException("handshake timed out after 10000ms"));
            }
            // Second call: success
            return Mono.just(ClientResponse.create(HttpStatus.OK)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body(successJson)
                    .build());
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        // retryMaxAttempts=1 (1 retry allowed → 2 total calls)
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        AiOptimizeResponse resp = service.optimizePrompt("prompt", null, null, null);

        assertNotNull(resp);
        assertEquals("p", resp.getOptimizedPrompt());
        assertEquals(2, callCount.get()); // initial + 1 retry
    }

    @Test
    @DisplayName("9b. Should retry on DNS resolution failure")
    void shouldRetryOnDnsFailure() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new UnknownHostException("fedora.tail1f8405.ts.net: Name or service not known"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(2, callCount.get()); // initial + 1 retry
    }

    @Test
    @DisplayName("9c. Should retry on Connection Refused")
    void shouldRetryOnConnectionRefused() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new ConnectException("Connection refused"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(2, callCount.get()); // initial + 1 retry
    }

    @Test
    @DisplayName("9d. Should retry on TCP Connection Timeout")
    void shouldRetryOnConnectTimeout() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new ConnectTimeoutException("connection timed out: 100.80.90.100:443"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(2, callCount.get()); // initial + 1 retry
    }

    @Test
    @DisplayName("9e. Should NOT retry on ResponseTimeoutException (inference timeout) — prevents duplicate GPU execution")
    void shouldNotRetryOnResponseTimeout() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new TimeoutException("Response timeout after 45000ms"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(1, callCount.get()); // exactly 1 call, NO retry
    }

    @Test
    @DisplayName("9f. Should NOT retry on Connection Reset — prevents duplicate GPU execution if server already received payload")
    void shouldNotRetryOnConnectionReset() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new SocketException("Connection reset by peer"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(1, callCount.get()); // exactly 1 call, NO retry
    }

    @Test
    @DisplayName("9g. Should NOT retry on generic fallback NETWORK_ERROR")
    void shouldNotRetryOnGenericNetworkError() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new RuntimeException("Unexpected socket pipeline glitch"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(1, callCount.get()); // exactly 1 call, NO retry
    }

    @Test
    @DisplayName("9h. Should NOT retry on HTTP 401 — authentication errors are deterministic")
    void shouldNotRetryOnHttp401() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.just(ClientResponse.create(HttpStatus.UNAUTHORIZED)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body("{\"detail\":\"Invalid key\"}")
                    .build());
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(1, callCount.get()); // exactly one call, no retry
    }

    @Test
    @DisplayName("9i. Should NOT retry on HTTP 403 Forbidden")
    void shouldNotRetryOnHttp403() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.just(ClientResponse.create(HttpStatus.FORBIDDEN)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body("{\"detail\":\"Forbidden\"}")
                    .build());
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.analyzePrompt("prompt", null));

        assertEquals(1, callCount.get()); // exactly one call, no retry
    }

    @Test
    @DisplayName("9j. Should NOT retry on HTTP 422 PolicyBlockedException")
    void shouldNotRetryOnHttp422() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.just(ClientResponse.create(HttpStatus.UNPROCESSABLE_ENTITY)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body("{\"detail\":{\"message\":\"Blocked\"}}")
                    .build());
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(PolicyBlockedException.class, () ->
                service.optimizePrompt("blocked prompt", null, null, null));

        assertEquals(1, callCount.get()); // exactly one call, no retry
    }

    @Test
    @DisplayName("9k. Should NOT retry on HTTP 429 Rate Limit")
    void shouldNotRetryOnHttp429() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.just(ClientResponse.create(HttpStatus.TOO_MANY_REQUESTS)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body("{\"detail\":\"Rate limit exceeded\"}")
                    .build());
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(1, callCount.get()); // exactly one call, no retry
    }

    @Test
    @DisplayName("9l. Should exhaust retries and throw AiServiceException on persistent connection failure")
    void shouldExhaustRetriesAndThrow() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new ConnectException("Connection refused"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        // 1 retry → 2 total calls
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(2, callCount.get()); // initial + 1 retry
        assertTrue(ex.getMessage().contains("connection refused"));
    }

    @Test
    @DisplayName("9m. Should NOT retry on Certificate validation failure (PKIX path building failure)")
    void shouldNotRetryOnCertificateValidationFailure() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new SSLHandshakeException("PKIX path building failed: sun.security.provider.certpath.SunCertPathBuilderException: unable to find valid certification path"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(1, callCount.get()); // exactly 1 call, NO retry
    }

    @Test
    @DisplayName("9n. Should NOT retry on Hostname mismatch (SSLPeerUnverifiedException)")
    void shouldNotRetryOnHostnameMismatch() {
        AtomicInteger callCount = new AtomicInteger(0);
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();
            return Mono.error(new SSLPeerUnverifiedException("Certificate for <fedora.ts.net> doesn't match CN: other.com"));
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, noOpCircuitBreaker(), 5,
                "key", 1, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        assertEquals(1, callCount.get()); // exactly 1 call, NO retry
    }

    // ─── 10. Circuit Breaker Behaviour & State Transitions ───────────────────

    @Test
    @DisplayName("10a. Circuit breaker should open after threshold failures and reject subsequent calls with AiCircuitBreakerOpenException")
    void circuitBreakerShouldOpenAfterThresholdFailures() {
        CircuitBreaker cb = sensitiveCircuitBreaker();

        // First call: fails and trips the breaker (1/1 = 100% failure rate → OPEN)
        ExchangeFunction failExchange = request ->
                Mono.error(new ConnectException("Connection refused"));
        WebClient failWebClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(failExchange)
                .build();
        AiServiceImpl service = new AiServiceImpl(failWebClient, cb, 5, "key",
                0, 10L, 50L, 0.0);

        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));

        // Now the circuit is OPEN — next call should fail-fast with AiCircuitBreakerOpenException
        AiCircuitBreakerOpenException cbEx = assertThrows(AiCircuitBreakerOpenException.class, () ->
                service.optimizePrompt("prompt2", null, null, null));

        assertTrue(cbEx.getMessage().contains("temporarily unavailable"));
        assertTrue(cbEx.getMessage().contains("service protection is active"));
        assertEquals(CircuitBreaker.State.OPEN, cb.getState());
    }

    @Test
    @DisplayName("10b. PolicyBlockedException and IllegalArgumentException should NOT trip the circuit breaker")
    void clientInputExceptionsShouldNotTripCircuitBreaker() {
        CircuitBreaker cb = sensitiveCircuitBreaker();

        ExchangeFunction blockedExchange = request ->
                Mono.just(ClientResponse.create(HttpStatus.UNPROCESSABLE_ENTITY)
                        .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                        .body("{\"detail\":{\"message\":\"Blocked\"}}")
                        .build());
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(blockedExchange)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, cb, 5, "key",
                0, 10L, 50L, 0.0);

        // Even if PolicyBlockedException occurs, circuit must remain CLOSED
        assertThrows(PolicyBlockedException.class, () ->
                service.optimizePrompt("blocked prompt", null, null, null));

        assertEquals(CircuitBreaker.State.CLOSED, cb.getState());
    }

    @Test
    @DisplayName("10c. State transition: OPEN -> HALF_OPEN -> CLOSED on successful half-open probe")
    void shouldTransitionFromOpenToHalfOpenToClosedOnSuccess() throws InterruptedException {
        // Fast transition: 50 ms in OPEN state, 1 permitted probe in HALF-OPEN
        CircuitBreaker cb = fastTransitionCircuitBreaker(Duration.ofMillis(50), 1);

        AtomicInteger callCount = new AtomicInteger(0);
        String successJson = "{\"original_prompt\":\"a\",\"optimized_prompt\":\"a\"}";

        ExchangeFunction exchange = request -> {
            if (callCount.incrementAndGet() == 1) {
                return Mono.error(new ConnectException("Connection refused"));
            }
            return Mono.just(ClientResponse.create(HttpStatus.OK)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body(successJson)
                    .build());
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchange)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, cb, 5, "key",
                0, 10L, 50L, 0.0);

        // 1. Initial call fails -> OPEN
        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));
        assertEquals(CircuitBreaker.State.OPEN, cb.getState());

        // 2. Wait for open-state duration to elapse
        Thread.sleep(70);

        // 3. Next call executes probe in HALF_OPEN and succeeds -> transitions to CLOSED
        AiOptimizeResponse resp = service.optimizePrompt("prompt", null, null, null);
        assertNotNull(resp);
        assertEquals(CircuitBreaker.State.CLOSED, cb.getState());
    }

    @Test
    @DisplayName("10d. State transition: OPEN -> HALF_OPEN -> OPEN on failed half-open probe")
    void shouldTransitionFromOpenToHalfOpenToOpenOnProbeFailure() throws InterruptedException {
        // Fast transition: 50 ms in OPEN state, 1 permitted probe in HALF-OPEN
        CircuitBreaker cb = fastTransitionCircuitBreaker(Duration.ofMillis(50), 1);

        ExchangeFunction failExchange = request ->
                Mono.error(new ConnectException("Persistent connection failure"));

        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(failExchange)
                .build();
        AiServiceImpl service = new AiServiceImpl(webClient, cb, 5, "key",
                0, 10L, 50L, 0.0);

        // 1. Initial call fails -> OPEN
        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("prompt", null, null, null));
        assertEquals(CircuitBreaker.State.OPEN, cb.getState());

        // 2. Wait for open-state duration to elapse
        Thread.sleep(70);

        // 3. Next probe call fails in HALF_OPEN -> transitions immediately back to OPEN
        assertThrows(AiServiceException.class, () ->
                service.optimizePrompt("probe prompt", null, null, null));
        assertEquals(CircuitBreaker.State.OPEN, cb.getState());
    }

    // ─── 11. Helper Method & isRetryable Unit Tests ───────────────────────────

    @Test
    @DisplayName("Helper: Classify Netty ReadTimeoutException as REQUEST_TIMEOUT")
    void helperShouldClassifyReadTimeout() {
        assertEquals(AiServiceErrorCategory.REQUEST_TIMEOUT, AiServiceImpl.classifyError(ReadTimeoutException.INSTANCE));
    }

    @Test
    @DisplayName("Helper: Sanitize URI and strip query parameters and credentials")
    void helperShouldSanitizeUri() {
        URI sensitiveUri = URI.create("https://fedora.tail1f8405.ts.net:8443/analyze?api_key=secret-key&token=123");
        String sanitized = AiServiceImpl.sanitizeUri(sensitiveUri);

        assertEquals("https://fedora.tail1f8405.ts.net:8443/analyze", sanitized);
        assertFalse(sanitized.contains("api_key"));
        assertFalse(sanitized.contains("secret-key"));
    }

    @Test
    @DisplayName("Helper: Extract root cause traversing multiple wrapper layers")
    void helperShouldExtractDeepRootCause() {
        UnknownHostException root = new UnknownHostException("fedora.tail1f8405.ts.net");
        RuntimeException layer1 = new RuntimeException("Layer 1", root);
        WebClientRequestException topLayer = new WebClientRequestException(
                layer1, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), new HttpHeaders());

        Throwable extracted = AiServiceImpl.extractRootCause(topLayer);
        assertSame(root, extracted);
    }

    @Test
    @DisplayName("11a. isRetryable: DNS failure should be retryable")
    void isRetryableShouldReturnTrueForDnsFailure() {
        assertTrue(AiServiceImpl.isRetryable(new UnknownHostException("not found"), "id", "/analyze"));
    }

    @Test
    @DisplayName("11b. isRetryable: Connection refused should be retryable")
    void isRetryableShouldReturnTrueForConnectionRefused() {
        assertTrue(AiServiceImpl.isRetryable(new ConnectException("Connection refused"), "id", "/analyze"));
    }

    @Test
    @DisplayName("11c. isRetryable: Connection timeout should be retryable")
    void isRetryableShouldReturnTrueForConnectTimeout() {
        assertTrue(AiServiceImpl.isRetryable(new ConnectTimeoutException("connection timed out"), "id", "/analyze"));
    }

    @Test
    @DisplayName("11d. isRetryable: Transient TLS handshake timeout should be retryable")
    void isRetryableShouldReturnTrueForTlsHandshakeTimeout() {
        assertTrue(AiServiceImpl.isRetryable(new SslHandshakeTimeoutException("handshake timed out after 15000ms"), "id", "/analyze"));
        assertTrue(AiServiceImpl.isRetryable(new SSLHandshakeException("handshake timed out after 10000ms"), "id", "/analyze"));
    }

    @Test
    @DisplayName("11e. isRetryable: Certificate validation failures should NOT be retryable")
    void isRetryableShouldReturnFalseForCertificateValidationFailures() {
        assertFalse(AiServiceImpl.isRetryable(new CertificateExpiredException("NotAfter: Wed Nov 04 2026"), "id", "/analyze"));
        assertFalse(AiServiceImpl.isRetryable(new CertificateException("Untrusted certificate authority"), "id", "/analyze"));
        assertFalse(AiServiceImpl.isRetryable(new SSLPeerUnverifiedException("Hostname does not match"), "id", "/analyze"));
        assertFalse(AiServiceImpl.isRetryable(new SSLHandshakeException("PKIX path building failed: unable to find valid certification path"), "id", "/analyze"));
    }

    @Test
    @DisplayName("11f. isRetryable: Response timeout / TimeoutException should NOT be retryable")
    void isRetryableShouldReturnFalseForResponseTimeout() {
        assertFalse(AiServiceImpl.isRetryable(new TimeoutException("Response timeout after 45000ms"), "id", "/optimize"));
        assertFalse(AiServiceImpl.isRetryable(ReadTimeoutException.INSTANCE, "id", "/optimize"));
    }

    @Test
    @DisplayName("11g. isRetryable: Connection reset should NOT be retryable")
    void isRetryableShouldReturnFalseForConnectionReset() {
        assertFalse(AiServiceImpl.isRetryable(new SocketException("Connection reset by peer"), "id", "/optimize"));
    }

    @Test
    @DisplayName("11h. isRetryable: Generic network error should NOT be retryable")
    void isRetryableShouldReturnFalseForGenericNetworkError() {
        assertFalse(AiServiceImpl.isRetryable(new RuntimeException("Generic network error"), "id", "/optimize"));
    }

    @Test
    @DisplayName("11i. isRetryable: PolicyBlockedException should NOT be retryable")
    void isRetryableShouldReturnFalseForPolicyBlocked() {
        assertFalse(AiServiceImpl.isRetryable(new PolicyBlockedException("blocked"), "id", "/optimize"));
    }

    @Test
    @DisplayName("11j. isRetryable: AiServiceException should NOT be retryable")
    void isRetryableShouldReturnFalseForAiServiceException() {
        assertFalse(AiServiceImpl.isRetryable(new AiServiceException("auth error"), "id", "/optimize"));
    }

    @Test
    @DisplayName("11k. isRetryable: IllegalArgumentException should NOT be retryable")
    void isRetryableShouldReturnFalseForIllegalArgument() {
        assertFalse(AiServiceImpl.isRetryable(new IllegalArgumentException("bad input"), "id", "/analyze"));
    }
}
