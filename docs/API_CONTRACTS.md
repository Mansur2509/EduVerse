# API Contracts

Product API base URL: `/api/v1`

Authentication API base URL: `/api/auth`

Profile API base URL: `/api/profile`

Events API base URL: `/api/events`

Organizer API base URL: `/api/organizer`

Event moderation API base URL: `/api/admin/events`

This document is an evolving Phase 1 contract. Breaking changes must update this file and the affected client types.

## Authentication

Browser API requests use JWT bearer authentication. Access tokens expire after 15 minutes; refresh tokens expire after 7 days. Refresh rotation and blacklist-after-rotation are enabled.

Send an access token as:

```http
Authorization: Bearer <access-token>
```

The Phase 1 web client stores tokens through one isolated local-storage helper. This is an MVP compromise, not the final production design. A future hardening task should move refresh credentials to Secure, HttpOnly, SameSite cookies.

### POST `/api/auth/register/`

Public. Creates a student user, `StudentProfile`, `UserPreference`, and Free `Subscription` atomically.

Request:

```json
{
  "email": "student@example.com",
  "full_name": "Student Example",
  "password": "strong password",
  "password_confirm": "strong password"
}
```

Returns HTTP 201 with `access`, `refresh`, and `user`.

### POST `/api/auth/login/`

Public. Accepts `email` and `password`. Returns `access`, `refresh`, and `user`.

### POST `/api/auth/token/refresh/`

Public to clients holding a valid refresh token. Rotates the refresh token and returns a new access token plus a new refresh token.

### POST `/api/auth/logout/`

Authenticated. Accepts a refresh token and blacklists it. The access token must be supplied in the `Authorization` header.

```json
{
  "refresh": "<refresh-token>"
}
```

Returns HTTP 204.

### GET `/api/auth/me/`

Authenticated. Returns:

```json
{
  "id": 1,
  "email": "student@example.com",
  "full_name": "Student Example",
  "role": "student",
  "profile": {
    "country": "Uzbekistan",
    "city": "Tashkent",
    "grade": "11",
    "education_status": "school student",
    "intended_major": "Computer Science",
    "scholarship_need": "unsure"
  },
  "subscription": {
    "tier": "free",
    "period_started_at": "2026-06-22T00:00:00Z",
    "ai_message_count": 0,
    "essay_review_count": 0,
    "saved_events_count": 0
  }
}
```

### PATCH `/api/auth/me/`

Authenticated. Updates `full_name` and supplied basic `profile` fields. `email`, `role`, subscription tier, and usage counters are read-only through this endpoint.

## Student profile

The profile API is self-only. It does not accept a user identifier in the URL and always resolves the profile from the authenticated request user.

### GET `/api/profile/me/`

Authenticated. Returns the student/applicant profile aggregate:

```json
{
  "id": 1,
  "email": "student@example.com",
  "role": "student",
  "full_name": "Student Example",
  "birth_date": "2008-04-12",
  "country": "Uzbekistan",
  "city": "Tashkent",
  "school_or_university": "Example Academic School",
  "grade": "11",
  "expected_graduation_year": 2027,
  "education_status": "school_student",
  "gpa": 4.5,
  "gpa_scale": 5,
  "intended_degree": "bachelor",
  "target_countries": ["United States", "Germany"],
  "intended_majors": ["Computer Science", "Economics"],
  "target_universities": ["Example University"],
  "university_unsure": false,
  "major_unsure": false,
  "scholarship_need": "yes",
  "interests": ["Research", "Debate"],
  "languages": ["Uzbek", "English", "Russian"],
  "test_scores": {
    "sat": 1450,
    "ielts": 7.5,
    "ap": ["Calculus BC: 5"]
  },
  "exam_plans": {
    "taken": ["IELTS"],
    "planned": [
      {
        "name": "SAT",
        "date": "2027-03-13",
        "target_score": "1450"
      }
    ]
  },
  "preparation_needs": ["SAT preparation"],
  "activities": {
    "extracurriculars": ["Coding club"],
    "honors": [],
    "sports": [],
    "olympiads": [],
    "research_projects": [],
    "mun_debate": [],
    "volunteering": [],
    "leadership": [],
    "work_internships": []
  },
  "essay_status": "not_yet",
  "essay_stage": "planning",
  "support_priorities": ["University research"],
  "interested_classes": ["Mathematics"],
  "ap_interests": ["Calculus"],
  "career_interests": ["Technology"],
  "research_interest": true,
  "finance_literacy_interest": true,
  "mun_debate_interest": false,
  "onboarding_sections": ["identity", "academic", "exams", "activities", "support"],
  "onboarding_version": 1,
  "onboarding_completed_at": null,
  "telegram_username": "@student_example",
  "phone": "+998 90 123 45 67",
  "updated_at": "2026-06-22T10:30:00Z"
}
```

