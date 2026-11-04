package com.promptshield.backend.service;

import com.promptshield.backend.dto.request.PromptRequest;
import com.promptshield.backend.dto.response.PromptResponse;
import com.promptshield.backend.dto.response.PromptStatsResponse;
import java.util.List;

public interface PromptService {


    PromptResponse optimizePrompt(String email, PromptRequest request);

    List<PromptResponse> getPromptHistory(String email);

    PromptStatsResponse getPromptStats(String email);

    void deletePrompt(String email, Long promptId);
}
