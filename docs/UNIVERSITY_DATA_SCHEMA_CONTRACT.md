# University Data Schema Contract

This contract defines the canonical 72-column university admissions workbook used by the CLI importer in `backend/services/university_service/data_import.py` and the machine-readable schema in `backend/services/university_service/import_schema.py`.

The first 10-50 rows of the original `Universities Data.xlsx` `Database` sheet are the practical alignment reference: row 1 is the header, column A is always the university name, column B is the country, column C is the city, and URL columns contain actual `http(s)` URLs. The phase34 workbook follows the expanded version of the same rule with 72 canonical columns.

## Row Alignment Rules

- `Name` must be an institution name. It must not be a country, URL, city, or blank.
- `Country` must be country-like and must not be a URL.
- `City` must be city-like and must not be a URL or country.
- If a row starts `Country, City, URL, URL...`, the importer classifies it as `shifted_left_missing_name`.
- A shifted row may be repaired only when at least 5 later cells repeat the same university-name prefix before a colon and the website domain plausibly matches that identity.
- Repaired rows are marked `repaired_shifted_missing_name` in audit output.
- Low-confidence shifted rows are not imported. They go to manual review with `shifted_row_unrepairable`.
- The importer never silently shifts columns, invents a missing name, or imports a row whose identity columns are unsafe.

## Column Contract

