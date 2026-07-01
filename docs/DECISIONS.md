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

## ADR-004: Evidence categories instead of admissions outcome odds

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

Preview pages must not fabricate admissions outcome odds, university statistics, exam outcomes, activity impact, or subscription functionality. Event Map remains visibly available on the Free plan. AI appears only as a small supporting card. The `preview:beta` frontend script provides a stable local command for founder review without changing production behavior.

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

The admissions fit analysis was extended with a `limited_data_for_category` next-action: when a category is assigned from only one of the three quantitative signals (acceptance rate, GPA average, SAT average) because the other two are unverified for that university, the response says so explicitly rather than presenting a partial-data classification as a complete one. Fit-analysis terminology uses categorical readiness language throughout code, API responses, and UI copy.

## ADR-024: Deterministic, source-aware roadmap generation with no AI

- **Status:** Accepted
- **Date:** 2026-06-28

The personalized admissions roadmap (`roadmap_service`) is a rule-based synthesis layer, not an AI feature. `roadmap_generator.py` evaluates a fixed set of deterministic rules against the student's structured profile, shortlisted universities, exam plans, and event registrations, and only ever emits a task when one of those rules is concretely triggered. This keeps every task auditable: each `RoadmapTask` carries `generated_reason` (why the rule fired), `evidence_note` (the specific data point), and `source_url` (populated from the matching `UniversityFieldVerification` when the task is anchored to a verified university statistic, otherwise empty).

Generation is idempotent by design. Each generated task is assigned a stable `dedup_key` (e.g. `university_deadline:{id}:30`, `profile_gap:portfolio`) computed from the rule and its inputs; regenerating a roadmap only inserts tasks for keys that don't already exist on the plan. This means regeneration is safe to call repeatedly as the student's profile or shortlist changes — it never duplicates a task, and it never deletes or resets a task the student has already completed or skipped. The tradeoff, accepted deliberately: regeneration does not retract a task whose underlying condition is no longer true (for example, unshortlisting a university leaves its deadline tasks in place) — the student skips it manually instead, consistent with "skip, don't delete" applying to the whole generated history.

