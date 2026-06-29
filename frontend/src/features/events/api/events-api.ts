import type {
  EventDetails,
  EventFilters,
  EventRegistration
} from "@/entities/event";
import { apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

function buildEventQuery(filters: EventFilters) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value?.trim()) {
      query.set(key, value.trim());
    }
  }
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export async function getEventsRequest(filters: EventFilters = {}) {
  const response = await apiRequest<unknown>(
    `/${buildEventQuery(filters)}`,
    { base: "events" }
  );
  return normalizePaginatedResponse<EventDetails>(response, "events");
}

export function getEventRequest(slug: string) {
  return apiRequest<EventDetails>(`/${encodeURIComponent(slug)}/`, {
    base: "events"
  });
}

export function registerForEventRequest(slug: string) {
  return apiRequest<EventRegistration>(`/${encodeURIComponent(slug)}/register/`, {
    base: "events",
    method: "POST"
  });
}

export function cancelEventRegistrationRequest(slug: string) {
  return apiRequest<EventRegistration>(
    `/${encodeURIComponent(slug)}/cancel-registration/`,
    {
      base: "events",
      method: "POST"
    }
  );
}

export async function getMyEventRegistrationsRequest() {
  const response = await apiRequest<unknown>("/my-registrations/", {
    base: "events"
  });
  return normalizePaginatedResponse<EventRegistration>(response, "event registrations");
}
