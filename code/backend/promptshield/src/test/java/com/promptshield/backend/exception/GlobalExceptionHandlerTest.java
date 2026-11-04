package com.promptshield.backend.exception;

import com.promptshield.backend.dto.response.ErrorResponse;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void handleAiServiceException_ShouldReturnBadGateway() {
        AiServiceException ex = new AiServiceException("AI microservice unreachable");
        ErrorResponse response = handler.handleAiServiceException(ex);

        assertNotNull(response);
        assertEquals(HttpStatus.BAD_GATEWAY.value(), response.getStatus());
        assertEquals("AI microservice unreachable", response.getError());
        assertNotNull(response.getTimestamp());
    }

    @Test
    void handleNotFound_ShouldReturnNotFound() {
        ResourceNotFoundException ex = new ResourceNotFoundException("Entity not found");
        ErrorResponse response = handler.handleNotFound(ex);

        assertNotNull(response);
        assertEquals(HttpStatus.NOT_FOUND.value(), response.getStatus());
        assertEquals("Entity not found", response.getError());
    }

    @Test
    void handleException_ShouldNotLeakInternalMessage() {
        ErrorResponse response = handler.handleException(
                new RuntimeException("could not execute statement; SQL [insert into users ...]"));

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), response.getStatus());
        assertEquals("Internal server error", response.getError());
    }

    @Test
    void handleInvalidCredentials_ShouldReturnUnauthorized() {
        ErrorResponse response = handler.handleInvalidCredentials(
                new InvalidCredentialsException("Invalid credentials"));

        assertEquals(HttpStatus.UNAUTHORIZED.value(), response.getStatus());
    }
}
