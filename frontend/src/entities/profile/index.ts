import type { UserRole } from "@/entities/user";

export type ScholarshipNeed = "yes" | "no" | "unsure";
export type BudgetFlexibility = "strict" | "flexible" | "unknown";
export type CourseRigorLevel = "standard" | "advanced" | "highly_advanced" | "unknown";

export type CurriculumRigor = {
  curriculum_context: string;
  rigor_score: number;
  rigor_confidence: "low" | "medium" | "high";
  missing_curriculum_data: string[];
  stem_rigor_signal: "unknown" | "low" | "medium" | "high";
  humanities_rigor_signal: "unknown" | "low" | "medium" | "high";
  business_economics_rigor_signal: "unknown" | "low" | "medium" | "high";
};

export type MajorCurriculumFit = {
  preparation_signal: "unknown" | "limited_context" | "some_context" | "strong_context";
  recommended_coursework: string[];
  note: string;
};

export type TestScoreValue = string | number | string[];
export type TestScores = Record<string, TestScoreValue>;

export type PlannedExam = {
  name: string;
  date: string;
  target_score: string;
  exam_type?: "SAT" | "AP" | "ACT" | "IELTS" | "TOEFL";
  planned_retake?: boolean;
  planned_retake_month?: string;
  current_score?: string;
  test_status?: string;
  registration_status?: "not_registered" | "registered" | "cancelled" | "not_required";
  result?: string;
  official_exam_date_id?: number;
  notification_intervals?: number[];
};

export type ExamPlans = {
  taken: string[];
  planned: PlannedExam[];
};

export type ActivityProfile = {
  extracurriculars: string[];
  honors: string[];
  sports: string[];
  olympiads: string[];
  research_projects: string[];
  mun_debate: string[];
  volunteering: string[];
  leadership: string[];
  work_internships: string[];
};

export type OnboardingSection =
  | "identity"
  | "academic"
  | "exams"
  | "activities"
  | "support";

export type StudentProfileDetails = {
  id: number;
  email: string;
  role: UserRole;
  full_name: string;
  birth_date: string | null;
  country: string;
  city: string;
  school_or_university: string;
  grade: string;
  expected_graduation_year: number | null;
  education_status: string;
  gpa: string | number | null;
  gpa_scale: string | number | null;
  original_gpa_value: string | number | null;
  original_gpa_scale: string | number | null;
  original_gpa_scale_type:
    | "4_0"
    | "5_0"
    | "percentage_100"
    | "ib_45"
    | "a_level"
    | "ap_heavy"
    | "uzbekistan_5"
    | "kazakhstan_local"
    | "kyrgyzstan_local"
    | "tajikistan_local"
    | "custom_unknown";
  normalized_gpa_4: string | number | null;
  normalized_percentage: string | number | null;
  curriculum_type:
    | "local_school"
    | "academic_lyceum"
    | "ib"
    | "a_level"
    | "ap"
    | "national_diploma"
    | "foundation"
    | "other"
    | "unknown";
  curriculum_country: string;
  course_rigor_level: CourseRigorLevel;
  ap_courses_count: number | null;
  ib_courses_count: number | null;
  a_level_subjects_count: number | null;
  honors_courses_count: number | null;
  curriculum_rigor: CurriculumRigor;
  major_curriculum_fit: MajorCurriculumFit;
  academic_normalization_confidence: "low" | "medium" | "high";
  academic_normalization_note: string;
  intended_degree: string;
  target_countries: string[];
  intended_majors: string[];
  target_universities: string[];
  university_unsure: boolean;
  major_unsure: boolean;
  scholarship_need: ScholarshipNeed;
  annual_budget_amount: string | number | null;
  annual_budget_currency: string;
  budget_flexibility: BudgetFlexibility;
  interests: string[];
  languages: string[];
  test_scores: TestScores;
  exam_plans: ExamPlans;
  preparation_needs: string[];
  activities: ActivityProfile;
  essay_status: "yes" | "no" | "not_yet";
  essay_stage: string;
  support_priorities: string[];
  interested_classes: string[];
  ap_interests: string[];
  career_interests: string[];
  mun_debate_interest: boolean;
  research_interest: boolean;
  finance_literacy_interest: boolean;
  onboarding_sections: OnboardingSection[];
  onboarding_version: number;
  onboarding_completed_at: string | null;
  telegram_username: string;
  phone: string;
  updated_at: string;
};

