# Architecture

## Overview

EduVerse is a monorepo with a Next.js frontend, a modular Django/DRF backend, and PostgreSQL. The MVP deploys as a modular monolith, while service boundaries are kept explicit enough to extract later if operational needs justify it.

```text
Browser
  |
  v
Next.js frontend
  |
  v
Django REST API
  |-------- PostgreSQL
  |-------- OpenRouter (backend AI gateway only)
  `-------- future cache/object storage/notifications
```

## Repository layout

```text
frontend/      Next.js App Router and FSD layers
backend/       Django project, shared infrastructure, domain services
docs/          product and engineering memory
compose.yaml   local service orchestration
```

## Frontend

Layers follow this dependency direction:

```text
app -> screens -> widgets -> features -> entities -> shared
```

- `app/`: routing, global styles, metadata, and providers.
- `screens/`: route-level composition.
- `widgets/`: reusable page sections such as navigation and dashboards.
- `features/`: user actions and workflows.
- `entities/`: domain display models and entity UI.
- `shared/`: UI primitives, API client, configuration, types, and utilities.

Server Components are the default. Add client components only for interaction, browser-only APIs, maps, or local state.

### Theme and localization

Theme values are semantic CSS variables declared in `frontend/src/app/globals.css` and exposed through Tailwind in `tailwind.config.ts`. Components consume names such as `background`, `surface`, `card`, `elevated`, `foreground`, `primary`, and `danger`; feature code must not introduce page-specific hex colors.

The internal localization layer lives in `frontend/src/shared/i18n/`. `I18nProvider` is mounted at the application root and exposes the current locale and the typed `t()` helper. Shared dictionaries are the source of truth for interface text. Navigation, auth, profile, dashboard, common actions, errors, empty states, and accessibility labels use translation keys.

The selected locale is stored under `eduverse.locale`, while `lang` and `dir` are synchronized on the document root. English is the deterministic server-rendered default; locale-aware routes and translated metadata can be added later if SEO requires them.

### Application authentication gate

`AuthProvider` models four explicit states: `checking`, `authenticated`, `unauthenticated`, and `offline`. `AppGate` sits above `AppShell`, so no protected navigation or route content mounts before `/api/auth/me/` confirms the access token. Guests receive the full-screen login/register gateway. Network or backend failures receive a retry screen and do not silently clear a potentially valid session.

The shared API client performs one refresh-token retry on HTTP 401 and broadcasts a single auth-invalid event when credentials are definitively rejected. This keeps expiry/logout behavior consistent across features. Route-level role guards remain useful for organizer/admin messaging, but DRF permissions are authoritative.

After authentication, `AppGate` requests `/api/profile/completion/`. An incomplete account mounts only the full-screen `OnboardingFlow`; `AppShell` and route children remain unmounted. A complete account receives the normal application shell. Onboarding drafts are persisted through partial backend profile updates at each step, with sessionStorage used only as a temporary resilience layer for unsaved inputs.

The final transition is explicit: `/api/profile/complete-onboarding/` records `onboarding_completed_at` only after required fields and reviewed section markers pass backend completion rules. Major recommendations are local rule-based category mappings and do not call the AI gateway.

### Beta preview shell

BETA-PREVIEW-001 makes the authenticated dashboard the primary command center. It composes real profile completion, current event registrations, subscription counters, and links to completed role-specific workflows. It does not create synthetic readiness scores or admission predictions.

Unfinished modules use the shared `BetaModuleScreen` composition and typed `betaModules` configuration. Each preview declares its purpose, three to five future capabilities, next planned implementation, adjacent working route, status, and product guardrail. This keeps preview pages coherent without pretending their backend workflows already exist.

Desktop navigation exposes the complete workspace in the sidebar. Mobile keeps five essential destinations in the fixed bottom navigation and exposes the full module set in a horizontally scrollable compact rail.

## Backend

`backend/services/` contains domain modules. Phase 0 includes concrete foundations for:

- identity and roles
- student profiles
- subscriptions and usage
- universities and sources
- moderated events
- original exam content
- AI gateway placeholder

Remaining service directories establish boundaries without prematurely implementing business logic.

Cross-cutting code belongs in `backend/common/`, including permissions, throttling, validators, exceptions, pagination, and health checks.

## API conventions

- Base prefix: `/api/v1/`
- Authentication prefix: `/api/auth/`
- JSON uses `snake_case`.
- Collection responses use DRF pagination.
- Writes require authentication unless a contract explicitly states otherwise.
- Product catalog APIs require authentication. Only health, registration, login, and the JWT refresh exchange are anonymous entry points.
- Errors use DRF's standard field-error shape in Phase 0; a stable error envelope is planned for Phase 1.

## Authentication boundary

`auth_service` owns registration, login, token refresh/revocation, and the current-user aggregate returned to the web client. It composes identity data with basic profile and subscription information while preserving ownership of those tables in their respective services.

The frontend auth feature owns login/register/logout actions and in-memory user state. Token persistence is isolated in `shared/lib/auth-storage.ts`; other features must use the shared API client and must not read localStorage directly.

## Profile boundary

`user_profile_service` owns the student/applicant profile aggregate and its self-only API under `/api/profile/`. `StudentProfile` stores identity-adjacent academic context, while `UserPreference` stores reusable interests. Email and role remain owned by `auth_service` and are read-only in profile responses.

Profile completion is computed from documented data-readiness dimensions instead of stored as a mutable percentage. This avoids stale derived state and keeps the meaning explicit: completion describes available profile data, not admission probability or personal merit.

Application readiness is computed on request from bounded profile, academic, exam, activity, essay, and timeline evidence. University-specific comparison is used only when matching published requirements and official source records exist; otherwise the API reports that official data is needed. The frontend must never convert readiness into an admission probability.

The dependency-free frontend admissions engine contains the structured major catalog, forty-question interest assessment, class suggestions, and event-type proposals. Session storage protects unfinished assessment answers, while the backend profile remains authoritative for selected majors and classes.

ONBOARDING-GATE-001 expands the completion contract to required identity, academic direction, exam, preparation, activity-review, and support dimensions. The percentage remains derived, while the explicit completion timestamp records that the user reviewed and finalized the current onboarding version.

Test scores use a bounded JSON object because exam systems have different score shapes and AP results can contain multiple subjects. Known SAT, IELTS, and TOEFL numeric ranges are validated; future exam-specific services may normalize these records into dedicated models when practice and scoring workflows require it.

The frontend profile feature owns `/api/profile/` calls and typed profile data. The profile screen composes responsive sections but does not perform roadmap, matching, or admission inference.

## Event boundary

`event_service` owns public event discovery, provenance, locations, lifecycle status, capacity, and user registrations. Canonical student-facing endpoints live under `/api/events/`; organizer and moderation workflows use `/api/organizer/` and `/api/admin/events/`. The `/api/v1/events/` router remains compatibility-only.

Only `published` and `public` events enter the student catalog queryset, and reading that queryset requires authentication. Registration writes lock the event row, re-check lifecycle/deadline/capacity, and create a snapshot of the user's profile and contact data. A partial database constraint prevents more than one active registration per user/event, while cancelled records may be reactivated.

Payment status is only a workflow placeholder. EVENTS-001 does not process money, issue QR tickets, send Telegram messages, export Sheets, or evaluate custom application forms.

The frontend event feature owns canonical event API calls. `entities/event` defines cards and response types; route-level screens provide the catalog, detail, and authenticated “My events” experiences.

### Organizer and moderation workflow

ORGANIZER-001 adds stable management boundaries under `/api/organizer/` and `/api/admin/events/`. Organizer creation is draft-first; submission and every moderation transition are explicit domain-service operations with transactional row locking and `EventModerationLog` records. The legacy `/api/v1/events/` router remains compatibility-only and should not be used by new frontend workflows.

The lifecycle is `draft -> pending_review -> published` or `rejected`, with rejected events editable and resubmittable. Published events may be cancelled, while unpublished work may be archived. Moderators cannot approve or reject their own events.

Organizer participant reads are a privacy projection, not raw registration serialization. They expose participant name, email, optional Telegram username, registration/payment status, and timestamp while withholding phone, academic profile fields, and raw snapshots.

Frontend ownership follows FSD: `features/organizer-events` owns organizer/moderation API actions; `screens/organizer-events` and `screens/event-moderation` compose role-protected routes. Role-aware navigation is a convenience only; backend permissions and object-scoped querysets remain authoritative.

## Roadmap boundary

`roadmap_service` owns the personalized admissions roadmap under `/api/roadmap/`. It is a synthesis layer: it reads from `user_profile_service` (structured profile items, exam plans, scholarship need), `university_service` (shortlist, verified statistics, fit analysis), and `event_service` (a student's own event registrations), but owns no data those services already own — only the `RoadmapPlan`/`RoadmapTask` records it generates.

`services/roadmap_service/roadmap_generator.py` is the deterministic, rule-based generation engine. It contains no AI call and produces no task without a concrete trigger: a missing structured-profile item, a verified university statistic (or its absence), the student's own planned exam date, a verified application/scholarship deadline, or a fit-analysis signal. Generation is idempotent — each task carries a stable `dedup_key` so re-running generation only adds tasks for newly-detected gaps and never duplicates or deletes existing ones (including completed/skipped tasks, which are preserved as a history, not removed).

Dates follow the same no-invention discipline as `university_service`: a task's `due_date` is either a real verified deadline (with `source_url` populated from the matching `UniversityFieldVerification` when one exists) or the student's own profile data (a planned exam date), or it is left null. The one exception is a small set of profile-gap tasks (research/portfolio project suggestions) that may get a *computed planning anchor* derived from the student's expected graduation year; those are explicitly labeled in `evidence_note` as an estimated planning window and use `source_type=generated`, never `university_deadline`, so the frontend can never mistake an estimate for an official date.

Every `RoadmapTask` is self-only (filtered by `user` in the viewset queryset, mirroring the `ProfileItemViewSet`/`SavedUniversity` pattern). Manual tasks (`source_type=manual`) are fully user-owned: editable on every field and deletable. Generated tasks are editable on title/description/due date/priority/status but not category, and cannot be deleted — only completed or skipped — so the generation history and its sourcing remain intact.

The frontend roadmap feature owns `/api/roadmap/` calls and typed roadmap data. The roadmap screen buckets the already-loaded task list into This week / This month / Later / Completed client-side rather than issuing separate paginated requests per bucket; the dedicated `/api/roadmap/tasks/` endpoint with `status`/`category`/`priority`/`linked_university`/`due_before`/`due_after` filters exists for API consumers and tests, not as the screen's primary data path.

`roadmap_generator.py` also reads (read-only) `essay_service.EssayWorkspace`: an essay with status `not_started` or `needs_revision` produces a `category=essays`/`source_type=essay_status` task. This is a plain cross-service query with no new model field on either side, consistent with the synthesis-layer boundary above.

## Essay workspace boundary

`essay_service` owns the safe essay-drafting workflow under `/api/essays/`: `EssayWorkspace` (draft, prompt, word limit, status, optional linked university), `EssayFeedback` (one row per feedback run), and `EssayRevisionTask` (a persistent checklist, separate from the per-run `EssayFeedback.revision_tasks` JSON snapshot). It is unrelated to `user_profile_service.EssayDraft`, the lightweight tracker from the structured-profile phase (`PROFILE-STRUCTURED-001`); the two are intentionally separate systems — `EssayDraft` is a profile-completion signal, `EssayWorkspace` is the actual drafting/feedback tool.

`services/essay_service/feedback_engine.py` is the deterministic, rule-based feedback engine: word count, word-limit status, generic-phrase detection, paragraph-break/conclusion structure, specificity (quantified-detail presence), why-school/why-major prompt-fit, and a sentence-length grammar proxy. It contains no AI call and never returns generated or rewritten essay text — only scores, a summary, strengths, issues, and revision-task suggestions. `POST /api/essays/{id}/feedback/` persists those suggestions as `EssayRevisionTask` rows, updating an existing `todo` task in the same category in place rather than duplicating it on repeated feedback runs, while completed/skipped tasks are preserved as history (the same "skip, don't delete" discipline as `roadmap_service`).

Every essay, feedback row, and revision task is self-only (filtered through the owning `EssayWorkspace.user`). There is no endpoint, button, or rule that writes or rewrites a student's essay; only feedback and checklist generation.

## Application tracker boundary

`application_service` owns the per-university application pipeline under `/api/applications/`: `ApplicationTrackerItem` (one per `(user, university)`, enforced by a unique constraint) and `ApplicationMilestone`. Creating an item never sets `status` beyond its `researching` default — the student moves it through the pipeline explicitly; nothing in the backend infers "applying" or "submitted" from other data.

`ApplicationMilestone.linked_roadmap_task` is an optional, validated-self-only foreign key into `roadmap_service.RoadmapTask`. `application_service` does not generate roadmap tasks itself or duplicate roadmap data; a milestone simply points at an existing task the student (or `roadmap_generator.py`) already created, the same read-without-owning relationship `roadmap_service` has with the services it reads from.

The frontend surfaces the university/roadmap connection without new backend surface: the applications screen and the university detail page's Deadlines/Roadmap tabs call the existing `/api/roadmap/tasks/?linked_university={id}` filter and the `/api/applications/?university={id}` filter (added alongside this feature) to show roadmap tasks and tracked-application status for a given university.

## Data ownership

The V1 event catalog includes an offline-safe map-preview/list hybrid built from stored coordinates. It does not require a network tile provider, and events without coordinates remain accessible in the catalog. Full Leaflet tile interaction remains an EVENTS-002 enhancement.

Each service owns its tables and business rules, even while sharing one PostgreSQL database. Cross-service references should use foreign keys only when transaction consistency is important. Future extraction should replace direct imports with service interfaces or events.

## AI gateway

All model calls go through `ai_gateway_service`. It will own provider routing, prompts, quotas, abuse checks, usage logs, disclaimers, and fallbacks. The browser never receives provider credentials.

## Deferred choices

- Authentication token/session strategy for production
- Background queue and scheduler
- Search engine
- Object storage
- Tile provider beyond MVP OpenStreetMap use
- Production hosting vendor

These choices require measured product or operational needs and must be recorded in `docs/DECISIONS.md`.
