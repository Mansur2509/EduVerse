export type SuggestionType =
  | "exam_date"
  | "exam_plan"
  | "essay_deadline"
  | "essay_word_limit"
  | "application_deadline"
  | "scholarship_deadline"
  | "scholarship_type"
  | "course_recommendation"
  | "ap_recommendation"
  | "document_deadline"
  | "profile_gap"
  | "roadmap_instruction";

export type SuggestionPriority = "low" | "medium" | "high" | "urgent";

export type SuggestionSourceType =
  | "official"
  | "verified_university_data"
  | "planning_window"
  | "profile_based"
  | "roadmap_based"
  | "missing_data_warning";

export type SuggestionStatus = "active" | "dismissed" | "added_to_roadmap";

export type SuggestedItem = {
  id: number;
  suggestion_type: SuggestionType;
  title: string;
  description: string;
  priority: SuggestionPriority;
  source_type: SuggestionSourceType;
  status: SuggestionStatus;
  linked_university: number | null;
  linked_university_name: string | null;
  linked_university_slug: string | null;
  linked_application: number | null;
  linked_application_university_name: string | null;
  linked_essay: number | null;
  linked_essay_title: string | null;
  linked_roadmap_task: number | null;
  linked_roadmap_task_title: string | null;
  recommended_start_date: string | null;
  recommended_end_date: string | null;
  official_deadline: string | null;
  word_limit: number | null;
  source_url: string;
  evidence_note: string;
  created_at: string;
  updated_at: string;
  dismissed_at: string | null;
  added_to_roadmap_at: string | null;
};

export type SuggestionFilters = {
  status?: SuggestionStatus | "";
  suggestion_type?: SuggestionType | "";
  linked_university?: string;
  linked_application?: string;
  linked_essay?: string;
};

export type GenerateSuggestionsResponse = {
  suggestions: SuggestedItem[];
};

export type AddSuggestionToRoadmapResponse = {
  suggestion: SuggestedItem;
  roadmap_task_id: number;
};
