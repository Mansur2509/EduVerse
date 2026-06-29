import type {
  GenerateRoadmapResponse,
  ManualRoadmapTaskInput,
  RoadmapPlanResponse,
  RoadmapTask,
  RoadmapTaskFilters,
  RoadmapTaskUpdateInput
} from "@/entities/roadmap";
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

export function getRoadmapRequest() {
  return apiRequest<RoadmapPlanResponse>("/", { base: "roadmap" });
}

export function generateRoadmapRequest() {
  return apiRequest<GenerateRoadmapResponse>("/generate/", {
    base: "roadmap",
    method: "POST"
  });
}

export async function getRoadmapTasksRequest(filters: RoadmapTaskFilters = {}) {
  const response = await apiRequest<unknown>(`/tasks/${buildQuery(filters)}`, {
    base: "roadmap"
  });
  return normalizePaginatedResponse<RoadmapTask>(response, "roadmap tasks");
}

export function createRoadmapTaskRequest(input: ManualRoadmapTaskInput) {
  return apiRequest<RoadmapTask>("/tasks/", {
    base: "roadmap",
    method: "POST",
    body: input
  });
}

export function updateRoadmapTaskRequest(id: number, input: RoadmapTaskUpdateInput) {
  return apiRequest<RoadmapTask>(`/tasks/${id}/`, {
    base: "roadmap",
    method: "PATCH",
    body: input
  });
}

export function deleteRoadmapTaskRequest(id: number) {
  return apiRequest<void>(`/tasks/${id}/`, {
    base: "roadmap",
    method: "DELETE"
  });
}

export function completeRoadmapTaskRequest(id: number) {
  return apiRequest<RoadmapTask>(`/tasks/${id}/complete/`, {
    base: "roadmap",
    method: "POST"
  });
}

export function skipRoadmapTaskRequest(id: number) {
  return apiRequest<RoadmapTask>(`/tasks/${id}/skip/`, {
    base: "roadmap",
    method: "POST"
  });
}
