# UniWay V1 Release Notes

V1 is the beta release confirmed deployed and approved as of
`c745dfc` (2026-07-15) on `origin/main`, live at
`https://uni-way-beta.vercel.app` (frontend) and
`https://eduverse-vvw2.onrender.com` (backend). See
`docs/V1_LOADING_PERFORMANCE_AUDIT_020.md` (Phase 15) for the approval
verdict and production smoke-test evidence.

## What V1 includes

Authenticated student workspace with mandatory onboarding; academic
profile with curriculum/GPA normalization; university catalog with
verified-source data, filters, and conditional/semantic fit scoring;
prospective-university and application tracking with milestones,
requirements, and a strategy view; essay workspace with AI-assisted
readiness scoring (Gemini, schema-validated, cached-fallback on
provider failure) and application linkage; an admissions roadmap
generated from profile/application/essay/exam state; exam-date
planning (SAT/AP/IELTS); event discovery, registration, and organizer
management with admin moderation; a student-facing report/feedback
workflow; light/dark/system theming and a shared icon system; a
canonical public demo student account; and the loading/performance
work in `docs/V1_LOADING_PERFORMANCE_AUDIT_020.md`.

Google OAuth sign-in is intentionally excluded from V1 (UI present,
disabled with a clear explanation when the provider is not configured;
see `docs/GOOGLE_OAUTH_PRODUCTION_SETUP_015.md`).

## Release-history correction

**One previously pushed commit message overclaimed its own contents.**
Commit `7fefa41` ("Add loading/performance audit doc and cold-start UX
for new screens") says it adds a cold-start "the server may be waking
up" hint and retry action to two screens, University detail and the
application timeline panel. That description is inaccurate for what
*this specific commit* contains.

Verified via `git log --name-only` against both files:

| File | Commit that actually contains the change | Commit message |
|---|---|---|
| `frontend/src/features/applications/ui/application-timeline.tsx` (cold-start hint + retry) | `16cd55d` | "Add essay <-> application linkage UI" |
| `frontend/src/screens/universities/university-detail.tsx` (cold-start hint) | `ab3ce5e` | "Add student-facing report action for universities, events, and essay reviews" |
| `docs/V1_LOADING_PERFORMANCE_AUDIT_020.md` (246-line new file) | `7fefa41` | "Add loading/performance audit doc and cold-start UX for new screens" |

What actually happened: both screens were touched by earlier, differently-themed
commits in the same session (each commit bundled a whole file's accumulated
changes across several same-day work phases, since splitting a
deeply-interleaved diff by hunk was judged riskier than an accurate
whole-file assignment -- see that session's own Phase 13 notes). By the
time the last commit of that batch was written, its message described the
*feature* (cold-start UX) rather than checking which commit the code had
actually landed in. Commit `7fefa41` itself contains only the new
246-line audit doc -- no source code.

**No production code is missing.** Every line described anywhere in
that session's commit messages is present on `origin/main`; this is a
commit-message attribution error, not a missing-change error. Confirmed
by `git diff origin/main..HEAD --stat` returning empty at the time of
this correction (working tree matched the remote exactly) and by the
`git log --name-only` mapping above.

**Git history was intentionally left intact.** No commit was amended,
no branch was rebased, no force-push occurred, and no replacement
commit was created. This correction lives in documentation only, per
this task's explicit instruction not to rewrite public history.

## Tag

`v1.0.0` (annotated) marks `c745dfc` as the exact commit confirmed
deployed and approved for V1, per the process above.
