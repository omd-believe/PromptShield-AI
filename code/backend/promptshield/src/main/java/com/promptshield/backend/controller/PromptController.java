package com.promptshield.backend.controller;


import com.promptshield.backend.dto.request.PromptRequest;
import com.promptshield.backend.dto.response.PromptResponse;
import com.promptshield.backend.service.PromptService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/prompts")
@RequiredArgsConstructor
public class PromptController {

    private final PromptService promptService;

    @PostMapping
    public ResponseEntity<PromptResponse> optimizePrompt(
            @Valid @RequestBody PromptRequest request,
            @AuthenticationPrincipal Jwt jwt) {

        String email = jwt.getSubject();

        return ResponseEntity.ok(
                promptService.optimizePrompt(email, request)
        );
    }

    @GetMapping("/user")
    public ResponseEntity<List<PromptResponse>> getPromptHistory(
            @AuthenticationPrincipal Jwt jwt) {

        String email = jwt.getSubject();

        return ResponseEntity.ok(
                promptService.getPromptHistory(email)
        );
    }


    @DeleteMapping("/{promptId}")
    public ResponseEntity<Void> deletePrompt(
            @PathVariable Long promptId,
            @AuthenticationPrincipal Jwt jwt) {

        String email = jwt.getSubject();

        promptService.deletePrompt(email, promptId);

        return ResponseEntity.noContent().build();
    }

}
