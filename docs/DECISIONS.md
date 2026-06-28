# Architecture Decision Log

## ADR-001: Modular monolith before distributed services

- **Status:** Accepted
- **Date:** 2026-06-22

The MVP uses one Django deployment and one PostgreSQL database with explicit domain service modules. This reduces operational cost while preserving extraction boundaries. Services will be split only when scaling, ownership, reliability, or deployment evidence justifies it.

## ADR-002: Next.js App Router with Feature-Sliced Design

- **Status:** Accepted
- **Date:** 2026-06-22

Routing and framework concerns live in `src/app`; product composition uses FSD layers. Server Components are preferred until client-side behavior is required.

## ADR-003: Backend-only AI provider access

- **Status:** Accepted
- **Date:** 2026-06-22

OpenRouter credentials and calls remain in `ai_gateway_service`. The gateway will enforce safety policy, routing, quotas, and logs.

## ADR-004: Evidence categories instead of admission probability

- **Status:** Accepted
- **Date:** 2026-06-22

EduVerse compares user metrics to published ranges and reports categorical alignment. It does not invent admission probabilities or guarantees.

## ADR-005: Original exam content only

- **Status:** Accepted
- **Date:** 2026-06-22

Question records require internal provenance and are seeded only with original demonstration content. Official exam specifications may guide format but proprietary questions may not be copied.

## ADR-006: Mock subscriptions in MVP foundation

- **Status:** Accepted
- **Date:** 2026-06-22

Plans and usage counters are modeled before choosing a payment provider. Stripe, Click, Payme, and Uzum remain deployment-market options, not current dependencies.

## ADR-007: Session authentication as Phase 0 development default

- **Status:** Superseded by ADR-009
- **Date:** 2026-06-22

Django session authentication supports local API development with CSRF protection. AUTH-001 will choose and document the production browser/API strategy.

## ADR-008: Commit migrations; do not generate them during container startup

- **Status:** Accepted
- **Date:** 2026-06-22

Django migrations are generated, reviewed, and committed with model changes. Local containers apply existing migrations at startup but do not create new migration files.

## ADR-009: SimpleJWT for the Phase 1 authentication slice

- **Status:** Accepted for MVP; browser storage is transitional
- **Date:** 2026-06-22

The API uses 15-minute JWT access tokens and 7-day rotating refresh tokens with blacklist support. Registration is student-only and atomically creates profile, preferences, and a Free subscription.

The initial web client keeps tokens in one localStorage helper so the vertical slice can operate without introducing a backend-for-frontend or cookie proxy. This storage choice is not approved as the final production posture. AUTH-002 will move refresh credentials to Secure HttpOnly cookies and add email verification and password reset.

## ADR-010: Dark-first semantic theme tokens

- **Status:** Superseded by ADR-017
- **Date:** 2026-06-22

Dark mode is the current EduVerse visual baseline. Components consume semantic CSS variables through Tailwind rather than fixed color values. A light token set remains available under `data-theme="light"` so future theme switching does not require component rewrites.

## ADR-011: Dependency-free client localization foundation

- **Status:** Accepted
- **Date:** 2026-06-22

The initial interface localization layer uses typed internal dictionaries and a React provider instead of a third-party package. English is the deterministic initial locale; Russian, Uzbek Latin, and Uzbek Cyrillic are included. The selected locale is persisted locally and updates document language metadata. Locale-prefixed routing and translated server metadata are deferred until SEO or server-rendering requirements justify them.

## ADR-012: Computed profile completion and flexible test scores

- **Status:** Accepted
- **Date:** 2026-06-22

Profile completion is computed on request from 13 documented data-readiness fields and is not stored. It must never be presented as an admission or student-quality score.

Test scores remain a validated JSON object during the profile foundation stage because SAT, IELTS, TOEFL, and multi-subject AP results have different shapes. The service validates bounded input and known numeric ranges while preserving a future path to dedicated exam-result models.

## ADR-013: Event registrations snapshot profile data

- **Status:** Accepted
- **Date:** 2026-06-22

