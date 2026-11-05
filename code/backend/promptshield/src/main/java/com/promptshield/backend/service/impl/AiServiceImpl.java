package com.promptshield.backend.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.promptshield.backend.dto.response.AiOptimizeResponse;
import com.promptshield.backend.dto.response.PrivacyAnalysisResponse;
import com.promptshield.backend.exception.AiCircuitBreakerOpenException;
import com.promptshield.backend.exception.AiServiceException;
import com.promptshield.backend.exception.PolicyBlockedException;
import com.promptshield.backend.service.AiService;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.netty.handler.ssl.SslHandshakeTimeoutException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;
import reactor.util.retry.Retry;

import java.net.URI;
import java.time.Duration;
import java.util.Map;

/**
 * Production-grade AI service client with:
 * <ul>
 *   <li>Detailed, privacy-safe error logging (no prompt text, no API keys)</li>
 *   <li>Precise network error classification (DNS, TLS, connect timeout, read timeout, connection reset)</li>
 *   <li>Conservative pre-request retry policy (default 1 retry) to prevent duplicate GPU inference</li>
 *   <li>Resilience4j circuit breaker returning HTTP 503 when the AI service is persistently unavailable</li>
 * </ul>
 *
 * <h3>Conservative Retry Policy</h3>
 * Retries are strictly limited to verified <em>pre-request</em> transient infrastructure failures:
 * <ul>
 *   <li>DNS resolution failures</li>
 *   <li>TCP connection timeouts</li>
 *   <li>Connection refused / host unreachable</li>
 *   <li>TLS handshake failures</li>
 * </ul>
 * <p>Retries are explicitly <em>rejected</em> for:
 * <ul>
 *   <li>{@code REQUEST_TIMEOUT} / {@code ResponseTimeoutException} — FastAPI received the POST body and may already be running GPU inference</li>
 *   <li>{@code CONNECTION_RESET_OR_CLOSED} — connection dropped after request transmission could lead to duplicate inference</li>
 *   <li>Generic {@code NETWORK_ERROR} — unknown errors or serialization faults must fail fast</li>
 *   <li>All HTTP 4xx responses (400, 401, 403, 422, 429)</li>
 *   <li>Application-level {@link AiServiceException}</li>
 * </ul>
 */
@Service
public class AiServiceImpl implements AiService {

    private static final Logger log = LoggerFactory.getLogger(AiServiceImpl.class);

    // ── Error Categories ──────────────────────────────────────────────────────

    public enum AiServiceErrorCategory {
        DNS_RESOLUTION_FAILURE,
        CONNECTION_TIMEOUT,
        CONNECTION_REFUSED_OR_UNREACHABLE,
        TLS_HANDSHAKE_TIMEOUT,
        TLS_CERTIFICATE_FAILURE,
        TLS_HANDSHAKE_FAILURE,
        REQUEST_TIMEOUT,
        CONNECTION_RESET_OR_CLOSED,
        HTTP_STATUS_ERROR,
        NETWORK_ERROR,
        UNKNOWN_ERROR
    }

    public record NetworkErrorDetails(
            AiServiceErrorCategory category,
            String rootCauseClass,
            String rootCauseMessage,
            String targetUri,
            String httpMethod
    ) {}

    // ── Fields ────────────────────────────────────────────────────────────────

    private final WebClient webClient;
    private final CircuitBreaker circuitBreaker;
    private final int timeoutSeconds;
    private final String apiKey;
    private final int retryMaxAttempts;
    private final long retryInitialBackoffMs;
    private final long retryMaxBackoffMs;
    private final double retryJitterFactor;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AiServiceImpl(
            WebClient webClient,
            CircuitBreaker circuitBreaker,
            @Value("${ai.service.timeout-seconds:45}") int timeoutSeconds,
            @Value("${ai.service.api-key:}") String apiKey,
            @Value("${ai.service.retry.max-attempts:1}") int retryMaxAttempts,
            @Value("${ai.service.retry.initial-backoff-ms:1000}") long retryInitialBackoffMs,
            @Value("${ai.service.retry.max-backoff-ms:3000}") long retryMaxBackoffMs,
            @Value("${ai.service.retry.jitter-factor:0.5}") double retryJitterFactor) {
        this.webClient = webClient;
        this.circuitBreaker = circuitBreaker;
        this.timeoutSeconds = timeoutSeconds;
        this.apiKey = apiKey;
        this.retryMaxAttempts = retryMaxAttempts;
        this.retryInitialBackoffMs = retryInitialBackoffMs;
        this.retryMaxBackoffMs = retryMaxBackoffMs;
        this.retryJitterFactor = retryJitterFactor;
    }

