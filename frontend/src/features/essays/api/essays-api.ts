import type {
  EssayFeedback,
  EssayRevisionTask,
  EssayRevisionTaskInput,
  EssayWorkspace,
  EssayWorkspaceInput,
  PaginatedResponse
} from "@/entities/essay";
import { apiRequest } from "@/shared/api/client";

export function getEssaysRequest() {
  return apiRequest<PaginatedResponse<EssayWorkspace>>("/", { base: "essays" });
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