`id`, `email`, `role`, and `updated_at` are read-only.

### PATCH `/api/profile/me/`

Authenticated. Accepts any writable subset of the profile response. Arrays must contain short text values. `test_scores` is a bounded object supporting text, numeric, or text-list values. Known numeric ranges are validated for SAT, IELTS, and TOEFL.

Example:

```json
{
  "country": "Uzbekistan",
  "city": "Tashkent",
  "intended_degree": "bachelor",
  "target_countries": ["United States"],
  "intended_majors": ["Computer Science"],
  "interests": ["Research"],
  "languages": ["Uzbek", "English"],
  "test_scores": {
    "sat": 1450
  }
}
```

Supplying `role`, `email`, or another user identifier cannot modify identity or authorization data.

### GET `/api/profile/completion/`

Authenticated. Returns a computed completion summary:

```json
{
  "percentage": 62,
  "completed_fields": 8,
  "total_fields": 13,
  "missing_fields": [
    "birth_date",
    "test_scores",
    "contact"
  ]
}
```

Completion is computed from profile data and is not stored as an authoritative score. It indicates data readiness, not admission readiness or student quality.

The response also includes mandatory onboarding state:

```json
{
  "percentage": 100,
  "completed_fields": 22,
  "total_fields": 22,
  "missing_fields": [],
  "missing_sections": [],
  "required_fields": ["full_name", "birth_date", "country"],
  "can_complete": true,
  "is_complete": false
}
```

`can_complete` means all required fields and reviewed sections are present. `is_complete` additionally requires a successful final completion action and a persisted `onboarding_completed_at`.

### GET `/api/profile/readiness/`

Authenticated. Returns a computed evidence summary, never an admission chance:

```json
{
  "stars": 4,
  "level": "strong",
  "score_components": {
    "profile": 5,
    "academics": 5,
    "exams": 4,
    "activities": 3,
    "essays": 2,
    "timeline": 4
  },
  "strengths": ["profile", "academics", "exams", "timeline"],
  "improvements": ["essays"],
  "comparison_status": "official_data_needed",
  "compared_universities": [],
  "official_sources": []
}
```

`comparison_status=published_ranges` is returned only when matching published university requirements can be compared with available profile evidence. Clients must retain the no-guarantee disclaimer and link any returned official sources.

### POST `/api/profile/complete-onboarding/`

Authenticated. Marks onboarding complete only when `can_complete=true`. Returns the updated completion response. Incomplete submissions return HTTP 400 with `missing_fields` and `missing_sections`.

## Common behavior

- JSON fields use `snake_case`.
- Timestamps use ISO 8601 UTC.
- List endpoints use `count`, `next`, `previous`, and `results`.
- Product reads require authentication, including published universities, events, exams, and questions.
- Writes are denied unless the endpoint and role explicitly allow them.

## Events and registration

Authenticated student event reads return only events with `status=published` and `visibility=public`. Organizer/admin workflows use the stable `/api/organizer/` and `/api/admin/events/` contracts; the legacy management router is compatibility-only.

### GET `/api/events/`

Authenticated. Returns a paginated event catalog ordered by start time. Each event may include the current user's `registration_status`.

Supported query parameters:

- `search`
- `category` — category slug
- `country`
- `city`
- `price_type`
- `format`
- `is_online`

Example item:

