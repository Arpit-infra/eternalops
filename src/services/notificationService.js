/**
 * In-App Notification Service connected to FastAPI backend.
 */
import { apiClient } from "./api";

export const notificationService = {
  /**
   * Fetch notifications.
   */
  getNotifications: async (unreadOnly = false) => {
    try {
      return await apiClient.get("/api/notifications", { unread_only: unreadOnly });
    } catch (err) {
      console.warn("[notificationService] Failed to fetch notifications:", err.message);
      return { total: 0, unread_count: 0, notifications: [] };
    }
  },

  /**
   * Mark a notification as read.
   */
  markRead: async (id) => {
    return await apiClient.post(`/api/notifications/${id}/read`);
  },

  /**
   * Mark all notifications as read.
   */
  markAllRead: async () => {
    return await apiClient.post("/api/notifications/read-all");
  },
};
