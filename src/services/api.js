/**
 * Backend API Client for EternalOps.
 * Connects to the FastAPI backend at VITE_API_URL or defaults to http://localhost:8000.
 */
const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export const apiClient = {
  get: async (endpoint, params = {}) => {
    try {
      const url = new URL(`${BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`);
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });

      const response = await fetch(url.toString(), {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
      });

      if (!response.ok) {
        let errorData = null;
        try {
          errorData = await response.json();
        } catch {
          // non-JSON error
        }
        const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
        error.status = response.status;
        error.data = errorData;
        throw error;
      }

      return await response.json();
    } catch (err) {
      console.warn(`[API Client] GET ${endpoint} failed:`, err.message);
      throw err;
    }
  },

  post: async (endpoint, data = {}) => {
    try {
      const url = `${BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        let errorData = null;
        try {
          errorData = await response.json();
        } catch {
          // non-JSON error
        }
        const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
        error.status = response.status;
        error.data = errorData;
        throw error;
      }

      return await response.json();
    } catch (err) {
      console.warn(`[API Client] POST ${endpoint} failed:`, err.message);
      throw err;
    }
  },
};