Event registration stores private profile and contact snapshots rather than relying only on live profile joins. This preserves what the student submitted at registration time and prepares stable payloads for future organizer forms, exports, tickets, and notifications.

Only one active registration per user/event is allowed through a partial unique constraint. Cancelled registrations may be reactivated. Capacity and lifecycle checks run transactionally, while payment, QR, Telegram, custom forms, and distributed inventory remain deferred.

## ADR-014: Explicit organizer event state machine and maker-checker moderation

- **Status:** Accepted
- **Date:** 2026-06-22

Organizer event creation is draft-first. Submission, approval, rejection, cancellation, and archival are explicit transactional service operations rather than arbitrary status field updates. Each transition writes an `EventModerationLog`, and rejection requires a reason.

Publication requires an admin action, and moderators cannot approve or reject events they own. Organizer participant access uses a privacy-limited projection instead of returning raw registration snapshots. Custom forms, exports, Telegram notifications, QR tickets, anti-abuse expansion, and payment processing remain separate future tasks.

## ADR-015: Beta preview uses real completed slices and honest module previews

- **Status:** Accepted
- **Date:** 2026-06-23

The beta shell treats the dashboard as the product command center and uses real profile completion, registration, authentication, organizer, and moderation workflows where they exist. Unfinished modules share one localized preview pattern that describes intended capabilities, the next planned feature, relevant guardrails, and a working link to an adjacent completed workflow.

Preview pages must not fabricate admissions chances, university statistics, exam outcomes, activity impact, or subscription functionality. Event Map remains visibly available on the Free plan. AI appears only as a small supporting card. The `preview:beta` frontend script provides a stable local command for founder review without changing production behavior.

## ADR-016: Backend-confirmed global application gate

- **Status:** Accepted
- **Date:** 2026-06-23

Every product route is private to an authenticated EduVerse account. The frontend mounts `AppGate` above the application shell and exposes no protected navigation or page content until `/api/auth/me/` confirms the session. Session checking, authenticated, unauthenticated, and backend-offline states are distinct so a connectivity failure does not impersonate logout or leak cached product UI.

Published event, university, exam, and question catalogs also require backend authentication. Health, registration, login, and JWT refresh remain the minimal anonymous entry points. UI gating is defense in depth; DRF permissions remain authoritative.

## ADR-017: Ivory, navy, and crimson academic V1 identity

- **Status:** Accepted
- **Date:** 2026-06-23

EduVerse V1 uses a warm ivory canvas, deep institutional navy navigation, Harvard-like crimson emphasis, restrained academic gold, serif headings, and crisp geometry. This direction borrows the seriousness and hierarchy of established universities without copying protected marks, seals, or page layouts.

Corners are capped at 4px for ordinary controls and surfaces. Gradients, glass effects, neon, large pills, generic soft SaaS cards, and AI-first visual language are excluded. A dark semantic token set remains supported, but the reviewed V1 baseline is light academic. Event Map stays a core feature on every plan, while subscription cards remain an honest non-purchasable preview until payment work is authorized.

## ADR-018: Mandatory backend-confirmed onboarding before product access

- **Status:** Accepted
- **Date:** 2026-06-23

An authenticated session is necessary but not sufficient to mount the EduVerse product shell. The frontend must also confirm `is_complete` through `/api/profile/completion/`. Incomplete accounts receive only the full-screen onboarding flow, and final completion is recorded by a dedicated backend endpoint after required fields and reviewed sections pass validation.

Onboarding saves partial drafts to the self-only profile API after each step. sessionStorage is a non-authoritative resilience layer. The major/profession helper is a transparent rule-based mapping over a structured catalog; it does not invoke an LLM or claim aptitude certainty.

## ADR-019: Separate Next development and production build directories

- **Status:** Accepted
- **Date:** 2026-06-23

The founder-visible red `1 Issue` indicator was the Next development tool surfacing stale/invalid chunks after `next build` and `next dev` shared `.next` during QA. Development now writes `.next-dev`, production builds keep `.next`, and beta preview disables only the framework's development indicator through `devIndicators: false`. Real runtime errors remain visible in console inspection and are not suppressed.

