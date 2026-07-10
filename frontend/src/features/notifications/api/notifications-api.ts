import type {
  Notification,
  NotificationPreference,
  NotificationPreferenceInput,
  NotificationStatus
} from "@/entities/notification";
import { apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

export async function getNotificationsRequest(params: { status?: NotificationStatus } = {}) {
  const query = params.status ? `?status=${params.status}` : "";
  const response = await apiRequest<unknown>(`/${query}`, { base: "notifications" });
  return normalizePaginatedResponse<Notification>(response, "notifications");
}

export function updateNotificationStatusRequest(id: number, notificationStatus: NotificationStatus) {
  return apiRequest<Notification>(`/${id}/`, {
    base: "notifications",
    method: "PATCH",
    body: { status: notificationStatus }
  });
}

export function markAllNotificationsReadRequest() {
  return apiRequest<{ updated: number }>("/mark-all-read/", {
    base: "notifications",
    method: "POST"
  });
}

export function getNotificationPreferencesRequest() {
  return apiRequest<NotificationPreference>("/preferences/", { base: "notifications" });
}

export function updateNotificationPreferencesRequest(input: NotificationPreferenceInput) {
  return apiRequest<NotificationPreference>("/preferences/", {
    base: "notifications",
    method: "PATCH",
    body: input
  });
}
