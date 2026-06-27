import type {
  PaginatedResponse,
  SavedUniversity,
  UniversityDetails,
  UniversityFilters,
  UniversityFitAnalysis
} from "@/entities/university";
import { apiRequest } from "@/shared/api/client";

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

export function getUniversitiesRequest(filters: UniversityFilters = {}) {
  return apiRequest<PaginatedResponse<UniversityDetails>>(
    `/universities/${buildQuery(filters)}`,
    { base: "api" }
  );
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

export function getShortlistRequest() {
  return apiRequest<PaginatedResponse<SavedUniversity>>("/universities/shortlist/", {
    base: "api"
  });
}
