export type RoadmapCategory =
  | "profile"
  | "exams"
  | "essays"
  | "universities"
  | "scholarships"
  | "activities"
  | "research"
  | "portfolio"
  | "deadlines"
  | "events"
  | "recommendations";

export type RoadmapPriority = "low" | "medium" | "high" | "urgent";

export type RoadmapStatus = "todo" | "in_progress" | "completed" | "skipped";

export type RoadmapSourceType =
  | "generated"
  | "manual"
  | "university_deadline"
  | "profile_gap"
  | "fit_analysis"
  | "essay_status"
  | "exam_plan"
  | "planning_window"
  | "event"
  | "cached_assessment";

export type RoadmapTaskKind = "manual" | "generated";

export type RoadmapEstimatedEffort = "short" | "medium" | "long";

export type RoadmapTask = {
  id: number;
  title: string;
  description: string;
  category: RoadmapCategory;
  priority: RoadmapPriority;
  status: RoadmapStatus;
  due_date: string | null;
  source_type: RoadmapSourceType;
  linked_university: number | null;
  linked_university_name: string | null;
  linked_university_slug: string | null;
  linked_program: number | null;
  linked_application: number | null;
  linked_application_university_name: string | null;
  linked_event: number | null;
  linked_event_title: string | null;
  linked_event_slug: string | null;
  linked_profile_section: string;
  linked_score_dimension: string;
  estimated_effort: RoadmapEstimatedEffort;
  generated_reason: string;
  evidence_note: string;
  source_url: string;
  task_kind: RoadmapTaskKind;
  is_timeline_marker: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type RoadmapReadinessSnapshot = {
  missing_data_warnings: string[];
  shortlisted_count: number;
  total_tasks: number;
  urgent_tasks: number;
  completed_tasks: number;
  new_tasks_added: number;
};

export type RoadmapPlan = {
  id: number;
  title: string;
  cycle_year: number | null;
  target_country: string;
  primary_goal: string;
  generated_at: string;
  last_refreshed_at: string;
  summary: string;
  readiness_snapshot: RoadmapReadinessSnapshot;
  active: boolean;
  tasks: RoadmapTask[];
};

export type RoadmapPlanResponse = {
  detail: string;
  plan: RoadmapPlan | null;
};

export type GenerateRoadmapResponse = {
  plan: RoadmapPlan;
  missing_data_warnings: string[];
};

export type RoadmapTaskFilters = {
  status?: string;
  category?: string;
  priority?: string;
  linked_university?: string;
  linked_application?: string;
  source_type?: string;
  task_kind?: RoadmapTaskKind | "";
  exam?: string;
  due_before?: string;
  due_after?: string;
  view?: "list" | "timeline" | "";
};

export type ManualRoadmapTaskInput = {
  title: string;
  description?: string;
  category: RoadmapCategory;
  priority?: RoadmapPriority;
  due_date?: string | null;
};

export type RoadmapTaskUpdateInput = Partial<{
  title: string;
  description: string;
  due_date: string | null;
  status: RoadmapStatus;
  priority: RoadmapPriority;
  category: RoadmapCategory;
}>;

export type PaginatedResponse<Item> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Item[];
};

const WEEK_WINDOW_DAYS = 7;
const MONTH_WINDOW_DAYS = 30;

export type RoadmapBucket = "this_week" | "this_month" | "later" | "completed";

export function bucketForTask(task: RoadmapTask, today: Date): RoadmapBucket {
  if (task.status === "completed" || task.status === "skipped") {
    return "completed";
  }
  if (!task.due_date) {
    return "later";
  }
  const due = new Date(`${task.due_date}T00:00:00`);
  const days = Math.ceil((due.getTime() - today.getTime()) / 86_400_000);
  if (days <= WEEK_WINDOW_DAYS) {
    return "this_week";
  }
  if (days <= MONTH_WINDOW_DAYS) {
    return "this_month";
  }
  return "later";
}

export { RoadmapTaskCard } from "./ui/roadmap-task-card";
