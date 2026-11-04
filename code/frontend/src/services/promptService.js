import api from './api';

/**
 * Prompt Service — aligned with Spring Boot endpoints:
 *
 * POST /api/v1/prompts
 *   Body: { "prompt": "..." }
 *   Response: {
 *     promptId: Long,
 *     originalPrompt: String,
 *     optimizedPrompt: String,
 *     createdAt: String,             // ISO 8601
 *     entities: [ { text: String, label: String } ],
 *     riskScore: Integer,
 *     riskLevel: String,
 *     originalTokens: Integer,
 *     optimizedTokens: Integer,
 *     reductionPercentage: Double,
 *     sensitiveDataDetected: Boolean
 *   }
 *
 * POST /api/v1/prompts/analyze
 *   Response: {
 *     originalPrompt, anonymizedPrompt, entities, privacyReport,
 *     riskScore, riskLevel
 *   }
 *
 * GET /api/v1/prompts/user
 *   Response: [ { promptId, originalPrompt, optimizedPrompt, createdAt, originalTokens, optimizedTokens, reductionPercentage, sensitiveDataDetected }, ... ]
 *
 * DELETE /api/v1/prompts/{id}
 *   Response: 204 No Content
 */

/**
 * Optimize a prompt through the AI pipeline.
 * @param {string} promptText
 */
export const optimizePrompt = async (promptText, options = {}) => {
  const response = await api.post('/prompts', {
    prompt: promptText,
    ...(options.targetMaxTokens ? { targetMaxTokens: Number(options.targetMaxTokens) } : {}),
    ...(options.minimumSemanticScore != null
      ? { minimumSemanticScore: Number(options.minimumSemanticScore) }
      : {}),
    ...(options.privacyPolicy ? { privacyPolicy: options.privacyPolicy } : {}),
  });
  return response.data;
};

/**
 * Analyze a prompt for sensitive information without optimizing it.
 * @param {string} promptText
 */
export const analyzePrompt = async (promptText, privacyPolicy) => {
  const response = await api.post('/prompts/analyze', {
    prompt: promptText,
    ...(privacyPolicy ? { privacyPolicy } : {}),
  });
  return response.data;
};

export const recordPrivacyAudit = async ({
  eventType,
  promptId,
  riskLevel,
  riskScore,
  categories = [],
}) => {
  await api.post('/prompts/audit', {
    eventType,
    promptId,
    riskLevel,
    riskScore,
    categories,
  });
};

/**
 * Fetch prompts for the logged-in user (newest first).
 * The backend returns the full list (no server-side paging), so `limit`
 * is applied here. `totalElements` is always the full count.
 * @param {number} [limit] - return only the newest `limit` prompts
 */
export const getHistory = async (limit) => {
  const response = await api.get('/prompts/user');
  const list = Array.isArray(response.data) ? response.data : [];
  const content = Number.isInteger(limit) && limit > 0 ? list.slice(0, limit) : list;
  return { content, totalElements: list.length };
};

/**
 * Derive dashboard stats from the user's prompt history.
 * @returns {{ totalPrompts, avgTokenReduction, totalPrivacyFlags, totalEntitiesDetected, totalTokensSaved, privacyCategories, riskLevels, semanticAcceptanceRate }}
 */
export const getDashboardStats = async () => {
  const response = await api.get('/prompts/stats');
  const stats = response.data || {};
  return {
    totalPrompts: stats.totalPrompts ?? 0,
    avgTokenReduction: stats.averageTokenReduction ?? 0,
    totalPrivacyFlags: stats.promptsWithSensitiveData ?? 0,
    totalEntitiesDetected: stats.totalEntitiesDetected ?? 0,
    totalTokensSaved: stats.totalTokensSaved ?? 0,
    privacyCategories: stats.privacyCategories || {},
    riskLevels: stats.riskLevels || {},
    semanticAcceptanceRate: stats.semanticAcceptanceRate ?? null,
  };
};

/**
 * Delete a prompt by ID.
 * @param {number} promptId
 */
export const deletePrompt = async (promptId) => {
  await api.delete(`/prompts/${promptId}`);
};
