export type NotificationType =
  | "deadline_upcoming"
  | "exam_date_upcoming"
  | "roadmap_task_due_soon"
  | "recommendation_missing"
  | "essay_missing"
  | "essay_review_completed"
  | "event_registration_confirmed"
  | "event_starting_soon"
  | "organizer_event_approved"
  | "organizer_event_rejected";

export type NotificationPriority = "low" | "normal" | "high" | "urgent";

export type NotificationStatus = "unread" | "read" | "archived";

export type Notification = {
  id: number;
  notification_type: NotificationType;
  title: string;
  message: string;
  priority: NotificationPriority;
  status: NotificationStatus;
  action_url: string;
  related_entity_type: string;
  related_entity_id: number | null;
  scheduled_for: string | null;
  sent_at: string | null;
  created_at: string;
};

export type NotificationPreference = {
  deadlines_enabled: boolean;
  exams_enabled: boolean;
  roadmap_enabled: boolean;
  recommendations_essays_enabled: boolean;
  essay_reviews_enabled: boolean;
  events_enabled: boolean;
  organizer_events_enabled: boolean;
  updated_at: string;
};

export type NotificationPreferenceInput = Partial<
  Omit<NotificationPreference, "updated_at">
>;

export type PaginatedResponse<Item> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Item[];
};
