/**
 * AI Copilot Service connected to FastAPI backend.
 */
import { apiClient } from "./api";

export const aiService = {
  /**
   * Send user prompt to backend AI Copilot and receive context-aware response.
   */
  chat: async (message, context = null) => {
    try {
      return await apiClient.post("/api/ai/chat", { message, context });
    } catch (err) {
      console.warn("[aiService] Chat request failed:", err.message);
      return {
        response: "Unable to reach EternalOps Copilot backend service. Please check API server connectivity.",
        intent: "error",
        suggested_actions: ["Check backend connection"],
      };
    }
  },
};
