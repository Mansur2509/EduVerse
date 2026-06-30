import type {
  SavedUniversity,
  UniversityDetails,
  UniversityFilters,
  UniversityFitAnalysis
} from "@/entities/university";
import { ApiError, apiRequest, normalizePaginatedResponse } from "@/shared/api/client";
import { env } from "@/shared/config/env";

type PaginationParams = {
  page?: number;
  page_size?: number;
};

function buildQuery(filters: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    const normalized = typeof value === "number" ? String(value) : value?.trim();
    if (normalized) {
      query.set(key, normalized);
    }
  }
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export async function getUniversitiesRequest(
  filters: UniversityFilters = {},
  pagination: PaginationParams = {}
) {
  const path = `/universities/${buildQuery({ ...filters, ...pagination })}`;
  try {
    const response = await apiRequest<unknown>(path, { base: "api" });
    // The catalog endpoint may return a bare array or a DRF `{ results: [...] }`
    // page; normalize both. An empty list yields `{ results: [] }` so the screen
    // shows its empty state rather than an error.
    return normalizePaginatedResponse<UniversityDetails>(response, "universities");
  } catch (error) {
    // Dev-only diagnostics for the most failure-prone call (it is the first
    // `base: "api"` request and the one that broke when the API base URL was
    // misconfigured). Never logs auth tokens.
    if (process.env.NODE_ENV !== "production") {
      console.warn("[universities-api] catalog load failed", {
        requestUrl: `${env.apiBaseUrl}${path}`,
        status: error instanceof ApiError ? error.status : undefined,
        message: error instanceof ApiError ? error.message : String(error),
        // `data` carries the response body preview / content-type that
        // `parseResponse` attaches for non-JSON (e.g. a 404 HTML page).
        responsePreview: error instanceof ApiError ? error.data : undefined
      });
    }
    throw error;
  }
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
