import type {
  AddSuggestionToRoadmapResponse,
  GenerateSuggestionsResponse,
  SuggestedItem,
  SuggestionFilters
} from "@/entities/suggestion";
import { apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

function buildQuery(filters: SuggestionFilters = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value?.trim()) {
      query.set(key, value.trim());
    }
  }
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export async function getSuggestionsRequest(filters: SuggestionFilters = {}) {
  const response = await apiRequest<unknown>(`/${buildQuery(filters)}`, {
    base: "suggestions"
  });
  return normalizePaginatedResponse<SuggestedItem>(response, "suggestions");
}

export function generateSuggestionsRequest() {
  return apiRequest<GenerateSuggestionsResponse>("/generate/", {
    base: "suggestions",
    method: "POST"
  });
}

export function addSuggestionToRoadmapRequest(id: number) {
  return apiRequest<AddSuggestionToRoadmapResponse>(`/${id}/add-to-roadmap/`, {
    base: "suggestions",
    method: "POST"
  });
}

export function dismissSuggestionRequest(id: number) {
  return apiRequest<SuggestedItem>(`/${id}/dismiss/`, {
    base: "suggestions",
    method: "PATCH"
  });
}
