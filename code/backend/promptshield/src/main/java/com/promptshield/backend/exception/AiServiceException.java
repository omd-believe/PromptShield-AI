package com.promptshield.backend.exception;

public class AiServiceException extends RuntimeException {
    public AiServiceException(String message) {
        super(message);
    }
}
