# Data Sources and Provenance

## Principles

- Prefer official university, organizer, and exam-issuer pages.
- Store the source URL, title, retrieval timestamp, and official/unofficial status.
- Keep data facts separate from EduVerse interpretation.
- Display freshness and verification reminders for high-impact information.
- Never import copyrighted question-bank content.

## Universities

15 real universities are seeded (`services/university_service/seed_data.py`): University of Pennsylvania, Princeton, Cornell, Carnegie Mellon, NYU, MIT, Stanford, Harvard, University of Toronto, UBC, Oxford, Cambridge, Bocconi, NUS, and KAIST.

Preferred sources, in order:

1. Official university admissions, financial-aid, and cost-of-attendance pages (`.edu` or the institution's own primary domain).
2. Common Data Set documents when published by the institution.
3. Official national or institutional testing requirements pages.
4. topuniversities.com (QS), used only for the `qs_ranking` field, since that figure is inherently a third-party ranking rather than something a university self-publishes.

Every non-null admissions/stat/cost/deadline field on a real `University` record has a matching `UniversityFieldVerification` row recording `source_url`, `last_verified_date`, and a `status`:

- `verified` — a page was directly fetched this session and the value was read verbatim from it.
- `partial` — the value came from a search-result snippet of an official source (not independently re-fetched), or was arithmetically derived from two verified official counts (e.g. Harvard's acceptance rate, calculated from its officially published applicant/admit counts since Harvard does not publish a rounded rate itself).
- `estimated` — reserved for future manually-curated approximations; not used by the current seed data.

Do not infer missing data. A field with no confirmed source is left `null`/blank and shown as "Not verified yet" — never as zero, never guessed. Several real universities (Stanford, UBC, KAIST) intentionally have almost no populated statistics because their official sites do not publish them, or (KAIST) could not be reached this session; that is the correct, honest state, not a gap to be filled in later by estimation.

Fictional demonstration universities (`is_demo: true`, seeded via `seed_university()` in `common/management/commands/seed_demo.py`) remain available for UI/infrastructure testing but are excluded from the default catalog list and never carry `UniversityFieldVerification` records — see `docs/DECISIONS.md` for the demo-vs-real policy.

## Events

Preferred sources:

- official organizer page
- official registration page
- official institution or venue page

Community submissions remain `pending` until moderation. A source link is mandatory for public approval.

## Exams

Official specifications may inform learning objectives, timing, structure, and question format. Questions, answer options, explanations, and lessons stored by EduVerse must be original or explicitly licensed.

## Seed data

Development seed records are fictional or clearly labeled demonstration content. They must not be shown as current real-world opportunities.

## Refresh policy

Phase 1 should assign freshness intervals by data type. Admissions deadlines and event dates require frequent verification; historical program descriptions may tolerate longer intervals.