    // ── Public API ────────────────────────────────────────────────────────────

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

    // ── Core call with retry + circuit breaker ────────────────────────────────

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

        long startTime = System.currentTimeMillis();

        // Check circuit breaker state before dispatching — fail fast with HTTP 503 equivalent
        if (!circuitBreaker.tryAcquirePermission()) {
            CircuitBreaker.State state = circuitBreaker.getState();
            log.warn("[{}] Circuit breaker is {} — rejecting AI request to {} immediately.",
                    requestId, state, path);
            throw new AiCircuitBreakerOpenException(
                    "AI optimization is temporarily unavailable (service protection is active). " +
                    "Please try again shortly.");
        }

        T response;
        long durationMs;
        try {
            response = executeWithRetry(requestId, path, prompt, targetMaxTokens,
                    minimumSemanticScore, privacyPolicy, responseType);
            durationMs = System.currentTimeMillis() - startTime;
            circuitBreaker.onSuccess(durationMs, java.util.concurrent.TimeUnit.MILLISECONDS);
            log.info("[{}] AI service call to {} succeeded in {} ms.", requestId, path, durationMs);
        } catch (PolicyBlockedException | IllegalArgumentException ex) {
            // Client-side input errors — do NOT count against the circuit breaker.
            circuitBreaker.releasePermission();
            throw ex;
        } catch (AiServiceException ex) {
            durationMs = System.currentTimeMillis() - startTime;
            circuitBreaker.onError(durationMs, java.util.concurrent.TimeUnit.MILLISECONDS, ex);
            throw ex;
        } catch (Exception ex) {
            durationMs = System.currentTimeMillis() - startTime;
            circuitBreaker.onError(durationMs, java.util.concurrent.TimeUnit.MILLISECONDS, ex);
            NetworkErrorDetails details = analyzeError(ex, "POST", path);
            Throwable rootCause = extractRootCause(ex);
            log.error("[{}] AI service connectivity failure [Category: {}]: method={}, target={}, " +
                      "rootCauseClass={}, rootCauseMessage={}, durationMs={}",
                    requestId, details.category(), details.httpMethod(), details.targetUri(),
                    details.rootCauseClass(), details.rootCauseMessage(), durationMs,
                    rootCause != null ? rootCause : ex);
            throw new AiServiceException(mapCategoryToUserMessage(details.category()), ex);
        }