export type UpdateStudentProfileInput = Partial<
  Omit<
    StudentProfileDetails,
    | "id"
    | "email"
    | "role"
    | "updated_at"
    | "curriculum_rigor"
    | "major_curriculum_fit"
    | "normalized_gpa_4"
    | "normalized_percentage"
    | "academic_normalization_confidence"
    | "academic_normalization_note"
  >
>;

export type ProfileCompletion = {
  percentage: number;
  completed_fields: number;
  total_fields: number;
  missing_fields: string[];
  missing_sections: string[];
  required_fields: string[];
  is_complete: boolean;
  can_complete: boolean;
};

export type ApplicationReadiness = {
  stars: 1 | 2 | 3 | 4 | 5;
  level: "incomplete" | "developing" | "solid" | "strong" | "excellent";
  score_components: Record<string, number>;
  categories: Array<{
    key: string;
    score: number;
    source_keys: string[];
    missing_sources: string[];
    status: string;
  }>;
  strengths: string[];
  improvements: string[];
  reasons: string[];
  next_actions: string[];
  cap_reason: string;
  comparison_status: "published_ranges" | "official_data_needed";
  compared_universities: string[];
  official_sources: Array<{
    title: string;
    url: string;
    university: string;
  }>;
};

export type ProfileAssessmentCategory =
  | "profile_evidence_score"
  | "activities_score"
  | "honors_olympiads_score"
  | "research_experience_score"
  | "portfolio_score"
  | "subject_passion_score"
  | "curiosity_score"
  | "originality_score"
  | "leadership_score"
  | "community_impact_score"
  | "research_fit_score"
  | "olympiads_score";

export const PROFILE_ASSESSMENT_CATEGORIES: ProfileAssessmentCategory[] = [
  "profile_evidence_score",
  "activities_score",
  "honors_olympiads_score",
  "research_experience_score",
  "portfolio_score",
  "subject_passion_score",
  "curiosity_score",
  "originality_score",
  "leadership_score",
  "community_impact_score",
  "research_fit_score",
  "olympiads_score"
];

export type BenchmarkSource =
  | "dream_universities"
  | "major_country_average"
  | "country_average"
  | "global_major_average"
  | "global_average"
  | "unavailable";

export type ReadinessSection = {
  key: string;
  score: number;
  status: string;
  main_strength: string | null;
  main_risk: string | null;
  missing_items: string[];
  next_action: string;
  cap_reasons: string[];
};

export type ReadinessScoresSummary = {
  status: string;
  cap_reason: string;
  reasons: string[];
  next_actions: string[];
  sections: ReadinessSection[];
};

export type MissingEvidenceFlags = {
  essays?: boolean;
  recommendation_letters?: boolean;
  honors?: boolean;
  research?: boolean;
  portfolio?: boolean;
  activities?: boolean;
  olympiads?: boolean;
  volunteering?: boolean;
};

export type DeterministicScores = {
  gpa?: { student: number | null; benchmark: number | null; status: string };
  sat?: {
    student: number | null;
    benchmark_p25: number | null;
    benchmark_p75: number | null;
    benchmark_average: number | null;
    status: string;
  };
  ielts?: {
    student: number | null;
    benchmark_minimum: number | null;
    benchmark_competitive: number | null;
    status: string;
  };
  toefl?: { student: number | null; present: boolean };
  ap?: { count: number; structured_subjects_available: boolean; subject_matches_major: boolean | null };
  missing_evidence?: MissingEvidenceFlags;
  profile_completion_percentage?: number;
  score_gaps?: {
    fit_band: string;
    signals_compared: number;
    signals_missing_data: number;
    counts_by_severity: Record<string, number>;
    per_signal: Record<string, { gap: number | null; severity: string }>;
  };
};

