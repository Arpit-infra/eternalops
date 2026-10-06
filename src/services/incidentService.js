/**
 * Incident Service for real FastAPI incident management.
 */
import { apiClient } from "./api";

export const incidentService = {
  /**
   * Fetch all incidents with optional filters.
   */
  getIncidents: async (filters = {}) => {
    try {
      const resp = await apiClient.get("/api/incidents", filters);
      return resp;
    } catch (err) {
      console.warn("[incidentService] Failed to fetch incidents:", err.message);
      return { total: 0, active_count: 0, resolved_count: 0, escalated_count: 0, incidents: [] };
    }
  },

  /**
   * Fetch single incident by ID.
   */
  getIncidentById: async (id) => {
    try {
      return await apiClient.get(`/api/incidents/${id}`);
    } catch (err) {
      console.warn(`[incidentService] Failed to fetch incident ${id}:`, err.message);
      return null;
    }
  },

  /**
   * Trigger autonomous healing on an incident.
   */
  healIncident: async (id) => {
    return await apiClient.post(`/api/incidents/${id}/heal`);
  },

  /**
   * Mark incident resolved manually.
   */
  resolveIncident: async (id) => {
    return await apiClient.post(`/api/incidents/${id}/resolve`);
  },

  /**
   * Escalate incident manually.
   */
  escalateIncident: async (id, reason) => {
    return await apiClient.post(`/api/incidents/${id}/escalate`, { reason });
  },

  /**
   * Trigger a safe test incident for demo or validation.
   */
  triggerTestIncident: async (data = {}) => {
    return await apiClient.post("/api/incidents/test", data);
  },
};