| Column name | Expected type | Valid example | Invalid examples | Import behavior | Visibility |
|---|---|---|---|---|---|
| Name | string | Massachusetts Institute of Technology (MIT) | USA; https://mit.edu; blank | Required. Reject if country/URL. May be repaired only by high-confidence shifted-row rule. | public |
| Country | string | USA | Cambridge, MA; https://example.edu | Required. Used for matching and dedupe. | public |
| City | string | Cambridge, MA | USA; https://example.edu | Optional location text. Reject URL/country-like values in row alignment. | public |
| Official Website | url | https://www.mit.edu/ | see website; mit.edu only | Store normalized URL only. Strip tracking params. | public |
| Admissions URL | url | https://mitadmissions.org/ | check portal; admissions page varies | Store normalized URL only. | public |
| Admissions Website | url | https://mitadmissions.org/apply/ | see official website | Store normalized URL only. | public |
| Financial Aid Website | url | https://sfs.mit.edu/ | financial aid available | Store normalized URL only. | public |
| Application Portal | url | https://apply.mitadmissions.org/apply/ | Common App maybe | Store normalized URL only. | public |
| International Students Office | url | https://iso.mit.edu/ | international office | Store normalized URL only. | public |
| Virtual Info Session | url | https://mitadmissions.org/visit/ | virtual/open-day route | Store normalized URL only. | public |
| Majors | list_string | Engineering; Computer Science; Physics | program list varies; verify exact majors | Dedupe concrete majors. Skip generic comments. | public |
| Deadlines | string | Early Action: Nov 1; Regular Decision: Jan 1 | verify exact deadline; deadline varies | Store specific deadline text only. No invented official dates. | public |
| Admissions Cycle Target | enum_string | Fall 2027 | current cycle maybe | Store controlled planning cycle text when explicit. | public |
| Standardized Testing Policy | enum_string | Test optional for 2026 entry | check official website | Store sourced policy text only. | public |
| SAT 25th | number | 1510 | strong SAT; no generated number | Store integer in valid SAT range. Prose skipped. | public |
| SAT 50th | number | 1540 | median high | Store integer in valid SAT range. Prose skipped. | public |
| SAT 75th | number | 1570 | top score range | Store integer in valid SAT range. Prose skipped. | public |
| IELTS Minimum | number | 7.0 | English required; see site | Store decimal 0-9. Prose skipped. | public |
| IELTS Competitive | number | 7.5 | competitive profile means 7+ | Store decimal 0-9. Prose skipped. | public |
| Average GPA | number | 3.90 | country average; average for this country | Store 4.0-scale numeric only. Generic country averages skipped. | public |
| Acceptance Rate | percent_or_text | No central undergraduate admit rate published | no generated percentage; 12 maybe | Store valid percentage or controlled not-published text. No fake exact rates. | public |
| QS World University Ranking | number | 1 | top tier | Store integer rank and optional year. | public |
| QS Overall Score | number | 99.2 | excellent | Store decimal 0-100. Prose skipped. | public |
| Tuition | number_or_text | USD 61990 | international tuition uses official fee schedule | Store amount when parseable plus source note. Skip vague commentary. | public |
| Scholarships | string | MIT need-based aid is available to admitted students | scholarships available | Store specific aid text. Skip generic availability. | public |
| Need-based Aid | string | Need-based financial aid available for undergraduates | available for eligible students | Store specific aid text. Skip generic boilerplate. | public |
| Merit Scholarship | string | No central merit scholarships for first-year undergraduates | check website | Store sourced controlled text. | public |
| Other Scholarships | string | External scholarships listed by financial aid office | see official website | Store specific aid text or controlled not-published value. | public |
| Scholarship Links | list_url | https://sfs.mit.edu/undergraduate-students/ | scholarship page | Store valid URLs only. | public |
| AP Recommendations by Major | list_string | Engineering: Calculus BC; Physics C | generic AP block | Store sourced major-specific recommendations only. | public |
| Application Requirements | list_string | Common App; counselor recommendation; transcript | check portal | Store concrete requirements only. | public |
| Essays | list_string | MIT short-answer questions, official prompt page linked | prompt varies; invented word limit | Store sourced essay requirement text only. No invented prompts/limits. | public |
| Profile Evidence | ai_only_string | MIT: research, technical projects, olympiad evidence | same generic profile text across schools | Store internal evidence context only when school-specific. | ai_only |
| Activities | ai_only_string | MIT: maker projects and STEM extracurriculars | initiative/curiosity/collaboration template | Store internal context only when school-specific. | ai_only |
| Honors / Olympiads | ai_only_string | MIT: math/science olympiad evidence can support fit | generic honors recommended | Store internal context only. | ai_only |
| Research Experience | ai_only_string | MIT: independent STEM research aligns with academic mission | any research helps | Store internal context only. | ai_only |
| Portfolio | ai_only_string | Architecture applicants may need portfolio evidence | portfolio if applicable | Store internal context only. | ai_only |
| Essay Drafts | ai_only_string | MIT: draft why-major and community answers against official prompts | problem/preparation/fit/contribution/reflection | Store internal context only. No ghostwriting. | ai_only |
| Recommendation Letters | ai_only_string | MIT: teacher recommendations required by application instructions | get strong recommendations | Store internal context only. | ai_only |
| What They Look For | ai_only_string | MIT: evidence of technical creativity and collaboration | copied school template | Store school-specific context only. | ai_only |
| Preferred Student Profile | ai_only_string | MIT: applicants showing problem-solving in STEM contexts | same sentence for every school | Store school-specific context only. | ai_only |
| Who They Seek | ai_only_string | MIT: students who use technical skill to solve real problems | generic ambitious students | Store school-specific context only. | ai_only |
| Student Traits Mentioned by University | ai_only_string | collaboration; curiosity; initiative, sourced from admissions pages | personality traits mentioned | Store sourced trait context only. | ai_only |
| Alumni Profile Evidence | ai_only_string | Official alumni outcome page shows research/industry pathways | alumni successful | Store sourced internal context only. | ai_only |
| Published Admitted Student Essays | ai_only_string | Not centrally published | sample admitted essays online | Store controlled value or sourced link only. | ai_only |
| Official Admissions Messaging | ai_only_string | MIT admissions messaging emphasizes match and contribution | source of truth is website | Store sourced school-specific messaging only. | ai_only |
| Student Life Page Signals | ai_only_string | MIT student life pages emphasize maker culture and collaboration | student life is vibrant | Store sourced signals only. | ai_only |
| Graduate/Alumni Outcomes | ai_only_string | Official outcomes page reports graduate study and employment paths | alumni have good outcomes | Store sourced outcomes only. | ai_only |
| Sample Admitted Essays | ai_only_string | Not centrally published | fake essay sample | Store controlled value or official source only. | ai_only |
| Essay Themes | ai_only_string | MIT: collaboration, problem-solving, community contribution | problem/preparation/fit/contribution/reflection | Store sourced/high-specificity themes only. | ai_only |
| Research/Leadership Themes | ai_only_string | MIT: technical initiative and research depth | build/test/publish/lead | Store school-specific themes only. | ai_only |
| Personality Traits Mentioned | ai_only_string | curiosity; collaboration; resilience, from official pages | initiative/curiosity/collaboration template | Store sourced traits only. | ai_only |
| Academic Interests Mentioned | ai_only_string | engineering; computing; physical sciences | any major | Store sourced interests only. | ai_only |
| Institutional Values | ai_only_string | Mens et Manus; public impact; technical creativity | generic excellence | Store school-specific values only. | ai_only |
| Source URLs | list_url | https://mitadmissions.org/apply/ | homepage only when claim needs deeper page | Store valid supporting URLs. Prefer direct claim source. | admin |
| Last Verified Date | date | 2026-07-08 | last week; recently | Store valid date. | admin |
| Verification Status | enum_string | verified | probably verified | Store controlled status: verified, partial, estimated, missing. | admin |
| Data Source | admin_string | Official admissions page | web search | Store operator-facing source label. | admin |
| Notes | admin_string | Requires manual review for programme-specific tuition | source of truth | Store operator notes only. Not student-facing if sensitive. | admin |
| Profile Evidence Score | system_score | 8 | high; 0; 11 | Store integer 1-10 only. System use. | system |
| Activities Score | system_score | 7 | strong activities | Store integer 1-10 only. System use. | system |
| Honors / Olympiads Score | system_score | 6 | olympiads useful | Store integer 1-10 only. System use. | system |
| Research Experience Score | system_score | 8 | research heavy | Store integer 1-10 only. System use. | system |
| Portfolio Score | system_score | 4 | portfolio maybe | Store integer 1-10 only. System use. | system |
| Subject Passion Score | system_score | 8 | passionate | Store integer 1-10 only. System use. | system |
| Curiosity Score | system_score | 8 | curious | Store integer 1-10 only. System use. | system |
| Originality Score | system_score | 7 | original | Store integer 1-10 only. System use. | system |
| Leadership Score | system_score | 6 | leader | Store integer 1-10 only. System use. | system |
| Community Impact Score | system_score | 6 | impact | Store integer 1-10 only. System use. | system |
| Research Fit Score | system_score | 8 | good research fit | Store integer 1-10 only. System use. | system |
| Olympiads Score | system_score | 6 | olympiad score high | Store integer 1-10 only. System use. | system |
| Profile Scoring Source | ai_only_string | Derived from official admissions pages and stored source URLs | model guessed | Store internal scoring provenance. | system |

