import type {
  FitMissingFieldCode,
  FitNextActionCode,
  FitRiskCode,
  FitStrengthCode,
  MajorCluster,
  MajorInference,
  ProgramFitItem,
  UniversitySubjectRanking,
  UniversityFitSourceNote
} from "@/entities/university";

export type RecommendationCategory = "dream" | "reach" | "target" | "safety";

export type DateConfidence = "verified" | "partial" | "user_provided" | "estimated" | "missing";

export type Urgency =
  | "overdue"
  | "critical"
  | "urgent"
  | "soon"
  | "upcoming"
  | "far"
  | "unknown";

export type CostRisk = "low" | "moderate" | "high" | "unknown";

export type RiskLevel = "low" | "moderate" | "high";

export type ProgramMatchType = "exact" | "cluster" | "related";

export type RecommendedProgram = {
  name: string;
  fit_reason_key: string;
  match_type: ProgramMatchType;
  confidence: "low" | "medium" | "high";
  program_fit_score: number;
  major_cluster: MajorCluster | "other";
  subject_ranking: ProgramFitItem["subject_ranking"];
};

export type ApplicationRoundInfo = {
  available_rounds: string[];
  recommended_round: string;
  reason_key: string;
  reason_params: { round?: string };
};

export type RecommendationItem = {
  university: {
    id: number;
    name: string;
    slug: string;
    country: string;
    city: string;
  };
  category: RecommendationCategory;
  /** The canonical Fit Engine's own independent tier (reach/competitive/target/safety),
   * shown for transparency alongside `category` -- the two may legitimately disagree,
   * since `category` also weighs program/cost/extracurricular/preference/readiness. */
  canonical_fit_tier: "reach" | "competitive" | "target" | "safety" | null;
  is_international: boolean | null;
  fit_score: number;
  confidence: "low" | "medium" | "high";
  recommended_programs: RecommendedProgram[];
  matched_programs: RecommendedProgram[];
  program_data_verified: boolean;
  best_program_fit_score: number | null;
  major_cluster_match: boolean;
  program_fit_confidence: "low" | "medium" | "high";
  program_strengths: string[];
  program_gaps: string[];
  subject_ranking_context: Omit<UniversitySubjectRanking, "id" | "program" | "program_name" | "notes"> | null;
  missing_program_data: string[];
  major_inference: MajorInference;
  application_round: ApplicationRoundInfo;
  deadline: string | null;
  deadline_confidence: DateConfidence;
  deadline_cycle_label?: string | null;
  days_remaining: number | null;
  urgency: Urgency;
  estimated_total_cost_usd: string | number | null;
  tuition_usd: string | number | null;
  aid_scholarship_note_key: "aid_signal_available" | "aid_not_verified";
  cost_risk: CostRisk;
  academic_risk: RiskLevel;
  profile_risk: RiskLevel;
  deadline_risk: RiskLevel;
  main_strength: FitStrengthCode | null;
  main_risk: FitRiskCode | FitMissingFieldCode | null;
  /** Bounded, deduplicated "top reasons" list -- extends main_strength without replacing it. */
  top_reason_keys: FitStrengthCode[];
  /** Bounded, deduplicated "main risks" list -- extends main_risk without replacing it. */
  main_risks: (FitRiskCode | FitMissingFieldCode)[];
  /** Coarse EC/holistic signal; null when there isn't yet enough evidence to say anything. */
  holistic_context_key: "extracurricular_strong_evidence" | "extracurricular_limited_evidence" | null;
  why_recommended_keys: string[];
  next_action: FitNextActionCode | string;
  missing_data: FitMissingFieldCode[];
  current_academic_subscore: number;
  conditional_notes: string[];
  conditional_fit_score: number | null;
  conditional_targets: { sat?: number; ielts?: number } | null;
  source_notes: UniversityFitSourceNote[];
  is_shortlisted: boolean;
  application_id: number | null;
  /** 022 Phase 11: always included regardless of quota/diversity capping, with the same
   * honestly-computed category as every other item -- pinning changes inclusion, never the label. */
  is_pinned: boolean;
};

export type RecommendationCounts = {
  dream: number;
  reach: number;
  target: number;
  safety: number;
  international: number;
  total: number;
};

export type FinancialRiskWarning = {
  active: boolean;
  high_cost_risk_count: number;
  total: number;
};

export type RecommendationsResponse = {
  recommendations: RecommendationItem[];
  counts: RecommendationCounts;
  missing_preferences: string[];
  /** Deduplicated checklist of profile-strength reason codes with no evidence yet (e.g. no
   * activities, no test scores) -- distinct from genuinely weak evidence, never penalized. */
  missing_profile_signals: string[];
  /** Set when the student has declared financial need and the current list is dominated by
   * confirmed-high cost risk (no verified aid signal) -- a signal about the list, not a school. */
  financial_risk_warning: FinancialRiskWarning;
  excluded_low_data_count: number;
  excluded_degree_mismatch_count: number;
  /** 022 Phase 11: universities the student explicitly excluded via the exclude control. */
  excluded_by_user_count: number;
  list_size_limited: boolean;
  disclaimer: string;
};

export const RECOMMENDATION_CATEGORIES: RecommendationCategory[] = [
  "dream",
  "reach",
  "target",
  "safety"
];
