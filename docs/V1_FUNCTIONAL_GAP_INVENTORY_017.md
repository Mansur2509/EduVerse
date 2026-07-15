# V1 Functional Gap Inventory (017)

Produced by a full crawl of every current frontend route (three parallel audits covering
core workflow, planning tools, and community/admin screens), cross-checked file-by-file
against actual call sites, sibling implementations of the same pattern, and backend
support. Every finding below was independently verified — the assigned auditors were
explicitly instructed to confirm before flagging, not to guess from a grep hit alone.

Classification:
- **Must fix** — broken or silently-failing behavior on a feature exposed in the current UI.
- **Should fix** — real gap, lower severity or larger scope than a one-line fix.
- **Future** — explicitly out of current V1 scope (already tracked elsewhere).
- **Intentional** — deliberately disclosed limitation, not a bug.

---

## Must fix for current V1

### GAP-001 — Silent failures on notification actions
**Route:** `/notifications` · `frontend/src/screens/notifications/index.tsx`
**Problem:** `updateStatus` (:116) and `handleMarkAllRead` (:125) have no try/catch at all — a failed request becomes an unhandled promise rejection with the button appearing to do nothing. `togglePreference` (:137) has try/finally but no catch, so a failed preference save silently reverts the checkbox with no message. The initial preferences fetch (:110) does `.catch(() => undefined)`, so on failure `preferences` stays `null` forever and the panel shows "loading…" permanently with no retry.
**Severity:** High (silent failure on a primary, frequently-used screen)
**User impact:** User believes an action succeeded (or is still loading) when it didn't.
**Backend support:** Yes — real endpoints, all confirmed with call sites.
**Frontend support:** Partial — the calls are correct, only error surfacing is missing.
**Fix required:** Add try/catch around all three mutation handlers with a visible error message (reuse the `actionError` pattern already used elsewhere in this same file for the main list); give the preferences panel a distinct error+retry state instead of an infinite "loading."
**Status:** Fixed — `updateStatus`/`handleMarkAllRead` now catch and show `notifications.page.actionError`; preferences load/save now has distinct error+retry states with an optimistic per-key toggle and rollback.
**Verification:** Force a 500/network failure (e.g. via devtools offline mode) on each action and confirm a visible error appears; confirm preferences panel shows retry after a forced failure.

