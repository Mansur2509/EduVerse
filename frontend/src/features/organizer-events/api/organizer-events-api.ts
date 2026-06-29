import type {
  EventCategory,
  EventModerationLog,
  OrganizerEvent,
  OrganizerEventInput,
  OrganizerParticipant
} from "@/entities/event";
import { apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

export function getOrganizerEventCategoriesRequest() {
  return apiRequest<EventCategory[]>("/event-categories/", {
    base: "organizer"
  });
}

export async function getOrganizerEventsRequest() {
  const response = await apiRequest<unknown>("/events/", {
    base: "organizer"
  });
  return normalizePaginatedResponse<OrganizerEvent>(response, "organizer events");
}

export function createOrganizerEventRequest(input: OrganizerEventInput) {
  return apiRequest<OrganizerEvent>("/events/", {
    base: "organizer",
    method: "POST",
    body: input
  });
}

export function getOrganizerEventRequest(slug: string) {
  return apiRequest<OrganizerEvent>(`/events/${encodeURIComponent(slug)}/`, {
    base: "organizer"
  });
}

export function updateOrganizerEventRequest(
  slug: string,
  input: Partial<OrganizerEventInput>
) {
  return apiRequest<OrganizerEvent>(`/events/${encodeURIComponent(slug)}/`, {
    base: "organizer",
    method: "PATCH",
    body: input
  });
}

function postOrganizerEventAction(slug: string, action: string) {
  return apiRequest<OrganizerEvent>(
    `/events/${encodeURIComponent(slug)}/${action}/`,
    {
      base: "organizer",
      method: "POST"
    }
  );
}

export function submitOrganizerEventRequest(slug: string) {
  return postOrganizerEventAction(slug, "submit");
}

export function archiveOrganizerEventRequest(slug: string) {
  return postOrganizerEventAction(slug, "archive");
}

export function cancelOrganizerEventRequest(slug: string) {
  return postOrganizerEventAction(slug, "cancel");
}

export async function getOrganizerEventParticipantsRequest(slug: string) {
  const response = await apiRequest<unknown>(
    `/events/${encodeURIComponent(slug)}/registrations/`,
    { base: "organizer" }
  );
  return normalizePaginatedResponse<OrganizerParticipant>(response, "event participants");
}

export async function getPendingEventsRequest() {
  const response = await apiRequest<unknown>("/pending/", {
    base: "moderation"
  });
  return normalizePaginatedResponse<OrganizerEvent>(response, "moderation events");
}

export function approveEventRequest(slug: string) {
  return apiRequest<OrganizerEvent>(`/${encodeURIComponent(slug)}/approve/`, {
    base: "moderation",
    method: "POST"
  });
}

export function rejectEventRequest(slug: string, reason: string) {
  return apiRequest<OrganizerEvent>(`/${encodeURIComponent(slug)}/reject/`, {
    base: "moderation",
    method: "POST",
    body: { reason }
  });
}

export function archiveModeratedEventRequest(slug: string) {
  return apiRequest<OrganizerEvent>(`/${encodeURIComponent(slug)}/archive/`, {
    base: "moderation",
    method: "POST"
  });
}

export function getEventModerationLogsRequest(slug: string) {
  return apiRequest<EventModerationLog[]>(
    `/${encodeURIComponent(slug)}/logs/`,
    { base: "moderation" }
  );
}
