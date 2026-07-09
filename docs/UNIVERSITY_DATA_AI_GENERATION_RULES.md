# University Data AI Generation Rules

These rules apply to any human-assisted or AI-assisted generation of UniWay university admissions workbooks. The goal is a verified admissions database, not a polished-looking spreadsheet.

## Non-Negotiable Structure

- Output exactly the canonical columns defined in `docs/UNIVERSITY_DATA_SCHEMA_CONTRACT.md`.
- Do not add, remove, merge, hide, or reorder columns.
- Row 1 must be the header row.
- Column A must be `Name`. It must contain the university name, not a country, city, URL, rank, or note.
- Column B must be `Country`.
- Column C must be `City`.
- URL fields must contain actual `http(s)` URLs or be blank. Do not write "see website", "check portal", or other instructions in URL fields.
- Scores must be integers from 1 to 10. Do not write prose in score fields.
- Date fields must be real dates or blank.
- Numeric fields must be numeric or an allowed controlled value for unknown/not-published facts.

## Allowed Unknown Values

Use controlled values only when the source genuinely does not publish a fact:

- `Not centrally published`
- `No central undergraduate admit rate published`
- `Programme-specific`
- `Course-level only`
- `Not required centrally`
- blank cell when a value is unknown and no controlled value is appropriate

Do not use vague placeholders:

- `verify exact deadline`
- `see official website`
- `program list varies`
- `check portal`
- `country average`
- `average for this country`
- `not publicly available`
- `no generated percentage`
- `official catalogue`
- `selection band`
- `deadline varies`
- `not captured`
- `not verified`
- `needs official`
- `source of truth`
- `where applicable`
- `placeholder`

## No Invented Facts

Never invent:

- acceptance rates;
- GPA averages;
- tuition amounts;
- scholarship amounts;
- exact deadlines;
- SAT/ACT percentiles;
- IELTS/TOEFL thresholds;
- essay prompts or word limits;
- portfolio requirements;
- application route/portal rules;
- major lists;
- AP recommendations;
- admitted student essay examples;
- alumni outcomes.

If the source does not provide an exact value, leave the cell blank or use a controlled unknown value. Do not backfill with country averages, generic rankings, or guessed competitive profiles.

## No Repeated Templates

Do not repeat the same sentence or same post-prefix body across many universities.

Invalid pattern:

```text
University A: students who can prove initiative, curiosity, collaboration, and impact.
University B: students who can prove initiative, curiosity, collaboration, and impact.
University C: students who can prove initiative, curiosity, collaboration, and impact.
```

Invalid generator skeletons:

- `problem/preparation/fit/contribution/reflection`
- `build/test/publish/lead`
- `initiative/curiosity/collaboration`
- `grades+prereqs+outputs+metric`

Every school-specific evidence field must be materially tied to that university's official admissions pages, program pages, student-life pages, scholarships, or published outcomes.

## University Identity Safety

- A field for one university must not start with another university's name.
- Do not copy another university row and edit only the name.
- If a row starts with `Country, City, URL, URL...`, stop and repair the row before delivery. Do not rely on the importer to guess.
- If a university has a known acronym, include it in the name only when it is part of the official identity or helps source/domain verification.

## Source Rules

- `Official Website` should be the official university domain.
- Admissions, aid, portal, international office, and virtual-info links should point to the relevant page, not only the homepage.
- Claims about deadlines, testing, aid, essays, or requirements need a direct official or reliable source URL.
- Homepage-only source links are acceptable only for identity/basic website fields.
- Do not cite unrelated pages or search result pages.

## AI/System Fields

The following fields are internal only and must never be written as public claims:

- profile evidence fields;
- "what they look for" style fields;
- personality/value/theme fields;
- score fields;
- profile scoring source.

They can support fit/recommendation logic only when grounded in source URLs or clear official messaging. They must stay non-predictive.

## Final QA Before Delivery

Before a workbook is used for dry-run:

- no banned placeholder phrases;
- no repeated post-prefix templates;
- no formula errors such as `#REF!`, `#VALUE!`, `#N/A`, or `#DIV/0!`;
- no shifted rows;
- no country in the `Name` column;
- no URL in the `Country` or `City` columns;
- no prose in numeric or score fields;
- no fake exact numbers;
- no unrelated university names inside another university row;
- all public claims have a source URL or controlled unknown value;
- AI/system fields stay internal and source-aware.
