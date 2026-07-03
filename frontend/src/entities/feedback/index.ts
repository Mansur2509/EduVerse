export type FeedbackType = "issue" | "idea" | "confusing" | "data";

export type FeedbackStatus = "new" | "reviewed" | "resolved" | "archived";

export type FeedbackPriority = "low" | "normal" | "high" | "critical";

export const FEEDBACK_STATUSES: FeedbackStatus[] = [
  "new",
  "reviewed",
  "resolved",
  "archived"
];

export const FEEDBACK_PRIORITIES: FeedbackPriority[] = [
  "low",
  "normal",
  "high",
  "critical"
];

export type FeedbackReportInput = {
  feedback_type: FeedbackType;
  page_module: string;
  message: string;
  contact?: string;
};

export type FeedbackReport = {
  id: number;
  user: number | null;
  user_email: string | null;
  contact: string;
  feedback_type: FeedbackType;
  page_module: string;
  message: string;
  status: FeedbackStatus;
  priority: FeedbackPriority;
  user_agent: string;
  admin_notes: string;
  created_at: string;
  updated_at: string;
};

export type FeedbackReportUpdateInput = {
  status?: FeedbackStatus;
  priority?: FeedbackPriority;
  admin_notes?: string;
};

export type FeedbackFilters = {
  status?: FeedbackStatus | "";
  feedback_type?: FeedbackType | "";
  priority?: FeedbackPriority | "";
  page_module?: string;
};