        if (response == null) {
            throw new AiServiceException("AI service returned an empty response.");
        }
        return response;
    }

    /**
     * Executes one WebClient call and applies conservative exponential-backoff retry
     * strictly for pre-request network failures.
     */
    private <T> T executeWithRetry(
            String requestId,
            String path,
            String prompt,
            Integer targetMaxTokens,
            Double minimumSemanticScore,
            Map<String, String> privacyPolicy,
            Class<T> responseType) {

        var requestSpec = webClient.post()
                .uri(path)
                .header("X-Request-ID", requestId);

        if (apiKey != null && !apiKey.isBlank()) {
            requestSpec.headers(h -> {
                h.set("X-API-Key", apiKey);
                h.set("X-AI-Service-Key", apiKey);
            });
        }

        return requestSpec
                .bodyValue(new PromptRequest(prompt, targetMaxTokens, minimumSemanticScore, privacyPolicy))
                .retrieve()
                .onStatus(HttpStatusCode::is4xxClientError, resp ->
                        resp.bodyToMono(String.class)
                                .defaultIfEmpty("")
                                .map(body -> {
                                    int status = resp.statusCode().value();
                                    log.warn("[{}] AI service returned client error HTTP {}", requestId, status);

                                    if (status == HttpStatus.UNAUTHORIZED.value()) {
                                        log.error("[{}] AI service authentication failed (HTTP 401). " +
                                                  "Verify AI_SERVICE_API_KEY configuration.", requestId);
                                        return new AiServiceException(
                                                "AI service rejected authentication. Please check API key configuration.");
                                    }

                                    if (status == HttpStatus.FORBIDDEN.value()) {
                                        log.error("[{}] AI service access forbidden (HTTP 403). " +
                                                  "Verify AI_SERVICE_API_KEY permissions.", requestId);
                                        return new AiServiceException("AI service access is forbidden.");
                                    }

                                    if (status == HttpStatus.UNPROCESSABLE_ENTITY.value()) {
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

                                    if (status == HttpStatus.BAD_REQUEST.value()) {
                                        String msg = "Invalid prompt input";
                                        try {
                                            JsonNode node = objectMapper.readTree(body);
                                            if (node.has("detail") && node.get("detail").isTextual()) {
                                                msg = node.get("detail").asText();
                                            }
                                        } catch (Exception ignored) {}
                                        return new IllegalArgumentException(msg);
                                    }

                                    if (status == HttpStatus.TOO_MANY_REQUESTS.value()) {
                                        return new AiServiceException(
                                                "AI service rate limit exceeded. Please try again shortly.");
                                    }

                                    return new AiServiceException(
                                            "AI service rejected the request (HTTP " + status + ").");
                                }))
                .onStatus(HttpStatusCode::is5xxServerError, resp ->
                        resp.bodyToMono(String.class)
                                .defaultIfEmpty("")
                                .map(body -> {
                                    int status = resp.statusCode().value();
                                    log.error("[{}] AI service returned server error HTTP {}", requestId, status);
                                    if (status == HttpStatus.SERVICE_UNAVAILABLE.value()
                                            || status == HttpStatus.GATEWAY_TIMEOUT.value()) {
                                        return new AiServiceException(
                                                "AI service is temporarily unavailable (HTTP " + status + "). Please try again.");
                                    }
                                    return new AiServiceException(
                                            "AI service failed to process the request (HTTP " + status + ").");
                                }))
                .bodyToMono(responseType)
                .timeout(Duration.ofSeconds(timeoutSeconds))
                .retryWhen(buildRetrySpec(requestId, path))
                .block();
    }

    /**
     * Builds an exponential-backoff retry specification for pre-request network failures.
     */
    private Retry buildRetrySpec(String requestId, String path) {
        return Retry.backoff(retryMaxAttempts, Duration.ofMillis(retryInitialBackoffMs))
                .maxBackoff(Duration.ofMillis(retryMaxBackoffMs))
                .jitter(retryJitterFactor)
                .filter(throwable -> isRetryable(throwable, requestId, path))
                .onRetryExhaustedThrow((spec, signal) -> {
                    log.error("[{}] Retry exhausted after {} attempt(s) for path={}.",
                            requestId, signal.totalRetries(), path);
                    return signal.failure();
                });
    }

    /**
     * Conservative retry predicate.
     *
     * <p>Only retries failures known to happen before the AI service receives the request:
     * <ul>
     *   <li>DNS resolution failure</li>
     *   <li>Connection refused / host unreachable</li>
     *   <li>Connection timeout during TCP handshake</li>
     *   <li>TLS handshake failure</li>
     * </ul>
     *
     * <p>Explicitly never retries:
     * <ul>
     *   <li>{@link PolicyBlockedException} — deterministic client policy violation</li>
     *   <li>{@link IllegalArgumentException} — bad client input (HTTP 400)</li>
     *   <li>{@link AiServiceException} — application-level classified errors (401, 403, 429, 5xx)</li>
     *   <li>{@code REQUEST_TIMEOUT} — inference was already dispatched; retrying duplicates GPU execution</li>
     *   <li>{@code CONNECTION_RESET_OR_CLOSED} — connection dropped after request transmission could duplicate inference</li>
     *   <li>Generic {@code NETWORK_ERROR} — fallback category must fail fast</li>
     * </ul>
     */
    public static boolean isRetryable(Throwable throwable, String requestId, String path) {
        // Never retry application-level classified exceptions
        if (throwable instanceof PolicyBlockedException
                || throwable instanceof IllegalArgumentException
                || throwable instanceof AiServiceException) {
            return false;
        }

        // Only retry failures known to happen before the AI service receives the request
        AiServiceErrorCategory category = classifyError(throwable);
        boolean retryable = switch (category) {
            case DNS_RESOLUTION_FAILURE,
                 CONNECTION_REFUSED_OR_UNREACHABLE,
                 CONNECTION_TIMEOUT,
                 TLS_HANDSHAKE_TIMEOUT -> true;
            default -> false; // TLS_CERTIFICATE_FAILURE, TLS_HANDSHAKE_FAILURE, CONNECTION_RESET_OR_CLOSED, REQUEST_TIMEOUT, NETWORK_ERROR are NOT retried
        };

        if (retryable) {
            log.warn("[{}] Transient pre-request failure [{}] on path={}; scheduling retry.",
                    requestId, category, path);
        } else {
            log.debug("[{}] Non-retryable error [{}] on path={}.", requestId, category, path);
        }
        return retryable;
    }

    // ── Error Analysis Utilities ──────────────────────────────────────────────

    /**
     * Maps an error category to a user-safe, descriptive message for frontend clients.
     */
    public static String mapCategoryToUserMessage(AiServiceErrorCategory category) {
        return switch (category) {
            case DNS_RESOLUTION_FAILURE ->
                "AI service is unreachable (DNS resolution failure). Please verify network configuration.";
            case CONNECTION_TIMEOUT ->
                "AI service connection timed out during network handshake. Please try again.";
            case TLS_HANDSHAKE_TIMEOUT ->
                "Secure connection to AI service timed out during TLS handshake. Please try again.";
            case TLS_CERTIFICATE_FAILURE, TLS_HANDSHAKE_FAILURE ->
                "Secure connection to AI service could not be established (TLS handshake failure).";
            case REQUEST_TIMEOUT ->
                "AI service request timed out during processing. Please try again with a shorter prompt or try later.";
            case CONNECTION_REFUSED_OR_UNREACHABLE ->
                "AI service is currently unavailable (connection refused). Please ensure the service is running.";
            case CONNECTION_RESET_OR_CLOSED ->
                "Connection to AI service was interrupted. Please try again.";
            default ->
                "AI service is unavailable. Please try again later.";
        };
    }

    /**
     * Extracts root cause and classifies the network failure into actionable categories.
     * Guaranteed never to inspect or return sensitive payload data or authorization credentials.
     */
    public static NetworkErrorDetails analyzeError(Throwable ex, String defaultMethod, String defaultPath) {
        Throwable rootCause = extractRootCause(ex);
        AiServiceErrorCategory category = classifyError(ex);

        String rootCauseClass = rootCause != null ? rootCause.getClass().getName() : "Unknown";
        String rootCauseMessage = rootCause != null && rootCause.getMessage() != null
                ? rootCause.getMessage()
                : "No message available";

        String method = defaultMethod;
        String targetUri = defaultPath;

        if (ex instanceof WebClientRequestException reqEx) {
            if (reqEx.getMethod() != null) {
                method = reqEx.getMethod().name();
            }
            if (reqEx.getUri() != null) {
                targetUri = sanitizeUri(reqEx.getUri());
            }
        } else if (ex instanceof WebClientResponseException respEx) {
            if (respEx.getRequest() != null) {
                if (respEx.getRequest().getMethod() != null) {
                    method = respEx.getRequest().getMethod().name();
                }
                if (respEx.getRequest().getURI() != null) {
                    targetUri = sanitizeUri(respEx.getRequest().getURI());
                }
            }
        }

        return new NetworkErrorDetails(category, rootCauseClass, rootCauseMessage, targetUri, method);
    }

    /**
     * Walks the entire exception chain to accurately classify network failure types.
     */
    public static AiServiceErrorCategory classifyError(Throwable ex) {
        if (ex == null) return AiServiceErrorCategory.UNKNOWN_ERROR;

        Throwable current = ex;
        while (current != null) {
            String className = current.getClass().getName();
            String msg = current.getMessage() != null ? current.getMessage().toLowerCase() : "";

            // 1. DNS Resolution Failure
            if (current instanceof java.net.UnknownHostException
                    || className.contains("UnknownHost")
                    || className.contains("DnsNameResolver")
                    || msg.contains("failed to resolve")
                    || msg.contains("name or service not known")) {
                return AiServiceErrorCategory.DNS_RESOLUTION_FAILURE;
            }

            // 2a. Transient TLS Handshake Timeout (retryable)
            if (current instanceof SslHandshakeTimeoutException
                    || className.contains("SslHandshakeTimeout")
                    || ((className.contains("SSL") || className.contains("Handshake") || current instanceof javax.net.ssl.SSLException)
                        && (msg.contains("handshake timed out") || msg.contains("handshake timeout")))) {
                return AiServiceErrorCategory.TLS_HANDSHAKE_TIMEOUT;
            }

            // 2b. Permanent TLS Certificate Validation / Verification Failures (non-retryable)
            if (current instanceof java.security.cert.CertificateException
                    || current instanceof javax.net.ssl.SSLPeerUnverifiedException
                    || className.contains("Cert")
                    || msg.contains("pkix")
                    || msg.contains("certificate")
                    || msg.contains("untrusted")
                    || msg.contains("expired")
                    || msg.contains("peer not authenticated")
                    || (msg.contains("hostname") && (msg.contains("mismatch") || msg.contains("not match") || msg.contains("verify") || msg.contains("does not match")))) {
                return AiServiceErrorCategory.TLS_CERTIFICATE_FAILURE;
            }

            // 2c. Other General TLS / SSL Failures (e.g. protocol or cipher issues, non-retryable)
            if (current instanceof javax.net.ssl.SSLException
                    || className.contains("SSL")
                    || className.contains("Handshake")) {
                return AiServiceErrorCategory.TLS_HANDSHAKE_FAILURE;
            }

            // 3. Connection Timeout (TCP handshake / connect timeout)
            if (className.contains("ConnectTimeout")
                    || (msg.contains("connection timed out") && !msg.contains("read"))) {
                return AiServiceErrorCategory.CONNECTION_TIMEOUT;
            }

            // 4. Connection Refused / Network Unreachable
            if (current instanceof java.net.NoRouteToHostException
                    || current instanceof java.net.ConnectException
                    || className.contains("AnnotatedConnectException")
                    || msg.contains("connection refused")
                    || msg.contains("no route to host")
                    || msg.contains("network is unreachable")) {
                return AiServiceErrorCategory.CONNECTION_REFUSED_OR_UNREACHABLE;
            }

            // 5. Request / Response / Read Timeout
            if (current instanceof java.util.concurrent.TimeoutException
                    || className.contains("TimeoutException")
                    || className.contains("ReadTimeout")
                    || className.contains("WriteTimeout")
                    || className.contains("ResponseTimeout")
                    || msg.contains("timeout on blocking read")
                    || msg.contains("response timeout")) {
                return AiServiceErrorCategory.REQUEST_TIMEOUT;
            }

            // 6. Connection Reset or Premature Close
            if (className.contains("PrematureClose")
                    || current instanceof java.nio.channels.ClosedChannelException
                    || msg.contains("connection reset")
                    || msg.contains("broken pipe")
                    || msg.contains("connection prematurely closed")) {
                return AiServiceErrorCategory.CONNECTION_RESET_OR_CLOSED;
            }

            // 7. HTTP Status Error
            if (current instanceof WebClientResponseException) {
                return AiServiceErrorCategory.HTTP_STATUS_ERROR;
            }

            if (current.getCause() == current) break;
            current = current.getCause();
        }

        return AiServiceErrorCategory.NETWORK_ERROR;
    }

    /**
     * Finds the deepest root cause in the throwable chain.
     */
    public static Throwable extractRootCause(Throwable throwable) {
        if (throwable == null) return null;
        Throwable current = throwable;
        while (current.getCause() != null && current.getCause() != current) {
            current = current.getCause();
        }
        return current;
    }

    /**
     * Sanitizes URI by stripping query strings, user info, and fragments.
     */
    public static String sanitizeUri(URI uri) {
        if (uri == null) return "unknown";
        try {
            StringBuilder sb = new StringBuilder();
            if (uri.getScheme() != null) sb.append(uri.getScheme()).append("://");
            if (uri.getHost() != null) sb.append(uri.getHost());
            if (uri.getPort() > 0 && uri.getPort() != 80 && uri.getPort() != 443) {
                sb.append(":").append(uri.getPort());
            }
            if (uri.getPath() != null) sb.append(uri.getPath());
            return sb.toString();
        } catch (Exception e) {
            return uri.toString().split("\\?")[0];
        }
    }

    // ── Internal DTO ──────────────────────────────────────────────────────────

    private record PromptRequest(
            String prompt,
            Integer target_max_tokens,
            Double minimum_semantic_score,
            Map<String, String> privacy_policy) {
    }
}
