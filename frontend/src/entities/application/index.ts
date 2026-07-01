export type ApplicationRound =
  | "early_decision"
  | "early_action"
  | "restrictive_early_action"
  | "regular_decision"
  | "rolling"
  | "scholarship"
  | "other";

export type ApplicationStatus =
  | "researching"
  | "shortlisted"
  | "preparing"
  | "applying"
  | "submitted"
  | "awaiting_decision"
  | "accepted"
  | "waitlisted"
  | "rejected"
  | "withdrawn";

export type ApplicationPriority = "low" | "medium" | "high" | "dream";

export type ApplicationTaskStatus =
  | "not_started"
  | "drafting"
  | "needs_revision"
  | "ready"
  | "submitted";

export type RecommendationsStatus = "not_started" | "requested" | "received" | "submitted";

export type TestScoresStatus = "not_required" | "planned" | "ready" | "sent";

export type DocumentsStatus = "not_started" | "collecting" | "ready" | "submitted";

export type FinancialAidStatus = "not_applying" | "researching" | "preparing" | "submitted";

export type MilestoneCategory =
  | "essays"
  | "recommendations"
  | "tests"
  | "financial_aid"
  | "documents"
  | "submission"
  | "interview"
  | "decision";

export type MilestoneStatus = "todo" | "in_progress" | "completed" | "skipped";

export type MilestonePriority = "low" | "medium" | "high";

export type ApplicationMilestone = {
  id: number;
  application: number;
  title: string;
  category: MilestoneCategory;
  due_date: string | null;
  status: MilestoneStatus;
  priority: MilestonePriority;
  notes: string;
  linked_roadmap_task: number | null;
  linked_roadmap_task_title: string | null;
  source_url: string;
  created_at: string;
  updated_at: string;
};

export type DateConfidence =
  | "verified"
  | "partial"
  | "user_provided"
  | "estimated"
  | "missing";

export type Urgency =
  | "overdue"
  | "critical"
  | "urgent"
  | "soon"
  | "upcoming"
  | "far"
  | "unknown";

export type TimelineDeadline = {
  kind: "application" | "financial_aid" | "scholarship";
  date: string | null;
  confidence: DateConfidence;
  days_remaining: number | null;
  urgency: Urgency;
  source_url: string;
  source_label: string;
  last_verified_date: string | null;
};

export type TimelineEvent = {
  type: string;
  title: string | null;
  date: string | null;
  days_remaining: number | null;
  urgency: Urgency;
  confidence: DateConfidence;
  reason_key?: string;
  weeks_before?: number;
  reference_deadline?: string | null;
  status?: string;
  is_timeline_marker?: boolean;
  source_url?: string;
  category?: string;
};

export type TimelineSuggestedDate = {
  type: string;
  date: string | null;
  days_remaining: number | null;
  urgency: Urgency;
  reason_key: string;
  weeks_before: number;
  reference_deadline: string | null;
  reference_confidence: DateConfidence;
  confidence: DateConfidence;
};

export type TimelineEssay = {
  id: number;
  title: string;
  essay_type: string;
  status: string;
  word_limit: number | null;
  word_count: number;
  updated_at: string;
  source_url: string;
};

export type TimelineExam = {
  exam: string;
  current_score: number | null;
  threshold: number | null;
  threshold_label: string | null;
  severity: string | null;
  planned_retake: boolean;
  official_test_date: string | null;
  official_test_date_confidence: string | null;
  registration_deadline: string | null;
  source_url: string;
  scores_arrive_before_deadline: boolean | null;
};

export type ApplicationTimeline = {
  deadlines: TimelineDeadline[];
  events: TimelineEvent[];
  suggested_dates: TimelineSuggestedDate[];
  linked_essays: TimelineEssay[];
  linked_exams: TimelineExam[];
};

export type ApplicationTrackerItem = {
  id: number;
  university: number;
  university_name: string;
  university_slug: string;
  target_program: number | null;
  target_program_name: string | null;
  application_round: ApplicationRound;
  status: ApplicationStatus;
  priority: ApplicationPriority;
  deadline: string | null;
  financial_aid_deadline: string | null;
  scholarship_deadline: string | null;
  essays_status: ApplicationTaskStatus;
  recommendations_status: RecommendationsStatus;
  test_scores_status: TestScoresStatus;
  documents_status: DocumentsStatus;
  financial_aid_status: FinancialAidStatus;
  notes: string;
  milestones: ApplicationMilestone[];
  created_at: string;
  updated_at: string;
};

export type ApplicationTrackerItemInput = Partial<{
  university: number;
  target_program: number | null;
  application_round: ApplicationRound;
  status: ApplicationStatus;
  priority: ApplicationPriority;
  deadline: string | null;
  financial_aid_deadline: string | null;
  scholarship_deadline: string | null;
  essays_status: ApplicationTaskStatus;
  recommendations_status: RecommendationsStatus;
  test_scores_status: TestScoresStatus;
  documents_status: DocumentsStatus;
  financial_aid_status: FinancialAidStatus;
  notes: string;
}>;

export type ApplicationMilestoneInput = {
  title: string;
  category: MilestoneCategory;
  due_date?: string | null;
  priority?: MilestonePriority;
  notes?: string;
  linked_roadmap_task?: number | null;
  source_url?: string;
};

export type PaginatedResponse<Item> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Item[];
};

export const APPLICATION_STATUSES: ApplicationStatus[] = [
  "researching",
  "shortlisted",
  "preparing",
  "applying",
  "submitted",
  "awaiting_decision",
  "accepted",
  "waitlisted",
  "rejected",
  "withdrawn"
];

export const APPLICATION_BOARD_COLUMNS: ApplicationStatus[] = [
  "researching",
  "shortlisted",
  "preparing",
  "applying",
  "submitted",
  "awaiting_decision"
];

export const DECISION_STATUSES: ApplicationStatus[] = [
  "accepted",
  "waitlisted",
  "rejected",
  "withdrawn"
];

export { ApplicationCard } from "./ui/application-card";
