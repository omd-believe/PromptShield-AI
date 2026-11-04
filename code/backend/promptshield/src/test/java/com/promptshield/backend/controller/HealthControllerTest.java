package com.promptshield.backend.controller;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class HealthControllerTest {

    private final HealthController healthController = new HealthController();

    @Test
    void health_ShouldReturnUpStatus() {
        ResponseEntity<Map<String, Object>> response = healthController.health();

        assertNotNull(response);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("UP", response.getBody().get("status"));
        assertEquals("PromptShield Backend", response.getBody().get("service"));
        assertTrue(response.getBody().containsKey("timestamp"));
    }
}

