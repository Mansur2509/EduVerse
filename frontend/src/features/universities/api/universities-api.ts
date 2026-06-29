import type {
  SavedUniversity,
  UniversityDetails,
  UniversityFilters,
  UniversityFitAnalysis
} from "@/entities/university";
import { apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

function buildQuery(filters: Record<string, string | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value?.trim()) {
      query.set(key, value.trim());
    }
  }
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export async function getUniversitiesRequest(filters: UniversityFilters = {}) {
  const response = await apiRequest<unknown>(
    `/universities/${buildQuery(filters)}`,
    { base: "api" }
  );
  return normalizePaginatedResponse<UniversityDetails>(response, "universities");
}

export function getUniversityRequest(slug: string) {
  return apiRequest<UniversityDetails>(`/universities/${encodeURIComponent(slug)}/`, {
    base: "api"
  });
}

export function getUniversityFitRequest(slug: string) {
  return apiRequest<UniversityFitAnalysis>(
    `/universities/${encodeURIComponent(slug)}/fit/`,
    { base: "api" }
  );
}

export function compareUniversitiesRequest(ids: number[]) {
  return apiRequest<UniversityDetails[]>(
    `/universities/compare/${buildQuery({ ids: ids.join(",") })}`,
    { base: "api" }
  );
}

export function addToShortlistRequest(slug: string) {
  return apiRequest<SavedUniversity>(
    `/universities/${encodeURIComponent(slug)}/shortlist/`,
    { base: "api", method: "POST" }
  );
}

export function removeFromShortlistRequest(slug: string) {
  return apiRequest<void>(`/universities/${encodeURIComponent(slug)}/shortlist/`, {
    base: "api",
    method: "DELETE"
  });
}

export async function getShortlistRequest() {
  const response = await apiRequest<unknown>("/universities/shortlist/", {
    base: "api"
  });
  return normalizePaginatedResponse<SavedUniversity>(response, "university shortlist");
}
