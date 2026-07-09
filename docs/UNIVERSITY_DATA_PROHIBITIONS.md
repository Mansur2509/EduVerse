# University Data Prohibitions And QA Contract

This document is the strict quality contract for UniWay university admissions data.
It applies to every workbook, sheet, generated row, repaired row, import preview, import audit, and public university field.

The goal is not to make a visually complete spreadsheet. The goal is a verified admissions database.

Every public cell must be one of these:

- A source-backed university-specific fact.
- A source-backed route/programme-specific fact, clearly scoped to that route/programme.
- A carefully written university-specific interpretation based on listed source URLs.
- Blank, if the fact is not verified yet.

Every unresolved public claim must go to a source queue or manual review. It must not be replaced with filler text such as `Programme-specific`, `No data`, `check official website`, or generic AI wording.

## Core Rule

Never trade accuracy for completeness.

Wrong data is worse than missing data. Generic text is worse than a blank cell. A repeated AI pattern is worse than no row. If a value cannot be verified, do not invent it and do not hide uncertainty inside public-facing prose.

## Scope

These rules apply to:

- University Data workbooks.
- `Sources` sheets.
- Import preview/dry-run logic.
- Import repair logic.
- Public university list/detail pages.
- Recommendation and fit inputs derived from university data.
- Admin-only audit and manual review exports.
- AI-assisted data generation prompts and outputs.

These rules especially apply to columns such as:

- `Majors`
- `Deadlines`
- `Standardized Testing Policy`
- `SAT 25th`
- `SAT 50th`
- `SAT 75th`
- `IELTS Minimum`
- `IELTS Competitive`
- `Average GPA`
- `Acceptance Rate`
- `Tuition`
- `Scholarships`
- `Need-based Aid`
- `Merit Scholarship`
- `Other Scholarships`
- `Scholarship Links`
- `AP Recommendations by Major`
- `Application Requirements`
- `Essays`
- `Profile Evidence`
- `Activities`
- `Honors / Olympiads`
- `Research Experience`
- `Portfolio`
- `Essay Drafts`
- `Recommendation Letters`
- `What They Look For`
- `Preferred Student Profile`
- `Who They Seek`
- `Student Traits Mentioned by University`
- `Alumni Profile Evidence`
- `Published Admitted Student Essays`
- `Official Admissions Messaging`
- `Student Life Page Signals`
- `Graduate/Alumni Outcomes`
- `Sample Admitted Essays`
- `Essay Themes`
- `Research/Leadership Themes`
- `Personality Traits Mentioned`
- `Academic Interests Mentioned`
- `Institutional Values`
- `Source URLs`
- `Last Verified Date`
- `Verification Status`
- `Data Source`
- `Notes`
- all scoring columns.

## Source Hierarchy

Use sources in this priority order.

1. Official university undergraduate admissions pages.
2. Official university international admissions pages.
3. Official university course/catalogue pages.
4. Official tuition and fee pages.
5. Official scholarship and financial aid pages.
6. Official English language/testing pages.
7. Official application deadline pages.
8. Official application portals only when they expose public requirements.
9. Official national application systems:
   - UCAS
   - Common App
   - Coalition App
   - Studielink
   - Studyinfo
   - UniversityAdmissions.se
   - uni-assist
   - Hochschulstart
   - Universitaly
   - UNEDasiss
   - provincial Canadian portals
   - JUPAS/non-JUPAS pages
   - EJU or official Japanese university routes
   - Korean university international admissions routes.
10. Common Data Set, IPEDS, NCES, government datasets, or official statistical releases.
11. QS only for QS ranking/rank score fields.
12. Reliable third-party sources only when official data is unavailable, and only with clear admin/source marking.

Do not use a university homepage as evidence for a specific claim unless the homepage itself contains that exact claim.

## Public Cells Vs Admin/QA Cells

Public fields are shown to students or used by student-facing logic.

Admin/QA fields are used for review, import audit, source tracking, or manual repair.

### Public Fields Must Not Contain

- placeholder phrases;
- source lookup instructions;
- uncertainty commentary;
- import repair notes;
- AI prompt fragments;
- manual review instructions;
- generated templates;
- unrelated student messages;
- admin notes;
- scoring rationale unless designed for public display;
- admission probability/chance/odds wording.

### Admin/QA Fields May Contain

Admin-only fields may contain a clear review state, but they must be visibly admin-only.

