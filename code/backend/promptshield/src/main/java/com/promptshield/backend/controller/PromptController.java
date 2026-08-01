package com.promptshield.backend.controller;


import com.promptshield.backend.dto.request.PromptRequest;
import com.promptshield.backend.dto.response.PromptResponse;
import com.promptshield.backend.service.PromptService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/prompts")
@RequiredArgsConstructor
public class PromptController {

    private final PromptService promptService;

    @PostMapping
    public ResponseEntity<PromptResponse> optimizePrompt(
            @Valid @RequestBody PromptRequest request) {

        return ResponseEntity.ok(promptService.optimizePrompt(request));
    }

    @GetMapping("/user/{userId}")
    public ResponseEntity<List<PromptResponse>> getPromptHistory(
            @PathVariable Long userId) {

        return ResponseEntity.ok(promptService.getPromptHistory(userId));
    }

    @GetMapping("/{promptId}")
    public ResponseEntity<PromptResponse> getPrompt(@PathVariable Long promptId){
        return ResponseEntity.ok(promptService.getPrompt(promptId));
    }

    @DeleteMapping("/{promptId}")
    public ResponseEntity<Void> deletePrompt(
            @PathVariable Long promptId) {

        promptService.deletePrompt(promptId);
        return ResponseEntity.noContent().build();
    }


}
