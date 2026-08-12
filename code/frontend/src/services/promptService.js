import api from './api';

/**
 * Prompt Service — aligned with Spring Boot endpoints:
 *
 * POST /api/prompt/optimize
 *   Body: { "promptText": "..." }
 *   Response: {
 *     promptId: Long,
 *     originalText: String,
 *     optimizedText: String,
 *     similarityScore: Double,      // 0.0 – 1.0
 *     originalTokenCount: Int,
 *     optimizedTokenCount: Int,
 *     tokenReduction: Int,
 *     tokenReductionPercent: Double,
 *     privacyReport: [
 *       { type: String, value: String, masked: String }
 *     ],
 *     createdAt: String             // ISO 8601
 *   }
 *
 * GET /api/prompt/history?page=0&size=10
 *   Response: {
 *     content: [...],
 *     totalPages: Int,
 *     totalElements: Int,
 *     number: Int
 *   }
 *
 * GET /api/prompt/stats
 *   Response: {
 *     totalPrompts: Int,
 *     avgTokenReduction: Double,
 *     totalPrivacyFlags: Int,
 *     avgSimilarityScore: Double
 *   }
 */

/**
 * Optimize a prompt through the full AI pipeline.
 * @param {string} promptText
 */
export const optimizePrompt = async (promptText) => {
  const response = await api.post('/prompt/optimize', { promptText });
  return response.data;
};

/**
 * Fetch paginated prompt history for the logged-in user.
 * @param {number} page - zero-based page index
 * @param {number} size - items per page
 */
export const getHistory = async (page = 0, size = 10) => {
  const response = await api.get('/prompt/history', { params: { page, size } });
  return response.data; // { content, totalPages, totalElements, number }
};

/**
 * Fetch dashboard stats for the logged-in user.
 */
export const getDashboardStats = async () => {
  const response = await api.get('/prompt/stats');
  return response.data; // { totalPrompts, avgTokenReduction, totalPrivacyFlags, avgSimilarityScore }
};