Allowed admin-only examples:

- `Needs official deadline source`
- `Scholarship amount source missing`
- `Course catalogue source required`
- `Row shifted left; manual review required`
- `Candidate source found, not yet verified`

These must not leak into public fields.

## Missing Data Rule

If exact data cannot be verified:

1. Search the official university source.
2. Search the official admissions PDF, catalogue, fee schedule, scholarship page, or national application system.
3. Search reliable government or official dataset sources where appropriate.
4. If still not found, leave the public cell blank.
5. Add the missing item to a source queue/manual review sheet with:
   - university name;
   - country;
   - field name;
   - current/bad value if any;
   - required source type;
   - candidate URLs if found;
   - reason;
   - date checked.

Do not fill public cells with `Programme-specific`, `No data`, `Not publicly published`, `check official website`, or similar placeholders.

## Absolute Bans

### 1. Repeated Templates

Repeated row text is banned even if the university name changes.

Forbidden:

```text
University X: students who can prove preparation through grades, projects, and leadership.
University Y: students who can prove preparation through grades, projects, and leadership.
```

Forbidden repeated content includes:

- identical majors;
- identical AP recommendations;
- identical activities;
- identical recommendation letter guidance;
- identical notes;
- identical portfolio blocks;
- identical essay themes;
- identical `Who They Seek` blocks;
- identical student trait blocks;
- identical scholarship blocks;
- identical text after `University:`;
- identical `Profile Evidence` text;
- identical `Research Experience` text;
- identical `What They Look For` text;
- identical `Preferred Student Profile` text;
- identical `Official Admissions Messaging` text;
- identical scoring vectors across many universities.

Bad:

```text
MIT: students who can prove preparation through grades + projects + impact.
Stanford: students who can prove preparation through grades + projects + impact.
Oxford: students who can prove preparation through grades + projects + impact.
```

Better:

```text
MIT: evidence should center on advanced math/science preparation, maker culture, research or engineering outputs, and problem-solving shown through built work.
Oxford Engineering: evidence should center on mathematical depth, physics preparation, tutorial-style reasoning, and course-specific academic readiness.
Stanford: evidence should show intellectual vitality, initiative, sustained contribution, and fit with the selected academic direction.
```

### 2. Placeholder Phrases

The following phrases are banned from public workbook cells.

```text
verify exact
check official website
source of truth
where applicable
not verified
not found
needs official
program list varies
official website is source of truth
see university website
planning band should be stored by programme
international tuition uses official fee schedule
selection band
competitive profile means
virtual/open-day route
estimated admitted
not captured
placeholder
Programme-specific
Course-level only
No data
Not publicly published
No central undergraduate admit rate published
No separate official competitive IELTS score published
No fixed IELTS minimum published
use official
exact eligibility from official scholarship page
external government/foundation awards
country scholarship databases
official catalogue
deadline varies
route-specific
depending policy
country average
average for this country
no generated percentage
check portal
```

If a value is unresolved, public cell stays blank and the issue moves to manual review/source queue.

### 3. Fake Exact Data

Never invent exact values.

Do not invent:

- acceptance rate;
- GPA range;
- average GPA;
- essay word limit;
- tuition;
- scholarship amount;
- application deadline;
- SAT/ACT policy;
- IELTS/TOEFL requirement;
- portfolio requirement;
- interview requirement;
- application route;
- undergraduate majors;
- number of recommendations;
- admitted student profile;
- employment outcomes;
- salary outcomes;
- alumni evidence;
- ranking score;
- AP credit or AP recommendation policy.

Bad:

```text
Acceptance Rate: 37%
Essays: 500-1,000 words
IELTS Minimum: 6.0-7.0
Scholarships: merit Yes; need Yes
Tuition: $30,000-$50,000
Average GPA: 3.6
```

Correct behavior:

- find an official source;
- write the exact sourced value;
- or leave the public cell blank and add a source queue item.

### 4. Generator Skeletons

The following AI skeletons are banned:

```text
problem; preparation; fit; contribution; reflection
build X; test Y; publish/share; lead team
initiative; curiosity; collaboration; discipline
rigor; integrity; impact; international readiness
grades + prerequisites + 2 outputs + 1 metric
project; competition; 12+ months; metric
mini-study; method + dataset/prototype + result
students who can prove preparation...
use official alumni/career pages...
no official admitted-essay database stored...
official messaging source = ...
capture admissions message as...
every stored claim needs a URL in BC
```