```json
{
  "id": 1,
  "title": "EduVerse Demo Planning Workshop",
  "slug": "eduverse-demo-planning-workshop",
  "short_description": "A fictional workshop for testing event discovery and registration.",
  "description": "Fictional local development event...",
  "category": {
    "name": "Workshop",
    "slug": "workshop"
  },
  "organizer_name": "EduVerse Demo Organizer",
  "location": {
    "country": "Uzbekistan",
    "city": "Tashkent",
    "venue": "Demo Academic Center",
    "latitude": null,
    "longitude": null
  },
  "is_online": true,
  "online_url": "https://example.com/eduverse-demo-planning-workshop",
  "format": "hybrid",
  "start_at": "2026-08-06T10:00:00Z",
  "end_at": "2026-08-06T12:00:00Z",
  "registration_deadline": "2026-07-22T10:00:00Z",
  "capacity": 40,
  "registration_count": 3,
  "spots_left": 37,
  "price_type": "free",
  "price_amount": null,
  "currency": "",
  "status": "published",
  "visibility": "public",
  "language": "English",
  "eligibility": "Demonstration only",
  "source": {
    "source_title": "Fictional demonstration source",
    "source_url": "https://example.com/eduverse-demo-planning-workshop",
    "is_official": false,
    "retrieved_at": "2026-06-22T10:00:00Z"
  },
  "registration_status": null
}
```

### GET `/api/events/{slug}/`

Authenticated. Returns one published public event or HTTP 404.

### POST `/api/events/{slug}/register/`

Authenticated and scoped-throttled. Creates an active registration and snapshots the user's current profile/contact data. Rejects duplicate active registration, unpublished/private/cancelled events, passed deadlines, started events, and full capacity.

No request body is required.

Returns HTTP 201 for a new registration or HTTP 200 when a previously cancelled registration is reactivated.

```json
{
  "id": 10,
  "event": {},
  "status": "registered",
  "payment_status": "not_required",
  "registration_data": {
    "full_name": "Student Example",
    "country": "Uzbekistan",
    "intended_majors": ["Computer Science"]
  },
  "contact_snapshot": {
    "email": "student@example.com",
    "telegram_username": "@student_example",
    "phone": "+998 90 123 45 67"
  },
  "created_at": "2026-06-22T10:00:00Z",
  "updated_at": "2026-06-22T10:00:00Z"
}
```

Registration and contact snapshots are private and are returned only to the owning authenticated user through registration endpoints.

### POST or DELETE `/api/events/{slug}/cancel-registration/`

Authenticated and scoped-throttled. Changes the current user's active `registered` or `waitlisted` registration to `cancelled`.

### GET `/api/events/my-registrations/`

Authenticated. Returns the current user's active registered, waitlisted, or attended events.

## Organizer event management

Organizer endpoints require an authenticated `organizer` or `admin` role. Organizers only receive their own events; administrators may manage any event. Creating an event always creates a `draft`. Public publication is impossible through organizer endpoints.

Lifecycle:

```text
draft -> pending_review -> published
                    `----> rejected -> pending_review