export type AIProfileAssessment = {
  id: number;
  assessment_version: string;
  overall_profile_score: number;
  category_scores: Record<ProfileAssessmentCategory, number>;
  confidence: "low" | "medium" | "high";
  public_summary: string;
  evidence_used: string[];
  missing_data: string[];
  improvement_areas: string[];
  target_context_used: boolean;
  expires_at: string;
  is_stale: boolean;
  created_at: string;
  status: "ok" | "fallback_used";
  benchmark_source: BenchmarkSource;
  benchmark_sample_size: number;
  benchmark_scores: Record<string, number>;
  benchmark_academic: Record<string, number>;
  deterministic_scores: DeterministicScores;
  readiness_scores: ReadinessScoresSummary | Record<string, never>;
  overall_readiness_score: number | null;
  next_allowed_refresh_at: string | null;
};

export type ProfileAssessmentReason =
  | "latest_assessment"
  | "no_previous_assessment"
  | "profile_changed"
  | "unchanged_cached"
  | "daily_limit_reached"
  | "ai_unavailable"
  | "validation_failed"
  | "fallback_used";

export type ProfileAssessmentEnvelope = {
  assessment: AIProfileAssessment | null;
  cached: boolean;
  reason: ProfileAssessmentReason;
  can_refresh: boolean;
  next_available_at: string | null;
  ai_available: boolean;
  disclaimer: string;
};

// Gap-based recommendations (`/api/v1/recommendations/me/`) -- `title`,
// `why_it_matters`, and `next_action` are short semantic keys translated via
// `admissions.recommendation.*` i18n, never raw prose from the backend.
export type RecommendationPriority = "urgent" | "high" | "medium" | "low";

export type ProfileRecommendation = {
  title: string;
  priority: RecommendationPriority;
  linked_dimension: string;
  why_it_matters: string;
  evidence_from_profile: Record<string, unknown>;
  expected_impact: string;
  next_action: string;
};

export type ProfileRecommendationsResponse = {
  recommendations: ProfileRecommendation[];
  needs_assessment: boolean;
};

// Time-bucketed action plan (`/api/v1/strategy/me/`).
export type StrategyEvent = {
  type: string;
  date: string | null;
  days_remaining: number | null;
  urgency: string;
  confidence: string;
  university?: string;
  application_id?: number;
  [key: string]: unknown;
};

// 022 Phase 9: the unified, prioritized action list spanning all ten
// categories (Academics/Testing/Extracurriculars/Research/Essays/
// Recommendations/Financial planning/University research/Application
// timeline/Documents). Every action shares this same shape regardless of
// category.
export type StrategyActionCategory =
  | "academics"
  | "testing"
  | "extracurriculars"
  | "research"
  | "essays"
  | "recommendations"
  | "financial_planning"
  | "university_research"
  | "application_timeline"
  | "documents";

export type StrategyActionUniversityRef = { id: number; name: string; slug: string };

export type StrategyAction = {
  title: string;
  category: StrategyActionCategory;
  reason: string;
  affected_universities: StrategyActionUniversityRef[];
  affected_university_count: number;
  urgency: string;
  estimated_effort: "low" | "medium" | "high";
  expected_strategic_value: "low" | "medium" | "high";
  evidence_source: Record<string, unknown>;
  deadline: string | null;
  completion_state: "not_started" | "in_progress" | "done";
  dependency: string | null;
  confidence: "low" | "medium" | "high";
  next_action: string;
};