These are prompt scaffolds, not university data.

### 5. Wrong Majors

Majors must be real undergraduate programmes from official course/catalogue/admissions pages.

Forbidden:

- random majors copied from an old seed file;
- `Architecture` where no undergraduate architecture route exists;
- `Medicine` where international students cannot apply directly to an undergraduate route;
- `Law` where law is not an undergraduate route;
- `Aerospace Engineering` just because it sounds strong;
- `Artificial Intelligence` or `Data Science` if only graduate-level;
- `Computer Science; Finance; Medicine` copied everywhere;
- mixing unrelated programmes into one row;
- listing national fields that do not match the university catalogue.

Bad:

```text
Majors: Computer Science; Finance; Medicine; Architecture; Aerospace Engineering
```

Better:

```text
Majors: Electrical Engineering and Computer Science; Mechanical Engineering; Economics; Chemical Engineering
```

Only write the better version if those exact undergraduate programmes are verified from the official catalogue.

### 6. Wrong Application Routes

Do not assign generic routes.

Correct route patterns:

- United States: Common App, Coalition App, QuestBridge, or institutional portal, depending on the university.
- United Kingdom: UCAS for most undergraduate applications.
- Germany: HZB, uni-assist, Hochschulstart, or direct university route, depending on programme.
- Netherlands: Studielink plus university portal.
- Finland: Studyinfo.
- Sweden: UniversityAdmissions.se.
- Spain: UNEDasiss, regional pre-registration, or university-specific route.
- Italy: Universitaly or university direct route.
- Canada: provincial portal or university direct route.
- Hong Kong: JUPAS or non-JUPAS.
- Japan: EJU, direct university route, or special international route.
- Korea: university direct international admissions route.

Forbidden:

```text
Application Route: direct portal
Application Route: Common App
Application Route: UCAS
```

These are forbidden when copied without country/system verification.

### 7. Wrong Testing Policies

Do not write generic testing values.

Forbidden:

```text
SAT/ACT required
SAT/ACT optional
SAT/ACT No/route
IELTS/TOEFL Yes
IELTS 6.0-7.0
common floor 6.0-7.0 IELTS by programme
English proof required where applicable
```

Required:

- exact SAT/ACT status for the application cycle;
- required, optional, test-blind, not used, or alternative qualification route;
- official English proof requirement;
- IELTS/TOEFL/PTE/Duolingo values only when sourced;
- A-level/IB/AP equivalents only when sourced;
- entrance exam or national exam requirement where applicable;
- portfolio/interview requirement if required.

Bad:

```text
Standardized Testing Policy: SAT/ACT No/route; IELTS/TOEFL Yes
```

Better:

```text
Standardized Testing Policy: SAT or ACT required for first-year applicants for the 2026-2027 MIT application cycle.
```

Only write the better version if the official admissions page confirms it.

### 8. Wrong Essay Limits And Essay Types

Do not invent essay limits.

Forbidden:

```text
personal statement — 500-1,000 words
motivation letter — 500-1,000 words
statement of purpose — 500-1,000 words
personal statement — 300-500 words
No needed for uni essay only motivation letter
```

Distinguish:

- essay;
- personal statement;
- motivation letter;
- statement of purpose;
- short answer;
- writing supplement;
- portfolio statement;
- research proposal;
- application form question.

Known exact examples:

- UCAS personal statement: `4,000 characters total`.
- Common App personal essay: `250-650 words`.

For every other route, use the official prompt/limit only if sourced. If not sourced, leave public cell blank and queue the field.

Also remove unrelated contamination from essay cells.

Forbidden contamination example:

```text
By the way, if I applied on July 7th, will I receive the $400 discount if I pass?
```

This is not university admissions data and must be removed from every sheet.

### 9. Generic AP Recommendations

Do not copy the same AP block across universities.

Forbidden:

```text
Engineering/CS: AP Calculus BC, AP Physics C, AP Computer Science A...
```

AP recommendations must match the verified undergraduate major family.

Use official College Board course names.

Acceptable AP mapping examples:

