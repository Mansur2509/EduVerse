# API Contracts

Product API base URL: `/api/v1`

Authentication API base URL: `/api/auth`

Profile API base URL: `/api/profile`

Profile assessment API base URL: `/api/profile/assessment`

Events API base URL: `/api/events`

Organizer API base URL: `/api/organizer`

Event moderation API base URL: `/api/admin/events`

University import API base URL: `/api/admin/university-import`

Suggestions API base URL: `/api/suggestions`

This document is an evolving Phase 1 contract. Breaking changes must update this file and the affected client types.

## Authentication

Browser API requests use JWT bearer authentication. Access tokens expire after 15 minutes; refresh tokens expire after 7 days. Refresh rotation and blacklist-after-rotation are enabled.

Send an access token as:

```http
Authorization: Bearer <access-token>
```

The browser keeps the short-lived access token in memory. The refresh token is
issued only as a `Secure` (production), `HttpOnly`, scoped SameSite cookie and is
not returned in new register/login/refresh JSON bodies. Cross-tab logout uses a
non-secret browser signal; it never shares a token. Refresh/logout requests
using the ambient cookie validate `Origin`/fetch-site against the configured
allowlist. A body refresh token is accepted only as transitional compatibility
for sessions issued before this migration.

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

Returns HTTP 201 with `access` and `user`, and sets the refresh cookie.

### POST `/api/auth/login/`

Public. Accepts `email` and `password`. Returns `access` and `user`, and sets the
refresh cookie. Invalid credentials use a generic response.

### POST `/api/auth/token/refresh/`

Public to clients holding a valid refresh cookie. Rotates/blacklists the old
refresh token, returns a new access token, and replaces the HttpOnly cookie.

### POST `/api/auth/logout/`

Authenticated. Reads and blacklists the refresh cookie, clears it, and returns
HTTP 204. The access token must be supplied in the `Authorization` header.

### GET `/api/auth/google/start/`

Public, throttled. Starts Google Authorization Code flow with state, nonce, and
S256 PKCE, stores only a signed HttpOnly short-lived state cookie, and redirects
to Google. The client secret is never returned to the browser.

### GET `/api/auth/google/callback/`

Public, throttled provider callback. Consumes state exactly once, exchanges the
code server-side, verifies issuer/audience/expiry/nonce/subject/verified email,
links only safe active student accounts, sets the normal refresh cookie, and
redirects to the single configured frontend result URL. Cancellation, conflict,
blocked, invalid, and unavailable outcomes use controlled result codes; no
caller-supplied redirect is accepted.

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
  "original_gpa_value": 4.5,
  "original_gpa_scale": 5,
  "original_gpa_scale_type": "five_point",
  "normalized_gpa_4": 3.6,
  "normalized_percentage": null,
  "curriculum_type": "national",
  "curriculum_country": "Uzbekistan",
  "academic_normalization_confidence": "high",
  "academic_normalization_note": "Converted proportionally from a 5.0 GPA scale.",
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
        "exam_type": "SAT",
        "date": "2027-03-13",
        "target_score": "1450",
        "current_score": "1320",
        "planned_retake": true,
        "planned_retake_month": "2027-03",
        "test_status": "preparing"
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

Academic comparison must use the normalized fields when confidence is high or medium. Raw GPA fields (`original_gpa_value`, `original_gpa_scale`, `original_gpa_scale_type`) preserve the student's source record; `normalized_gpa_4` is the comparable 4.0-scale value (for example, `4.8/5.0 -> 3.84/4.0`) and must never be confused with the raw score. Unsupported or ambiguous systems keep `normalized_gpa_4=null` with a low-confidence note.

### PATCH `/api/profile/me/`

Authenticated. Accepts any writable subset of the profile response. Arrays remain bounded by item count and field-appropriate item length: taxonomy-like fields such as target countries and languages stay short, university/major/class names allow normal names, and onboarding activity, preparation, support, and career entries allow normal admissions-detail text while still rejecting spam-length values. `test_scores` is a bounded object supporting text, numeric, or text-list values. Known numeric ranges are validated for SAT, IELTS, and TOEFL.

GPA writes should include `original_gpa_value`, `original_gpa_scale`, and `original_gpa_scale_type` where possible. `exam_plans.planned[]` may include `exam_type`, `current_score`, `planned_retake`, `planned_retake_month`, and `test_status`; SAT/AP official-date guidance is generated only from verified `OfficialExamDate` records, not from guessed dates.

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

Authenticated. Returns a computed evidence summary, never an admissions outcome estimate:

```json
{
  "stars": 2,
  "level": "developing",
  "score_components": {
    "academic_readiness": 5,
    "testing_readiness": 4,
    "activities_leadership": 2,
    "honors_competitions": 1,
    "research_portfolio": 1,
    "application_execution": 2
  },
  "categories": [
    {
      "key": "academic_readiness",
      "score": 5,
      "source_keys": ["profile", "academics", "timeline"],
      "missing_sources": [],
      "status": "excellent"
    }
  ],
  "strengths": ["academic_readiness", "testing_readiness"],
  "improvements": ["honors_competitions", "research_portfolio", "application_execution"],
  "reasons": ["evidence_incomplete", "academically_promising_evidence_incomplete"],
  "next_actions": ["honors_competitions", "research_portfolio", "application_execution"],
  "cap_reason": "evidence_incomplete",
  "comparison_status": "official_data_needed",
  "compared_universities": [],
  "official_sources": []
}
```

Readiness is deterministic across six category groups: academic readiness, testing readiness, activities/leadership, honors/competitions, research/portfolio, and application execution. `stars` is capped when the foundation profile is incomplete or when too many evidence categories are missing, so a high GPA/test profile is not labeled strong without supporting application evidence. `comparison_status=published_ranges` is returned only when matching published university requirements can be compared with available profile evidence. Clients must retain the no-guarantee disclaimer and link any returned official sources.

### GET `/api/profile/assessment/latest/`

Authenticated and self-only. Returns the caller's latest cached AI-assisted profile-readiness assessment, or a safe empty state if no assessment exists. This endpoint never calls the AI provider.

```json
{
  "assessment": {
    "id": 1,
    "assessment_version": "2026-07-profile-v1",
    "overall_profile_score": 72,
    "category_scores": {
      "profile_evidence_score": 7,
      "activities_score": 6,
      "honors_olympiads_score": 5,
      "research_experience_score": 8,
      "portfolio_score": 6,
      "subject_passion_score": 8,
      "curiosity_score": 8,
      "originality_score": 7,
      "leadership_score": 7,
      "community_impact_score": 6,
      "research_fit_score": 8,
      "olympiads_score": 4
    },
    "confidence": "medium",
    "public_summary": "Short user-facing summary based on saved profile data.",
    "evidence_used": ["structured activities", "research projects"],
    "missing_data": ["more proof links"],
    "improvement_areas": ["document project impact"],
    "target_context_used": true,
    "expires_at": "2027-07-03T00:00:00Z",
    "is_stale": false,
    "created_at": "2026-07-03T00:00:00Z"
  },
  "cached": true,
  "reason": "latest_assessment",
  "can_refresh": false,
  "next_available_at": null,
  "ai_available": true,
  "disclaimer": "This is a profile-readiness estimate based on saved UniWay profile data. It is not an admissions decision and does not promise an outcome."
}
```

