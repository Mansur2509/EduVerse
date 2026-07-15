export type UserAnalytics = {
  profile_completion_percent: number;
  roadmap_tasks_completed: number;
  roadmap_tasks_total: number;
  applications_by_status: Record<string, number>;
  essay_reviews_count: number;
  upcoming_deadlines_count: number;
  activity_by_type: Record<string, number>;
};

export type AdminAnalyticsSummary = {
  total_users: number;
  new_users_7d: number;
  new_users_30d: number;
  active_users_7d: number;
  active_users_30d: number;
  applications_created_total: number;
  universities_shortlisted_total: number;
  essay_reviews_requested_total: number;
  roadmap_generations_total: number;
  event_registrations_total: number;
  organizer_events_created_total: number;
  retained_users_2plus_actions: number;
  onboarding_completion_rate_percent: number;
};

export type AdminFeatureUsage = Record<string, number>;

export type AdminAnalyticsActivity = {
  daily_event_counts: Record<string, number>;
};