| Major family | Possible AP recommendations if appropriate |
| --- | --- |
| Computer Science / AI / Data | AP Computer Science A; AP Calculus BC; AP Statistics; AP Physics C: Mechanics |
| Engineering | AP Calculus BC; AP Physics C: Mechanics; AP Physics C: Electricity and Magnetism; AP Chemistry; AP Computer Science A |
| Finance / Economics / Business | AP Microeconomics; AP Macroeconomics; AP Calculus AB or AP Calculus BC; AP Statistics |
| Life Sciences / Medicine-related routes | AP Biology; AP Chemistry; AP Statistics; AP Psychology |
| Architecture / Design | AP 2-D Art and Design; AP Drawing; AP Art History; AP Calculus AB; AP Physics 1 or AP Physics C where relevant |
| Law / Politics / Humanities | AP English Language and Composition; AP Comparative Government and Politics; AP United States Government and Politics; AP United States History; AP World History: Modern |

Do not recommend AP courses for a university or country where AP is irrelevant unless the route accepts AP or AP is being used as optional preparation, and label it accurately.

### 10. Generic Scholarships And Aid

Do not write vague scholarship blocks.

Forbidden:

```text
merit Yes; need Yes
external; government; country award; X prize
need-based support is route-specific
merit route: strong grades, olympiads, leadership...
government awards, embassy/foundation funding...
external government/foundation awards
country scholarship databases
```

Required scholarship format:

```text
Scholarship name — amount/value — eligibility — undergraduate/international status — source
```

Examples of acceptable structure:

```text
MIT Scholarship — need-based institutional grant; median MIT Scholarship $69,777 for 2024-2025; undergraduate financial aid recipients; source URL required.
```

```text
UCL Global Undergraduate Scholarship — £5,000 or £10,000 per year; international fee-status students; undergraduate applicants; source URL required.
```

If amount or eligibility is not published, do not invent it. Leave the public cell blank and queue it.

### 11. Wrong Tuition

Do not write vague tuition statements.

Forbidden:

```text
International undergraduate tuition uses official fee schedule...
planning band should be stored by programme
programme-specific tuition
course-level tuition
tuition varies
official fee schedule
```

Required tuition format:

```text
payer group / route — year or entry cycle — amount — currency — period — source
```

Good structure:

```text
International undergraduate, 2026 entry, Engineering group — £44,214 per year — source URL required.
```

```text
First-year undergraduate tuition, 2026-2027 academic year — $66,720 — source URL required.
```

Do not:

- mix domestic and international tuition;
- mix undergraduate and graduate tuition;
- use application fees as tuition;
- use living cost as tuition;
- use old-year fees without year label;
- convert currency unless the source is clearly stored and conversion is explicitly labeled.

### 12. Wrong Deadlines

Deadlines must include route/round and cycle.

Forbidden:

```text
deadline varies
check portal
verify exact deadline
Fall deadline
January deadline
rolling
```

Good structure:

```text
Early Decision I — Nov 1, 2026 — Fall 2027 first-year entry — source URL required.
```

```text
UCAS equal consideration deadline — Jan 14, 2026, 18:00 UK time — 2026 entry — source URL required.
```

Do not use stale years for urgency or days remaining. Store the source cycle and normalize separately for the user cycle.

### 13. Bad Source Links

Source URLs must support the actual claim.

Forbidden source-only patterns:

- only homepage;
- only QS link;
- only country study portal;
- only College Board AP link;
- only Wikipedia;
- only a generic admissions landing page when the claim is about tuition, scholarships, deadline, or testing.

Required source categories:

- undergraduate admissions;
- international admissions;
- application requirements;
- course/programme catalogue;
- tuition/fees;
- scholarships/financial aid;
- language requirements;
- application deadlines;
- testing policy;
- portfolio/interview requirement;
- essay/personal statement requirement;
- application portal;
- QS ranking page when QS fields are used.

Bad:

```text
Source URLs: https://www.university.edu/
```

Better:

```text
Source URLs: https://example.edu/undergraduate-admissions/; https://example.edu/tuition-fees/; https://example.edu/scholarships/; https://example.edu/course-catalogue/
```

### 14. Generic Profile And Signal Blocks

Do not write generic admissions language.

Forbidden:

```text
students with strong grades and motivation
rigorous academic preparation
course fit and intellectual energy
one or two deep commitments
evidence of readiness
international readiness
initiative and curiosity
leadership and impact
strong profile
well-rounded student
```

Required:

- university-specific fit;
- programme-specific preparation;
- exact prerequisites where sourced;
- evidence types connected to the major;
- activities that make sense for the academic field;
- source-aware language.