published -> cancelled
draft/pending_review/rejected -> archived
admin may archive any non-archived event
```

### GET/POST `/api/organizer/events/`

GET returns organizer-owned events with moderation capabilities. POST creates a draft. The write payload uses canonical timestamps and nested location/source records:

```json
{
  "title": "Student Research Workshop",
  "short_description": "A practical research planning workshop.",
  "description": "Complete event description.",
  "category_slug": "workshop",
  "organizer_name": "Example Academic Center",
  "format": "hybrid",
  "is_online": true,
  "online_url": "https://example.com/live",
  "start_at": "2026-09-10T09:00:00Z",
  "end_at": "2026-09-10T12:00:00Z",
  "registration_deadline": "2026-09-08T18:00:00Z",
  "capacity": 50,
  "price_type": "free",
  "price_amount": null,
  "currency": "",
  "visibility": "public",
  "cover_image_url": "",
  "language": "English",
  "eligibility": "Secondary school and university students",
  "location": {
    "country": "Uzbekistan",
    "city": "Tashkent",
    "venue": "Example Academic Center",
    "latitude": null,
    "longitude": null
  },
  "source": {
    "source_title": "Official organizer page",
    "source_url": "https://example.com/research-workshop",
    "is_official": true
  }
}
```

Responses include `status`, `moderation_note`, `can_edit`, `can_submit`, and `can_view_participants`. Slugs and ownership are server-controlled.

### GET/PATCH `/api/organizer/events/{slug}/`

Returns or updates an organizer-owned event. Organizers may edit `draft`, `pending_review`, and `rejected` events. `organizer`, slug, lifecycle status, and moderation data are read-only.

### POST `/api/organizer/events/{slug}/submit/`

Transitions `draft` or `rejected` to `pending_review`, creates or refreshes `EventSubmission`, and writes a moderation log.

### POST `/api/organizer/events/{slug}/cancel/`

Cancels an organizer-owned published event. Cancelled events immediately leave the public catalog.

### POST `/api/organizer/events/{slug}/archive/`

Archives an organizer-owned draft, pending, or rejected event.

### GET `/api/organizer/events/{slug}/registrations/`

Available only for organizer-owned published events. Returns privacy-limited participant records:

```json
{
  "id": 12,
  "full_name": "Student Example",
  "email": "student@example.com",
  "telegram_username": "@student_example",
  "status": "registered",
  "payment_status": "not_required",
  "created_at": "2026-06-22T10:00:00Z"
}
```

Phone, academic profile data, raw `registration_data`, and raw `contact_snapshot` are not returned.

### GET `/api/organizer/event-categories/`

Returns available category names and slugs for the organizer event form.

## Event moderation

All moderation endpoints require an admin role. A moderator cannot approve or reject an event they own.

- `GET /api/admin/events/pending/` lists pending submissions.
- `POST /api/admin/events/{slug}/approve/` publishes a pending event.
- `POST /api/admin/events/{slug}/reject/` rejects a pending event and requires `{"reason": "..."}`.
- `POST /api/admin/events/{slug}/archive/` archives an event.
- `GET /api/admin/events/{slug}/logs/` returns status history, actor email, note, and timestamp.

## Endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/auth/register/` | Public | Register student and issue JWT pair |
| POST | `/api/auth/login/` | Public | Login with email/password |
| POST | `/api/auth/logout/` | Authenticated | Blacklist refresh token |
| POST | `/api/auth/token/refresh/` | Refresh token holder | Rotate JWT pair |
| GET/PATCH | `/api/auth/me/` | Authenticated | Current user, basic profile, and plan |
| GET/PATCH | `/api/profile/me/` | Authenticated | Current user's full student profile |
| GET | `/api/profile/completion/` | Authenticated | Computed profile data completion |
| GET | `/api/profile/readiness/` | Authenticated | Evidence-based 1–5 readiness summary; never an admission probability |
| POST | `/api/profile/complete-onboarding/` | Authenticated | Finalize mandatory onboarding when requirements are satisfied |
| GET | `/api/events/` | Authenticated | Published public event catalog |
| GET | `/api/events/{slug}/` | Authenticated | Published public event detail |
| POST | `/api/events/{slug}/register/` | Authenticated | Register using a profile/contact snapshot |
| POST/DELETE | `/api/events/{slug}/cancel-registration/` | Authenticated | Cancel own active registration |
| GET | `/api/events/my-registrations/` | Authenticated | List own active registrations |
| GET/POST | `/api/organizer/events/` | Organizer/admin | List managed events or create a draft |
| GET/PATCH | `/api/organizer/events/{slug}/` | Owner/admin | Read or update an editable event |
| POST | `/api/organizer/events/{slug}/submit/` | Owner/admin | Submit draft or rejected event |
| GET | `/api/organizer/events/{slug}/registrations/` | Owner/admin | Privacy-limited participant list |
| POST | `/api/organizer/events/{slug}/cancel/` | Owner/admin | Cancel a published event |
| POST | `/api/organizer/events/{slug}/archive/` | Owner/admin | Archive an unpublished event |
| GET | `/api/admin/events/pending/` | Admin | Moderation queue |
| POST | `/api/admin/events/{slug}/approve/` | Admin, not owner | Publish pending event |
| POST | `/api/admin/events/{slug}/reject/` | Admin, not owner | Reject with required reason |
| POST | `/api/admin/events/{slug}/archive/` | Admin | Archive event |
| GET | `/api/admin/events/{slug}/logs/` | Admin | Read moderation history |
| GET | `/health/` | Public | Service health |
| GET | `/api/v1/universities/` | Authenticated | University catalog, search/filter; excludes `is_demo=true` records unless `?include_demo=true` |
| GET | `/api/v1/universities/{slug}/` | Authenticated | University detail: stats, programs, scholarships, sources, `field_verifications` |
| GET | `/api/v1/universities/{slug}/fit/` | Authenticated | Admissions fit analysis (Reach/Competitive/Target/Safety) from the caller's profile and this university's verified stats only |
| POST/DELETE | `/api/v1/universities/{slug}/shortlist/` | Authenticated | Add/remove this university from the caller's shortlist |
| GET | `/api/v1/universities/shortlist/` | Authenticated | List the caller's shortlisted universities |
| GET | `/api/v1/universities/compare/?ids=1,2,3` | Authenticated | Side-by-side detail for 2-4 universities by id |
| GET | `/api/roadmap/` | Authenticated | Caller's active roadmap plan and tasks, or `{"plan": null}` if none generated yet |
| POST | `/api/roadmap/generate/` | Authenticated | Generate or refresh the caller's roadmap from current profile/shortlist/exam data |
| GET/POST | `/api/roadmap/tasks/` | Authenticated | List caller's tasks (filters: `status`, `category`, `priority`, `linked_university`, `due_before`, `due_after`) or create a manual task |
| GET/PATCH/DELETE | `/api/roadmap/tasks/{id}/` | Authenticated, self-only | Read/update any own task; delete only `source_type=manual` tasks (others return 400 — skip instead) |
| POST | `/api/roadmap/tasks/{id}/complete/` | Authenticated, self-only | Mark a task completed and stamp `completed_at` |
| POST | `/api/roadmap/tasks/{id}/skip/` | Authenticated, self-only | Mark a task skipped without deleting it |
| GET/POST | `/api/essays/` | Authenticated, self-only | List caller's essay workspaces or create one |
| GET/PATCH/DELETE | `/api/essays/{id}/` | Authenticated, self-only | Read/update/delete an essay workspace |
| GET/POST | `/api/essays/{id}/feedback/` | Authenticated, self-only | Read latest feedback, or generate new rule-based feedback (creates `EssayFeedback` + revision tasks) |
| POST | `/api/essays/{id}/revision-tasks/` | Authenticated, self-only | Add a manual revision task to an essay |
| GET/PATCH | `/api/essays/revision-tasks/{id}/` | Authenticated, self-only | Read/update a revision task's title/description/category/status |
| GET/POST | `/api/applications/` | Authenticated, self-only | List caller's application tracker items or start tracking a university |
| GET/PATCH/DELETE | `/api/applications/{id}/` | Authenticated, self-only | Read/update/delete an application tracker item (filters: `status`, `university`) |
| GET/POST | `/api/applications/{id}/milestones/` | Authenticated, self-only | List or add milestones for an application |
| GET/PATCH | `/api/applications/milestones/{id}/` | Authenticated, self-only | Read/update a milestone, optionally linking to one of the caller's own roadmap tasks |
| GET/PATCH/POST | `/api/v1/events/...` | Role-dependent | Legacy organizer/admin management router |
| GET/PATCH | `/profiles/me/` | Student | Legacy compatibility route under `/api/v1`; prefer `/api/profile/me/` |
| GET | `/subscriptions/me/` | Authenticated | Current plan and counters |
| GET | `/exams/` | Authenticated | Published exam catalog |
| GET | `/questions/` | Authenticated | Published original demo questions |
| POST | `/ai/mentor/` | Authenticated | Placeholder; provider integration deferred |

