import type {
  AIEssayScoreReport,
  AIEssayScoreResponse,
  EssayFeedback,
  EssayRevisionTask,
  EssayRevisionTaskInput,
  EssayWorkspace,
  EssayWorkspaceInput
} from "@/entities/essay";
import { ApiError, ESSAY_REVIEW_TIMEOUT_MS, apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

type EssayListParams = {
  page?: number;
  page_size?: number;
};

function buildQuery(params: EssayListParams) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      query.set(key, String(value));
    }
  }
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export async function getEssaysRequest(params: EssayListParams = {}) {
  const response = await apiRequest<unknown>(`/${buildQuery(params)}`, { base: "essays" });
  return normalizePaginatedResponse<EssayWorkspace>(response, "essays");
}

export function getEssayRequest(id: number) {
  return apiRequest<EssayWorkspace>(`/${id}/`, { base: "essays" });
}

export function createEssayRequest(input: EssayWorkspaceInput) {
  return apiRequest<EssayWorkspace>("/", { base: "essays", method: "POST", body: input });
}

export function updateEssayRequest(id: number, input: Partial<EssayWorkspaceInput>) {
  return apiRequest<EssayWorkspace>(`/${id}/`, {
    base: "essays",
    method: "PATCH",
    body: input
  });
}

export function deleteEssayRequest(id: number) {
  return apiRequest<void>(`/${id}/`, { base: "essays", method: "DELETE" });
}

export function generateEssaySuggestionsRequest() {
  return apiRequest<{
    created_count: number;
    existing_count: number;
    essays: EssayWorkspace[];
  }>("/generate-suggestions/", { base: "essays", method: "POST" });
}

export function generateEssayFeedbackRequest(id: number) {
  return apiRequest<{ detail: string; feedback: EssayFeedback; essay: EssayWorkspace }>(
    `/${id}/feedback/`,
    { base: "essays", method: "POST" }
  );
}

export function getEssayFeedbackRequest(id: number) {
  return apiRequest<{ detail: string; feedback: EssayFeedback | null }>(`/${id}/feedback/`, {
    base: "essays"
  });
}

export function createEssayRevisionTaskRequest(
  essayId: number,
  input: EssayRevisionTaskInput
) {
  return apiRequest<EssayRevisionTask>(`/${essayId}/revision-tasks/`, {
    base: "essays",
    method: "POST",
    body: input
  });
}

export async function scoreEssayRequest(
  id: number,
  options: { signal?: AbortSignal } = {}
): Promise<AIEssayScoreResponse> {
  try {
    // A fresh AI review can take substantially longer than the global request
    // timeout: the backend may run an initial Gemini call plus a retry, and if
    // validation fails, a repair-prompt pass plus its own retry (see
    // ESSAY_REVIEW_TIMEOUT_MS's doc comment for the full worst-case math). Use
    // that dedicated, longer budget here instead of the platform default.
    return await apiRequest<AIEssayScoreResponse>(`/${id}/score/`, {
      base: "essays",
      method: "POST",
      timeoutMs: ESSAY_REVIEW_TIMEOUT_MS,
      signal: options.signal
    });
  } catch (error) {
    // The backend returns a structured, safe-to-render body (reason,
    // quota_remaining, next_available_at) even for expected non-2xx outcomes
    // like quota_exceeded/ai_unavailable/validation_failed/review_already_running
    // -- surface that instead of treating it as a generic request failure.
    if (
      error instanceof ApiError &&
      error.data &&
      typeof error.data === "object" &&
      "reason" in error.data
    ) {
      return error.data as AIEssayScoreResponse;
    }
    throw error;
  }
}

export function getEssayScoresRequest(id: number) {
  return apiRequest<{ results: AIEssayScoreReport[] }>(`/${id}/scores/`, { base: "essays" });
}

export function getLatestEssayScoreRequest(id: number) {
  return apiRequest<{ score: AIEssayScoreReport | null }>(`/${id}/score/latest/`, { base: "essays" });
}

export function updateEssayRevisionTaskRequest(
  taskId: number,
  input: Partial<{ status: string; title: string; description: string }>
) {
  return apiRequest<EssayRevisionTask>(`/revision-tasks/${taskId}/`, {
    base: "essays",
    method: "PATCH",
    body: input
  });
}
