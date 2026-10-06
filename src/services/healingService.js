/**
 * Self-Healing Service connected to FastAPI backend.
 */
import { apiClient } from "./api";

export const healingService = {
  /**
   * Get overall healing engine status, active operation, and recent history.
   */
  getStatus: async () => {
    try {
      return await apiClient.get("/api/healing/status");
    } catch (err) {
      console.warn("[healingService] Failed to fetch healing status:", err.message);
      return {
        enabled: true,
        currently_healing: null,
        active_stage: null,
        recent_healed: [],
        total_healed_count: 0,
        total_escalated_count: 0,
      };
    }
  },

  /**
   * Get currently active healing incident.
   */
  getCurrentHealing: async () => {
    try {
      return await apiClient.get("/api/healing/current");
    } catch (err) {
      console.warn("[healingService] Failed to fetch current healing:", err.message);
      return null;
    }
  },

  /**
   * Get recent healed or escalated incident history.
   */
  getHealingHistory: async (limit = 10) => {
    try {
      return await apiClient.get("/api/healing/history", { limit });
    } catch (err) {
      console.warn("[healingService] Failed to fetch healing history:", err.message);
      return [];
    }
  },

  /**
   * Execute autonomous healing on a specific incident.
   */
  runHealing: async (incidentId) => {
    return await apiClient.post(`/api/healing/run/${incidentId}`);
  },
};
