/**
 * Audit Log Service connected to FastAPI backend.
 */
import { apiClient } from "./api";

export const auditService = {
  /**
   * Fetch audit logs with optional filtering.
   */
  getAuditLogs: async (params = {}) => {
    try {
      return await apiClient.get("/api/audit-logs", params);
    } catch (err) {
      console.warn("[auditService] Failed to fetch audit logs:", err.message);
      return { total: 0, logs: [] };
    }
  },
};
