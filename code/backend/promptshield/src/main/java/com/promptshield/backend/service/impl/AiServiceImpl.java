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
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.net.URI;
import java.time.Duration;
import java.util.Map;

@Service
public class AiServiceImpl implements AiService {

    private static final Logger log = LoggerFactory.getLogger(AiServiceImpl.class);

    private final WebClient webClient;
    private final int timeoutSeconds;
    private final String apiKey;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public enum AiServiceErrorCategory {
        DNS_RESOLUTION_FAILURE,
        CONNECTION_TIMEOUT,
        CONNECTION_REFUSED_OR_UNREACHABLE,
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

    public AiServiceImpl(
            WebClient webClient,
            @Value("${ai.service.timeout-seconds:90}") int timeoutSeconds,
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

        long startTime = System.currentTimeMillis();
        T response;
        try {
            var requestSpec = webClient.post()
                    .uri(path)
                    .header("X-Request-ID", requestId);

            if (apiKey != null && !apiKey.isBlank()) {
                requestSpec.headers(h -> {
                    h.set("X-API-Key", apiKey);
                    h.set("X-AI-Service-Key", apiKey);
                });
            }

            response = requestSpec
                    .bodyValue(new PromptRequest(prompt, targetMaxTokens, minimumSemanticScore, privacyPolicy))
                    .retrieve()
                    .onStatus(HttpStatusCode::is4xxClientError, resp ->
                            resp.bodyToMono(String.class)
                                    .defaultIfEmpty("")
                                    .map(body -> {
                                        int status = resp.statusCode().value();
                                        log.warn("[{}] AI service returned client error HTTP {}", requestId, status);

                                        if (status == HttpStatus.UNAUTHORIZED.value()) {
                                            log.error("[{}] AI service authentication failed (HTTP 401). Verify AI_SERVICE_API_KEY configuration.", requestId);
                                            return new AiServiceException("AI service rejected authentication. Please check API key configuration.");
                                        }

                                        if (status == HttpStatus.FORBIDDEN.value()) {
                                            log.error("[{}] AI service access forbidden (HTTP 403). Verify AI_SERVICE_API_KEY permissions.", requestId);
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
                                            return new AiServiceException("AI service rate limit exceeded. Please try again shortly.");
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
                                        if (status == HttpStatus.SERVICE_UNAVAILABLE.value() || status == HttpStatus.GATEWAY_TIMEOUT.value()) {
                                            return new AiServiceException("AI service is temporarily unavailable (HTTP " + status + "). Please try again.");
                                        }
                                        return new AiServiceException("AI service failed to process the request (HTTP " + status + ").");
                                    }))
                    .bodyToMono(responseType)
                    .timeout(Duration.ofSeconds(timeoutSeconds))
                    .block();
        } catch (PolicyBlockedException | IllegalArgumentException ex) {
            throw ex;
        } catch (AiServiceException ex) {
            // Already handled and categorized in onStatus handlers
            throw ex;
        } catch (Exception ex) {
            long durationMs = System.currentTimeMillis() - startTime;
            NetworkErrorDetails details = analyzeError(ex, "POST", path);
            Throwable rootCause = extractRootCause(ex);

            // Detailed, privacy-safe error logging:
            // 1. Logs root cause class and message.
            // 2. Classifies network error (DNS, TLS, Connection, Timeout, etc.).
            // 3. Sanitizes URI (removes query strings/fragments).
            // 4. Excludes API keys, authorization headers, and raw prompt content.
            log.error("[{}] AI service connectivity failure [Category: {}]: method={}, target={}, rootCauseClass={}, rootCauseMessage={}, durationMs={}",
                    requestId,
                    details.category(),
                    details.httpMethod(),
                    details.targetUri(),
                    details.rootCauseClass(),
                    details.rootCauseMessage(),
                    durationMs,
                    rootCause != null ? rootCause : ex);

            String userMessage = mapCategoryToUserMessage(details.category());
            throw new AiServiceException(userMessage, ex);
        }

        if (response == null) {
            throw new AiServiceException("AI service returned an empty response.");
        }
        return response;
    }

    /**
     * Maps an error category to a user-safe, descriptive message for frontend clients.
     */
    public static String mapCategoryToUserMessage(AiServiceErrorCategory category) {
        return switch (category) {
            case DNS_RESOLUTION_FAILURE ->
                "AI service is unreachable (DNS resolution failure). Please verify network configuration.";
            case CONNECTION_TIMEOUT, REQUEST_TIMEOUT ->
                "AI service request timed out during processing. Please try again with a shorter prompt or try later.";
            case CONNECTION_REFUSED_OR_UNREACHABLE ->
                "AI service is currently unavailable (connection refused). Please ensure the service is running.";
            case TLS_HANDSHAKE_FAILURE ->
                "Secure connection to AI service could not be established (TLS handshake failure).";
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

            // 2. TLS / SSL Handshake Failure
            if (current instanceof javax.net.ssl.SSLException
                    || current instanceof java.security.cert.CertificateException
                    || className.contains("SSL")
                    || className.contains("Cert")
                    || className.contains("Handshake")
                    || msg.contains("handshake")
                    || msg.contains("pkix")
                    || msg.contains("certificate")) {
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

    private record PromptRequest(
            String prompt,
            Integer target_max_tokens,
            Double minimum_semantic_score,
            Map<String, String> privacy_policy) {
    }
}
