package com.promptshield.backend.service.impl;

import com.promptshield.backend.dto.request.PromptRequest;
import com.promptshield.backend.dto.response.PromptResponse;
import com.promptshield.backend.entity.Prompt;
import com.promptshield.backend.entity.User;
import com.promptshield.backend.exception.ResourceNotFoundException;
import com.promptshield.backend.repository.PromptRepository;
import com.promptshield.backend.repository.UserRepository;
import com.promptshield.backend.service.PromptService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class PromptServiceImpl implements PromptService {

    private final PromptRepository promptRepository;
    private final UserRepository userRepository;

    @Override
    public PromptResponse optimizePrompt(
            String email,
            PromptRequest request) {

        User user = userRepository.findByEmail(email)
                .orElseThrow(() ->
                        new ResourceNotFoundException("User not found"));

        Prompt prompt = new Prompt();

        prompt.setOriginalPrompt(request.getPrompt());

        // Temporary optimization logic
        prompt.setOptimizedPrompt(
                "Optimized: " + request.getPrompt()
        );

        prompt.setUser(user);

        Prompt savedPrompt = promptRepository.save(prompt);

        return new PromptResponse(
                savedPrompt.getPromptId(),
                savedPrompt.getOriginalPrompt(),
                savedPrompt.getOptimizedPrompt(),
                savedPrompt.getCreatedAt()
        );
    }

    @Override
    public List<PromptResponse> getPromptHistory(String email) {

        User user = userRepository.findByEmail(email)
                .orElseThrow(() ->
                        new ResourceNotFoundException("User not found"));

        List<Prompt> prompts =
                promptRepository.findByUserOrderByCreatedAtDesc(user);

        return prompts.stream()
                .map(p -> new PromptResponse(
                        p.getPromptId(),
                        p.getOriginalPrompt(),
                        p.getOptimizedPrompt(),
                        p.getCreatedAt()
                ))
                .toList();
    }


    @Override
    public void deletePrompt(String email, Long promptId) {

        User user = userRepository.findByEmail(email)
                .orElseThrow(() ->
                        new ResourceNotFoundException("User not found"));

        Prompt prompt = promptRepository
                .findByPromptIdAndUser(promptId, user)
                .orElseThrow(() ->
                        new ResourceNotFoundException("Prompt not found"));

        promptRepository.delete(prompt);
    }


}