Bad:

```text
Profile Evidence: strong grades, leadership, and passion.
```

Better:

```text
Profile Evidence: for MIT engineering/CS routes, strongest evidence should include advanced math and science grades, original technical builds, research or competition outputs, and teacher evidence of independent problem-solving.
```

### 15. Unrelated Theme Mixing

Do not combine unrelated academic directions.

Bad:

```text
Marine and Antarctic Studies; Environmental Science; Medicine; ICT; Business
```

Bad:

```text
Computing Science profile evidence focused on field stations, conservation groups, and marine biology.
```

Required:

- primary academic interest;
- secondary interests that support the primary interest;
- no random cross-field bundle;
- no major-family mismatch between majors, APs, activities, essays, and profile evidence.

### 16. Formula Errors And Spreadsheet Garbage

The workbook must not contain:

```text
#REF!
#VALUE!
#N/A
#DIV/0!
#NAME?
#NULL!
#NUM!
```

Also forbidden:

- hidden duplicated blocks;
- broken formulas;
- shifted columns;
- merged-cell artifacts that break import;
- accidental student messages;
- raw prompt fragments;
- unexplained empty cells inside a batch that was supposed to be completed;
- columns pasted into the wrong sheet.

### 17. Score Column Abuse

Score columns must be integers from 1 to 10.

Affected columns include:

- `Profile Evidence Score`
- `Activities Score`
- `Honors / Olympiads Score`
- `Research Experience Score`
- `Portfolio Score`
- `Subject Passion Score`
- `Curiosity Score`
- `Originality Score`
- `Leadership Score`
- `Community Impact Score`
- `Research Fit Score`
- `Olympiads Score`

Forbidden:

```text
strong profile
good
high
8/10
8.5
N/A
same as MIT
```

Also forbidden:

- same score vector copied across many universities;
- all universities receiving the same final scores;
- scores unrelated to row evidence;
- scores used as admission probability;
- scores implying admission guarantee.

Good behavior:

- integer only;
- row-specific;
- based on verified selectivity, programme evidence needs, source depth, and profile expectations;
- documented in `Profile Scoring Source`;
- no probability/chance wording.

### 18. Notes Column Abuse

`Notes` is not a dumping ground.

Forbidden:

- generic admin boilerplate;
- copied repair text across rows;
- student messages;
- source instructions;
- prompt fragments;
- public-facing claims;
- fake confidence comments;
- repeated text such as `rewritten across profile/admissions-fit columns`.

Bad:

```text
Notes: rewritten across profile/admissions-fit columns.
```

Better admin-only note:

```text
Notes: 2026-07-09 repair pass: removed shifted essay contamination; tuition and scholarship fields still queued for official source verification.
```

If a note is not row-specific, remove it.

### 19. Admissions Chance, Probability, Odds, Guarantee

Never show or store admission probability language.

Forbidden:

```text
chance
probability
odds
guaranteed admission
likely admit
admit estimate
admission predictor
acceptance prediction
estimated admitted
```

Allowed framing:

- `Fit Score`
- `Fit Estimate`
- `Academic fit`
- `Profile fit`
- `Readiness signal`
- `Comparison against published requirements`

Every fit or recommendation feature must make clear that it is not an admission prediction.

### 20. Row Alignment And Schema Violations

Rows must match the canonical schema exactly.

Rules:

- First column must be university name.
- `Name` must not be a country.
- `Country` must be a country.
- `City` must not be a URL.
- URL columns must contain URLs.
- Score columns must contain integers 1-10.
- Date columns must contain dates or approved structured date text.
- A shifted row must not be imported silently.

Bad shifted row:

```text
Norway, Trondheim, https://www.ntnu.edu, ...
```

This means `Name` is missing and the row is shifted left.

High-confidence repair is allowed only when:

- first cell looks like country;
- second cell looks like city;
- third cell is URL;
- at least five later cells contain the same university-name prefix before colon;
- extracted name is consistent;
- domain plausibly matches identity;
- no conflicting extracted names exist.

Otherwise the row goes to manual review.

### 21. Import Safety

The importer must not:

- import placeholder text into public fields;
- overwrite good existing data with generic text;
- import shifted rows silently;
- import wrong-university prefixes;
- import boilerplate suspected across many rows;
- import field values with wrong type;
- import homepage-only source as proof for specific claims;
- import admin/AI-only fields into public serializers;
- run automatically without explicit admin action.

