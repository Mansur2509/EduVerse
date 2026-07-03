// The DRF default router (universities, exams, profiles, subscriptions) is
// mounted under `/api/v1/`, so `apiBaseUrl` MUST end with `/api/v1`. A real
// production incident came from setting NEXT_PUBLIC_API_BASE_URL to the bare
// backend origin (e.g. `https://eduverse-vvw2.onrender.com`) without that
// suffix: every `base: "api"` call (e.g. the university catalog) then hit
// `<origin>/universities/` and 404'd, while auth/events/roadmap/essays/etc kept
// working because they are rebuilt from `new URL(apiBaseUrl).origin` below.
// Normalize defensively so the catalog loads regardless of how the env var is
// set: keep a value that already ends with `/api/v1`, otherwise force the
// origin + `/api/v1`.
function normalizeApiBaseUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, "");
  if (/\/api\/v1$/.test(trimmed)) {
    return trimmed;
  }
  try {
    return `${new URL(trimmed).origin}/api/v1`;
  } catch {
    // Not an absolute URL (shouldn't happen in practice) — fall back to the
    // documented local default rather than throwing at module load.
    return "http://localhost:8000/api/v1";
  }
}

const apiBaseUrl = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"
);

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
    `${new URL(apiBaseUrl).origin}/api/applications`,
  suggestionsApiBaseUrl:
    process.env.NEXT_PUBLIC_SUGGESTIONS_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/suggestions`,
  universityImportApiBaseUrl:
    process.env.NEXT_PUBLIC_UNIVERSITY_IMPORT_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/admin/university-import`,
  feedbackApiBaseUrl:
    process.env.NEXT_PUBLIC_FEEDBACK_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/feedback`,
  adminFeedbackApiBaseUrl:
    process.env.NEXT_PUBLIC_ADMIN_FEEDBACK_API_BASE_URL ??
    `${new URL(apiBaseUrl).origin}/api/admin/feedback`
} as const;
