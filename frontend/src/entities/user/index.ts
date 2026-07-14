export type UserRole = "student" | "organizer" | "admin";

export type UserProfile = {
  country: string;
  city: string;
  grade: string;
  education_status: string;
  intended_major: string;
  scholarship_need: "yes" | "no" | "unsure";
};

export type UserSubscription = {
  tier: "free" | "starter" | "growth" | "premium";
  period_started_at: string;
  ai_message_count: number;
  essay_review_count: number;
  saved_events_count: number;
};

export type CurrentUser = {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  google_linked: boolean;
  profile: UserProfile;
  subscription: UserSubscription;
};

export type AuthResponse = {
  access: string;
  user: CurrentUser;
};

export type LoginInput = {
  email: string;
  password: string;
};

export type RegisterInput = LoginInput & {
  full_name: string;
  password_confirm: string;
};

export type UpdateCurrentUserInput = {
  full_name?: string;
  profile?: Partial<UserProfile>;
};