Public student-visible fields are limited to the overall score, category scores, confidence, summary, missing data, improvement areas, target-context flag, and timestamps. Internal keywords, category rationales, raw AI output, and the profile snapshot hash are not returned to students.

### POST `/api/profile/assessment/run/`

Authenticated, self-only, and scoped by the `ai` throttle. Runs assessment only when provider access is enabled, the Gemini API key is configured, and the daily limit allows it. If the current `profile_snapshot_hash` matches the latest valid assessment, the endpoint returns the cached assessment instead of calling AI.

Response envelope matches `latest/`. `reason` is one of:

- `no_previous_assessment`
- `profile_changed`
- `unchanged_cached`
- `daily_limit_reached`
- `ai_unavailable`
- `validation_failed`

The backend sends a compact sanitized profile summary only: no passwords, payment data, phone number, Telegram username, email, proof URLs, or raw essay text. Raw provider output is accepted only if it validates against the fixed profile-assessment JSON schema, uses integer category scores in range, returns at most 20 compact internal keywords, and contains no admission chance/probability/odds/guarantee wording.

### POST `/api/admin/users/{id}/profile-assessment/run/`

Admin-only force reassessment endpoint. It uses the same validation and storage path as the self-service endpoint but bypasses the normal daily-refresh guard for operational review. Students and organizers receive HTTP 403.

### POST `/api/profile/complete-onboarding/`

Authenticated. Marks onboarding complete only when `can_complete=true`. Returns the updated completion response. Incomplete submissions return HTTP 400 with `missing_fields` and `missing_sections`.

## Common behavior

- JSON fields use `snake_case`.
- Timestamps use ISO 8601 UTC.
- List endpoints use `count`, `next`, `previous`, and `results`.
- Paginated list endpoints accept `page` and `page_size`; the shared backend cap remains `max_page_size=100`. The frontend uses `page_size=21` for standard card/list pages so desktop grids show up to 3 columns x 7 rows per page.
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
  "title": "UniWay Demo Planning Workshop",
  "slug": "uniway-demo-planning-workshop",
  "short_description": "A fictional workshop for testing event discovery and registration.",
  "description": "Fictional local development event...",
  "category": {
    "name": "Workshop",
    "slug": "workshop"
  },
  "organizer_name": "UniWay Demo Organizer",
  "location": {
    "country": "Uzbekistan",
    "city": "Tashkent",
    "venue": "Demo Academic Center",
    "latitude": null,
    "longitude": null
  },
  "is_online": true,
  "online_url": "https://example.com/uniway-demo-planning-workshop",
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
    "source_url": "https://example.com/uniway-demo-planning-workshop",
    "is_official": false,
    "retrieved_at": "2026-06-22T10:00:00Z"
  },
  "registration_status": null
}
```

### GET `/api/events/{slug}/`

Authenticated. Returns one published public event or HTTP 404. Detail responses include organizer-defined `registration_form_fields` ordered by `order`. If the current user already has an active registration with a ticket, `registration_ticket` is included for that user only.

### POST `/api/events/{slug}/register/`

Authenticated and scoped-throttled. Creates an active registration and snapshots the user's current profile/contact data. Rejects duplicate active registration, unpublished/private/cancelled events, passed deadlines, started events, and full capacity.

No request body is required unless the event defines custom registration fields. When custom fields exist, answers are submitted by field id:

```json
{
  "answers": {
    "14": "student@example.com",
    "15": ["Research", "Debate"]
  }
}
```

Required organizer-defined fields are validated before the registration is accepted.

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
  "ticket": {
    "code": "EVT-A1B2C3D4",
    "status": "active",
    "issued_at": "2026-06-22T10:00:00Z",
    "checked_in_at": null
  },
  "answers": [
    {
      "field": 14,
      "field_label": "Contact email",
      "value": "student@example.com"
    }
  ],
  "created_at": "2026-06-22T10:00:00Z",
  "updated_at": "2026-06-22T10:00:00Z"
}
```

Registration and contact snapshots are private and are returned only to the owning authenticated user through registration endpoints.

### POST or DELETE `/api/events/{slug}/cancel-registration/`

Authenticated and scoped-throttled. Changes the current user's active `registered` or `waitlisted` registration to `cancelled`.

### GET `/api/events/my-registrations/`

Authenticated. Returns the current user's active registered, waitlisted, or attended events.

### GET `/api/events/participation-records/`

Authenticated. Returns the current user's verified event participation records, including event title, event slug, verification status, verified timestamp, and optional certificate URL.

### GET `/api/events/my-notifications/`

Authenticated. Returns recent internal event notifications for the current user. These records are an in-app notification foundation only; they do not send external Telegram, email, or SMS messages.

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

### GET `/api/organizer/events/analytics/`

Returns aggregate metrics for organizer-owned events: total events, published count, registrations, checked-in registrations, and attendance rate.

### GET/PATCH `/api/organizer/events/{slug}/`

Returns or updates an organizer-owned event. Organizers may edit `draft`, `pending_review`, and `rejected` events. `organizer`, slug, lifecycle status, and moderation data are read-only.

### GET/PUT `/api/organizer/events/{slug}/form/`

