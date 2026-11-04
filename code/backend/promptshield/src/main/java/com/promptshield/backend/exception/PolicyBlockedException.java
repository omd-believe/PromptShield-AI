package com.promptshield.backend.exception;

public class PolicyBlockedException extends RuntimeException {
    public PolicyBlockedException(String message) {
        super(message);
    }
}