## University source fields

University records carry two complementary sourcing mechanisms:

- `data_sources[]` (existing) — page-level citations for the institution as a whole: `source_url`, `source_title`, `published_at` when known, `retrieved_at`, `is_official`. Used as the fit analysis's `source_notes` fallback.
- `field_verifications[]` (added for real, source-backed universities) — per-field sourcing for any non-null admissions/stat/cost/deadline value: `field_name`, `status` (`verified` | `partial` | `estimated`), `source_url`, `last_verified_date`, `note`. A field with a non-null value but no matching `field_verifications` entry should not occur for real universities (enforced by a seed-data integrity test); demo/fictional universities never carry verification records.

Any University field with no confirmed source is left `null`/blank and rendered client-side as "Not verified yet" — it is never displayed as zero or guessed. `is_demo: true` marks clearly-fictional development records (see `docs/DECISIONS.md`); the default catalog list excludes them.

`international_office_url` and `virtual_info_session_url` are identity-ish contact links (same exemption as `admissions_url`/`financial_aid_url`/`application_portal_url`) shown on the university detail page's Contact tab; they do not require a `field_verifications` entry and are simply blank when unknown.

The admissions fit analysis (`/api/v1/universities/{slug}/fit/`) only ever compares `acceptance_rate`, `gpa_average`, and `sat_average` against the caller's profile. It returns `category: null` when none of those three are verified for either side, and adds a `limited_data_for_category` next-action when a category is assigned from only one of the three. It never uses the words "probability", "chance", or "percentage"; response keys and UI copy use "fit", "category" (`reach`/`competitive`/`target`/`safety`), "strengths", "risks", "missing_fields", and "next_actions" instead.