ESLint runs as the explicit `npm run lint` check. Next's duplicated build-time lint integration is disabled because its legacy plugin detector warns incorrectly with the project's ESLint 9 flat configuration; production builds still run TypeScript validation.

## ADR-020: Transparent admissions recommendations and readiness

- **Status:** Accepted
- **Date:** 2026-06-23

EduVerse V1 uses a deterministic, dependency-free admissions exploration engine: a structured major catalog, forty non-diagnostic questions, and explicit mappings to majors, preparation classes, exams, and event types. Results organize interests; they do not diagnose aptitude or predict admission.

Readiness is returned as one to five stars plus Foundation, Developing, Competitive, Strong, or Outstanding. University-specific comparisons are permitted only when published requirements and official sources exist; otherwise the interface says that official data is needed. Admission probabilities and guarantees are prohibited.

## ADR-021: Offline-safe Event Map preview and independent app scrolling

- **Status:** Accepted
- **Date:** 2026-06-23

The V1 events experience uses stored coordinates to render an offline-safe map-preview/list hybrid without requesting third-party tiles. Events without coordinates remain fully available in the catalog. Leaflet tile interaction stays deferred to EVENTS-002.

On desktop, the shell occupies one `100dvh` viewport. The fixed-width sidebar and main workspace scroll independently, while mobile returns to normal document flow with compact navigation. Role-specific links are separated from the student workspace.

## ADR-022: Local-only role demo accounts for founder preview

- **Status:** Accepted
- **Date:** 2026-06-23

The local `seed_demo` command creates fictional student, organizer, and admin accounts with a shared documented demo password so founder review can reliably test each role without manual database setup. These accounts are scoped to the local SQLite preview path and are not production credentials or a production access mechanism.

The seed also creates a registered student event and a pending organizer submission. This keeps `/events/my`, organizer participants, and admin moderation reviewable in a fresh local preview while preserving the real role and moderation rules.

## ADR-023: Real, per-field-verified university data separated from fictional demo records

- **Status:** Accepted
- **Date:** 2026-06-28

The university catalog previously contained only fictional, clearly-labeled demo institutions (ADR for that infrastructure predates this entry). For the product to look credible, 15 real universities were added with deliberately partial, source-backed data, while the existing fictional records were kept (for infrastructure testing) and marked `is_demo=True` on the `University` model.

Two separation mechanisms were added, both purely additive — no existing field, endpoint shape, or fit-analysis logic was changed:

1. **Catalog separation.** `is_demo` defaults to `False`. `UniversityViewSet`'s default list/search excludes `is_demo=True` records; a `?include_demo=true` query param opts back in for testing. Direct retrieve/shortlist/compare on a demo university still work, since a user may have legitimately interacted with one while testing.
2. **Per-field verification.** A new `UniversityFieldVerification` model (one row per `(university, field_name)`) records `source_url`, `last_verified_date`, and a `status` of `verified` (directly fetched and verbatim-confirmed this session), `partial` (relayed via a search snippet of an official source, or arithmetically derived from two verified official counts), or `estimated` (reserved, unused by current seed data). Real universities only ever set a statistic when a verification record can accompany it; a seed-data integrity test (`test_seed_data_integrity.py`) enforces this for every future edit to `seed_data.py`. Demo universities never carry verification records.

Many real universities intentionally have most fields `null` (Stanford withholds its acceptance rate until the Common Data Set is released; UBC and Toronto publish tuition per-program rather than as one figure; KAIST's official site could not be reached this session). This is treated as correct, honest output — never backfilled with an estimate — and is exactly what "Not verified yet" communicates in the UI.

The admissions fit analysis was extended with a `limited_data_for_category` next-action: when a category is assigned from only one of the three quantitative signals (acceptance rate, GPA average, SAT average) because the other two are unverified for that university, the response says so explicitly rather than presenting a partial-data classification as a complete one. No fit-analysis terminology uses "probability," "chance," or "percentage" anywhere in code, API responses, or UI copy.
