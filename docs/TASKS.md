# Tasks

## Phase 0 — Foundation

- [x] P0-001 Create repository rules and core documentation.
- [x] P0-002 Create monorepo and local environment structure.
- [x] P0-003 Create Next.js, TypeScript, Tailwind, and FSD skeleton.
- [x] P0-004 Create academic design tokens and placeholder product routes.
- [x] P0-005 Create Django/DRF modular service skeleton.
- [x] P0-006 Add initial user, profile, subscription, university, event, and exam models.
- [x] P0-007 Add API routing, serializers, permissions, and admin foundations.
- [x] P0-008 Add PostgreSQL and Docker Compose configuration.
- [x] P0-009 Add environment examples and demo seed command.
- [ ] P0-010 Run frontend dependency install, lint, and type checks. Blocked on 2026-06-22 by npm registry TLS/network errors (`ECONNRESET` and `UNABLE_TO_VERIFY_LEAF_SIGNATURE`).
- [x] P0-011 Generate backend migrations; run Django checks, migrations, seed, Ruff, and tests.
- [ ] P0-012 Validate Docker Compose startup.

P0-012 requires Docker, which was not installed in the local environment on 2026-06-22. See the latest status in the Phase 0 handoff.

## Phase 1 — Core vertical slices

- [x] **AUTH-001** Implement basic JWT registration, login, refresh, blacklist logout, current-user/profile API, frontend auth state, protected pages, and auth tests.
- [x] **UI-SYSTEM-001** Add semantic dark-first theme tokens and migrate shared/auth/profile/dashboard UI.
- [x] **I18N-001** Add dependency-free typed dictionaries, locale persistence, four locales, and a language switcher.
- [ ] **AUTH-002** Add email verification, password reset, HttpOnly refresh cookies, session/device management, and production auth hardening.
- [x] **PROFILE-001** Implement the self-only student profile aggregate, academic/contact fields, computed completion, localized responsive UI, migration, and tests.
- [x] **PROFILE-STRUCTURED-001** Implement 7 structured admissions profile item types (Activities, Honors, Olympiads, Sports, Research Projects, Essay Drafts, Portfolio Projects) with full CRUD APIs, permission-based access control, reusable frontend components, 4-language i18n, and comprehensive test coverage. All verifications passed: 53/53 backend tests, TypeScript type checks, ESLint linting, Next.js production build, and i18n parity (984 keys across 4 locales).
- [x] **EVENTS-001** Implement event lifecycle, public catalog/detail, profile-snapshot registration, cancellation, my events, localized UI, seed data, migration, and tests.
- [ ] **EVENTS-002** Build Leaflet map/calendar views, save action, and richer eligibility/recommendation filters.
- [x] **UNI-001 / UNIVERSITY-DATABASE-001 / ADMISSIONS-CALCULATOR-001** Implement university catalog search/filter, detail pages, 2-4-way comparison, self-only shortlist, and an admissions fit analysis (Reach/Competitive/Target/Safety) computed only from verified profile and university data, with "Not verified yet" honest empty states everywhere a statistic is unconfirmed. Backend: extended `University` model with nullable admissions fields, `SavedUniversity` shortlist model, `fit`/`shortlist`/`compare` actions on `UniversityViewSet`, pure fit-calculation helpers in `services.py`, 8 fictional demo universities with deliberately partial seed data. Frontend: `/universities`, `/universities/[slug]`, `/universities/compare` routes. All verifications passed: 84/84 backend tests, ruff clean, TypeScript clean, ESLint clean, Next.js build (24 routes), i18n parity (1059 keys x 4 locales). Manually verified end-to-end in the local beta (search/filter, detail, shortlist persistence across refresh, 2- and 4-way compare, fit analysis, no horizontal overflow or double scrollbar at 390px width). Found and fixed a floating-point boundary bug in the GPA-difference threshold check during manual QA.
- [x] **UNIVERSITY-DATA-VERIFICATION-001** Replace the fictional-only catalog with 15 real, source-backed universities (Penn, Princeton, Cornell, CMU, NYU, MIT, Stanford, Harvard, Toronto, UBC, Oxford, Cambridge, Bocconi, NUS, KAIST), each researched via direct official-page fetches/search-result relay (never invented). Added `is_demo` to `University` (default catalog list now excludes the 8 fictional demo records; `?include_demo=true` opts back in) and a new `UniversityFieldVerification` model giving every non-null admissions/stat/cost/deadline field a `source_url`, `last_verified_date`, and `verified`/`partial`/`estimated` status, enforced by a seed-data integrity test. Added `admissions_url`, `financial_aid_url`, `application_portal_url`, `test_policy`, `ielts_minimum`, `sat_p25`/`sat_p75`, `essay_requirements`, `qs_ranking`/`qs_ranking_year` fields. Frontend shows a `VerifiedStat` badge (Verified/Partial/Estimated) with last-verified date and source link per field, "Not verified yet" for anything unconfirmed, and a "Demo data" badge on fictional records. Fit analysis gained a `limited_data_for_category` next-action so a category assigned from only one verified statistic is never presented as a complete picture. All verifications passed: 94/94 backend tests, ruff clean, `makemigrations --check` clean, TypeScript clean, ESLint clean, Next.js build (24 routes), i18n parity (1079 keys x 4 locales). Manually verified end-to-end: real universities appear by default and demo ones are hidden until opted in, Harvard/MIT/NUS/Stanford each render the correct mix of Verified/Partial/"Not verified yet" fields, fit analysis correctly returns "Not enough verified data" for NUS despite its rich non-quantitative data, shortlist and 3-way real-university comparison work, no horizontal overflow or double scrollbar at 390px.
- [ ] **ROAD-001** Implement roadmap, milestones, deadlines, and add-event-to-roadmap workflow.
- [ ] **ESSAY-001** Implement private essay submission and feedback contracts with strict no-ghostwriting controls.
- [ ] **AI-001** Implement backend OpenRouter adapter, quotas, usage logs, safety policy, prompt-injection defenses, and provider fallback.
- [ ] **EXAM-001** Implement original question authoring/admin, practice sessions, answers, explanations, and scoring foundations.
- [ ] **FIN-001** Implement educational finance modules and quizzes with mandatory advice disclaimer.
- [ ] **SUB-001** Implement plan definitions, feature access rules, atomic usage counters, and monthly reset job.

