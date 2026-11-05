package com.promptshield.backend.controller;

import com.promptshield.backend.config.JwtConfig;
import com.promptshield.backend.config.SecurityConfig;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.security.autoconfigure.web.servlet.ServletWebSecurityAutoConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.head;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = HealthController.class)
@Import({SecurityConfig.class, JwtConfig.class, ServletWebSecurityAutoConfiguration.class})
@TestPropertySource(properties = {
        "jwt.secret=01234567890123456789012345678901"
})
class HealthSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    @DisplayName("GET /actuator/health without JWT returns HTTP 200 and status UP")
    void getActuatorHealth_Unauthenticated_ShouldReturnOk() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.service").value("PromptShield Backend"))
                .andExpect(jsonPath("$.timestamp").exists());
    }

    @Test
    @DisplayName("HEAD /actuator/health without JWT returns HTTP 200")
    void headActuatorHealth_Unauthenticated_ShouldReturnOk() throws Exception {
        mockMvc.perform(head("/actuator/health"))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/v1/health without JWT returns HTTP 200 and status UP")
    void getApiV1Health_Unauthenticated_ShouldReturnOk() throws Exception {
        mockMvc.perform(get("/api/v1/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.service").value("PromptShield Backend"))
                .andExpect(jsonPath("$.timestamp").exists());
    }

    @Test
    @DisplayName("HEAD /api/v1/health without JWT returns HTTP 200")
    void headApiV1Health_Unauthenticated_ShouldReturnOk() throws Exception {
        mockMvc.perform(head("/api/v1/health"))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("Unauthenticated request to protected endpoint (/api/v1/prompts) returns HTTP 401 Unauthorized")
    void protectedEndpoint_Unauthenticated_ShouldReturnUnauthorized() throws Exception {
        mockMvc.perform(get("/api/v1/prompts"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("Unauthenticated request to root endpoint (/) returns HTTP 401 Unauthorized")
    void rootEndpoint_Unauthenticated_ShouldReturnUnauthorized() throws Exception {
        mockMvc.perform(get("/"))
                .andExpect(status().isUnauthorized());
    }
}