export type ProfileStrategy = {
  generated_at: string;
  has_tracked_applications: boolean;
  has_verified_deadlines: boolean;
  overdue: StrategyEvent[];
  next_7_days: StrategyEvent[];
  next_30_days: StrategyEvent[];
  next_90_days: StrategyEvent[];
  before_deadline: StrategyEvent[];
  unscheduled: StrategyEvent[];
  testing_plan: Record<string, unknown>;
  essay_plan: {
    essays_missing: boolean;
    planned_dates: StrategyEvent[];
    workspaces: Array<Record<string, unknown>>;
    next_action: string;
  };
  recommendation_letter_plan: {
    recommendation_letters_missing: boolean;
    planned_dates: StrategyEvent[];
    recommenders: Array<Record<string, unknown>>;
    next_action: string;
  };
  activities_research_plan: {
    missing_evidence: Record<string, boolean>;
    next_actions: string[];
  };
  university_list_strategy: Record<string, unknown>;
  prioritized_actions: StrategyAction[];
  needs_assessment: boolean;
};

// Structured profile items
export type Activity = {
  id: number;
  title: string;
  role: string;
  organization: string;
  category: string;
  start_date: string | null;
  end_date: string | null;
  year: number | null;
  hours_per_week: number | null;
  weeks_per_year: number | null;
  scale: "school" | "city" | "regional" | "national" | "international";
  impact_number: string;
  description: string;
  proof_link: string;
  created_at: string;
  updated_at: string;
};

export type Honor = {
  id: number;
  title: string;
  issuing_organization: string;
  level: string;
  year: number | null;
  result_rank: string;
  description: string;
  proof_link: string;
  created_at: string;
  updated_at: string;
};

export type Olympiad = {
  id: number;
  name: string;
  subject: string;
  level: string;
  year: number | null;
  result: string;
  rank_percentile: string;
  description: string;
  proof_link: string;
  created_at: string;
  updated_at: string;
};

export type Sport = {
  id: number;
  sport_name: string;
  level: string;
  years_trained: string;
  peak_result: string;
  competition_name: string;
  description: string;
  proof_link: string;
  created_at: string;
  updated_at: string;
};

export type ResearchProject = {
  id: number;
  title: string;
  field: string;
  research_question: string;
  sample_size: string;
  countries_region: string;
  methods_used: string;
  current_stage: "planning" | "active" | "completed" | "published";
  manuscript_link: string;
  publication_status: string;
  description: string;
  created_at: string;
  updated_at: string;
};

export type EssayDraft = {
  id: number;
  essay_type: string;
  school_program: string;
  status: "draft" | "in_progress" | "submitted" | "reviewed";
  word_limit: number | null;
  draft_status: string;
  last_reviewed_date: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type PortfolioProject = {
  id: number;
  title: string;
  project_type: string;
  link: string;
  tech_stack: string;
  users_impact: string;
  status: string;
  description: string;
  created_at: string;
  updated_at: string;
};

export type Volunteer = {
  id: number;
  title: string;
  role: string;
  organization: string;
  start_date: string | null;
  end_date: string | null;
  hours_per_week: number | null;
  weeks_per_year: number | null;
  scale: "school" | "city" | "regional" | "national" | "international";
  impact_number: string;
  beneficiaries: string;
  description: string;
  proof_link: string;
  created_at: string;
  updated_at: string;
};

export type Recommender = {
  id: number;
  name: string;
  relationship_role: string;
  status: "not_started" | "planned" | "requested" | "confirmed" | "submitted";
  requested_date: string | null;
  submitted_date: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
};

export {
  majorCatalog,
  recommendationSignals,
  type MajorCategoryId,
  type MajorOption
} from "./major-catalog";
export {
  classCatalog,
  targetCountries,
  type RecommendedClass,
  type RecommendedClassId
} from "./admissions-catalog";
export {
  assessmentQuestions,
  categoryForMajor,
  recommendFromAssessment,
  recommendationsForMajors,
  type AssessmentAnswer,
  type RecommendationResult
} from "./recommendation-engine";
export { ReadinessCard } from "./ui/readiness-card";
export { GapRecommendationsPanel } from "./ui/gap-recommendations-panel";
export { StrategyPanel } from "./ui/strategy-panel";
