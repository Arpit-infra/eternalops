/**
 * Environment & Organization Service for Control Plane UI.
 */
import { apiClient } from "./api";

export const environmentService = {
  /**
   * List all registered infrastructure environments.
   */
  getEnvironments: async (params = {}) => {
    try {
      const data = await apiClient.get("/api/environments", params);
      return data.environments || [];
    } catch (err) {
      console.warn("[environmentService] Failed to fetch environments, fallback to default local:", err.message);
      return [
        {
          id: "env_local_dev",
          name: "Local Development",
          description: "Local Docker Desktop Kubernetes cluster",
          provider: "docker-desktop",
          platform: "kubernetes",
          connection_type: "local_kubernetes",
          status: "CONNECTED",
        },
      ];
    }
  },

  /**
   * Get environment details by ID.
   */
  getEnvironment: async (environmentId) => {
    return await apiClient.get(`/api/environments/${environmentId}`);
  },

  /**
   * Probe health of an environment.
   */
  getEnvironmentHealth: async (environmentId) => {
    return await apiClient.get(`/api/environments/${environmentId}/health`);
  },

  /**
   * Generate agent enrollment token.
   */
  generateEnrollmentToken: async (environmentId) => {
    return await apiClient.post(`/api/environments/${environmentId}/token`);
  },

  /**
   * Get synthesized system health summary.
   */
  getHealthSummary: async () => {
    return await apiClient.get("/api/health/summary");
  },

  /**
   * Get detailed workload health states.
   */
  getWorkloadHealth: async () => {
    return await apiClient.get("/api/health/workloads");
  },
};
