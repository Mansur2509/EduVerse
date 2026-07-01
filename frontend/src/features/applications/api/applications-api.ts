import type {
  ApplicationMilestone,
  ApplicationMilestoneInput,
  ApplicationTimeline,
  ApplicationTrackerItem,
  ApplicationTrackerItemInput
} from "@/entities/application";
import { apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

type ApplicationListParams = {
  status?: string;
  university?: string;
  page?: number;
  page_size?: number;
};

export async function getApplicationsRequest(filters: ApplicationListParams = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    const normalized = typeof value === "number" ? String(value) : value?.trim();
    if (normalized) {
      query.set(key, normalized);
    }
  }
  const queryString = query.toString();
  const response = await apiRequest<unknown>(`/${queryString ? `?${queryString}` : ""}`, {
    base: "applications"
  });
  return normalizePaginatedResponse<ApplicationTrackerItem>(response, "applications");
}

export function getApplicationRequest(id: number) {
  return apiRequest<ApplicationTrackerItem>(`/${id}/`, { base: "applications" });
}

export function getApplicationTimelineRequest(id: number) {
  return apiRequest<ApplicationTimeline>(`/${id}/timeline/`, { base: "applications" });
}

export function createApplicationRequest(input: ApplicationTrackerItemInput) {
  return apiRequest<ApplicationTrackerItem>("/", {
    base: "applications",
    method: "POST",
    body: input
  });
}

export function updateApplicationRequest(
  id: number,
  input: Partial<ApplicationTrackerItemInput>
) {
  return apiRequest<ApplicationTrackerItem>(`/${id}/`, {
    base: "applications",
    method: "PATCH",
    body: input
  });
}

export function deleteApplicationRequest(id: number) {
  return apiRequest<void>(`/${id}/`, { base: "applications", method: "DELETE" });
}

export function createApplicationMilestoneRequest(
  applicationId: number,
  input: ApplicationMilestoneInput
) {
  return apiRequest<ApplicationMilestone>(`/${applicationId}/milestones/`, {
    base: "applications",
    method: "POST",
    body: input
  });
}

export function updateApplicationMilestoneRequest(
  milestoneId: number,
  input: Partial<ApplicationMilestoneInput & { status: string }>
) {
  return apiRequest<ApplicationMilestone>(`/milestones/${milestoneId}/`, {
    base: "applications",
    method: "PATCH",
    body: input
  });
}
