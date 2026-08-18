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
 *     createdAt: String             // ISO 8601
 *   }
 *
 * GET /api/v1/prompts/user
 *   Response: [ { promptId, originalPrompt, optimizedPrompt, createdAt }, ... ]
 *
 * DELETE /api/v1/prompts/{id}
 *   Response: 204 No Content
 */

/**
 * Optimize a prompt through the AI pipeline.
 * @param {string} promptText
 */
export const optimizePrompt = async (promptText) => {
  // Backend PromptRequest field name is "prompt" (not "promptText")
  const response = await api.post('/prompts', { prompt: promptText });
  return response.data; // { promptId, originalPrompt, optimizedPrompt, createdAt }
};

/**
 * Fetch all prompts for the logged-in user (ordered by newest first).
 * Backend returns a plain List, not a paginated object.
 */
export const getHistory = async () => {
  const response = await api.get('/prompts/user');
  // Wrap in a { content: [...] } shape so Dashboard.jsx works without changes
  const list = Array.isArray(response.data) ? response.data : [];
  return { content: list, totalElements: list.length };
};

/**
 * Derive dashboard stats from the user's prompt history.
 * The backend has no dedicated /stats endpoint — we compute from history.
 * @returns {{ totalPrompts, avgTokenReduction, totalPrivacyFlags, avgSimilarityScore }}
 */
export const getDashboardStats = async () => {
  const response = await api.get('/prompts/user');
  const list = Array.isArray(response.data) ? response.data : [];

  const totalPrompts = list.length;

  // Backend PromptResponse fields: originalPrompt, optimizedPrompt
  // Token count approximation: word count × 1.33
  const approxTokens = (text = '') => Math.ceil((text.trim().split(/\s+/).length) * 1.33);

  let totalReduction = 0;
  list.forEach((p) => {
    const orig = approxTokens(p.originalPrompt);
    const opt = approxTokens(p.optimizedPrompt);
    if (orig > 0) totalReduction += ((orig - opt) / orig) * 100;
  });

  return {
    totalPrompts,
    avgTokenReduction: totalPrompts > 0 ? totalReduction / totalPrompts : 0,
    totalPrivacyFlags: 0,   // backend doesn't expose this yet
    avgSimilarityScore: 0,  // backend doesn't expose this yet
  };
};

/**
 * Delete a prompt by ID.
 * @param {number} promptId
 */
export const deletePrompt = async (promptId) => {
  await api.delete(`/prompts/${promptId}`);
};
