package com.promptshield.backend.service;

import com.promptshield.backend.dto.response.AiOptimizeResponse;
import com.promptshield.backend.dto.response.PrivacyAnalysisResponse;
import com.promptshield.backend.exception.AiServiceException;
import com.promptshield.backend.exception.PolicyBlockedException;
import com.promptshield.backend.service.impl.AiServiceImpl;
import com.promptshield.backend.service.impl.AiServiceImpl.AiServiceErrorCategory;
import com.promptshield.backend.service.impl.AiServiceImpl.NetworkErrorDetails;
import io.netty.channel.ConnectTimeoutException;
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
import java.net.ConnectException;
import java.net.SocketException;
import java.net.URI;
import java.net.UnknownHostException;
import java.util.Map;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

class AiServiceImplTest {

    private AiServiceImpl createServiceWithResponse(HttpStatus status, String jsonBody, AtomicReference<ClientRequest> requestRef) {
        ExchangeFunction exchangeFunction = request -> {
            if (requestRef != null) {
                requestRef.set(request);
            }
            return Mono.just(ClientResponse.create(status)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body(jsonBody)
                    .build());
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        return new AiServiceImpl(webClient, 5, "test-secret-api-key");
    }

    private AiServiceImpl createServiceWithError(Throwable error, AtomicReference<ClientRequest> requestRef) {
        ExchangeFunction exchangeFunction = request -> {
            if (requestRef != null) {
                requestRef.set(request);
            }
            return Mono.error(error);
        };
        WebClient webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .exchangeFunction(exchangeFunction)
                .build();
        return new AiServiceImpl(webClient, 5, "test-secret-api-key");
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
        TimeoutException timeout = new TimeoutException("Response timeout after 90000ms");
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

    // ─── Direct Helper Method Tests ─────────────────────────────────────────

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
}
