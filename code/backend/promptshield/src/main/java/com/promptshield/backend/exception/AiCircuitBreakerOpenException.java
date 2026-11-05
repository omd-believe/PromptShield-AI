package com.promptshield.backend.exception;

/**
 * Exception thrown when the AI service circuit breaker is in OPEN state,
 * failing fast to protect client response times, GPU resources, and backend health.
 */
public class AiCircuitBreakerOpenException extends AiServiceException {

    public AiCircuitBreakerOpenException(String message) {
        super(message);
    }

    public AiCircuitBreakerOpenException(String message, Throwable cause) {
        super(message, cause);
    }
}

