package com.promptshield.backend.service;

import com.promptshield.backend.exception.AiServiceException;
import com.promptshield.backend.service.impl.AiServiceImpl;
import com.promptshield.backend.service.impl.AiServiceImpl.AiServiceErrorCategory;
import com.promptshield.backend.service.impl.AiServiceImpl.NetworkErrorDetails;
import io.netty.channel.ConnectTimeoutException;
import io.netty.handler.timeout.ReadTimeoutException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;

import javax.net.ssl.SSLHandshakeException;
import java.net.ConnectException;
import java.net.SocketException;
import java.net.URI;
import java.net.UnknownHostException;
import java.util.Map;
import java.util.concurrent.TimeoutException;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AiServiceImplTest {

    @Mock
    private WebClient webClient;

    @Mock
    private WebClient.RequestBodyUriSpec requestBodyUriSpec;

    private AiServiceImpl aiService;

    @BeforeEach
    void setUp() {
        aiService = new AiServiceImpl(webClient, 90, "test-secret-key-12345");
    }

    @Test
    @DisplayName("Should classify UnknownHostException as DNS_RESOLUTION_FAILURE")
    void shouldClassifyDnsResolutionFailure() {
        UnknownHostException dnsEx = new UnknownHostException("fedora.tail1f8405.ts.net: Name or service not known");
        WebClientRequestException webEx = new WebClientRequestException(
                dnsEx, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), new HttpHeaders());

        AiServiceErrorCategory category = AiServiceImpl.classifyError(webEx);
        assertEquals(AiServiceErrorCategory.DNS_RESOLUTION_FAILURE, category);

        NetworkErrorDetails details = AiServiceImpl.analyzeError(webEx, "POST", "/analyze");
        assertEquals(AiServiceErrorCategory.DNS_RESOLUTION_FAILURE, details.category());
        assertEquals("java.net.UnknownHostException", details.rootCauseClass());
        assertTrue(details.rootCauseMessage().contains("fedora.tail1f8405.ts.net"));
        assertEquals("https://fedora.tail1f8405.ts.net/analyze", details.targetUri());
        assertEquals("POST", details.httpMethod());
    }

    @Test
    @DisplayName("Should classify ConnectTimeoutException as CONNECTION_TIMEOUT")
    void shouldClassifyConnectTimeout() {
        ConnectTimeoutException connTimeout = new ConnectTimeoutException("connection timed out: fedora.tail1f8405.ts.net/100.80.90.100:443");
        WebClientRequestException webEx = new WebClientRequestException(
                connTimeout, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), new HttpHeaders());

        AiServiceErrorCategory category = AiServiceImpl.classifyError(webEx);
        assertEquals(AiServiceErrorCategory.CONNECTION_TIMEOUT, category);

        NetworkErrorDetails details = AiServiceImpl.analyzeError(webEx, "POST", "/analyze");
        assertEquals(AiServiceErrorCategory.CONNECTION_TIMEOUT, details.category());
        assertEquals("io.netty.channel.ConnectTimeoutException", details.rootCauseClass());
        assertTrue(details.rootCauseMessage().contains("connection timed out"));
    }

    @Test
    @DisplayName("Should classify ConnectException with Connection refused as CONNECTION_REFUSED_OR_UNREACHABLE")
    void shouldClassifyConnectionRefused() {
        ConnectException refused = new ConnectException("Connection refused");
        WebClientRequestException webEx = new WebClientRequestException(
                refused, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), new HttpHeaders());

        AiServiceErrorCategory category = AiServiceImpl.classifyError(webEx);
        assertEquals(AiServiceErrorCategory.CONNECTION_REFUSED_OR_UNREACHABLE, category);

        NetworkErrorDetails details = AiServiceImpl.analyzeError(webEx, "POST", "/analyze");
        assertEquals(AiServiceErrorCategory.CONNECTION_REFUSED_OR_UNREACHABLE, details.category());
        assertEquals("java.net.ConnectException", details.rootCauseClass());
        assertEquals("Connection refused", details.rootCauseMessage());
    }

    @Test
    @DisplayName("Should classify SSLHandshakeException as TLS_HANDSHAKE_FAILURE")
    void shouldClassifyTlsHandshakeFailure() {
        SSLHandshakeException sslEx = new SSLHandshakeException("PKIX path building failed: unable to find valid certification path");
        WebClientRequestException webEx = new WebClientRequestException(
                sslEx, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), new HttpHeaders());

        AiServiceErrorCategory category = AiServiceImpl.classifyError(webEx);
        assertEquals(AiServiceErrorCategory.TLS_HANDSHAKE_FAILURE, category);

        NetworkErrorDetails details = AiServiceImpl.analyzeError(webEx, "POST", "/analyze");
        assertEquals(AiServiceErrorCategory.TLS_HANDSHAKE_FAILURE, details.category());
        assertEquals("javax.net.ssl.SSLHandshakeException", details.rootCauseClass());
        assertTrue(details.rootCauseMessage().contains("PKIX path building failed"));
    }

    @Test
    @DisplayName("Should classify ReadTimeoutException as REQUEST_TIMEOUT")
    void shouldClassifyReadTimeout() {
        ReadTimeoutException readTimeout = ReadTimeoutException.INSTANCE;
        WebClientRequestException webEx = new WebClientRequestException(
                readTimeout, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), new HttpHeaders());

        AiServiceErrorCategory category = AiServiceImpl.classifyError(webEx);
        assertEquals(AiServiceErrorCategory.REQUEST_TIMEOUT, category);

        NetworkErrorDetails details = AiServiceImpl.analyzeError(webEx, "POST", "/analyze");
        assertEquals(AiServiceErrorCategory.REQUEST_TIMEOUT, details.category());
    }

    @Test
    @DisplayName("Should classify TimeoutException as REQUEST_TIMEOUT")
    void shouldClassifyTimeoutException() {
        TimeoutException timeout = new TimeoutException("Response timeout after 90000ms");
        AiServiceErrorCategory category = AiServiceImpl.classifyError(timeout);
        assertEquals(AiServiceErrorCategory.REQUEST_TIMEOUT, category);
    }

    @Test
    @DisplayName("Should classify SocketException Connection reset as CONNECTION_RESET_OR_CLOSED")
    void shouldClassifyConnectionReset() {
        SocketException reset = new SocketException("Connection reset by peer");
        WebClientRequestException webEx = new WebClientRequestException(
                reset, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), new HttpHeaders());

        AiServiceErrorCategory category = AiServiceImpl.classifyError(webEx);
        assertEquals(AiServiceErrorCategory.CONNECTION_RESET_OR_CLOSED, category);
    }

    @Test
    @DisplayName("Should sanitize URI and strip query parameters/credentials")
    void shouldSanitizeUriSafely() {
        URI sensitiveUri = URI.create("https://fedora.tail1f8405.ts.net/analyze?api_key=super-secret-key&token=12345");
        String sanitized = AiServiceImpl.sanitizeUri(sensitiveUri);

        assertEquals("https://fedora.tail1f8405.ts.net/analyze", sanitized);
        assertFalse(sanitized.contains("api_key"));
        assertFalse(sanitized.contains("super-secret-key"));
    }

    @Test
    @DisplayName("Should extract root cause traversing multiple wrapper layers")
    void shouldExtractRootCause() {
        UnknownHostException root = new UnknownHostException("fedora.tail1f8405.ts.net");
        RuntimeException layer1 = new RuntimeException("Channel connection failed", root);
        WebClientRequestException topLayer = new WebClientRequestException(
                layer1, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), new HttpHeaders());

        Throwable extracted = AiServiceImpl.extractRootCause(topLayer);
        assertSame(root, extracted);
    }

    @Test
    @DisplayName("Should wrap connection failure in AiServiceException with cause preserved and without leaking secrets")
    void shouldWrapExceptionSafely() {
        UnknownHostException dnsEx = new UnknownHostException("fedora.tail1f8405.ts.net");
        HttpHeaders headers = new HttpHeaders();
        headers.add("X-API-Key", "SECRET_KEY_NEVER_LEAK");

        WebClientRequestException webEx = new WebClientRequestException(
                dnsEx, HttpMethod.POST, URI.create("https://fedora.tail1f8405.ts.net/analyze"), headers);

        when(webClient.post()).thenReturn(requestBodyUriSpec);
        when(requestBodyUriSpec.uri(anyString())).thenThrow(webEx);

        AiServiceException ex = assertThrows(AiServiceException.class, () ->
                aiService.analyzePrompt("Confidential prompt text with sensitive data", Map.of()));

        // Verify message is user-safe
        assertEquals("AI service is unavailable or timed out. Please try again.", ex.getMessage());
        // Verify underlying cause is preserved
        assertSame(webEx, ex.getCause());
        // Verify prompt text is never leaked in the exception message
        assertFalse(ex.getMessage().contains("Confidential"));
        assertFalse(ex.getMessage().contains("SECRET_KEY_NEVER_LEAK"));
    }
}