Returns or replaces the event's custom registration form fields. Only draft, pending, and rejected events are editable by the owner/admin. Fields are bounded, ordered, and typed; raw answers are stored separately from the event definition.

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
  "ticket_status": "active",
  "checked_in_at": null,
  "participation_verified": false,
  "answers": [
    {
      "field": 14,
      "field_label": "Contact email",
      "value": "student@example.com"
    }
  ],
  "created_at": "2026-06-22T10:00:00Z"
}
```

Phone, academic profile data, raw `registration_data`, and raw `contact_snapshot` are not returned. Custom answers are limited to organizer-defined form fields for that event.

### GET `/api/organizer/events/{slug}/registrations/export/`

Owner/admin only. Returns a CSV export of the same privacy-limited participant projection.

### POST `/api/organizer/events/{slug}/registrations/{registration_id}/check-in/`

Owner/admin only. Marks a participant as attended, marks the ticket as checked in, creates or updates the participation record, and returns the updated participant projection. Repeating the same check-in is idempotent.

### POST `/api/organizer/events/{slug}/tickets/verify/`

Owner/admin only. Accepts `{"code": "EVT-A1B2C3D4"}` and returns whether the ticket belongs to that event and can be checked in.

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
| GET | `/api/profile/readiness/` | Authenticated | Evidence-based 1-5 readiness summary; never an admissions outcome estimate |
| GET | `/api/profile/assessment/latest/` | Authenticated, self-only | Latest cached AI-assisted profile-readiness assessment or safe empty state; no provider call |
| POST | `/api/profile/assessment/run/` | Authenticated, self-only | Run profile assessment only when enabled, changed, and within daily limit; otherwise return cached/safe state |
| POST | `/api/admin/users/{id}/profile-assessment/run/` | Admin | Force profile reassessment for one user through the same schema/validation path |
| POST | `/api/profile/complete-onboarding/` | Authenticated | Finalize mandatory onboarding when requirements are satisfied |
| GET | `/api/events/` | Authenticated | Published public event catalog |
| GET | `/api/events/{slug}/` | Authenticated | Published public event detail |
| POST | `/api/events/{slug}/register/` | Authenticated | Register using a profile/contact snapshot |
| POST/DELETE | `/api/events/{slug}/cancel-registration/` | Authenticated | Cancel own active registration |
| GET | `/api/events/my-registrations/` | Authenticated | List own active registrations |
| GET | `/api/events/participation-records/` | Authenticated | List own verified participation records |
| GET | `/api/events/my-notifications/` | Authenticated | List own internal event notifications |
| GET/POST | `/api/organizer/events/` | Organizer/admin | List managed events or create a draft |
| GET | `/api/organizer/events/analytics/` | Organizer/admin | Aggregate owned-event metrics |
| GET/PATCH | `/api/organizer/events/{slug}/` | Owner/admin | Read or update an editable event |
| GET/PUT | `/api/organizer/events/{slug}/form/` | Owner/admin | Read or replace custom registration form fields |
| POST | `/api/organizer/events/{slug}/submit/` | Owner/admin | Submit draft or rejected event |
| GET | `/api/organizer/events/{slug}/registrations/` | Owner/admin | Privacy-limited participant list |
| GET | `/api/organizer/events/{slug}/registrations/export/` | Owner/admin | CSV export of privacy-limited participant list |
| POST | `/api/organizer/events/{slug}/registrations/{id}/check-in/` | Owner/admin | Idempotently check in a participant |
| POST | `/api/organizer/events/{slug}/tickets/verify/` | Owner/admin | Verify a ticket code for the event |
| POST | `/api/organizer/events/{slug}/cancel/` | Owner/admin | Cancel a published event |
| POST | `/api/organizer/events/{slug}/archive/` | Owner/admin | Archive an unpublished event |
| GET | `/api/admin/events/pending/` | Admin | Moderation queue |
| POST | `/api/admin/events/{slug}/approve/` | Admin, not owner | Publish pending event |
| POST | `/api/admin/events/{slug}/reject/` | Admin, not owner | Reject with required reason |
| POST | `/api/admin/events/{slug}/archive/` | Admin | Archive event |
| GET | `/api/admin/events/{slug}/logs/` | Admin | Read moderation history |
| POST | `/api/admin/university-import/dry-run/` | Admin/staff | Upload `.xlsx`, create an import job, parse through the existing importer, and roll back writes |
| POST | `/api/admin/university-import/execute/` | Admin/staff | Upload `.xlsx`, create an import job, and run the idempotent real import |
| GET | `/api/admin/university-import/jobs/{id}/` | Admin/staff | Read import job status, counters, report JSON, or error message |

The separate university data-cleaning importer is CLI-only and must not be exposed through public APIs. Use `python manage.py import_universities_data <path>` for a default dry-run, or add `--commit` to write safe creates/missing-field updates. It supports `.csv`, `.tsv`, and multi-sheet `.xlsx` workbooks. XLSX files are opened in read-only mode; every worksheet with recognizable `Name`/`Country` headers is processed by default, while empty/reference/notes sheets are recorded as skipped. Operators can list/select/exclude sheets with `--list-sheets`, `--sheets`, `--exclude-sheets`, `--sheet-header-row`, and `--max-rows-per-sheet`.

The importer now has a machine-readable workbook schema contract in `backend/services/university_service/import_schema.py` and a human-readable version in `docs/UNIVERSITY_DATA_SCHEMA_CONTRACT.md`. Before any row can be matched/upserted, its identity columns are checked for alignment. Rows that start `Country, City, URL, URL...` are classified as `shifted_left_missing_name`; they are repaired only when the same university-name prefix appears in at least 5 later cells and the website domain plausibly matches the extracted identity. Low-confidence shifted rows are written to manual review with `shifted_row_unrepairable` and are not imported.

It performs deterministic cell cleaning before saving, skips placeholder/commentary/country-average/wrong-prefix/repeated-boilerplate cells, writes optional audit/manual-review CSVs including `source_sheet_name`, `source_row_number`, `raw_name`, `normalized_name`, and `row_alignment_status`, stores committed row fingerprints in `UniversityDataImportBatch`/`UniversityDataImportRowLog`, and never serializes skipped raw cells, audit rows, manual-review rows, row hashes, admin notes, AI-only context, or system-only signal weights through student-facing endpoints.
| GET | `/health/` | Public | Service health |
| GET | `/api/v1/universities/` | Authenticated | University catalog, search/filter; excludes `is_demo=true` records unless `?include_demo=true` |
| GET | `/api/v1/universities/filter-options/` | Authenticated | Data-backed catalog filter/autocomplete options for countries, cities, institution types, verification states, cost confidence, and university names |
| GET | `/api/v1/universities/recommendations/` | Authenticated | Balanced 20-25 university recommendation list grouped by dream/reach/target/safety with program/cost/deadline/round context, shortlist/tracking state, and no admissions-odds language |
| GET | `/api/v1/universities/{slug}/` | Authenticated | University detail: stats, programs, scholarships, sources, `field_verifications` |
| GET | `/api/v1/universities/{slug}/fit/` | Authenticated | Admissions fit analysis with a 1-100 fit score and `dream`/`reach`/`competitive`/`target`/`safety` category from normalized profile data and verified university stats only |
| POST/DELETE | `/api/v1/universities/{slug}/shortlist/` | Authenticated | Add/remove this university from the caller's shortlist |
| GET | `/api/v1/universities/shortlist/` | Authenticated | List the caller's shortlisted universities |
| GET | `/api/v1/universities/compare/?ids=1,2,3` | Authenticated | Side-by-side detail for 2-4 universities by id |
| GET | `/api/roadmap/` | Authenticated | Caller's active roadmap plan and tasks, or `{"plan": null}` if none generated yet |
| POST | `/api/roadmap/generate/` | Authenticated | Generate or refresh the caller's roadmap from current profile/shortlist/exam data |
| GET/POST | `/api/roadmap/tasks/` | Authenticated | List caller's tasks (filters: `status`, `category`, `priority`, `linked_university`, `linked_application`, `source_type`, `task_kind`, `exam`, `due_before`, `due_after`, `view=list\|timeline`) or create a manual task |
| GET/PATCH/DELETE | `/api/roadmap/tasks/{id}/` | Authenticated, self-only | Read/update any own task; delete only `source_type=manual` tasks (others return 400 — skip instead) |
| POST | `/api/roadmap/tasks/{id}/complete/` | Authenticated, self-only | Mark a task completed and stamp `completed_at` |
| POST | `/api/roadmap/tasks/{id}/skip/` | Authenticated, self-only | Mark a task skipped without deleting it |
| GET/POST | `/api/essays/` | Authenticated, self-only | List caller's essay workspaces or create one |
| POST | `/api/essays/generate-suggestions/` | Authenticated, self-only | Create idempotent source-aware suggested essay drafts from caller's shortlist/tracked applications |
| GET/PATCH/DELETE | `/api/essays/{id}/` | Authenticated, self-only | Read/update/delete an essay workspace |
| GET/POST | `/api/essays/{id}/feedback/` | Authenticated, self-only | Read latest feedback, or generate new rule-based feedback (creates `EssayFeedback` + revision tasks) |
| POST | `/api/essays/{id}/score/` | Authenticated, self-only, AI quota scoped | Score an essay with the backend-only AI essay-readiness engine, or return a cached/safe quota/unavailable state |
| GET | `/api/essays/{id}/scores/` | Authenticated, self-only | List the caller's stored AI essay score reports for this essay |
| GET | `/api/essays/{id}/score/latest/` | Authenticated, self-only | Return the latest stored AI essay score report for this essay, or `null` |
| POST | `/api/essays/{id}/revision-tasks/` | Authenticated, self-only | Add a manual revision task to an essay |
| GET/PATCH | `/api/essays/revision-tasks/{id}/` | Authenticated, self-only | Read/update a revision task's title/description/category/status |
| GET/POST | `/api/applications/` | Authenticated, self-only | List caller's application tracker items or start tracking a university |
| GET/PATCH/DELETE | `/api/applications/{id}/` | Authenticated, self-only | Read/update/delete an application tracker item (filters: `status`, `university`) |
| GET | `/api/applications/{id}/timeline/` | Authenticated, self-only | Derived, read-only source-aware timeline for one application (deadlines, events, suggested finish dates, linked essays/exams). Nothing is persisted; no invented dates |
| GET/POST | `/api/applications/{id}/milestones/` | Authenticated, self-only | List or add milestones for an application (milestones now carry `priority` and `notes`) |
| GET/PATCH | `/api/applications/milestones/{id}/` | Authenticated, self-only | Read/update a milestone, optionally linking to one of the caller's own roadmap tasks |
| GET | `/api/suggestions/` | Authenticated, self-only | List caller's active suggestions (filters: `status`, `suggestion_type`, `linked_university`, `linked_application`, `linked_essay`) |
| POST | `/api/suggestions/generate/` | Authenticated, self-only | Generate or refresh source-aware rule-based suggestions; no AI and no invented official dates |
| POST | `/api/suggestions/{id}/add-to-roadmap/` | Authenticated, self-only | Create or reuse a roadmap task from the suggestion and mark it `added_to_roadmap` |
| PATCH | `/api/suggestions/{id}/dismiss/` | Authenticated, self-only | Mark a suggestion dismissed without deleting history |
| GET/PATCH/POST | `/api/v1/events/...` | Role-dependent | Legacy organizer/admin management router |
| GET/PATCH | `/profiles/me/` | Student | Legacy compatibility route under `/api/v1`; prefer `/api/profile/me/` |
| GET | `/subscriptions/me/` | Authenticated | Current plan and counters |
| GET | `/exams/` | Authenticated | Published exam catalog |
| GET | `/api/v1/exam-dates/` | Authenticated | Read-only official-exam planning dates for SAT/AP, including registration deadlines, late deadlines, AP test times, source URL, and verification status |
| GET | `/questions/` | Authenticated | Published original demo questions |
| POST | `/ai/mentor/` | Authenticated | Placeholder; provider integration deferred |

## University source fields

Catalog list query parameters:

- `page`, `page_size` use the shared DRF paginated response shape: `count`, `next`, `previous`, `results`; `page_size` is capped at 100 and the frontend standard catalog size is 21.
- `search` searches university name, city, country, and program names across the full backend queryset, not just the current page.
- `country` and `city` use case-insensitive partial matching; `institution_type`, `scholarship_available`, `test_policy`, and `verification_status` narrow results exactly. `verification_status` accepts `verified`, `partial`, or `estimated` and matches universities that have at least one field verification with that status.
- `ordering` supports `name`, `country`, `created_at`, `acceptance_rate`, `qs_ranking`, `tuition_usd_amount`, and `total_cost_usd_amount`; prefix with `-` for descending order. QS ranking and USD cost sorts keep missing comparable values last.
- `/api/v1/universities/filter-options/` returns distinct data-backed options for autocomplete/filter UIs. It follows the same demo-record visibility rule as the catalog: normal users do not see demo universities, while admins may opt into `?include_demo=true`.

The catalog list uses a compact serializer for card/search UI only. It includes identity/location, public ranking/stat/cost summary fields, `scholarship_available`, an 8-item `majors_list` preview, `admissions_cycle_target`, timestamps, and caller-specific `is_shortlisted`. It deliberately excludes detail-only nested records and long/raw/import-derived text: `programs`, `subject_rankings`, `requirements`, `scholarships`, `data_sources`, `field_verifications`, `program_matching`, `budget_comparison`, source URLs/notes, audit/manual-review rows, import logs, signal-weight/system fields, essay/application requirement prose, and data-quality notes. `GET /api/v1/universities/{slug}/` remains the detail serializer for full public university profile data.

University records carry two complementary sourcing mechanisms:

- `data_sources[]` (existing) — page-level citations for the institution as a whole: `source_url`, `source_title`, `published_at` when known, `retrieved_at`, `is_official`. Used as the fit analysis's `source_notes` fallback.
- `field_verifications[]` (added for real, source-backed universities) — per-field sourcing for any non-null admissions/stat/cost/deadline value: `field_name`, `status` (`verified` | `partial` | `estimated`), `source_url`, `last_verified_date`, `note`. A field with a non-null value but no matching `field_verifications` entry should not occur for real universities (enforced by a seed-data integrity test); demo/fictional universities never carry verification records.

Any University field with no confirmed source is left `null`/blank and rendered client-side as "Not verified yet" — it is never displayed as zero or guessed. `is_demo: true` marks clearly-fictional development records (see `docs/DECISIONS.md`); the default catalog list excludes them.

`international_office_url` and `virtual_info_session_url` are identity-ish contact links (same exemption as `admissions_url`/`financial_aid_url`/`application_portal_url`) shown on the university detail page's Contact tab; they do not require a `field_verifications` entry and are simply blank when unknown.

The university detail object also carries `ielts_competitive` (nullable decimal) and six raw-text fields populated by the XLSX importer (`docs/DATA_SOURCES.md`): `application_requirements`, `ap_recommendations`, `deadlines_text`, `financial_aid_notes`, `scholarships_text`, and `data_quality_notes`. These hold source text preserved verbatim when it is too unstructured to split safely; each is an empty string when not provided and is rendered as a labelled block in the Requirements/Deadlines/Financial Aid/Sources tabs. `data_quality_notes` surfaces importer caveats (placeholder SAT, textual GPA, missing currency conversion) so questionable values are transparent rather than silently trusted.

Program listings expose display-safe labels alongside the stored raw text. Each entry in `programs[]` now includes a computed `display_name` in addition to the unchanged raw `name`, and the university object carries a top-level `program_display_names[]` (deduplicated, order-preserving flatten of all programs' display labels). The display helper (`services/university_service/program_display.py`) parses a parent category with parenthetical or comma-split subtracks — e.g. a stored `"Engineering (Civil, Mechanical, EE, Aerospace, Chemical)"` becomes `Engineering — Civil`, `Engineering — Mechanical`, `Engineering — Electrical Engineering`, `Engineering — Aerospace`, `Engineering — Chemical` — strips stray parentheses, and expands abbreviations only in a safe parent context (`EE`→Electrical Engineering under Engineering, `CS`→Computer Science under Computing, `Econ`→Economics under Economics/Business). Raw `UniversityProgram.name` is never mutated; the parsing is display-only. The frontend prefers `program_display_names` and falls back to per-program `display_name`.

Tuition and cost fields preserve source currency separately from comparable USD values: `tuition_original_amount`, `tuition_original_currency`, `tuition_usd_amount`, `total_cost_original_amount`, `total_cost_original_currency`, `total_cost_usd_amount`, `currency_conversion_rate`, `currency_conversion_date`, `currency_conversion_source`, `currency_conversion_confidence`, and `cost_notes`. Non-USD values are converted only when a stored `ExchangeRate` exists; missing rates leave USD fields null and show a low-confidence note. University list ordering supports `tuition_usd_amount`, `-tuition_usd_amount`, `total_cost_usd_amount`, and `-total_cost_usd_amount`.

The admissions fit analysis (`/api/v1/universities/{slug}/fit/`) uses normalized GPA, SAT percentile bands where available, IELTS minimum/competitive gaps, curriculum context, published acceptance rate, cost context, and profile completeness. It returns `fit_score` (1-100), `category` (`dream`/`reach`/`competitive`/`target`/`safety` or `null`), `confidence`, component subscores, `strengths`, `risks`, `missing_fields`, `missing_data`, `next_actions`, `conditional_notes`, `student_academic_context`, `cost_context`, `source_notes`, `profile_evidence`, and a no-guarantee disclaimer. `profile_evidence` is a conservative optional-evidence breakdown (research, portfolio, olympiads, volunteering) with category contributions, missing evidence, confidence, program-relevance notes, and `assessment_context`. When a current cached `AIProfileAssessment` exists, `assessment_context.available=true` and the profile-evidence subscore blends the rule-based evidence score with the cached AI profile-evidence score; if no current assessment exists, the fit engine stays fully rule-based and marks `profile_assessment_not_run`. Fit never calls the AI provider. Profile evidence remains lower-weight than academics and never implies an admissions outcome. Ultra-selective universities below 5% acceptance are never shown as safety; a planned retake may add a conditional note but must not erase a current score gap. Response keys and UI copy use "fit", "score", "category", "strengths", "risks", "missing_fields", and "next_actions" instead of admissions-odds language.

`GET /api/v1/universities/recommendations/` (`services/university_service/recommendations.py`) turns the fit engine into a full admissions-planning list rather than a single-university lookup. It computes `calculate_university_fit` for every country/region-matching candidate, folds the fit engine's `competitive` category into `reach` for list purposes only (the per-university fit endpoint's five-category output is unchanged), and returns a balanced set capped at 5 dream / 7 reach / 8 target / 6 safety (20-25 total when enough verified candidates exist). The response shape:

- `recommendations[]` — each item has `university` (`id`/`name`/`slug`/`country`/`city`), `category` (`dream`/`reach`/`target`/`safety`), `is_international` (`true`/`false`/`null` when the student's profile country is unset), `fit_score`, `confidence`, `recommended_programs[]` (1-4 items with `name`, `fit_reason_key`, `match_type: "exact"|"related"`, `confidence`; empty when no major or cluster match exists — never invented), `program_data_verified`, `application_round` (`available_rounds[]` parsed from raw deadline/requirement text via word-boundary matching, `recommended_round`, `reason_key`, `reason_params`), `deadline` (the normalized user-cycle date when the profile has an expected graduation year; `null` when only a source-year date exists), `deadline_confidence` (`verified`/`partial`/`missing`), `deadline_cycle_label` (for example `2026-2027`, or `null` when no user-cycle date can be derived), `days_remaining`, `urgency` (`far`/`upcoming`/`soon`/`urgent`/`critical`/`overdue`/`unknown`, same thresholds as the application timeline), `estimated_total_cost_usd`, `tuition_usd`, `aid_scholarship_note_key`, `cost_risk` (`low`/`moderate`/`high`/`unknown` internal planning code; UI must render this as cost context / review-needed wording, not as affordability certainty), `academic_risk`/`profile_risk`/`deadline_risk` (`low`/`moderate`/`high`, derived from the fit engine's existing subscores), `main_strength`/`main_risk` (reuse the fit engine's existing strength/risk/missing-field codes), `why_recommended_keys[]`, `next_action`, `missing_data[]`, `current_academic_subscore`, `conditional_notes[]` (reused verbatim from the fit engine, including its planned-retake and after-deadline warnings), `source_notes[]`, `is_shortlisted`, and `application_id` (non-null only if the caller already has an `ApplicationTrackerItem` for that university).
- `counts` — `{dream, reach, target, safety, international, total}`.
- `missing_preferences[]` — `preferred_countries` and/or `intended_major` when absent; every item's `confidence` is capped at `medium` while `preferred_countries` is missing, per the "cautious default" rule.
- `excluded_low_data_count` — universities filtered out because the fit engine could not assign any category (not silently merged into a bucket).
- `list_size_limited` — `true` only when the shortfall is genuinely too few verified candidates, not a quota cap.
- `disclaimer` — the fixed required sentence: *"This is a fit estimate based on available profile and university data. It is not an admissions prediction or guarantee."*

Program matching never invents offerings: it checks the university's actual `programs[]` (via `program_display.format_program_display_names`) for an exact intended-major match first, then a small set of conservative subject clusters (CS/engineering, business/finance/economics, politics/law/IR, biology/pre-med, psychology, social sciences, humanities, arts/design, education, environmental studies, data/AI) for a related match, and returns an empty list — never a guess — when neither matches. `is_shortlisted`/`application_id` and the two prerequisite bulk lookups add only 2 extra queries regardless of catalog size (no per-university N+1).

## Major-cluster and subject-ranking matching

`services/university_service/major_matching.py` adds major/program-aware scoring on top of the existing fit and recommendation engines (see `docs/DECISIONS.md` ADR-038). It never invents ranking or program data — every score component is derived from stored profile fields, stored program fields, or is honestly reported as missing.

`infer_major_clusters(profile)` returns a `MajorInference` with `primary_major_cluster`, `secondary_major_clusters`, `possible_program_keywords`, `strong_preparation_signals`/`weak_preparation_signals` (from research/portfolio/olympiad/volunteering evidence counts), `missing_data`, and `confidence` (`high` when the profile has a declared major, `medium` when only inferred from activity/research/essay text, `low` when neither exists). Supported clusters: `stem`, `business_economics_finance`, `social_sciences`, `humanities`, `law_politics_ir`, `medicine_biology_health`, `engineering`, `computer_science_ai_data`, `design_arts`, `education`, `environmental_sustainability`, `public_policy_social_impact`, `psychology_cognitive_science`, `undecided_interdisciplinary`, `other`.

`score_program_fit(profile, program, university=None, inference=None)` scores one `UniversityProgram`: academics (normalized GPA + test score + curriculum rigor) is 45% of the raw score, program/major relevance (exact/cluster/keyword match plus evidence bonuses) is 30%, essay readiness is 10%, and the program's own stated requirements are 15%; a verified matching `UniversitySubjectRanking` (see below) adds a small 2-4 point bonus on top. It returns `program_fit_score` (1-100), `preparation_strengths`/`preparation_gaps`, `missing_requirements`, `confidence`, `subject_ranking` (or `null`), `data_notes` (e.g. `subject_ranking_not_available`, `official_program_page_not_verified`), and `match_type` (`exact`/`cluster`/`keyword`/`low_context`).

`match_programs_to_profile(profile, university)` scores all of a university's programs, drops `low_context` matches, and returns `major_inference`, `recommended_programs[]` (top 4), `program_data_verified` (`false` when the university has no `programs` rows at all — never faked), `missing_data[]`, and `confidence`. This is the same helper the university detail serializer, recommendations, and strategy all call — there is exactly one program-matching implementation.

University-level endpoints exposing this:

- `GET /api/v1/universities/{slug}/` — `program_matching` (the `match_programs_to_profile` payload above) is included **only on this detail action** (`include_program_matching` context flag gated to `self.action == "retrieve"`); it is `null` on list/compare responses to avoid recomputing program-fit scoring across a whole paginated catalog. `programs[]` items now also include `major_cluster`, `department_or_school`, `degree_level`, `official_url`, `portfolio_required`, `research_heavy`, `stem_heavy`, `interdisciplinary`, `program_requirements_summary`, `source_confidence`, `last_verified_date`, and their own `subject_rankings[]`. The university object also carries a top-level `subject_rankings[]` and the new ranking fields `global_rank`, `the_rank`, `national_rank`, `ranking_source`, `ranking_source_url`, `ranking_year`, `ranking_last_verified_date`, `ranking_confidence` (alongside the existing `qs_ranking`/`qs_ranking_year`) — all nullable/blank and rendered as "not verified yet" when absent.
- `GET /api/v1/universities/recommendations/` and `GET /api/v1/universities/strategy/` — each item gains `matched_programs[]` (same shape as `recommended_programs[]` above, trimmed for list display), `program_data_verified`, `best_program_fit_score`, `major_cluster_match`, `program_fit_confidence`, `program_strengths`/`program_gaps` (from the best-matched program), `subject_ranking_context` (the closest verified ranking for the student's inferred clusters, or `null`), `missing_program_data[]`, and `major_inference`. Strategy additionally groups results `by_country` and `by_major_cluster` (falling back to `program_data_not_verified` when no program has a confirmed cluster), alongside the existing category/round groupings.
- `GET /api/v1/universities/filter-options/` gains `major_clusters[]` (only clusters that actually appear on a stored program), `program_names[]`, `subject_areas[]`, and `ranking_sources[]` — all derived from the current queryset, never a hardcoded list.
- Catalog list filters (`GET /api/v1/universities/`) gain `major_cluster`, `program_search`, `subject_area`, `ranking_source`, `subject_rank_min`/`subject_rank_max`, `has_subject_ranking`, `portfolio_required`/`research_heavy`/`stem_heavy`/`interdisciplinary` (all `true`/`false`), `source_confidence` (matches program source confidence, subject-ranking confidence, or the university's own `ranking_confidence`), and `global_rank_min`/`_max`, `qs_ranking_min`/`_max`, `the_rank_min`/`_max`, `national_rank_min`/`_max`. All of these `.distinct()` the queryset since they join across `programs`/`subject_rankings`. `ordering` additionally supports `global_rank`/`-global_rank`, `the_rank`/`-the_rank`, `national_rank`/`-national_rank` with the same nulls-last behavior as `qs_ranking`.

A new `UniversitySubjectRanking` model (`university` FK, optional `program` FK, `subject_area`, `major_cluster`, `rank`, `source_name`, `source_url`, `ranking_year`, `last_verified_date`, `confidence`) holds subject/program-specific rankings distinct from the university-level ranking fields; it is unique per `(university, subject_area, source_name, ranking_year)`.

## University import response shapes

Admin/staff users can upload a workbook through `/api/admin/university-import/`; students, organizers, and anonymous users cannot. The endpoints accept `multipart/form-data` with a single `file` field. Only `.xlsx` files up to 10 MB are accepted.

Both `dry-run` and `execute` create a `UniversityImportJob`:

```json
{
  "id": 12,
  "uploaded_by": 1,
  "uploaded_by_email": "admin@example.com",
  "status": "completed",
  "mode": "dry_run",
  "original_filename": "Universities Data.xlsx",
  "row_count": 80,
  "created_count": 66,
  "updated_count": 14,
  "skipped_count": 0,
  "warning_count": 3,
  "source_url_count": 160,
  "field_verification_count": 420,
  "parsed_deadline_count": 75,
  "parsed_essay_count": 40,
  "questionable_sat_count": 2,
  "processed_count": 80,
  "current_row": 81,
  "current_university": "Example University",
  "last_heartbeat_at": "2026-06-30T10:00:05Z",
  "summary_json": {
    "progress": {
      "stage": "completed",
      "row_count": 80,
      "processed_count": 80,
      "current_row": 81,
      "current_university": "Example University",
      "last_heartbeat_at": "2026-06-30T10:00:05Z"
    },
    "summary": {},
    "rows": []
  },
  "error_message": "",
  "created_at": "2026-06-30T10:00:00Z",
  "started_at": "2026-06-30T10:00:01Z",
  "finished_at": "2026-06-30T10:00:05Z"
}
```

`status` is `pending`, `running`, `completed`, or `failed`; `mode` is `dry_run` or `execute`. Running jobs update `row_count` after workbook parse, `processed_count`, `current_row`, `current_university`, `last_heartbeat_at`, and a compact `summary_json.progress` object while rows finish. A running job whose heartbeat is older than the configured stale window is marked `failed` with an explicit timeout `error_message` the next time an admin reads the job detail. This avoids jobs staying `running` forever after a process interruption.

Dry-run behavior uses the same `xlsx_import.py` parser as execute but performs only read-only planning: parse rows and bulk-check existing slugs. Execute writes one university per short transaction and performs the existing idempotent upsert by slug/name. It does not delete existing universities and does not overwrite curated verified rows unless the importer policy is changed deliberately.

## Roadmap response shapes

`GET /api/roadmap/` and `POST /api/roadmap/generate/` both nest the plan under a `plan` key (`{"plan": {...} | null, ...}`) rather than returning a flat plan object, so the frontend has one consistent shape to check regardless of whether a roadmap exists yet:

- `GET /api/roadmap/` → `{"detail": "...", "plan": RoadmapPlan | null}`.
- `POST /api/roadmap/generate/` → `{"plan": RoadmapPlan, "missing_data_warnings": string[]}`. The warnings (e.g. `no_graduation_year`, `no_shortlisted_universities`) are also persisted on `plan.readiness_snapshot.missing_data_warnings` so they reappear on the next plain `GET` without needing to regenerate.

Each `RoadmapTask` always reports `generated_reason`, `evidence_note`, and `source_url` (empty string when no official source backs the task) so the UI can show why a task exists and where its claim comes from without a second request. `source_type` distinguishes a real verified deadline (`university_deadline`) from a generated/estimated one (`generated`) — never both implied at once. Tasks also report `task_kind` (`manual` or `generated`), `is_timeline_marker`, and optional `linked_application` / `linked_application_university_name` so clients can separate actionable list tasks from timeline-only countdown markers and filter by application context.

`view=list` excludes university-deadline countdown markers (`university_deadline:{id}:60/30/15/14/7`) while keeping actionable final-deadline tasks. `view=timeline` keeps dated timeline material, including those markers. Existing generated tasks are dismissed by calling `POST /api/roadmap/tasks/{id}/skip/`; generated tasks are not hard-deleted. Manual tasks may still be deleted by the owner.

The generator additionally reads (read-only) the caller's own `EssayWorkspace` records: any essay with `status` in `suggested`/`planned`/`not_started`/`needs_revision` produces a `category=essays`, `source_type=essay_status` task (dedup key `essay_workspace:{id}:{status}`), with `due_date`/`source_url` populated first from the essay record and then from the linked university's verified/normalized application deadline when one exists. `skipped`, `drafting`, `ready`, and `submitted` essays do not create active roadmap tasks. This remains a plain cross-service query, the same pattern already used for `user_profile_service`/`university_service`/`event_service`.

## Essay workspace response shapes

`EssayWorkspace` embeds its own `latest_feedback` (most recent `EssayFeedback`, or `null`) and `revision_tasks[]` so the frontend can render the editor, feedback panel, and checklist from one request. It may link to `university` and optionally `application`, and carries source-aware planning fields: `status` (`suggested`, `planned`, `not_started`, `drafting`, `needs_revision`, `reviewed`, `ready`, `submitted`, `skipped`), `priority`, `due_date`, `prompt_verification_status` (`verified`, `needs_verification`, `missing`), `prompt_confidence` (`low`, `medium`, `high`), `source_url`, `notes`, and read-only `suggestion_key`.

`word_limit` is validated as a realistic planning value (`10..2000`). If a linked university has a verified `essay_requirements` field that contains a parseable word limit, creating/updating an essay without a manual word limit may auto-fill that value and mark the prompt metadata as verified with the stored source URL. If no verified word limit exists, the API leaves it unset/verification-needed rather than inventing one.

`POST /api/essays/generate-suggestions/` reads only the caller's own shortlisted universities and tracked applications, then creates missing `EssayWorkspace` rows with stable `suggestion_key` values. It creates a single Common App planning draft plus per-university/application supplement and scholarship verification drafts when the stored data supports those signals. Official prompts are never invented: if `essay_requirements` is missing or lacks a verification source, the draft is labeled `missing`/`needs_verification` and asks the student to check the official application portal. Existing suggestions are returned as `existing_count`; skipped or edited drafts are never overwritten or duplicated.

`POST /api/essays/{id}/feedback/` runs the deterministic rule engine in `services/essay_service/feedback_engine.py` (word count, word-limit status, generic-language detection, paragraph structure, specificity, prompt-fit for why-school/why-major types, sentence-length grammar proxy) and returns `{"detail": "", "feedback": EssayFeedback, "essay": EssayWorkspace}`. It also creates/refreshes `EssayRevisionTask` rows: an existing `todo` task in the same `category` is updated in place rather than duplicated, while `completed`/`skipped` tasks are left untouched as history. No endpoint generates, writes, or rewrites essay text — every response is feedback and checklist items only.

`POST /api/essays/{id}/score/` runs the backend-only AI essay-readiness scorer. The request body is empty; the backend reads only the caller-owned `EssayWorkspace`, its linked application/university/program when present, verified prompt text/source metadata when present, word count/limit, and up to 10 cached profile-assessment keywords when a current profile assessment already exists. It does not send passwords, payment data, unrelated profile data, other essays, the full university database, or provider keys to the frontend.

The score response is:

```json
{
  "reason": "scored",
  "cached": false,
  "quota_remaining": 0,
  "next_available_at": null,
  "score": {
    "id": 1,
    "essay": 9,
    "rubric_version": "essay_numeric_v1",
    "overall_essay_readiness": 78,
    "confidence": "medium",
    "verified_context_used": true,
    "subscores": {
      "prompt_fit": 20,
      "structure": 16,
      "specificity_evidence": 15,
      "authenticity": 12,
      "language_clarity": 8,
      "word_limit_discipline": 4,
      "school_program_alignment": 4
    },
    "nullable_scores": {"school_program_alignment": 4},
    "word_count": 512,
    "word_limit_status": "within",
    "ai_paraphrase_style_signal": "low",
    "generic_language_signal": "medium",
    "unsupported_claims_signal": "low",
    "strength_flags": ["clear motivation"],
    "risk_flags": ["needs more evidence"],
    "approximate_suggestions": ["Add one specific example of impact."],
    "source_warnings": [],
    "disclaimers": [
      "This is an automated essay-readiness estimate, not an admissions decision or guarantee.",
      "Scores are based only on the essay text and verified UniWay context available.",
      "AI/paraphrase style signal is not proof of AI use.",
      "For important submissions, verify requirements yourself and ideally review with a qualified human reviewer."
    ],
    "created_at": "2026-07-03T00:00:00Z"
  }
}
```

`reason` is one of `cached`, `scored`, `quota_exceeded`, `ai_unavailable`,
`validation_failed`, `missing_essay_text`, or `essay_too_long`. The last two
input errors return HTTP 400; oversized text is rejected before a provider call.
Cached results are keyed by `essay_text_hash + context_hash` and do not consume
quota or call the provider. Failed provider calls and invalid provider JSON do
not consume quota. Free users get 1 new score per day; Basic/Starter,
Premium/Growth, and Pro/Premium-style tiers map to 10, 30, and 100 new scores
per month by environment-configurable settings.

The provider output must be strict JSON with only the documented fields. Suggestions are capped at 3 items and 20 words each, and are high-level revision guidance only. The backend rejects output that attempts to include rewritten essay text, generated drafts, unexpected fields, out-of-range scores, or admissions-outcome promises. If verified school/prompt context is missing, `school_program_alignment` is stored as `null`, confidence is lower, and a source warning is included rather than inventing requirements.

## Application tracker response shapes

`ApplicationTrackerItem` embeds its `milestones[]`. Creating an application only requires `university`; all status fields (`status`, `essays_status`, `recommendations_status`, `test_scores_status`, `documents_status`, `financial_aid_status`) default to their "not started" equivalents — the API never auto-advances a status. Active rows are unique per `(user, university)`. DELETE archives by setting `archived_at`; `POST /api/applications/{id}/restore/` restores when no active duplicate exists.

The same object is the canonical prospective-university record. It accepts a
university-owned `target_program`, application round, `target_intake_year`,
priority, notes, and a clearly separate `personal_estimated_deadline`. The
read-only `official_deadline` envelope contains `date`, `source_date`,
`source_url`, `source_title`, `last_verified_date`, `intake_year`, `round_type`,
`timezone`, and `status` (`verified`, `estimated`, `not_published`, `outdated`,
or `requires_review`). Stale/wrong-cycle or unverified source dates are not
returned as a precise official deadline. `ApplicationMilestone.linked_roadmap_task`
is optional and validated to belong to the caller.

## Application timeline response shapes

`GET /api/applications/{id}/timeline/` returns a **derived, read-only** planning view for one tracked application, assembled fresh on each request from data that already exists (the tracker item, the linked university's verified/imported fields and scholarships, the caller's essays linked to this application, official College Board exam dates, linked roadmap tasks, and milestones). Nothing is persisted and no date is invented. The payload has five arrays:

- `deadlines[]` — application / financial-aid / scholarship deadlines, each with `date`, `days_remaining`, `urgency` (`far` | `upcoming` | `soon` | `urgent` | `critical` | `overdue` | `unknown`), `confidence` (`verified` | `partial` | `user_provided` | `estimated` | `missing`), `source_url`, `source_label`, and optional deadline-cycle fields (`source_date`, `normalized_year`, `cycle_label`, `cycle_explanation`). A user-entered tracker deadline is used as entered. A university application deadline uses the stored official source month/day but recomputes the year from the student's expected graduation year (Aug-Dec -> `graduation_year - 1`, Jan-Jul -> `graduation_year`). If the source date exists but the student has no expected graduation year, `source_date` is preserved but `date`, `days_remaining`, and `urgency` stay `null`/`unknown` rather than treating a stale source year as current-cycle guidance. A missing deadline is returned with `date: null` and `confidence: "missing"` — never as a safe/zero value.
- `events[]` — dated timeline items (real deadlines, milestones, roadmap tasks, and clearly-labelled suggested checkpoints), each with `type`, `date`, `days_remaining`, `urgency`, and `confidence`, sorted chronologically.
- `suggested_dates[]` — phase-aware suggested finish dates (`type`, `date`, `reason_key`, `weeks_before`, `reference_deadline`, `confidence: "estimated"`). They are only produced when a real reference deadline exists and only within the window appropriate to how far away it is, so a distant deadline never generates urgent work and an imminent one drops unrealistic long-term tasks. Add-to-roadmap remains the existing idempotent `suggestions_service` flow; these are informational.
- `linked_essays[]` — the caller's essays explicitly linked to this application via `EssayWorkspace.application` (`title`, `status`, `word_limit`, `word_count`, `updated_at`). An essay that merely shares this application's university without being linked is not included; link/unlink it via `PATCH /api/essays/{id}/` with `application: <id>` or `null` (from either the essay or application screen).
- `linked_exams[]` — SAT/IELTS/TOEFL/AP context (`current_score`, `threshold`, `threshold_label`, `severity` reusing the fit gap-severity model, `planned_retake`, official `official_test_date`/`registration_deadline` for SAT/AP only, and `scores_arrive_before_deadline` which is `false` when an official test date is too late to help this cycle). No admission-probability language.

SAT/AP entries in `linked_exams[]` may also include `late_registration_deadline`, AP `official_test_time`, `late_test_date`, and `late_test_time` when a source-backed `OfficialExamDate` record exists. These fields are planning metadata only and must be rendered with their `verification_status`/source context, not as a guarantee that the official testing body has not changed the calendar.

## Official exam date response shapes

`GET /api/v1/exam-dates/` returns DRF pagination by default and accepts
`exam_type`, `event_kind`, `academic_year`, `exam_year`,
`verification_status`, `include_past=true`, and ordering by `test_date`,
`registration_deadline`, or `late_registration_deadline`. By default past
records are excluded while an explicit not-published future-year record may be
returned with `test_date: null`. The endpoint is read-only for authenticated
users. Every SAT/AP source URL must be an official College Board URL.

Each record includes `exam_type`, `event_kind` (`exam`, `ordering_deadline`,
`performance_task`, or `portfolio_deadline`), `name`, nullable `test_date`,
optional times/deadlines, `academic_year`, `exam_year`, `region`, `source_url`,
`source_title`, `last_verified_date`, `last_verified_at`, `local_timezone`,
stored `verification_status`, effective `date_status` (`verified`,
`not_published`, `outdated`, or `requires_review`), `countdown_days`, and
`notes`. A verified record requires an exact date; a not-published record
forbids one. Past dates are always serialized as effectively outdated.

`exam_plans.planned[]` in the profile can store `exam_type`, `date`,
`target_score`, `test_status` (`planned`, `preparing`, `registered`, `taken`,
`result_recorded`), `registration_status`, `result`,
`official_exam_date_id`, and unique `notification_intervals`. When an official
ID is supplied, the backend verifies the exam type and canonicalizes the date
from that record. Past dates are accepted only for taken/result-recorded exams.

`POST /api/roadmap/tasks/from-exam-plan/` accepts an official exam-date ID,
title, and optional description. It creates an `exam_plan` roadmap task only
for a verified upcoming record, preserves the College Board source, and is
idempotent by user/roadmap/official-date key. Repeated clicks return the same
task rather than a duplicate.

## Suggestions response shapes

`suggestions_service` owns persistent, self-only `SuggestedItem` records under `/api/suggestions/`. Suggestions are deterministic and rule-based; they read the caller's profile, exam plans, shortlist/tracked universities, verified university fields, essays, applications, and existing roadmap context. They never call AI, never estimate admission probability, and never invent official dates.

Each suggestion includes `suggestion_type`, `priority`, `source_type`, optional links (`linked_university`, `linked_application`, `linked_essay`, `linked_roadmap_task`), optional dates (`recommended_start_date`, `recommended_end_date`, `official_deadline`), optional `word_limit`, `source_url`, and `evidence_note`. When `official_deadline` comes from a university application deadline, it is the normalized user-cycle date derived from the stored official source month/day; if no expected graduation year is available, the suggestion does not use the stale source year as a planning deadline.

`source_type` is the key contract:

- `official` / `verified_university_data`: sourced from stored official scholarship records or `UniversityFieldVerification`.
- `planning_window`: a suggested checkpoint or exam window; not an official date.
- `profile_based`: derived from the student's own tracker/profile input and should still be verified externally.
- `roadmap_based`: explanatory roadmap guidance.
- `missing_data_warning`: a verification task because official data is not stored.

`POST /api/suggestions/generate/` is idempotent by `(user, dedup_key)`: active suggestions update in place, dismissed suggestions stay dismissed, and suggestions already added to roadmap stay linked rather than reappearing as new active items. `POST /api/suggestions/{id}/add-to-roadmap/` creates or reuses exactly one roadmap task with `source_type=planning_window`, `profile_gap`, `university_deadline`, or `generated` according to the suggestion source, preserves `source_url` and `linked_application` when present, then marks the suggestion `added_to_roadmap`.

## Error behavior

Validation errors return HTTP 400 with field-level details. Permission failures return 403, missing authentication returns 401/403 depending on authentication mechanism, missing resources return 404, and throttling returns 429.

## Required disclaimers

Clients must show module-specific admissions, event, essay, finance, and AI disclaimers defined in `docs/PRODUCT_SPEC.md`. The backend should return disclaimer identifiers or text for generated guidance in Phase 1.
