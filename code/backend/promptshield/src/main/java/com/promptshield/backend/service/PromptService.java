package com.promptshield.backend.service;

import com.promptshield.backend.dto.request.PromptRequest;
import com.promptshield.backend.dto.response.PromptResponse;
import java.util.List;

public interface PromptService {


    PromptResponse optimizePrompt(PromptRequest request);

    List<PromptResponse> getPromptHistory(Long userId);

    PromptResponse getPrompt(Long promptId);

    void deletePrompt(Long promptId);
}
