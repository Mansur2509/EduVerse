export type InstitutionType = "public" | "private" | "";

export type UniversityProgram = {
  id: number;
  name: string;
  display_name?: string;
  degree_level: string;
  official_url: string;
};

export type UniversityRequirementItem = {
  id: number;
  requirement_type: string;
  value: string;
  notes: string;
};

export type UniversityScholarshipItem = {
  id: number;
  name: string;
  summary: string;
  official_url: string;
  deadline: string | null;
};

export type UniversityDataSourceItem = {
  id: number;
  source_title: string;
  source_url: string;
  is_official: boolean;
  published_at: string | null;
  retrieved_at: string;
};

export type VerificationStatus = "verified" | "partial" | "estimated";

export type UniversityFieldVerification = {
  field_name: string;
  status: VerificationStatus;
  source_url: string;
  last_verified_date: string;
  note: string;
};

export type TestPolicy = "required" | "optional" | "blind" | "varies" | "";

export type UniversitySummary = {
  id: number;
  name: string;
  slug: string;
  country: string;
  city: string;
  official_website: string;
  admissions_url: string;
  financial_aid_url: string;
  application_portal_url: string;
  international_office_url: string;
  virtual_info_session_url: string;
  summary: string;
  institution_type: InstitutionType;
  is_published: boolean;
  is_demo: boolean;
  acceptance_rate: string | null;
  gpa_average: string | null;
  sat_average: number | null;
  sat_p25: number | null;
  sat_p75: number | null;
  ielts_minimum: string | null;
  ielts_competitive: string | null;
  test_policy: TestPolicy;
  tuition_amount: string | null;
  tuition_currency: string;
  tuition_original_amount: string | null;
  tuition_original_currency: string;
  tuition_usd_amount: string | null;
  total_cost_original_amount: string | null;
  total_cost_original_currency: string;
  total_cost_usd_amount: string | null;
  currency_conversion_rate: string | null;
  currency_conversion_date: string | null;
  currency_conversion_source: string;
  currency_conversion_confidence: "" | "low" | "medium" | "high";
  cost_notes: string;
  application_deadline: string | null;
  scholarship_available: boolean | null;
  essay_requirements: string;
  application_requirements: string;
  ap_recommendations: string;
  deadlines_text: string;
  financial_aid_notes: string;
  scholarships_text: string;
  data_quality_notes: string;
  qs_ranking: number | null;
  qs_ranking_year: number | null;
  is_shortlisted: boolean;
  program_display_names?: string[];
  programs: UniversityProgram[];
  requirements: UniversityRequirementItem[];
  scholarships: UniversityScholarshipItem[];
  data_sources: UniversityDataSourceItem[];
  field_verifications: UniversityFieldVerification[];
  created_at: string;
  updated_at: string;
};

export type UniversityDetails = UniversitySummary;

export type UniversityFilters = {
  search?: string;
  country?: string;
  city?: string;
  institution_type?: string;
  scholarship_available?: string;
  verification_status?: string;
  include_demo?: string;
  ordering?: string;
  ielts_minimum__lte?: string;
  sat_average__gte?: string;
  sat_average__lte?: string;
  gpa_average__lte?: string;
};

export type FitCategory = "dream" | "reach" | "competitive" | "target" | "safety";

export type FitStrengthCode =
  | "gpa_above_average"
  | "sat_above_average"
  | "sat_competitive"
  | "sat_above_p75"
  | "ielts_meets_competitive"
  | "curriculum_context_available"
  | "major_matches_program"
  | "profile_depth";

export type FitRiskCode =
  | "gpa_below_average"
  | "sat_below_average"
  | "sat_below_p25"
  | "sat_partial_fit"
  | "ielts_below_minimum"
  | "ielts_below_competitive"
  | "gpa_scale_not_confirmed"
  | "deadline_passed"
  | "deadline_close"
  | "cost_conversion_missing"
  | "aid_data_missing";

export type FitMissingFieldCode =
  | "profile_gpa"
  | "profile_sat"
  | "profile_ielts"
  | "profile_curriculum"
  | "profile_intended_major"
  | "profile_activities"
  | "profile_essays"
  | "university_gpa_average"
  | "university_sat_average"
  | "university_acceptance_rate"
  | "university_programs"
  | "university_application_deadline"
  | "university_cost"
  | "currency_conversion";

export type FitNextActionCode =
  | "add_gpa_to_profile"
  | "add_sat_to_profile"
  | "add_ielts_to_profile"
  | "add_curriculum_context"
  | "verify_university_data"
  | "limited_data_for_category"
  | "plan_exam_retake"
  | "verify_exam_date_before_deadline";

export type UniversityFitSourceNote = {
  title: string;
  url: string;
  is_official: boolean;
};

export type UniversityFitAnalysis = {
  fit_score: number;
  category: FitCategory | null;
  confidence: "low" | "medium" | "high";
  academic_subscore: number;
  program_subscore: number;
  profile_subscore: number;
  essay_subscore: number;
  deadline_subscore: number;
  cost_subscore: number;
  strengths: FitStrengthCode[];
  risks: FitRiskCode[];
  missing_fields: FitMissingFieldCode[];
  missing_data: FitMissingFieldCode[];
  next_actions: FitNextActionCode[];
  conditional_notes: string[];
  student_academic_context: {
    original_gpa_value: string | number | null;
    original_gpa_scale: string | number | null;
    original_gpa_scale_type: string;
    normalized_gpa_4: string | number | null;
    normalized_percentage: string | number | null;
    confidence: "low" | "medium" | "high";
    note: string;
    curriculum_type: string;
    curriculum_country: string;
  };
  cost_context: {
    tuition_original_amount: string | number | null;
    tuition_original_currency: string;
    tuition_usd_amount: string | number | null;
    total_cost_original_amount: string | number | null;
    total_cost_original_currency: string;
    total_cost_usd_amount: string | number | null;
    conversion_rate: string | number | null;
    conversion_date: string | null;
    conversion_source: string;
    conversion_confidence: "" | "low" | "medium" | "high";
    cost_notes: string;
  };
  source_notes: UniversityFitSourceNote[];
  disclaimer: string;
};

export type SavedUniversity = {
  id: number;
  university: UniversityDetails;
  created_at: string;
};

export type PaginatedResponse<Item> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Item[];
};

export function formatTuitionAmount(amount: string | number | null): string | null {
  if (amount === null) {
    return null;
  }
  const numeric = typeof amount === "number" ? amount : Number.parseFloat(amount);
  if (Number.isNaN(numeric)) {
    return String(amount);
  }
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0
  }).format(numeric);
}

export function getFieldVerification(
  verifications: UniversityFieldVerification[],
  fieldName: string
): UniversityFieldVerification | undefined {
  return verifications.find((verification) => verification.field_name === fieldName);
}

export { UniversityCard } from "./ui/university-card";
export { StatValue } from "./ui/stat-value";
export { VerifiedStat, VerificationBadge } from "./ui/verified-stat";
