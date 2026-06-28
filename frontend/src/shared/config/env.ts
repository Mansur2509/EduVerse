const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const env = {
  apiBaseUrl,
  authApiBaseUrl:
    process.env.NEXT_PUBLIC_AUTH_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/auth`,
  profileApiBaseUrl:
    process.env.NEXT_PUBLIC_PROFILE_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/profile`,
  eventsApiBaseUrl:
    process.env.NEXT_PUBLIC_EVENTS_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/events`,
  organizerApiBaseUrl:
    process.env.NEXT_PUBLIC_ORGANIZER_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/organizer`,
  eventModerationApiBaseUrl:
    process.env.NEXT_PUBLIC_EVENT_MODERATION_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/admin/events`,
  roadmapApiBaseUrl:
    process.env.NEXT_PUBLIC_ROADMAP_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/roadmap`,
  essaysApiBaseUrl:
    process.env.NEXT_PUBLIC_ESSAYS_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/essays`,
  applicationsApiBaseUrl:
    process.env.NEXT_PUBLIC_APPLICATIONS_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/applications`
} as const;