Two date-honesty rules mirror the university-data policy in ADR-023. First, a task's `due_date` is either backed by a real source (a verified `application_deadline`/scholarship deadline, or the student's own planned exam date from their profile) or it is left null — generation never invents an official date. Second, the one controlled exception (a soft planning anchor for research/portfolio profile-gap suggestions, derived from the student's expected graduation year) is explicitly labeled `source_type=generated` with an `evidence_note` stating it is an estimated planning window, so the frontend can never present it as an official deadline. Priority similarly follows a fixed function of days-until-due (urgent ≤14, high ≤60, medium otherwise) rather than being inferred or invented.

When a category is assigned to a reach-classified university but the fit analysis only had one verified statistic to work with, the roadmap surfaces a `fit_missing` task to verify the gap rather than fabricating a weak-dimension claim — the same "do not overclassify" discipline as the fit analysis itself (ADR-023) carries through to the tasks generated from it.

PRODUCTION-RESCUE-004 clarified two roadmap production rules. First, a tracked application counts as a target university for generation even when the university is not separately shortlisted, so the UI does not warn the student to shortlist when their application tracker already provides target context. Second, SAT, IELTS/TOEFL, and AP suggestions created from missing or low scores use `source_type=planning_window` and evidence text that explicitly tells the student to verify official test dates; they are planning prompts, not official exam dates.

## ADR-025: Rule-based essay feedback with no ghostwriting, and a self-contained application tracker

- **Status:** Accepted
- **Date:** 2026-06-28

`essay_service` adds a full essay-drafting workspace (`EssayWorkspace`/`EssayFeedback`/`EssayRevisionTask`) deliberately separate from `user_profile_service.EssayDraft`, the lightweight tracker added during `PROFILE-STRUCTURED-001`. They serve different purposes — `EssayDraft` is a profile-completion signal ("do you have an essay drafted for this program, yes/no/status text"), while `EssayWorkspace` is the actual editor, prompt, word-limit tracker, and feedback tool — and merging them would have forced either a profile-service essay-text field (out of scope for a structured-profile item) or a roadmap-service-style cross-app migration. Keeping them separate cost nothing: `roadmap_generator.py`'s existing `profile_gap:essays` rule still reads `EssayDraft` (a profile-completeness gap), and a new `_essay_workspace_tasks` rule reads `EssayWorkspace` (an active-drafting gap) — both can coexist as independent signals.

`feedback_engine.py` follows the same discipline as `roadmap_generator.py` and the fit analysis: deterministic rules only, no AI call, and critically, **no code path that returns generated or rewritten essay text**. Every output is a score (0-100, heuristic), a label (weak/developing/solid/strong/excellent), a strengths/issues list, and revision-task suggestions — checklist items describing what to fix, never replacement prose. This is enforced structurally, not just by convention: there is no endpoint that accepts "write this essay" or returns essay content the student didn't type themselves.

Revision tasks use an update-in-place dedup strategy distinct from roadmap's `dedup_key`: on each feedback run, an existing `todo` task in the same category is updated (title/description refreshed) rather than duplicated, while `completed`/`skipped` tasks are left alone. This avoids checklist spam from repeated "Get feedback" clicks while still preserving completed-task history, the same "skip/complete, don't delete" principle used throughout the roadmap and structured-profile items.

`application_service` (`ApplicationTrackerItem`/`ApplicationMilestone`) deliberately does not auto-advance any status field. Creating a tracker item for a university only ever defaults to `status=researching` and every sub-status (essays/recommendations/tests/documents/financial aid) to its "not started" equivalent — the student is the only actor that moves an application through the pipeline. This mirrors the roadmap/fit-analysis stance of describing reality rather than inferring it: EduVerse has no reliable signal that an application was actually submitted, so it never claims one.

`ApplicationMilestone.linked_roadmap_task` is the one new cross-service foreign key added in this phase (`application_service` → `roadmap_service`), validated so a milestone can only link to a roadmap task the same user owns. This is additive only — no field or migration was added to `roadmap_service` itself. The university detail page's Deadlines/Roadmap tabs and the applications screen instead reuse the existing `linked_university` filter on `/api/roadmap/tasks/` (already present from `ROADMAP-GENERATOR-001`) plus a newly added `university` filter on `/api/applications/`, so "show me everything tied to this university" needed zero new aggregate endpoints.

Two new `University` fields, `international_office_url` and `virtual_info_session_url`, were added for the detail page's Contact tab. Like `admissions_url`/`financial_aid_url`/`application_portal_url`, they are identity-ish contact links exempt from the `UniversityFieldVerification` requirement (ADR-023) — they are simply blank, never guessed, when not on file.

## ADR-026: Persistent source-aware suggestions and inactive beta pricing

- **Status:** Accepted
- **Date:** 2026-06-29

EduVerse will deepen the existing admissions workflow through a persistent, rule-based suggestions layer instead of adding a broad new module. `suggestions_service` owns `SuggestedItem` records that can be dismissed or added to the roadmap, while reading existing profile, university, roadmap, essay, and application data as context. This preserves user intent (dismissed items do not immediately reappear) and makes "add to roadmap" an explicit action rather than an automatic mutation.

Suggestions follow the same evidence policy as university data and roadmap tasks. Official deadlines are only shown when backed by stored source data. Student-entered tracker dates are labeled `profile_based`; computed exam windows, essay checkpoints, and document preparation dates are labeled `planning_window`; missing official data becomes a verification suggestion. No suggestion estimates admission probability, award probability, or guaranteed outcomes. No AI is used.

Onboarding exam plans remain in the existing flexible `StudentProfile.exam_plans` JSON rather than introducing a new exam schema before the exam product exists. The frontend now writes richer planned-retake metadata (`exam_type`, `current_score`, `target_score`, `planned_retake`, `planned_retake_month`, `test_status`) so suggestions can generate meaningful exam planning without a migration-heavy model split.

Beta pricing is explicitly inactive. The plans page may show future tiers for positioning, but paid cards are labeled Upcoming/Coming soon/Not active during beta, no checkout or upgrade CTA is shown, and all currently available beta features remain free for beta users. This supersedes any UI copy that implied active paid restrictions during beta.

Demo cleanup is handled by hiding demo universities from normal suggestion/roadmap generation and labeling demo events when seeded demo data is visible. Demo accounts can keep local demo data for founder review, but normal users should see clean empty states, real university data, and source-aware suggestions.

## ADR-027: Bulk university dataset import with data-quality safeguards

- **Status:** Accepted
- **Date:** 2026-06-30

Real university data is imported from an XLSX workbook via a management command (`import_universities_xlsx`) backed by a pure, unit-tested parsing module, rather than by hand-editing `seed_data.py` or hardcoding values in the frontend. The importer carries the same no-invention discipline as ADR-023 (university data) into bulk loading:

- **Idempotent enrichment, not duplication.** Universities are matched by a slug derived from the name with a trailing `(...)` stripped, so dataset rows that overlap the curated seed (e.g. "MIT (MIT)" vs the seeded "Massachusetts Institute of Technology") upsert into the existing record. By default only blank fields are filled and existing `UniversityFieldVerification` rows are preserved, so curated/manually-verified data is never silently downgraded; `--replace-existing` opts into overwriting.
- **Preserve, never fabricate.** Content that cannot be parsed confidently (multi-line deadlines, essay prompts, application requirements, AP recommendations, scholarship and financial-aid prose) is kept verbatim in dedicated raw-text fields and shown as labelled blocks. Missing values stay `null`/blank ("Not verified yet").
- **Questionable data is quarantined, not trusted.** Identical SAT 25/50/75 percentiles are detected as placeholders and, by default, are not stored as statistics (so admissions-fit never uses them); `--include-questionable-stats` stores them only with an `estimated` verification. Textual GPA (A-Level/IB) is preserved as a note instead of being coerced into the numeric `gpa_average`. A `$` tuition figure on a non-US institution keeps the source's USD-equivalent and records a transparency note in `data_quality_notes`.
- **Acceptance rate** is normalized to the catalog's percentage-number convention; it continues to feed only the Reach/Competitive/Target/Safety fit classification and never an exact admission probability.

The dataset workbook is committed under `backend/data/universities/` for local/ops fallback, but production imports should use the admin upload workflow from ADR-028 rather than requiring a manual `DATABASE_URL` or Render shell session.

## ADR-028: Admin-only university XLSX import jobs instead of shell imports

- **Status:** Accepted
- **Date:** 2026-06-30

Manual production imports through local `DATABASE_URL`, Render Shell, or a startup command are too error-prone for EduVerse's current beta operations. A long import inside migrations or web-service startup can also block Render's port scan and fail deploys before gunicorn is ready.

EduVerse therefore exposes a protected admin/staff-only upload workflow under `/api/admin/university-import/` and `/admin/university-import`. It creates a `UniversityImportJob` record, accepts only `.xlsx` files up to 10 MB, stores the upload in a temporary file, and deletes that file after processing when possible. Students, organizers, and anonymous users cannot access the endpoints; UI hiding is not the security boundary.

The workflow reuses `services/university_service/xlsx_import.py` for file reading, parsing, normalization, and upsert behavior. Dry-run is a true read-only planner: it parses the workbook and performs a bulk slug lookup to estimate created/updated/skipped rows without calling `save()`, `get_or_create()`, or `update_or_create()`. Execute writes one university per short transaction and preserves the existing safety policy: idempotent upsert by slug/name, no deletes, no invented data, placeholder SAT quarantining, raw text preservation, and curated verification rows preserved unless the importer policy changes deliberately.

Because there is no dedicated production queue yet, job processing uses a beta-only daemon thread after the job row is created. This is intentionally narrow: it avoids startup imports and long blocking requests without adding Celery/RQ/managed queue infrastructure prematurely. The job row is the operational truth: it now stores row progress, current row/university, and a heartbeat while running; an old running job with no heartbeat beyond the configured stale window is marked failed with an explicit timeout message when an admin reads it. If import volume or reliability needs grow, a real queue should replace the thread and this ADR should be amended.

## ADR-029: Page-based grids and lists for repeated content

- **Status:** Accepted
- **Date:** 2026-06-30

Repeated item surfaces use explicit page controls instead of infinite scroll, endless "load more", or first-page-only rendering. The default dense catalog pattern is 21 items per page (3 columns x 7 rows on desktop), backed by DRF `page` + `page_size` when the API is paginated. Backend pagination remains enabled and capped by `DefaultPagination.max_page_size=100`; the frontend requests `page_size=21` for normal catalog/list screens.

The shared frontend primitives are `PaginationControls`, `PaginatedGrid`, and `PaginatedList` under `frontend/src/shared/ui/pagination.tsx`. Grids are used for catalog/card surfaces such as universities and events; list or board pages such as roadmap, applications, moderation, and participant tables keep their domain layout but still expose previous/next, page number, total pages, and range summaries. Local pagination is used only after the full relevant client-side filtered set is already loaded, such as essay tab filters and roadmap task buckets.

EDUVERSE-GLOBAL-PAGINATION-AND-SLIDERS-001 tightened this pattern: `PaginationControls` now supports `pageSize`, `totalCount`, and first/last page controls while preserving the older `onPrevious`/`onNext`/`onPageSelect` callback style. The university catalog remains backend-paginated at 21 cards per page and now exposes city, verification-status, QS ranking, tuition, and total-cost filters/sorts through the same paginated API instead of filtering only the visible page.

## ADR-030: Normalized academics, sourced costs, and fit score foundation

- **Status:** Accepted
- **Date:** 2026-06-30

EduVerse stores a student's raw academic record and derived comparison values separately. `StudentProfile.original_gpa_value`, `original_gpa_scale`, `original_gpa_scale_type`, curriculum fields, and normalization confidence preserve the source context; `normalized_gpa_4` is the comparable value used by readiness and university fit. A raw 5-point GPA is never compared directly to a 4-point university range. Unsupported curricula keep a low-confidence note instead of a forced conversion.

University affordability comparisons also separate source values from comparable values. Tuition and total cost preserve original amount/currency, and USD fields are populated only from native USD amounts or a stored `ExchangeRate`. EduVerse does not hardcode live exchange rates, fetch rates at request time, or silently treat non-USD values as USD.

The university fit response is an evidence-based 1-100 `fit_score` with categorical labels (`dream`, `reach`, `competitive`, `target`, `safety`), component subscores, risks, missing data, confidence, and a disclaimer. It is not an admission probability and must not be described as odds, chance, likelihood of acceptance, or a guarantee. Planned retakes may be shown as conditional context only; current IELTS/SAT gaps still remain visible.

Official SAT/AP dates are modeled through `OfficialExamDate` and can be marked verified only with a `collegeboard.org` source. Roadmap generation reads that model when available; otherwise it creates a verification task instead of inventing official exam deadlines.

## ADR-031: Roadmap list/timeline separation and compact suggestions UX

- **Status:** Accepted
- **Date:** 2026-07-01

Roadmap task management separates actionable work from calendar context. Normal list view shows tasks the student can act on, while generated university deadline countdowns (`60/30/15/14/7` day markers) are classified as `is_timeline_marker=true` and shown only in Timeline View. Existing `14`-day markers remain recognized so production roadmaps do not gain duplicate `15`-day tasks merely because the UI wording changed; future generation policy can migrate that window deliberately if needed. Generated tasks continue to be skipped/dismissed rather than hard-deleted, preserving history, while manual tasks may be deleted by the owner after confirmation.

Source-aware suggestions are compact by default. The frontend groups near-identical exam planning suggestions by exam/source/application context and shows one carousel card at a time, with details/subitems available on demand. IELTS/TOEFL items remain generic planning guidance; SAT/AP official-date claims still require verified College Board-backed `OfficialExamDate` records. Missing official source data is rendered as verification status, not as an invented date.

## ADR-032: Display-only program normalization and severity-aware requirement gaps

- **Status:** Accepted
- **Date:** 2026-07-01

University detail pages present program tracks and academic-requirement gaps with more nuance without touching stored data or introducing admissions-odds language. Two display-only changes:

**Program display normalization.** Imported program strings sometimes preserve a parent category with parenthetical or comma-split subtracks (`"Engineering (Civil, Mechanical, EE, Aerospace, Chemical)"`, or the same value split across broken fragments such as `"Engineering (Civil"`, `"Mechanical"`, `"EE)"`). A pure helper (`services/university_service/program_display.py`) flattens these into clean labels (`Engineering — Civil`, … `Engineering — Electrical Engineering`, …), removes stray parentheses, and carries a parent context forward only after an explicit unmatched `(` in the source sequence — it does not over-infer from unrelated rows. Abbreviations expand only in a safe parent context (`EE`→Electrical Engineering under Engineering; otherwise the abbreviation is preserved, e.g. `Business — EE`). The raw `UniversityProgram.name` is never mutated; the serializer adds a computed `display_name` per program and a top-level `program_display_names[]` (see `docs/API_CONTRACTS.md`).

**Severity-aware requirement gaps.** The requirements table previously showed a binary `on_track` / `gap`. It now derives a graded status from the actual numeric gap, per metric. IELTS: at/above threshold → on track; within 0.5 → near target; 0.5–1.0 → moderate; 1.0–1.5 → substantial; 1.5+ → significant. SAT: within 50 → close; 50–100 → below target; 100–150 → well below; 150+ → significant. A hard rule applies everywhere — the UI never shows "On track" when the student's score is below the relevant threshold. This fixes a prior bug where the IELTS *competitive* row was hard-coded to `on_track` whenever the university had any competitive value, regardless of the student's score; both the minimum and competitive rows now run the same comparison. GPA is compared on the normalized 4.0 estimate only (never raw 5.0 vs 4.0); the row shows the original scale, the normalized estimate, and a "converted for comparison only" note. Missing benchmarks or scores render as "Not verified" / "Not enough data" rather than a false on-track. Short labels live in the status badge; the concrete numeric gap and explanation live in a hover tooltip so the table stays uncluttered.

The same severity thresholds feed the Fit Score's academic subscore so a ~300-point SAT gap reduces academic fit more than a 0.5 IELTS gap, instead of both applying a flat penalty. This is a weighting refinement only: the fit API response contract is unchanged (no new fields), planned retakes remain conditional context rather than a current-score boost, and none of this introduces admission-probability, odds, or chance language.

## ADR-033: Derived application timelines and deadline intelligence

- **Status:** Accepted
- **Date:** 2026-07-01

Each tracked application gets an independent, source-aware planning timeline without new persistence or a parallel suggestion system. `GET /api/applications/{id}/timeline/` (backed by the pure `application_service/timeline.py`) assembles the view fresh on each request from data that already exists — the tracker item, the linked university's verified/imported deadline and scholarships, the caller's essays for that university, official College Board exam dates, linked roadmap tasks, and milestones. Deadlines already lived on `University.application_deadline` + `deadlines_text`, `UniversityScholarship.deadline`, and the tracker's own date fields (there is no separate `UniversityDeadline`/`UniversityEssay` model), so the timeline derives rather than duplicates.

Every date carries an explicit confidence: `verified` (university deadline with a `verified` field verification), `partial` (imported/source-aware value without a verified record, or an official scholarship date), `user_provided` (entered on the tracker/milestone), `estimated` (a suggested checkpoint), or `missing`. A missing deadline is surfaced as "Deadline not verified yet" with a verify action — never treated as safe — and EduVerse never invents an official university or exam date. Urgency is a pure function of days remaining (`far`/`upcoming`/`soon`/`urgent`/`critical`/`overdue` at 90/30/14/7/0 boundaries), mirrored identically in the frontend list filter and dashboard widget.

Suggested finish dates are phase-aware: each checkpoint (exam registration, essay brainstorm, essay draft, recommendation request, financial-aid forms, final review) is worked back from a real reference deadline by a fixed offset and only appears when days-until-deadline falls in that checkpoint's applicable window. A deadline more than ~6 months out therefore produces only calm long-lead planning items, and one inside ~2 weeks produces only a final review — never unrealistic long-term work. These suggested dates are informational in the timeline; the actionable, idempotent "Add to roadmap" continues through the existing `suggestions_service`, which already generates the same windows, so there is a single source of truth for roadmap creation.

Linked exams reuse the ADR-032 gap-severity helpers, add planned-retake context from the profile's `exam_plans`, and flag `scores_arrive_before_deadline: false` when an official SAT/AP test date (plus a score-release lag) lands after the application deadline — warning "this exam may not help this application cycle" rather than assuming a planned retake raises the current score. `ApplicationMilestone` gained `priority` and `notes` (migration `0002`) so milestones are more expressive while add/save/complete stay reliable. None of this introduces admission-probability, odds, or chance language.

## ADR-034: University recommendation engine as a balanced, source-aware planning list

- **Status:** Accepted
- **Date:** 2026-07-01

`GET /api/v1/universities/recommendations/` turns the existing single-university `calculate_university_fit` engine into a real 20-25 university admissions-planning list, built entirely from data already computed or already stored — no new prediction model, no invented university data. The audit found the foundation was already substantial (fit score, category, confidence, subscores, strengths/risks/missing-fields/next-actions, conditional planned-retake notes, cost/GPA normalization) and reused it directly rather than duplicating logic.

**Category bucketing.** The fit engine's five categories (`dream`/`reach`/`competitive`/`target`/`safety`) collapse `competitive` into `reach` at the recommendation layer only — the per-university `/fit/` endpoint's five-category contract is untouched. The engine assembles a balanced list (quotas: 5 dream / 7 reach / 8 target / 6 safety) rather than a flat top-N by score, so a student never sees 25 near-identical target schools. "International" is a cross-cutting boolean facet (`university.country != profile.country`), not a fifth additive bucket — a dream school abroad is both `dream` and `is_international`, matching the observation that international overlaps the other categories rather than sitting apart from them. Universities the fit engine cannot categorize (no comparable data at all) are excluded from the list and counted in `excluded_low_data_count` rather than silently forced into a bucket.

**Program matching without invention.** `_match_programs` checks the university's real `programs[]` (through the ADR-032 `program_display` helper for clean names) for an exact intended-major match; if none exists, a small, explicit set of subject clusters (CS/engineering, business/economics, politics/law/IR, biology/pre-med, psychology, social sciences, humanities, arts/design, education, environmental studies, data/AI) finds a *related* program instead. When neither matches, `recommended_programs` is empty and `program_data_verified` communicates whether the university has any program data at all — never a guessed program.

**Cost, deadline, and round honesty.** `cost_risk` (`low`/`moderate`/`high`/`unknown`) is qualitative, not a fabricated budget threshold, because no budget-preference field exists in the profile (per the "do not invent preference" rule, this was left missing rather than added as new onboarding scope). `deadline_confidence` mirrors the ADR-033 timeline's verified/partial/missing levels, and `urgency` reuses its exact day thresholds via a local pure copy (`university_service` cannot import `application_service`'s helper without a circular import, since `application_service` already imports `university_service`). Application rounds are parsed from the raw `deadlines_text`/`application_requirements` text with word-boundary regex (no per-round deadline table exists), and the *recommended* round factors in days-remaining plus a coarse essay/exam-readiness signal (`profile.essay_status`, fit engine SAT/IELTS risk codes) — a genuine, bounded planning heuristic, not an invented ED/REA policy.

**Guardrails carried over unchanged.** The ultra-selective "never safety below 10% acceptance" rule and the "planned retake never boosts the current score" rule already existed in the fit engine and needed no new code — they were verified with new regression tests at the recommendation layer. `is_shortlisted`/`application_id` reuse the existing shortlist and `ApplicationTrackerItem` machinery unchanged (idempotent by construction), and two bulk lookups keep the whole recommendation computation at a small constant number of queries regardless of catalog size. The mandated disclaimer ("This is a fit estimate based on available profile and university data. It is not an admissions prediction or guarantee.") is returned by the API and duplicated as a translated i18n string for display, since it is the one sanctioned place the word "guarantee" appears (to negate it).