## Roadmap response shapes

`GET /api/roadmap/` and `POST /api/roadmap/generate/` both nest the plan under a `plan` key (`{"plan": {...} | null, ...}`) rather than returning a flat plan object, so the frontend has one consistent shape to check regardless of whether a roadmap exists yet:

- `GET /api/roadmap/` → `{"detail": "...", "plan": RoadmapPlan | null}`.
- `POST /api/roadmap/generate/` → `{"plan": RoadmapPlan, "missing_data_warnings": string[]}`. The warnings (e.g. `no_graduation_year`, `no_shortlisted_universities`) are also persisted on `plan.readiness_snapshot.missing_data_warnings` so they reappear on the next plain `GET` without needing to regenerate.

Each `RoadmapTask` always reports `generated_reason`, `evidence_note`, and `source_url` (empty string when no official source backs the task) so the UI can show why a task exists and where its claim comes from without a second request. `source_type` distinguishes a real verified deadline (`university_deadline`) from a generated/estimated one (`generated`) — never both implied at once.

The generator additionally reads (read-only) the caller's own `EssayWorkspace` records: any essay with `status` in `not_started`/`needs_revision` produces a `category=essays`, `source_type=essay_status` task (dedup key `essay_workspace:{id}:{status}`), with `due_date`/`source_url` populated from the linked university's verified `application_deadline` when one exists. This requires no schema change to `roadmap_service` — it is a plain cross-service query, the same pattern already used for `user_profile_service`/`university_service`/`event_service`.

## Essay workspace response shapes

`EssayWorkspace` embeds its own `latest_feedback` (most recent `EssayFeedback`, or `null`) and `revision_tasks[]` so the frontend can render the editor, feedback panel, and checklist from one request.

`POST /api/essays/{id}/feedback/` runs the deterministic rule engine in `services/essay_service/feedback_engine.py` (word count, word-limit status, generic-language detection, paragraph structure, specificity, prompt-fit for why-school/why-major types, sentence-length grammar proxy) and returns `{"detail": "", "feedback": EssayFeedback, "essay": EssayWorkspace}`. It also creates/refreshes `EssayRevisionTask` rows: an existing `todo` task in the same `category` is updated in place rather than duplicated, while `completed`/`skipped` tasks are left untouched as history. No endpoint generates, writes, or rewrites essay text — every response is feedback and checklist items only.

## Application tracker response shapes

`ApplicationTrackerItem` embeds its `milestones[]`. Creating an application only requires `university`; all status fields (`status`, `essays_status`, `recommendations_status`, `test_scores_status`, `documents_status`, `financial_aid_status`) default to their "not started" equivalents — the API never auto-advances a status. A second `POST` for the same `(user, university)` pair returns 400. `ApplicationMilestone.linked_roadmap_task` is optional and validated to belong to the caller; it lets a milestone point at an existing roadmap task without `application_service` owning or duplicating roadmap data.

## Error behavior

Validation errors return HTTP 400 with field-level details. Permission failures return 403, missing authentication returns 401/403 depending on authentication mechanism, missing resources return 404, and throttling returns 429.

## Required disclaimers

Clients must show module-specific admissions, event, essay, finance, and AI disclaimers defined in `docs/PRODUCT_SPEC.md`. The backend should return disclaimer identifiers or text for generated guidance in Phase 1.
