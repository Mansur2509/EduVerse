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

### Bulk dataset import

A larger real dataset (80 institutions) can be imported from an XLSX workbook through the admin UI:

1. Sign in with an admin/staff account.
2. Open `/admin/university-import`.
3. Upload `Universities Data.xlsx`.
4. Run dry-run and review the report.
5. Run execute only when skipped rows, warnings, questionable SAT placeholders, and source URL counts look safe.

The same importer remains available as a local/ops fallback:

```
python manage.py import_universities_xlsx "backend/data/universities/Universities Data.xlsx"
```

Useful flags: `--dry-run` (parse + report, roll back), `--replace-existing` (overwrite instead of filling only blanks), `--include-questionable-stats` (store placeholder-looking SAT values as `estimated` instead of dropping them), `--default-verification {verified|partial|estimated}` (default `partial`), `--source-label "..."`, `--report <path>`.

Parsing/normalization lives in `services/university_service/xlsx_import.py`; the admin upload flow and management command are thin wrappers around the same parser. Data-quality policy enforced by the importer:

- **Idempotent upsert.** Universities are matched by a slug derived from the name with any trailing `(...)` stripped, so re-running never duplicates and rows that overlap the curated seed catalog are *enriched* in place. Existing scalar values and curated `UniversityFieldVerification` rows are preserved unless `--replace-existing` is passed.
- **Never invent data.** Anything that cannot be parsed confidently is preserved as raw text (`deadlines_text`, `application_requirements`, `ap_recommendations`, `financial_aid_notes`, `scholarships_text`, `essay_requirements`) and the row is flagged in the JSON import report. Missing fields stay `null`/blank.
- **Acceptance rate** is stored as a percentage number (e.g. `0.038` → `3.80`, `"28.0%"` → `28.00`), matching the existing catalog convention.
- **Tuition**: numeric amount + currency. Currency is read from a `$ £ € ¥` symbol first, otherwise inferred from the country. When the source writes a `$` figure for a non-US institution, the currency is kept as the source's USD-equivalent and a note is added to `data_quality_notes`.
- **USD cost normalization**: source amounts are preserved in `*_original_amount` / `*_original_currency`. Comparable `*_usd_amount` fields are populated only when the source currency is already USD or a stored `ExchangeRate` exists. EduVerse does not invent exchange rates; missing rates produce a low-confidence note and leave USD values blank until an official/source-reviewed rate is added.
- **Excel serial dates** (e.g. `45565`) and ISO/`Mon D, YYYY` strings are both parsed for `Last Verified Date` and deadlines.
- **Placeholder SAT detection.** Identical SAT 25/50/75 percentiles (e.g. the `550/550/550` rows) are treated as placeholders: by default they are *not* stored as statistics, are flagged in the report, and a `data_quality_notes` caveat is written. `--include-questionable-stats` stores them but marks the verification `estimated`, so admissions-fit never treats them as trustworthy.
- **Textual GPA** (A-Level / IB grade strings) is never forced into the numeric `gpa_average`; it is preserved in `data_quality_notes`.
- **Per-field verification.** Where a primary source URL and a verified date exist, a `UniversityFieldVerification` row is created (default status `partial`).

Imported universities are `is_published=True, is_demo=False`. Admin uploads create a `UniversityImportJob` with row-level report JSON plus running progress/heartbeat fields; uploaded temporary files are deleted after processing when possible and are never committed to the repo. A management-command real run can also write a timestamped JSON report (`import_report_*.json`) next to the workbook (git-ignored). To add a future dataset, upload the new workbook or point the command at it; the same upsert/verification rules apply.

## Events

Preferred sources:

- official organizer page
- official registration page
- official institution or venue page

Community submissions remain `pending` until moderation. A source link is mandatory for public approval.

## Exams

Official specifications may inform learning objectives, timing, structure, and question format. Questions, answer options, explanations, and lessons stored by EduVerse must be original or explicitly licensed.

Official SAT/AP date guidance is stored in `exam_content_service.OfficialExamDate`. A date can be marked `verified` only when its `source_url` is on `collegeboard.org`; non-College Board sources may be stored as unverified research notes but must not power official-date roadmap claims. When no verified SAT/AP date exists, roadmap generation creates a verification task instead of inventing a deadline.

## Seed data

Development seed records are fictional or clearly labeled demonstration content. They must not be shown as current real-world opportunities.

## Refresh policy

Phase 1 should assign freshness intervals by data type. Admissions deadlines and event dates require frequent verification; historical program descriptions may tolerate longer intervals.
