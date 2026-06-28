import type {
  ApplicationMilestone,
  ApplicationMilestoneInput,
  ApplicationTrackerItem,
  ApplicationTrackerItemInput,
  PaginatedResponse
} from "@/entities/application";
import { apiRequest } from "@/shared/api/client";

export function getApplicationsRequest(filters: { status?: string; university?: string } = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value?.trim()) {
      query.set(key, value.trim());
    }
  }
  const queryString = query.toString();
  return apiRequest<PaginatedResponse<ApplicationTrackerItem>>(`/${queryString ? `?${queryString}` : ""}`, {
    base: "applications"
  });
}

export function getApplicationRequest(id: number) {
  return apiRequest<ApplicationTrackerItem>(`/${id}/`, { base: "applications" });
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