## Recommended order

`FORMS-001 -> TICKETS-001 -> EVENTS-002 -> UNI-001 -> SUB-001 -> ROAD-001 -> ESSAY-001 -> AI-001 -> EXAM-001 -> FIN-001`

`AUTH-002` is required before production launch and may run alongside later product slices.

## Next recommended product tasks

Recommended sequence:

`FORMS-001 -> TICKETS-001 -> TELEGRAM-001 -> EXPORT-001 -> ANTIABUSE-001 -> PAYMENTS-001 -> AUTH-002`

- [x] **ORGANIZER-001** Add organizer draft creation, ownership, submission, moderation, status logs, participant access, and localized role-aware UI.
- [x] **BETA-PREVIEW-001** Connect completed modules into a coherent beta shell, command-center dashboard, complete navigation, and localized preview pages.
- [x] **LOCAL-RUN-001** Add a founder-friendly SQLite backend launcher, frontend environment preparation, preview diagnostics, and a local troubleshooting guide.
- [x] **BETA-QA-001** Complete founder visual QA, remove duplicate navigation, improve role-guard recovery, and polish mobile overflow behavior.
- [x] **AUTH-GUARD-001** Require a backend-confirmed session before mounting any product shell or content, protect catalog reads, and distinguish offline from logout.
- [x] **V1-UI-REDESIGN-001** Consolidate the beta into a coherent V1 shell, dashboard, event-first workflow, honest preview modules, and real plan comparison.
- [x] **V1-BRAND-REDESIGN-002** Apply the ivory/navy/crimson academic identity, crisp geometry, restrained typography, and EduVerse favicon across the frontend.
- [x] **ONBOARDING-GATE-001** Require backend-confirmed onboarding, add the six-step profile foundation, rule-based major exploration, exam countdowns, layout polish, and clean preview build isolation.
- [x] **V1-ADMISSIONS-ONBOARDING-FINAL-001** Add the expanded major catalog, 40-question assessment, admissions proposals, recommended classes, target countries, and evidence-based readiness.
- [x] **V1-FINAL-POLISH-CONTINUE-001** Finish independent shell scrolling, compact profile layout, event map/filter hybrid, role navigation, organizer status summary, documentation, and final local checks.
- [x] **V1-DEMO-STABILIZATION-001** Stabilize founder demo auth/onboarding, normalize fresh profile payloads, seed role-specific local demo accounts, and document the founder review checklist.
- [x] **V1-FREEZE-HANDOFF-001** Freeze the current V1 beta state in `docs/V1_HANDOFF.md`; do not start a new feature before founder visual review.
- [ ] **FORMS-001** Standardize accessible form fields, validation summaries, and translated backend error mapping.
- [ ] **TICKETS-001** Model event registration/ticket intent without introducing payment processing.
- [ ] **TELEGRAM-001** Design an opt-in Telegram notification integration with privacy and rate-limit controls.
- [ ] **EXPORT-001** Add privacy-aware user data and roadmap exports.
- [ ] **ANTIABUSE-001** Add layered abuse controls for auth, event submissions, AI usage, and public forms.
- [ ] **PAYMENTS-001** Define provider-neutral payment intents and reconciliation after ticketing and abuse controls are ready.