### GAP-002 — Silent failures on admin moderation actions
**Routes:** `/admin/moderation`, `/admin/organizers`, `/admin/reports`
**Files:** `admin-moderation/index.tsx:85` (`submitAction`), `admin-organizers/index.tsx:76` (`updateStatus`), `admin-reports/index.tsx:79` (`updateStatus`)
**Problem:** All three use try/finally with no catch — a failed approve/reject/verify/status-update silently resets button state (or, on admin-reports, silently snaps the `<select>` back to its old value) with zero explanation.
**Severity:** High (these are trust & safety / compliance actions — an admin needs to know if their action didn't take effect)
**User impact:** Admin believes a moderation action succeeded when it silently failed.
**Backend support:** Yes.
**Frontend support:** Partial — same shape as GAP-001.
**Fix required:** Add catch + visible error message to all three. `admin-feedback/index.tsx` and `admin-analytics/index.tsx` already do this correctly in the same codebase — copy that pattern.
**Status:** Fixed — all three now catch and show a per-row error message matching the `admin-feedback` pattern.
**Verification:** Force a failure on each action, confirm a visible error message appears.

### GAP-003 — Silent failures on university-detail roadmap/suggestions actions
**Route:** `/universities/[slug]` · `frontend/src/screens/universities/university-detail.tsx`
**Problem:** `handleAddToRoadmap` (:311) has no try/catch and its triggering button (:1184) has no loading/disabled binding — a failed call is an unhandled rejection with no feedback, and rapid double-clicks are unguarded. `handleRefreshSuggestions`/`handleAddSuggestion`/`handleDismissSuggestion` (:321-353) all have empty (comment-only) catch blocks — failures are fully swallowed.
**Severity:** High
**User impact:** Same class as GAP-001/002, on a heavily-trafficked detail page.
**Backend support:** Yes.
**Frontend support:** Partial.
**Fix required:** Mirror `screens/dashboard/index.tsx`'s already-correct implementation of the exact same two features (`handleGenerateRoadmap` at :268, `handleRefreshSuggestions`/`handleAddSuggestion`/`handleDismissSuggestion` at :280-311) — both screens share the same underlying capability; only the dashboard's copy handles errors correctly.
**Status:** Fixed — all four handlers now catch and set `hasPartialError`; the roadmap button now has a real `isAddingToRoadmap` loading/disabled binding.
**Verification:** Force failures on all four actions from this screen, confirm visible errors and a disabled/loading button state during the request.

### GAP-004 — Silent failures on application sub-panels
**Files:** `features/applications/ui/application-requirements.tsx:74,79`, `application-recommendations.tsx:44,49`, `application-documents.tsx:44,49`
**Problem:** `handleStatusChange` and `handleAdd` in all three files have no try/catch. Invoked as `void handler(...)`, so a failed status update or a failed "add custom requirement/recommender/document" silently reverts the control with no message.
**Severity:** High (6 call sites across 3 files, all inside the main Applications workflow)
**User impact:** Same silent-failure class as above.
**Backend support:** Yes.
**Frontend support:** Partial.
**Fix required:** Add catch + visible per-row error to all three files.
**Status:** Fixed — all three now catch and show `applications.states.actionError`.
**Verification:** Force a failure on each of the 6 actions, confirm visible errors.

### GAP-005 — Misleading error message on application/prospective-target create
**File:** `features/applications/ui/application-form.tsx:85` (`submitValues`)
**Problem:** The catch block always shows `t("applications.form.duplicateError")` ("You are already tracking an application for this university.") regardless of the actual failure — network error, timeout, session expiry, and validation errors all get the same wrong message. This shared form is used by both `/applications` and `/prospective-universities`.
**Severity:** High (actively wrong information shown to the user, not just missing information)
**User impact:** A user hitting e.g. a network blip is told they already have a duplicate application, which is false and misleading.
**Backend support:** N/A (frontend-only bug)
**Frontend support:** N/A
**Fix required:** Inspect the actual error (status code / `ApiError` type) and show a message appropriate to the real cause; keep the duplicate-specific message only for an actual 400 duplicate-validation response.
**Status:** Fixed — now classifies `ApiError.errorCode`/`status`/`data.university` before choosing timeout/network/duplicate/generic messaging.
**Verification:** Trigger each failure mode (real duplicate, forced network failure, forced 401) and confirm the message differs appropriately.

### GAP-006 — No guidance when shortlist is empty on the application/prospective-target form
**File:** `features/applications/ui/application-form.tsx:132-158`
**Problem:** The university `<select>`'s helper text only covers `shortlistLoadError` and `isShortlistLoading`; if the fetch succeeds but returns an empty array (a new user who hasn't shortlisted anything yet), nothing renders — the dropdown just shows the placeholder with zero explanation or link to go shortlist a university.
**Severity:** Medium-High (blocks a new user from understanding why they can't create a target/application, on both `/applications` and `/prospective-universities`)
**User impact:** New user confusion, unclear next step.
**Backend support:** N/A
**Frontend support:** Partial
**Fix required:** Add an explicit empty-shortlist message with a link to `/universities`.
**Status:** Fixed — added an empty-shortlist message with a link to `/universities`.
**Verification:** Open the form as a user with zero shortlisted universities, confirm a clear message + link appears.

### GAP-007 — Onboarding incorrectly tells AP-only students they have no exam plan
**File:** `features/onboarding/ui/onboarding-flow.tsx:1214-1223`
**Problem:** `hasExamPlan` (passed into `AdmissionsProposals`) is computed as `Boolean(satDate || ieltsDate || apDate || otherExamDate || satScore || ieltsScore || toeflScore || actScore)` — it never checks `form.apPlans`. A student whose only exam signal is one or more AP-subject rows still gets the "you haven't planned an exam yet" nudge. The sibling check in the *same file*, `hasAnyExamSignal()` (:469-487), was correctly updated to check `form.apPlans.some(...)` (:483) when AP moved to a multi-row structure — `hasExamPlan` was missed in that same refactor.
**Severity:** High (incorrect guidance shown to a real, common user population — any AP-track student)
**User impact:** Wrong nudge/roadmap suggestion for AP-only students.
**Backend support:** N/A
**Frontend support:** N/A (frontend logic bug)
**Fix required:** Make `hasExamPlan` check `form.apPlans` the same way `hasAnyExamSignal()` does — ideally derive both from one shared function instead of two separately-maintained boolean expressions.
**Status:** Fixed — `hasExamPlan` now delegates directly to `hasAnyExamSignal(form)`, eliminating the duplicate expression entirely.
**Verification:** Complete onboarding as a student with only an AP-subject row filled in, confirm the "no exam plan" nudge does not appear.

### GAP-008 — Legacy dead `apDate`/`apTarget` onboarding fields
**File:** `features/onboarding/ui/onboarding-flow.tsx:86-87,152-153,252-253`
**Problem:** Loaded from the profile on mount but never bound to any input and never read by `formPayload()` (:415-452, which only reads `form.apPlans`). Directly related to GAP-007 — this is the same incomplete apPlans migration.
**Severity:** Medium (dead state, but its presence is exactly what let GAP-007 happen — `hasExamPlan` above still reads the dead `apDate` variable)
**User impact:** None directly, but see GAP-007.
**Backend support:** N/A
**Frontend support:** N/A
**Fix required:** Remove the dead `apDate`/`apTarget` state once GAP-007 is fixed to use `apPlans` directly.
**Status:** Fixed — `apDate`/`apTarget` removed from the type, initial state, mount-load assignment, and `hasAnyExamSignal`'s own OR-chain.
**Verification:** Confirm no remaining reference to `apDate`/`apTarget` in this file after the fix.

### GAP-009 — Essay/Roadmap forms missing double-submit guard
**Files:** `screens/essays/index.tsx:651-661` (never passes `isSubmitting` to `EssayForm`), `screens/roadmap/index.tsx:574` (passes a hardcoded `isSubmitting={false}` literal)
**Problem:** Both forms' Save/Create buttons can never be disabled while the request is in flight, so a fast double-click fires duplicate create/update requests. `screens/prospective-universities/index.tsx` (:47,134,157,265) shows the correct pattern — a real `isSubmitting` state set around the request and passed through.
**Severity:** Medium (real duplicate-request risk, not just cosmetic — worth checking whether the backend has a uniqueness constraint that would reject the duplicate cleanly or actually create two rows)
**User impact:** Possible duplicate essay/roadmap-task records from a double-click.
**Backend support:** N/A
**Frontend support:** N/A (frontend wiring gap)
**Fix required:** Add real `isSubmitting` state to both screens and pass it through, matching the prospective-universities pattern.
**Status:** Fixed — both screens now track real `isSubmittingForm` state around the request and pass it through.
**Verification:** Rapidly double-click Save on both forms, confirm only one request fires (check network tab) and the button visibly disables.

### GAP-010 — Events list and My Events show stale data with no loading feedback on refetch
**Files:** `screens/events/index.tsx:236,269-277`, `screens/events/my-events.tsx:79,102-104`
**Problem:** Both screens' loading guards are only `isLoading && <empty array>`, true solely on first load. Changing a filter, paging, or switching the My-Events List/Calendar tab re-triggers a fetch but the UI keeps showing the previous (possibly differently-scoped) results with no spinner/skeleton/"refreshing" indicator until the new data arrives — `my-events.tsx` specifically can show the calendar view rendering the list view's smaller, differently-paged dataset for a moment. `screens/universities/index.tsx:978` already solves this exact problem with a "· Refreshing" indicator next to the result count.
**Severity:** Medium (confusing but not incorrect once settled; no data corruption)
**User impact:** Momentary confusion, appears unresponsive or shows wrong-scoped data during the fetch window.
**Backend support:** N/A
**Frontend support:** N/A
**Fix required:** Add the same "refreshing" indicator pattern used in `universities/index.tsx` to both files.
**Status:** Fixed — added a shared `isRefreshing` prop to `CollapsibleFilterPanel` (used by `events/index.tsx`) and a standalone refreshing line on `my-events.tsx`.
**Verification:** Change a filter/page/tab and confirm a visible refreshing indicator appears instead of a silent stale render.

### GAP-011 — `updateUser`/account-update capability is completely unreachable
**Files:** `features/auth/api/auth-api.ts:41` (`updateCurrentUserRequest`), `features/auth/model/auth-context.tsx:130` (`updateUser`)
**Problem:** Both exist, are correctly implemented, and are exported — but `updateUser` has zero call sites anywhere in any screen or component. There is currently no UI path to update the account's own `full_name` (or any other auth-context-level field) anywhere in the app.
**Severity:** Medium today; becomes directly relevant to Phase 3 (Settings) since this is the natural mechanism a Settings "Account" section should use.
**User impact:** No way to correct your own display name from the UI.
**Backend support:** Yes (confirmed working, just unused).
**Frontend support:** Function exists, wiring doesn't.
**Fix required:** Wire this into the new Settings "Account" section (Phase 3) rather than building a parallel mechanism.
**Status:** Fixed — wired into the Settings "Account" section's display-name form; verified live (save → reload → persisted via `/api/auth/me/`).
**Verification:** From Settings, change display name, reload, confirm it persisted via `/api/auth/me/`.

---

## Should fix before production

### GAP-012 — Application-essay linkage has no frontend UI
**Files:** `features/applications/api/applications-api.ts:191` (`getApplicationEssaysRequest`), `:195` (`createApplicationEssayRequest`) — both confirmed orphaned (zero call sites). The only essay-related control in `screens/applications/index.tsx` is a manual `essays_status` dropdown (:875, a plain enum the user sets by hand), not a real linked-essay list/creation view.
**Severity:** Medium — the backend feature (tested: essay creation scoped to an application, essay list scoped to an application) exists but isn't reachable.
**User impact:** Users can't actually link or create essays from within an application's workspace; the status dropdown is a manual proxy, not the real thing.
**Backend support:** Yes, tested.
**Frontend support:** No — this needs a real UI addition (a small panel listing linked essays + "create essay for this application"), which is a larger lift than the one-line fixes above.
**Fix required:** Build a linked-essays panel in the application detail view using the existing, already-tested backend endpoints.
**Status:** Open, deferred — flagging clearly rather than rushing a shallow implementation in an already-large release.

### GAP-013 — Roadmap source-type filter missing a valid option
**File:** `screens/roadmap/index.tsx:57-67` (`ROADMAP_SOURCE_TYPES`)
**Problem:** Lists 9 of the 10 valid `RoadmapSourceType` values (`entities/roadmap/index.ts:18-28`) — missing `"cached_assessment"`. A task with that source type displays fine on its card but can never be isolated via the filter dropdown.
**Severity:** Low-Medium
**Fix required:** Add the missing value to the const array.
**Status:** Fixed — `"cached_assessment"` added to `ROADMAP_SOURCE_TYPES`.
**Verification:** Confirm a `cached_assessment`-sourced task appears when that filter is selected.

### GAP-014 — Essay feedback "issues" list fetched but never displayed
**File:** `screens/essays/index.tsx:1059`
**Problem:** `EssayFeedback.issues: string[]` is fetched and its `.length` checked, but the actual issue text is never rendered — only the sibling `strengths` array is rendered as a bulleted list (:1044-1058). No `essays.feedback.issues` translation key exists, suggesting this section was never built rather than intentionally hidden.
**Severity:** Medium (a real piece of AI feedback the student paid attention-cost for is invisible)
**Fix required:** Add the missing rendering block + i18n keys, mirroring the `strengths` block.
**Status:** Fixed — added an "Areas to improve" list mirroring `strengths`, with a pointer to the revision checklist for full detail, plus `essays.feedback.issues`/`essays.feedback.issue.*` keys across all 4 locales.

### GAP-015 — Dynamic i18n keys built from unbounded backend strings (spot-check risk)
**Files (representative, not exhaustive):**
- `screens/essays/index.tsx:1053` — `essays.feedback.strength.${strength}` where `strength` is a plain backend `string`, not a frontend enum.
- `screens/roadmap/index.tsx:564` — `roadmap.warnings.${code}` from `missing_data_warnings: string[]`.
- `screens/recommendations/index.tsx:721-725` — compound two-variable key selecting between `missingFields`/`risks` namespaces based on a runtime membership check.
- `screens/universities/university-detail.tsx:1301-1310,1317,1639,1648,1656` — several `string[]`-backed keys (`preparation_strengths`, `preparation_gaps`, `data_notes`, relevance notes, `missing_evidence`), unlike the sibling bounded `FitStrengthCode[]`/`FitRiskCode[]` fields.
- `screens/profile/index.tsx:1240,1249` — `missing_curriculum_data`/`recommended_coursework`, both bare `string[]`.
**Problem:** None of these are confirmed broken today (existing backend values all currently have matching translation keys), but nothing enforces that a new backend-emitted code ships with a matching key in all 4 locale dictionaries — the `t()` fallback degrades to printing the raw key rather than crashing (confirmed in `shared/i18n/provider.tsx:53-66`), so a future mismatch is a silent i18n leak, not a crash.
**Severity:** Low today, worth a process fix.
**Fix required:** Either constrain these backend fields to typed enums matching the pattern already used for `FitStrengthCode`/`FitRiskCode`, or add a lint/test that all currently-possible backend values have matching keys in all locales.
**Status:** Fixed — `backend/common/tests/test_i18n_dynamic_key_coverage.py` derives the current value set for each dynamic-key family directly from source (AST-parses the real `.append(...)`/`flag(...)` call sites in `feedback_engine.py`, `roadmap_generator.py`, `major_matching.py`, `curriculum_rigor.py`; imports `OPTIONAL_EVIDENCE_WEIGHTS`/`RECOMMENDED_COURSEWORK_BY_CLUSTER`/confidence constants directly; regex-parses the `FitStrengthCode`/`FitRiskCode`/`FitMissingFieldCode` TS unions) and asserts every value has a matching key in all 4 locale dictionaries. 13/13 pass today (confirming no existing gap); a future backend code addition without a matching translation key now fails this test instead of silently degrading to a raw key at runtime.

### GAP-016 — `PlannedExamFields` shared-component claim is false for the Exams screen
**Files:** `features/exams/ui/planned-exam-fields.tsx:37-40` (doc comment) vs `screens/exams/index.tsx` (does not import it)
**Problem:** The comment claims this is "the single source of truth for planned SAT/IELTS/AP fields, shared by onboarding, Profile, and the Exams page," but the Exams screen has its own separate, incompatible inline AP/SAT editor with additional fields (`registrationStatus`/`testStatus`/`result`/`notificationIntervals`) not present in the shared component's `ApPlanRow`.
**Severity:** Low (maintainability/architecture, not user-facing)
**Fix required:** Either update the comment to reflect reality, or reconcile the two implementations so there's actually one source of truth (larger effort — recommend just correcting the comment for this release and tracking reconciliation separately).
**Status:** Fixed — comment corrected to state only onboarding and Profile share this component, and that Exams has its own separate editor.

### GAP-017 — AP subject dropdown has no fallback when no official dates are seeded
**File:** `features/exams/ui/planned-exam-fields.tsx:176-188`
**Problem:** The AP subject `<select>`'s only options come from currently-seeded upcoming official AP dates. If that list is empty for any reason, "Add AP Subject" still adds a row with an empty, unusable dropdown and no free-text fallback.
**Severity:** Low (edge case, dependent on seed-data completeness)
**Fix required:** Add a free-text fallback or a clear "no subjects available" message in that state.
**Status:** Fixed — "Add AP Subject" is now disabled when no subject options are available (the existing "no upcoming AP dates" message above it already explains why).

### GAP-018 — No student-facing way to report a university/organizer/event
**File:** `features/admin-moderation/api/admin-moderation-api.ts:44` (`createUserReportRequest`) — confirmed orphaned, zero call sites.
**Problem:** The admin-side triage tooling (`admin-reports/index.tsx`) is fully functional, but nothing in the student/organizer-facing UI ever calls this endpoint — there's no "report this" entry point anywhere.
**Severity:** Medium (trust & safety gap — moderators can act on reports, but users have no way to file one)
**Fix required:** Add a report action somewhere reachable (e.g., on a university or event page) that calls this existing endpoint — this is new UI surface, not a bug fix, so sizing it accordingly.
**Status:** Open, deferred — same reasoning as GAP-012.

---

## Future roadmap, not current scope (already tracked)

- Organizer form-builder UI, participant-management UI, analytics widgets, and the student-facing "verified participation records" display — already tracked as pending tasks (events-organizer-infrastructure work). The backend for all of it is complete and tested; only the frontend surface is deferred. Confirmed still true: `getParticipationRecordsRequest` and `registrations_by_event` remain unused, consistent with this known, already-scoped gap.

## Intentional limitations (not bugs)

- **Mock subscription/pricing** (`dashboard.subscription.mock`, `beta.status.mock`) — explicitly labeled "Mock subscription"/"Mock plans" with an on-screen disclaimer that no payment is collected. Payments are out of current V1 scope per this task's own instructions.
- **Finance / Activities / Research module screens** — intentionally render a shared `BetaModuleScreen` placeholder with working links to real routes (roadmap/dashboard/events/profile). Not broken, working as designed.
- **`/onboarding` routed screen is dead code** — `AppGate` intercepts before it and shows its own inline onboarding flow for both the incomplete and complete-but-on-this-path cases, so the dedicated route/screen component is unreachable. Onboarding itself works correctly for users; this is a code-organization observation, not a functional gap. Low-priority cleanup candidate, not fixing in this release given zero user impact.
- **Dead code with no user reachability:** `widgets/module-screen/index.tsx`'s non-Beta `ModuleScreen` component (unused, and its primary button has no handler if it were ever reconnected — but it never is), `screens/content.ts` (144 lines, fully orphaned, predates the i18n refactor — raw hardcoded English), `getEssayFeedbackRequest`/`getEssayScoresRequest` (orphaned essay API wrappers), `getApplicationRequest` (orphaned, get-application-by-id never called), `entities/exam/index.ts`'s `verification_status` field (superseded by `date_status`, never read). None of these are reachable by any user; noted for future cleanup, not part of this release's fix list.

---

## Summary

- **11 Must-fix items** (GAP-001 through GAP-011), spanning notifications, admin moderation ×3, university detail, application sub-panels ×3, application-form error messaging and empty-shortlist guidance, onboarding exam-plan detection, essay/roadmap double-submit guards, and events/my-events stale-refetch feedback.
- **7 Should-fix items** (GAP-012 through GAP-018), independently re-confirmed by a fresh skeptical sweep in task 018: essay-linkage UI, one missing filter option, one missing feedback-rendering section, a family of i18n dynamic-key risks, one doc-comment/architecture drift, one edge-case dropdown fallback, and one missing report-abuse entry point. **4 of 7 fixed in 018** (GAP-013 filter, GAP-014 feedback rendering, GAP-016 stale comment, GAP-017 dropdown fallback). **3 remain open by design**: GAP-012 (essay-application linkage UI) and GAP-018 (report entry point) are real new-UI-surface work, each spun off as a separate tracked follow-up task rather than rushed into this release; GAP-015 (dynamic i18n key risk) is a process/lint-rule suggestion with nothing currently broken.
- **1 already-tracked future item** (events-organizer frontend), confirmed still accurate.
- **5 intentional/non-issues** confirmed correctly labeled or architecturally inert.

No Critical-severity findings (nothing found that corrupts data, leaks secrets, or grants incorrect access) — everything above is either a silent-failure UX gap, a wrong/missing message, one confirmed logic bug (GAP-007), or dead code.
