package com.promptshield.backend.service.impl;

import com.promptshield.backend.dto.request.LoginRequest;
import com.promptshield.backend.dto.request.RegisterRequest;
import com.promptshield.backend.dto.response.AuthResponse;
import com.promptshield.backend.entity.User;
import com.promptshield.backend.repository.UserRepository;
import com.promptshield.backend.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;


@RequiredArgsConstructor
@Service
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder;


    public AuthResponse register(RegisterRequest request) {

        if (userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("Email already exists");
        }


        User newUser = new User();
        newUser.setName(request.getName());
        newUser.setEmail(request.getEmail());
        newUser.setPassword(passwordEncoder.encode(request.getPassword()));

        userRepository.save(newUser);

        return new AuthResponse(
                "Registration Successful",
                newUser.getEmail()
        );
    }

    public AuthResponse login(LoginRequest request) {

        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new RuntimeException("User not found"));

        if(!passwordEncoder.matches(
                request.getPassword(),
                user.getPassword()
        )){
            throw new RuntimeException("Invalid Credentials");
        }


        return new AuthResponse(
                "Login Successful",
                user.getEmail()
        );


    }
}