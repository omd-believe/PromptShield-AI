package com.promptshield.backend.service;


import com.promptshield.backend.dto.response.AiOptimizeResponse;
import com.promptshield.backend.dto.response.PrivacyAnalysisResponse;
import java.util.Map;

public interface AiService {

    AiOptimizeResponse optimizePrompt(String prompt, Integer targetMaxTokens,
                                      Double minimumSemanticScore, Map<String, String> privacyPolicy);

    PrivacyAnalysisResponse analyzePrompt(String prompt, Map<String, String> privacyPolicy);
}