Dry-run must expose:

- accepted fields;
- skipped fields;
- conflicts;
- manual review rows;
- repair status;
- source quality warnings;
- boilerplate warnings;
- type validation warnings.

### 22. Wrong-University Text

A row must not contain another university's name inside source-specific fields unless it is a legitimate comparison or joint programme and clearly sourced.

Bad:

```text
Current row: Vanderbilt University
Field: University of Macau: students should show...
```

Expected behavior:

- skip field;
- mark conflict;
- send to manual review;
- do not import into public data.

### 23. Country Average And System Average Misuse

Do not use country averages as university data.

Forbidden:

```text
average for this country is 4.5 but in other system it is 3.6
country average GPA
typical GPA in this country
```

University fields need university-specific data. If unavailable, leave blank and queue.

### 24. Contaminated Cells

Any non-database message inside workbook cells must be removed.

Forbidden example:

```text
EssaysBy the way, if I applied on July 7th, will I receive the $400 discount if I pass? I saw that applicants who applied by this date receive a discount.
```

This must be treated as contamination, not transformed into data.

Expected behavior:

- remove from public row;
- add audit note if needed;
- inspect adjacent columns for shifted paste damage;
- verify row alignment.

## Column-Specific Required Formats

| Column | Required format | Forbidden format |
| --- | --- | --- |
| `Name` | Exact university name, optionally with accepted abbreviation | country name, city name, URL |
| `Country` | Country name | university name, city, URL |
| `City` | City and region if useful | URL, country-only value |
| `Official Website` | Official homepage URL | `see website`, non-URL text |
| `Admissions URL` | Direct admissions URL | homepage-only if specific page exists |
| `Majors` | verified undergraduate programme names separated by semicolons | random popular majors, graduate-only fields |
| `Deadlines` | round/route — exact date — cycle — source-backed | `deadline varies`, `check portal` |
| `Standardized Testing Policy` | policy — cycle — route — source-backed | `SAT/ACT No/route`, `IELTS Yes` |
| `SAT 25th/50th/75th` | exact sourced number or blank | invented range, commentary |
| `IELTS Minimum` | exact sourced value and route, or blank | `6.0-7.0`, `varies` |
| `IELTS Competitive` | sourced competitive value, or blank | invented higher score |
| `Average GPA` | university-specific sourced value, or blank | country average, guessed conversion |
| `Acceptance Rate` | official/CDS/source-backed number with cycle, or blank | invented percent |
| `Tuition` | payer group — year/cycle — amount — currency — period — source | `programme-specific`, vague bands |
| `Scholarships` | scholarship name — amount/value — eligibility — source | `merit Yes; need Yes` |
| `Need-based Aid` | named aid policy/programme with eligibility | generic need-based wording |
| `Merit Scholarship` | named award and amount/value if published | `merit route: strong grades...` |
| `Other Scholarships` | named external/government award if relevant | generic external funding list |
| `Scholarship Links` | direct scholarship URLs | homepage-only |
| `AP Recommendations by Major` | major-family-specific AP names | one copied AP block |
| `Application Requirements` | exact sourced requirements | generic transcript/recommendation/essay list copied everywhere |
| `Essays` | exact essay/personal statement/motivation letter prompt or limit | invented word limit |
| `Profile Evidence` | university/programme-specific evidence | generic strong profile text |
| `Activities` | major-relevant activities | generic leadership/service copied everywhere |
| `Honors / Olympiads` | field-relevant honors | generic national/international olympiad list copied everywhere |
| `Research Experience` | field-appropriate research evidence | `mini-study; method + dataset...` |
| `Portfolio` | exact requirement or field-appropriate artifact guidance | generic 3-5 artifacts everywhere |
| `Essay Drafts` | sourced prompt angle or university-specific writing guidance | copied essay skeleton |
| `Recommendation Letters` | route-specific recommendation expectations | generic teacher letter text |
| `What They Look For` | source-aware institutional priorities | generic curiosity/impact wording |
| `Preferred Student Profile` | university/programme-specific profile | copied rigorous preparation wording |
| `Who They Seek` | source-aware student type | repeated `students who can prove...` |
| `Student Traits Mentioned by University` | traits actually present in messaging | invented traits |
| `Alumni Profile Evidence` | sourced outcomes/alumni patterns | generic outcomes |
| `Official Admissions Messaging` | exact/source-aware admissions message | prompt instruction text |
| `Source URLs` | direct source URLs supporting row claims | homepage-only |
| `Last Verified Date` | ISO date of verification pass | blank after claimed verification |
| `Verification Status` | admin status from approved enum | public uncertainty filler |
| `Notes` | row-specific admin-only audit note | generic copied notes |
| score columns | integer 1-10 | prose, decimals, repeated score vectors |

