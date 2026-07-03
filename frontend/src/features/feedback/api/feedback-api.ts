import type {
  FeedbackFilters,
  FeedbackReport,
  FeedbackReportInput,
  FeedbackReportUpdateInput
} from "@/entities/feedback";
import { apiRequest, normalizePaginatedResponse } from "@/shared/api/client";

type AdminFeedbackParams = FeedbackFilters & {
  page?: number;
  page_size?: number;
};

function buildQuery(params: AdminFeedbackParams) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

// Auth is intentionally left at its default (attach a token when the caller
// is logged in) rather than forced off, since the backend links submissions
// to the user when authenticated. The endpoint itself allows anonymous
// requests too (this modal is also reachable from the pre-auth login page),
// so a logged-out caller still succeeds with no token attached.
export function createFeedbackRequest(input: FeedbackReportInput) {
  return apiRequest<FeedbackReport>("/", {
    base: "feedback",
    method: "POST",
    body: input
  });
}

export async function getAdminFeedbackListRequest(params: AdminFeedbackParams = {}) {
  const response = await apiRequest<unknown>(buildQuery(params), {
    base: "adminFeedback"
  });
  return normalizePaginatedResponse<FeedbackReport>(response, "admin feedback");
}

export function updateAdminFeedbackRequest(id: number, input: FeedbackReportUpdateInput) {
  return apiRequest<FeedbackReport>(`/${id}/`, {
    base: "adminFeedback",
    method: "PATCH",
    body: input
  });
}
