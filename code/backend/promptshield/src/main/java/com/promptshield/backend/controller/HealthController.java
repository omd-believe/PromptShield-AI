package com.promptshield.backend.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

/**
 * Lightweight health check endpoint.
 *
 * <p>Used by:
 * <ul>
 *   <li>Render Web Service health check ({@code /api/v1/health})</li>
 *   <li>Docker HEALTHCHECK ({@code /api/v1/health})</li>
 *   <li>Monitoring / uptime probes e.g. UptimeRobot ({@code /actuator/health})</li>
 * </ul>
 *
 * <p>This endpoint is intentionally public (no JWT required) — see
 * SecurityConfig where it is listed under .permitAll(). Both GET and HEAD
 * requests are supported.
 *
 * <p>It does NOT expose database credentials, internal service URLs,
 * AI model status, or any other internal infrastructure details.
 */
@RestController
public class HealthController {

    @GetMapping({"/api/v1/health", "/actuator/health"})
    public ResponseEntity<Map<String, Object>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "PromptShield Backend",
                "timestamp", Instant.now().toString()
        ));
    }
}