## Bad-To-Good Examples

### Scholarship

Bad:

```text
Scholarships: merit Yes; need Yes; external government/foundation awards.
```

Good:

```text
Scholarships: UCL Global Undergraduate Scholarship — £5,000 or £10,000 per year; international fee-status undergraduate students; source URL required.
```

If the exact scholarship cannot be verified:

```text
Public cell: blank
Manual review: Scholarship field requires direct official scholarship source.
```

### Tuition

Bad:

```text
Tuition: international undergraduate tuition uses official fee schedule; planning band should be stored by programme.
```

Good:

```text
Tuition: International undergraduate, 2026-2027 academic year — $66,720 tuition — source URL required.
```

### Essays

Bad:

```text
Essays: motivation letter — 500-1,000 words.
```

Good:

```text
Essays: Common App personal essay — 250-650 words; MIT supplemental short-answer questions required; source URL required.
```

### Deadlines

Bad:

```text
Deadlines: ED deadline varies; check portal.
```

Good:

```text
Deadlines: Early Decision I — Nov 1, 2026; Early Decision II — Jan 5, 2027; Fall 2027 first-year entry; source URL required.
```

### Testing Policy

Bad:

```text
Standardized Testing Policy: SAT/ACT optional; IELTS/TOEFL Yes.
```

Good:

```text
Standardized Testing Policy: SAT or ACT required for first-year applicants for the 2026-2027 cycle; source URL required.
```

### Profile Evidence

Bad:

```text
Profile Evidence: strong grades, leadership, curiosity, and international readiness.
```

Good:

```text
Profile Evidence: for computer science/engineering applicants, strongest evidence should show advanced math preparation, original technical builds, research or competition output, and teacher evidence of independent problem-solving.
```

Only write this if it is consistent with the university's actual admissions/course messaging.

## Search And Repair Workflow

For every university and every important field:

1. Read the existing cell.
2. Check if it violates any banned phrase, duplicate, wrong-field, source, or fake-data rule.
3. Search direct official source.
4. Confirm the exact claim.
5. Replace only the bad cell, not the whole row.
6. Preserve existing good data.
7. Add or update direct source URL.
8. Update `Last Verified Date`.
9. Add row-specific admin note only if useful.
10. Run QA scans.

Do not bulk-fill all rows from a template.

## Required QA Gates

Every completed workbook must pass these gates.

### Gate 1: Banned Phrase Scan

No public cell may contain banned placeholder or AI-template phrases.

### Gate 2: Duplicate Scan

No exact duplicated fields across many universities.

Check:

- full-cell duplicates;
- sentence-level duplicates;
- post-prefix duplicates after `University:`;
- repeated score vectors;
- repeated AP blocks;
- repeated scholarship blocks;
- repeated notes;
- repeated essay themes.

### Gate 3: Source Scan

Every public factual claim must have a direct source URL.

Homepage-only sources fail for:

- deadlines;
- tuition;
- scholarships;
- testing;
- language requirements;
- course list;
- portfolio;
- essays;
- acceptance rate;
- GPA;
- SAT percentiles.

### Gate 4: Fake Number Scan

Reject unsourced exact values:

- percentages;
- GPA values;
- SAT/ACT values;
- IELTS/TOEFL values;
- tuition values;
- scholarship values;
- dates;
- word counts.

### Gate 5: Major Validity Scan

Majors must exist in the official undergraduate catalogue.

Reject:

- random major bundles;
- graduate-only programmes;
- professional routes unavailable to undergraduates;
- programmes unavailable to international applicants when the row targets international students.

### Gate 6: Application Route Scan

Application route must match country/system/university.

Reject generic:

- `direct portal`;
- `Common App`;
- `UCAS`;
- `institutional portal`;

unless verified for that specific university and cycle.

### Gate 7: Testing Policy Scan

