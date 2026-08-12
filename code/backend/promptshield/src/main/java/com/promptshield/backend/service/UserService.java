package com.promptshield.backend.service;

import com.promptshield.backend.dto.request.LoginRequest;
import com.promptshield.backend.dto.request.RegisterRequest;
import com.promptshield.backend.dto.response.AuthResponse;
import org.springframework.stereotype.Service;


public interface UserService {

    AuthResponse register(RegisterRequest request);

    AuthResponse login(LoginRequest request);
}
