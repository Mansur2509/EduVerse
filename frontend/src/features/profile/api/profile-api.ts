import type {
  ApplicationReadiness,
  ProfileAssessmentEnvelope,
  ProfileCompletion,
  ProfileRecommendationsResponse,
  ProfileStrategy,
  StudentProfileDetails,
  UpdateStudentProfileInput
} from "@/entities/profile";
import { apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

export function getProfileRequest() {
  return apiRequest<StudentProfileDetails>("/me/", {
    base: "profile"
  });
}

export function updateProfileRequest(input: UpdateStudentProfileInput) {
  return apiRequest<StudentProfileDetails>("/me/", {
    base: "profile",
    method: "PATCH",
    body: input
  });
}

export function getProfileCompletionRequest() {
  return apiRequest<ProfileCompletion>("/completion/", {
    base: "profile"
  });
}

export function completeOnboardingRequest() {
  return apiRequest<ProfileCompletion>("/complete-onboarding/", {
    base: "profile",
    method: "POST"
  });
}

export function getApplicationReadinessRequest() {
  return apiRequest<ApplicationReadiness>("/readiness/", {
    base: "profile"
  });
}

export function getProfileAssessmentLatestRequest() {
  return apiRequest<ProfileAssessmentEnvelope>("/assessment/latest/", {
    base: "profile"
  });
}

export function runProfileAssessmentRequest() {
  return apiRequest<ProfileAssessmentEnvelope>("/assessment/run/", {
    base: "profile",
    method: "POST"
  });
}

// PROTOCOL-008 PART 7: gap-based recommendations and the time-bucketed
// action plan, both read-only and built purely from the cached assessment --
// never trigger an AI call on render.
export function getProfileRecommendationsRequest() {
  return apiRequest<ProfileRecommendationsResponse>("/recommendations/me/", {
    base: "api"
  });
}

export function getProfileStrategyRequest() {
  return apiRequest<ProfileStrategy>("/strategy/me/", {
    base: "api"
  });
}

// Profile item CRUD endpoints
type ItemType =
  | "activities"
  | "honors"
  | "olympiads"
  | "sports"
  | "research-projects"
  | "essays"
  | "portfolio-projects"
  | "volunteering"
  | "recommenders";

interface ProfileItem {
  id: number;
  created_at: string;
  updated_at: string;
}

export async function getProfileItemsRequest<T extends ProfileItem>(itemType: ItemType) {
  const response = await apiRequest<unknown>(`/${itemType}/`, {
    base: "profile"
  });
  return normalizePaginatedResponse<T>(response, `profile ${itemType}`);
}

export function createProfileItemRequest<T extends Partial<ProfileItem>>(itemType: ItemType, data: T) {
  return apiRequest<T & ProfileItem>(`/${itemType}/`, {
    base: "profile",
    method: "POST",
    body: data
  });
}

export function updateProfileItemRequest<T extends Partial<ProfileItem>>(itemType: ItemType, id: number, data: T) {
  return apiRequest<T & ProfileItem>(`/${itemType}/${id}/`, {
    base: "profile",
    method: "PATCH",
    body: data
  });
}

export function deleteProfileItemRequest(itemType: ItemType, id: number) {
  return apiRequest<void>(`/${itemType}/${id}/`, {
    base: "profile",
    method: "DELETE"
  });
}
