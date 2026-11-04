package com.promptshield.backend.service.impl;

import com.promptshield.backend.dto.request.LoginRequest;
import com.promptshield.backend.dto.request.RegisterRequest;
import com.promptshield.backend.dto.response.AuthResponse;
import com.promptshield.backend.entity.User;
import com.promptshield.backend.exception.InvalidCredentialsException;
import com.promptshield.backend.exception.ResourceAlreadyExistsException;
import com.promptshield.backend.repository.UserRepository;
import com.promptshield.backend.service.JwtService;
import com.promptshield.backend.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.Locale;


@RequiredArgsConstructor
@Service
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder;
    private final JwtService jwtService;


    @Override
    public AuthResponse register(RegisterRequest request) {

        String email = normalizeEmail(request.getEmail());

        if (userRepository.existsByEmail(email)) {
            throw new ResourceAlreadyExistsException("Email already exists");
        }


        User newUser = new User();
        newUser.setName(request.getName().trim());
        newUser.setEmail(email);
        newUser.setPassword(passwordEncoder.encode(request.getPassword()));

        userRepository.save(newUser);

        // Log the new user straight in: the response must carry a real JWT
        // (it used to return the e-mail address in the token field).
        return new AuthResponse(
                "Registration Successful",
                jwtService.generateToken(newUser.getEmail())
        );
    }

    @Override
    public AuthResponse login(LoginRequest request) {

        // Same error for "unknown e-mail" and "wrong password" so the API
        // cannot be used to find out which e-mail addresses are registered.
        User user = userRepository.findByEmail(normalizeEmail(request.getEmail()))
                .orElseThrow(() -> new InvalidCredentialsException("Invalid credentials"));

        if(!passwordEncoder.matches(
                request.getPassword(),
                user.getPassword()
        )){
            throw new InvalidCredentialsException("Invalid credentials");
        }

        String token = jwtService.generateToken(user.getEmail());

        return new AuthResponse(
                "Login Successful",
                token
        );
    }

    /** E-mail is case-insensitive: "Bob@X.com" and "bob@x.com" are one account. */
    private static String normalizeEmail(String email) {
        return email.trim().toLowerCase(Locale.ROOT);
    }
}