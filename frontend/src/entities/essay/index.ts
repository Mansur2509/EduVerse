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
  | "suggested"
  | "planned"
  | "not_started"
  | "drafting"
  | "needs_revision"
  | "reviewed"
  | "ready"
  | "submitted"
  | "skipped";

export type EssayPriority = "low" | "medium" | "high" | "urgent";

export type EssayPromptVerificationStatus = "verified" | "needs_verification" | "missing";

export type EssayPromptConfidence = "low" | "medium" | "high";

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
  application: number | null;
  application_university_name: string | null;
  application_round: string | null;
  prompt_text: string;
  word_limit: number | null;
  draft_text: string;
  status: EssayStatus;
  priority: EssayPriority;
  due_date: string | null;
  prompt_verification_status: EssayPromptVerificationStatus;
  prompt_confidence: EssayPromptConfidence;
  source_url: string;
  notes: string;
  suggestion_key: string;
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
  application?: number | null;
  prompt_text?: string;
  word_limit?: number | null;
  draft_text?: string;
  status?: EssayStatus;
  priority?: EssayPriority;
  due_date?: string | null;
  prompt_verification_status?: EssayPromptVerificationStatus;
  prompt_confidence?: EssayPromptConfidence;
  source_url?: string;
  notes?: string;
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
  "suggested",
  "planned",
  "not_started",
  "drafting",
  "needs_revision",
  "reviewed",
  "ready",
  "submitted",
  "skipped"
];

export const ESSAY_PRIORITIES: EssayPriority[] = ["low", "medium", "high", "urgent"];

export type AIEssayScoreConfidence = "low" | "medium" | "high";

export type AIEssayScoreWordLimitStatus = "under" | "within" | "near_limit" | "over" | "unknown";

export type AIEssayScoreStyleSignal = "low" | "medium" | "high" | "inconclusive";

export type AIEssayScoreGenericLanguageSignal = "low" | "medium" | "high";

export type AIEssayScoreClaimsSignal = "low" | "medium" | "high" | "inconclusive";

export type AIEssayScoreSubscores = {
  prompt_fit: number;
  structure: number;
  specificity_evidence: number;
  authenticity: number;
  language_clarity: number;
  word_limit_discipline: number | null;
  school_program_alignment: number | null;
};

export type AIEssayScoreReport = {
  id: number;
  essay: number;
  rubric_version: string;
  overall_essay_readiness: number;
  confidence: AIEssayScoreConfidence;
  verified_context_used: boolean;
  subscores: AIEssayScoreSubscores;
  nullable_scores: { school_program_alignment: number | null };
  word_count: number;
  word_limit_status: AIEssayScoreWordLimitStatus;
  ai_paraphrase_style_signal: AIEssayScoreStyleSignal;
  generic_language_signal: AIEssayScoreGenericLanguageSignal;
  unsupported_claims_signal: AIEssayScoreClaimsSignal;
  strength_flags: string[];
  risk_flags: string[];
  approximate_suggestions: string[];
  source_warnings: string[];
  disclaimers: string[];
  biggest_strength: string;
  biggest_weakness: string;
  reflective_questions: string[];
  action_plan: string;
  created_at: string;
};

export type AIEssayScoreReason =
  | "cached"
  | "scored"
  | "quota_exceeded"
  | "ai_unavailable"
  | "validation_failed"
  | "missing_essay_text"
  | "essay_too_long"
  | "review_already_running";

export type AIEssayScoreErrorKind = "not_configured" | "rate_limited" | "provider_unavailable" | null;

export type AIEssayScoreResponse = {
  reason: AIEssayScoreReason;
  cached: boolean;
  quota_remaining: number | null;
  next_available_at: string | null;
  ai_error_kind: AIEssayScoreErrorKind;
  score: AIEssayScoreReport | null;
};

export { EssayCard } from "./ui/essay-card";
