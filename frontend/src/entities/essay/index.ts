export type EssayType =
  | "common_app"
  | "supplement"
  | "scholarship"
  | "activity"
  | "intellectual_interest"
  | "why_major"
  | "why_school"
  | "additional_information"
  | "other";

export type EssayStatus =
  | "not_started"
  | "drafting"
  | "needs_revision"
  | "reviewed"
  | "ready"
  | "submitted";

export type EssayOverallLabel = "weak" | "developing" | "solid" | "strong" | "excellent";

export type EssayWordLimitStatus = "too_short" | "within_limit" | "too_long";

export type EssayRevisionTaskCategory =
  | "structure"
  | "clarity"
  | "specificity"
  | "authenticity"
  | "grammar"
  | "word_count"
  | "prompt_fit";

export type EssayRevisionTaskStatus = "todo" | "completed" | "skipped";

export type EssayRevisionTask = {
  id: number;
  essay: number;
  title: string;
  description: string;
  category: EssayRevisionTaskCategory;
  status: EssayRevisionTaskStatus;
  created_at: string;
  completed_at: string | null;
};

export type EssayFeedback = {
  id: number;
  overall_label: EssayOverallLabel;
  structure_score: number | null;
  clarity_score: number | null;
  authenticity_score: number | null;
  specificity_score: number | null;
  grammar_score: number | null;
  prompt_fit_score: number | null;
  word_count: number;
  word_limit_status: EssayWordLimitStatus;
  summary: string;
  strengths: string[];
  issues: string[];
  revision_tasks: Array<{ category: string; title: string; description: string }>;
  created_at: string;
};

export type EssayWorkspace = {
  id: number;
  title: string;
  essay_type: EssayType;
  university: number | null;
  university_name: string | null;
  university_slug: string | null;
  prompt_text: string;
  word_limit: number | null;
  draft_text: string;
  status: EssayStatus;
  source_url: string;
  last_reviewed_at: string | null;
  latest_feedback: EssayFeedback | null;
  revision_tasks: EssayRevisionTask[];
  word_count: number;
  created_at: string;
  updated_at: string;
};

export type EssayWorkspaceInput = {
  title: string;
  essay_type?: EssayType;
  university?: number | null;
  prompt_text?: string;
  word_limit?: number | null;
  draft_text?: string;
  status?: EssayStatus;
  source_url?: string;
};

export type EssayRevisionTaskInput = {
  title: string;
  description?: string;
  category: EssayRevisionTaskCategory;
};

export type PaginatedResponse<Item> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Item[];
};

export const ESSAY_TYPES: EssayType[] = [
  "common_app",
  "supplement",
  "scholarship",
  "activity",
  "intellectual_interest",
  "why_major",
  "why_school",
  "additional_information",
  "other"
];

export const ESSAY_STATUSES: EssayStatus[] = [
  "not_started",
  "drafting",
  "needs_revision",
  "reviewed",
  "ready",
  "submitted"
];

export { EssayCard } from "./ui/essay-card";
