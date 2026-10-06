/**
 * Kubernetes Service for live data from FastAPI Kubernetes proxy backend.
 */
import { apiClient } from "./api";

export const kubernetesService = {
  /**
   * Check Kubernetes cluster status.
   */
  getStatus: async () => {
    try {
      return await apiClient.get("/api/kubernetes/status");
    } catch (err) {
      return {
        available: false,
        in_cluster: false,
        context: null,
        cluster_version: null,
        error: err.message || "Failed to contact Kubernetes proxy",
      };
    }
  },

  /**
   * Get Kubernetes cluster information.
   */
  getClusterInfo: async () => {
    try {
      return await apiClient.get("/api/kubernetes/cluster");
    } catch (err) {
      return {
        available: false,
        git_version: null,
        major: null,
        minor: null,
        platform: null,
        error: err.message || "Failed to get cluster info",
      };
    }
  },

  /**
   * List all namespaces.
   */
  getNamespaces: async () => {
    try {
      return await apiClient.get("/api/kubernetes/namespaces");
    } catch (err) {
      return {
        available: false,
        total: 0,
        namespaces: [],
        error: err.message || "Failed to list namespaces",
      };
    }
  },

  /**
   * List cluster nodes.
   */
  getNodes: async () => {
    try {
      return await apiClient.get("/api/kubernetes/nodes");
    } catch (err) {
      return {
        available: false,
        total: 0,
        nodes: [],
        error: err.message || "Failed to list nodes",
      };
    }
  },

  /**
   * List cluster pods, optionally filtered by namespace.
   */
  getPods: async (namespace = null) => {
    try {
      const params = namespace && namespace !== "all" ? { namespace } : {};
      return await apiClient.get("/api/kubernetes/pods", params);
    } catch (err) {
      return {
        available: false,
        total: 0,
        pods: [],
        error: err.message || "Failed to list pods",
      };
    }
  },

  /**
   * List deployments, optionally filtered by namespace.
   */
  getDeployments: async (namespace = null) => {
    try {
      const params = namespace && namespace !== "all" ? { namespace } : {};
      return await apiClient.get("/api/kubernetes/deployments", params);
    } catch (err) {
      return {
        available: false,
        total: 0,
        deployments: [],
        error: err.message || "Failed to list deployments",
      };
    }
  },

  /**
   * List services, optionally filtered by namespace.
   */
  getServices: async (namespace = null) => {
    try {
      const params = namespace && namespace !== "all" ? { namespace } : {};
      return await apiClient.get("/api/kubernetes/services", params);
    } catch (err) {
      return {
        available: false,
        total: 0,
        services: [],
        error: err.message || "Failed to list services",
      };
    }
  },
};