Reject vague testing text.

Testing policy must identify:

- route;
- cycle;
- required/optional/test-blind/not used;
- alternatives;
- English proof values if sourced.

### Gate 8: Essay Field Scan

Reject invented limits and wrong essay type.

Essay field must not contain:

- motivation letter mislabeled as essay;
- random word count;
- unrelated messages;
- prompt fragments.

### Gate 9: Scholarship Scan

Scholarship fields must contain named scholarships or be blank with queue.

Reject:

- generic aid availability;
- government/external/foundation lists without named programme;
- unsourced amounts.

### Gate 10: Tuition Scan

Tuition must include:

- payer group;
- amount;
- currency;
- period;
- year/cycle;
- source.

Reject vague programme-specific text in public cells.

### Gate 11: Formula And Alignment Scan

Reject:

- formula errors;
- shifted rows;
- wrong number of columns;
- country in `Name`;
- URL in `City`;
- prose in score columns.

### Gate 12: Admissions Probability Scan

Reject any probability/chance/odds/guarantee language.

Allowed:

- fit;
- readiness;
- comparison;
- estimate with disclaimer.

## Banned Phrase Scan List

Use this as a starter list for automated scans.

```text
verify exact
check official website
source of truth
where applicable
not verified
not found
needs official
program list varies
official website is source of truth
see university website
planning band should be stored by programme
international tuition uses official fee schedule
selection band
competitive profile means
virtual/open-day route
estimated admitted
not captured
placeholder
programme-specific
program-specific
course-level only
no data
not publicly published
no central undergraduate admit rate published
no separate official competitive IELTS score published
no fixed IELTS minimum published
use official
exact eligibility from official scholarship page
external government/foundation awards
country scholarship databases
official catalogue
deadline varies
route-specific
depending policy
country average
average for this country
no generated percentage
check portal
students who can prove
problem; preparation; fit; contribution; reflection
build X; test Y; publish/share; lead team
initiative; curiosity; collaboration; discipline
rigor; integrity; impact; international readiness
grades + prerequisites + 2 outputs + 1 metric
project; competition; 12+ months; metric
mini-study; method + dataset/prototype + result
every stored claim needs a URL
official messaging source =
capture admissions message as
chance
probability
odds
guaranteed
likely admit
admit estimate
admission predictor
acceptance prediction
```

The scan must be case-insensitive.

## Manual Review Queue Requirements

When a field cannot be completed, do not fill it with public filler. Add it to manual review.

Manual review row must include:

- workbook name;
- sheet name;
- row number;
- university name;
- country;
- field name;
- current value;
- proposed action;
- required source type;
- candidate source URLs;
- reason;
- severity;
- reviewer;
- last checked date.

Example:

```text
University: Example University
Field: Tuition
Current value: programme-specific tuition
Action: clear public cell; verify official 2026 international undergraduate fee schedule
Required source: official tuition/fees page
Candidate URLs: https://example.edu/fees
Reason: placeholder public value
Severity: high
```

## Definition Of Done

A university row is done only when:

- first column is the correct university name;
- all columns are aligned;
- no public placeholder phrases remain;
- no unrelated contamination remains;
- majors are real undergraduate programmes;
- application route is country/system correct;
- deadlines are exact, route-specific, and cycle-labeled;
- testing policy is exact and cycle-labeled;
- IELTS/TOEFL/SAT/ACT values are sourced or blank;
- GPA and acceptance values are sourced or blank;
- tuition has payer group, amount, currency, period, year/cycle, and source;
- scholarships are named with amount/value and eligibility if published;
- essay fields use exact official prompt/limit/type, or stay blank;
- AP recommendations are major-specific and use official AP names;
- profile/signal blocks are university-specific and not copied;
- score columns are integer 1-10 and not copied across rows;
- notes are row-specific and admin-only;
- source URLs are direct and support the claims;
- `Last Verified Date` reflects the actual verification pass;
- no formula errors exist;
- no admission chance/probability/odds/guarantee language exists;
- unresolved public facts are blank and represented in manual review/source queue.

## Non-Negotiable Final Standard

No water.

No repeated templates.

No fake numbers.

No public placeholders.

No homepage-only evidence for specific claims.

No copied score vectors.

No random majors.

No invented essay limits.

No generic scholarship blocks.

No admission probability language.

Every public claim must be source-backed, university-specific, and field-correct.