## Audit Output

Audit CSV fields include:

| Field | Meaning |
|---|---|
| source_sheet_name | Workbook sheet name or `(file)` for CSV/TSV. |
| source_row_number | Original worksheet row number. |
| row_number | Importer run row number after sheet selection. |
| raw_name | Source `Name` value before any shifted-row repair. |
| normalized_name | Normalized identity used for matching. |
| university_name | Final row identity after repair, if any. |
| country | Final country after repair, if any. |
| row_alignment_status | `aligned`, `repaired_shifted_missing_name`, or a shifted/manual-review status. |
| matched_university_id | Existing or newly-created `University.id` when matched. |
| action | `create`, `update_missing`, `skip_duplicate`, `repair`, or `manual_review`. |
| field_name | Canonical column name or `__row_alignment__`. |
| raw_value | Original source cell. |
| cleaned_value | Cleaned value that may be written. |
| status | Cell status such as `accepted`, `normalized`, `skipped_placeholder`, `skipped_boilerplate_suspected`, or `skipped_wrong_university_prefix`. |
| reason | Deterministic reason. |
| confidence | Importer confidence in the classification. |

Manual-review CSV fields include the audit identity fields plus `raw_first_5_cells`, `extracted_possible_name`, `detected_country`, `detected_city`, `possible_reason`, `existing_value`, `new_cleaned_value`, and `suggested_action`.

## Public API Safety

Student-facing university list/detail/compare/recommendation endpoints must not expose:

- skipped raw cells;
- audit rows;
- manual-review rows;
- row hashes/import batch logs;
- admin notes that are not intentionally public;
- `raw_context_json`;
- system signal weights;
- AI-only prompt/context fields.

Only public university profile fields, verified/source-aware public supporting records, and explicit public source links may be serialized.
