package com.promptshield.backend.service;

import com.promptshield.backend.dto.request.LoginRequest;
import com.promptshield.backend.dto.request.RegisterRequest;
import com.promptshield.backend.dto.response.AuthResponse;
import com.promptshield.backend.entity.User;
import com.promptshield.backend.exception.InvalidCredentialsException;
import com.promptshield.backend.exception.ResourceAlreadyExistsException;
import com.promptshield.backend.repository.UserRepository;
import com.promptshield.backend.service.impl.UserServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class UserServiceImplTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private BCryptPasswordEncoder passwordEncoder;

    @Mock
    private JwtService jwtService;

    @InjectMocks
    private UserServiceImpl userService;

    @Test
    void register_ShouldReturnJwtNotEmailAndStoreNormalizedEmail() {
        RegisterRequest request = new RegisterRequest();
        request.setName("  Alice  ");
        request.setEmail("  Alice@Example.COM ");
        request.setPassword("password123");

        when(userRepository.existsByEmail("alice@example.com")).thenReturn(false);
        when(passwordEncoder.encode("password123")).thenReturn("hashed");
        when(jwtService.generateToken("alice@example.com")).thenReturn("jwt-token");

        AuthResponse response = userService.register(request);

        assertEquals("jwt-token", response.getToken());

        ArgumentCaptor<User> saved = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(saved.capture());
        assertEquals("alice@example.com", saved.getValue().getEmail());
        assertEquals("Alice", saved.getValue().getName());
        assertEquals("hashed", saved.getValue().getPassword());
    }

    @Test
    void register_ShouldRejectDuplicateEmailCaseInsensitively() {
        RegisterRequest request = new RegisterRequest();
        request.setName("Alice");
        request.setEmail("ALICE@example.com");
        request.setPassword("password123");

        when(userRepository.existsByEmail("alice@example.com")).thenReturn(true);

        assertThrows(ResourceAlreadyExistsException.class, () -> userService.register(request));
        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void login_UnknownEmail_ShouldBeIndistinguishableFromWrongPassword() {
        LoginRequest request = new LoginRequest();
        request.setEmail("ghost@example.com");
        request.setPassword("whatever1");

        when(userRepository.findByEmail("ghost@example.com")).thenReturn(Optional.empty());

        assertThrows(InvalidCredentialsException.class, () -> userService.login(request));
    }

    @Test
    void login_WrongPassword_ShouldThrowInvalidCredentials() {
        User user = new User();
        user.setEmail("alice@example.com");
        user.setPassword("hashed");

        LoginRequest request = new LoginRequest();
        request.setEmail("alice@example.com");
        request.setPassword("wrong-pass");

        when(userRepository.findByEmail("alice@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("wrong-pass", "hashed")).thenReturn(false);

        assertThrows(InvalidCredentialsException.class, () -> userService.login(request));
        verifyNoInteractions(jwtService);
    }

    @Test
    void login_ValidCredentials_ShouldReturnToken() {
        User user = new User();
        user.setEmail("alice@example.com");
        user.setPassword("hashed");

        LoginRequest request = new LoginRequest();
        request.setEmail("Alice@Example.com");
        request.setPassword("password123");

        when(userRepository.findByEmail("alice@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("password123", "hashed")).thenReturn(true);
        when(jwtService.generateToken("alice@example.com")).thenReturn("jwt-token");

        assertEquals("jwt-token", userService.login(request).getToken());
    }
}
