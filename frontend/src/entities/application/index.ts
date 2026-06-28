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

export type ApplicationMilestone = {
  id: number;
  application: number;
  title: string;
  category: MilestoneCategory;
  due_date: string | null;
  status: MilestoneStatus;
  linked_roadmap_task: number | null;
  linked_roadmap_task_title: string | null;
  source_url: string;
  created_at: string;
  updated_at: string;
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
