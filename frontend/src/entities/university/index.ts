export type InstitutionType = "public" | "private" | "";

export type UniversityProgram = {
  id: number;
  name: string;
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

export type UniversitySummary = {
  id: number;
  name: string;
  slug: string;
  country: string;
  city: string;
  official_website: string;
  summary: string;
  institution_type: InstitutionType;
  is_published: boolean;
  acceptance_rate: string | null;
  gpa_average: string | null;
  sat_average: number | null;
  tuition_amount: string | null;
  tuition_currency: string;
  application_deadline: string | null;
  scholarship_available: boolean | null;
  is_shortlisted: boolean;
  programs: UniversityProgram[];
  requirements: UniversityRequirementItem[];
  scholarships: UniversityScholarshipItem[];
  data_sources: UniversityDataSourceItem[];
  created_at: string;
  updated_at: string;
};

export type UniversityDetails = UniversitySummary;

export type UniversityFilters = {
  search?: string;
  country?: string;
  institution_type?: string;
  scholarship_available?: string;
};

export type FitCategory = "reach" | "competitive" | "target" | "safety";

export type FitStrengthCode = "gpa_above_average" | "sat_above_average";

export type FitRiskCode = "gpa_below_average" | "sat_below_average";

export type FitMissingFieldCode =
  | "profile_gpa"
  | "profile_sat"
  | "university_gpa_average"
  | "university_sat_average"
  | "university_acceptance_rate";

export type FitNextActionCode =
  | "add_gpa_to_profile"
  | "add_sat_to_profile"
  | "verify_university_data";

export type UniversityFitSourceNote = {
  title: string;
  url: string;
  is_official: boolean;
};

export type UniversityFitAnalysis = {
  category: FitCategory | null;
  strengths: FitStrengthCode[];
  risks: FitRiskCode[];
  missing_fields: FitMissingFieldCode[];
  next_actions: FitNextActionCode[];
  source_notes: UniversityFitSourceNote[];
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

export { UniversityCard } from "./ui/university-card";
