"""Safe importer for the ~450-university / 72-column dataset.

Deliberately separate from `xlsx_import.py` (the existing async-job-backed
importer used by the admin upload UI, which targets a different 22-column
schema and its own slug-based upsert key). This module is additive: it never
touches the existing importer, its models, or its tests.

Column layout (1-indexed, matching the source spreadsheet exactly):
  1-38   public-facing university data -- stored on `University`.
  39-58  guidance/context layer for backend workflows (essay review, fit
         analysis, recommendation prep, profile improvement) -- stored on
         `UniversityGuidanceContext`, never serialized publicly.
  59     admin/source note -- stored on `UniversityGuidanceContext.notes`.
  60-72  system-only profile-scoring vector -- stored on
         `UniversitySignalWeights`, never serialized publicly.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction

from .models import University, UniversityGuidanceContext, UniversitySignalWeights

REQUIRED_COLUMNS = ("Name", "Country", "City")

# Cell values that mean "intentionally not provided" rather than real content.
# Matched case-insensitively against the *entire* trimmed cell -- never against
# a substring, so genuine prose that happens to contain these words is kept
# verbatim.
PLACEHOLDER_VALUES = {
    "",
    "n/a",
    "na",
    "none",
    "unknown",
    "tbd",
    "-",
    "not used",
    "not applicable",
    "verify on official website",
    "check official website",
    "see official website",
}

_LEADING_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")
_ORDINAL_RANK_RE = re.compile(r"(\d+)(?:st|nd|rd|th)?")
_YEAR_RE = re.compile(r"(20\d{2})")

# Public column -> University field. `None` values are computed with
# dedicated parsing (numbers/dates/majors) rather than a straight string copy.
PUBLIC_TEXT_FIELD_MAP = {
    "Official Website": "official_website",
    "Admissions URL": "admissions_url",
    "Admissions Website": "admissions_website",
    "Financial Aid Website": "financial_aid_url",
    "Application Portal": "application_portal_url",
    "International Students Office": "international_office_url",
    "Virtual Info Session": "virtual_info_session_url",
    "Deadlines": "deadlines_text",
    "Admissions Cycle Target": "admissions_cycle_target",
    "Standardized Testing Policy": "standardized_testing_policy_text",
    "Scholarships": "scholarships_text",
    "Need-based Aid": "need_based_aid_notes",
    "Merit Scholarship": "merit_scholarship_notes",
    "Other Scholarships": "other_scholarships_notes",
    "Scholarship Links": "scholarship_links_text",
    "AP Recommendations by Major": "ap_recommendations",
    "Application Requirements": "application_requirements",
    "Essays": "essay_requirements",
    "Profile Evidence": "profile_evidence_notes",
    "Activities": "activities_notes",
    "Honors / Olympiads": "honors_olympiads_notes",
    "Research Experience": "research_experience_notes",
    "Portfolio": "portfolio_notes",
    "Essay Drafts": "essay_drafts_notes",
}
URL_FIELDS = {
    "official_website",
    "admissions_url",
    "admissions_website",
    "financial_aid_url",
    "application_portal_url",
    "international_office_url",
    "virtual_info_session_url",
}

GUIDANCE_TEXT_FIELD_MAP = {
    "Recommendation Letters": "recommendation_letters",
    "What They Look For": "what_they_look_for",
    "Preferred Student Profile": "preferred_student_profile",
    "Who They Seek": "who_they_seek",
    "Student Traits Mentioned by University": "student_traits_mentioned",
    "Alumni Profile Evidence": "alumni_profile_evidence",
    "Published Admitted Student Essays": "published_admitted_student_essays",
    "Official Admissions Messaging": "official_admissions_messaging",
    "Student Life Page Signals": "student_life_page_signals",
    "Graduate/Alumni Outcomes": "graduate_alumni_outcomes",
    "Sample Admitted Essays": "sample_admitted_essays",
    "Essay Themes": "essay_themes",
    "Research/Leadership Themes": "research_leadership_themes",
    "Personality Traits Mentioned": "personality_traits_mentioned",
    "Academic Interests Mentioned": "academic_interests_mentioned",
    "Institutional Values": "institutional_values",
    "Source URLs": "source_urls",
    "Verification Status": "verification_status",
    "Data Source": "data_source",
    "Notes": "notes",
}

SIGNAL_SCORE_FIELD_MAP = {
    "Profile Evidence Score": "profile_evidence_score",
    "Activities Score": "activities_score",
    "Honors / Olympiads Score": "honors_olympiads_score",
    "Research Experience Score": "research_experience_score",
    "Portfolio Score": "portfolio_score",
    "Subject Passion Score": "subject_passion_score",
    "Curiosity Score": "curiosity_score",
    "Originality Score": "originality_score",
    "Leadership Score": "leadership_score",
    "Community Impact Score": "community_impact_score",
    "Research Fit Score": "research_fit_score",
    "Olympiads Score": "olympiads_score",
}


class ImportConfigurationError(Exception):
    """Raised for problems that stop the whole import before any row runs
    (missing file, missing required columns, unsupported extension)."""


@dataclass
class RowResult:
    row_number: int
    name: str
    status: str  # created | updated | skipped_existing | skipped_error
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportSummary:
    rows_read: int = 0
    created: int = 0
    updated: int = 0
    skipped_existing: int = 0
    skipped_errors: int = 0
    duplicate_keys_in_file: int = 0
    missing_required: int = 0
    public_fields_imported: int = 0
    guidance_contexts_imported: int = 0
    signal_vectors_imported: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rows: list[RowResult] = field(default_factory=list)


def clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def is_placeholder(value: str) -> bool:
    return value.strip().lower() in PLACEHOLDER_VALUES


def clean_public_text(value) -> str:
    """Trim + drop exact-match placeholder junk; keep real prose verbatim
    even if it merely *contains* a word like "unknown"."""
    text = clean(value)
    return "" if is_placeholder(text) else text


def normalize_key_part(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def strip_parenthetical(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def normalized_university_key(name: str, country: str) -> tuple[str, str]:
    base_name = strip_parenthetical(name) or name
    return normalize_key_part(base_name), normalize_key_part(country)


def looks_like_http_url(value: str) -> bool:
    return bool(re.match(r"^https?://\S+$", value))


def parse_optional_int(value) -> tuple[int | None, str | None]:
    text = clean(value)
    if is_placeholder(text):
        return None, None
    match = _LEADING_NUMBER_RE.search(text.replace(",", ""))
    if not match:
        return None, f"could not parse '{text[:60]}' as a number; left blank"
    try:
        return int(round(float(match.group()))), None
    except ValueError:
        return None, f"could not parse '{text[:60]}' as a number; left blank"


def parse_optional_decimal(value, *, max_digits: int, decimal_places: int) -> tuple[Decimal | None, str | None]:
    text = clean(value)
    if is_placeholder(text):
        return None, None
    match = _LEADING_NUMBER_RE.search(text.replace(",", ""))
    if not match:
        return None, f"could not parse '{text[:60]}' as a number; left blank"
    try:
        raw = Decimal(match.group()).quantize(Decimal(1).scaleb(-decimal_places))
    except InvalidOperation:
        return None, f"could not parse '{text[:60]}' as a number; left blank"
    max_value = Decimal(10) ** (max_digits - decimal_places) - Decimal(1).scaleb(-decimal_places)
    if abs(raw) > max_value:
        return None, f"'{text[:60]}' out of range for storage; left blank"
    return raw, None


def parse_score_0_10(value) -> tuple[int | None, str | None]:
    text = clean(value)
    if is_placeholder(text):
        return None, None
    number, warning = parse_optional_int(text)
    if warning:
        return None, warning
    if number is None:
        return None, None
    if number < 0 or number > 10:
        return None, f"score {number} out of range 0-10; left blank"
    return number, None


def parse_date_safe(value) -> tuple[date | None, str | None]:
    text = clean(value)
    if is_placeholder(text):
        return None, None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date(), None
        except ValueError:
            continue
    # Excel serial date (numeric, no separators) -- days since 1899-12-30.
    if re.fullmatch(r"\d{4,6}(\.0+)?", text):
        try:
            serial = int(float(text))
            return date(1899, 12, 30) + __import__("datetime").timedelta(days=serial), None
        except (ValueError, OverflowError):
            pass
    return None, f"could not parse '{text[:60]}' as a date; left blank"


def parse_qs_ranking(value) -> tuple[int | None, int | None, str | None]:
    """Extract (rank, year) from strings like '1st overall, QS WUR 2027'."""
    text = clean(value)
    if is_placeholder(text):
        return None, None, None
    rank_match = _ORDINAL_RANK_RE.search(text)
    year_match = _YEAR_RE.search(text)
    rank = int(rank_match.group(1)) if rank_match else None
    year = int(year_match.group(1)) if year_match else None
    if rank is None and year is None:
        return None, None, f"could not parse QS ranking from '{text[:60]}'; left blank"
    return rank, year, None


def split_majors(value) -> list[str]:
    text = clean(value)
    if is_placeholder(text):
        return []
    parts = re.split(r"[;\n]|(?<!\d),(?!\d)", text)
    seen: dict[str, str] = {}
    for part in parts:
        item = part.strip().strip(".")
        if not item or is_placeholder(item):
            continue
        key = item.lower()
        if key not in seen:
            seen[key] = item[:240]
    return list(seen.values())


def read_rows(path: str) -> tuple[list[str], list[dict[str, str]]]:
    file_path = Path(path)
    if not file_path.is_file():
        raise ImportConfigurationError(f"File not found: {path}")

    suffix = file_path.suffix.lower()
    if suffix == ".xlsx":
        return _read_xlsx(file_path)
    if suffix in (".csv", ".tsv", ".txt"):
        return _read_delimited(file_path)
    raise ImportConfigurationError(f"Unsupported file extension: {suffix} (use .csv, .tsv, or .xlsx)")


def _read_xlsx(file_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        import openpyxl
    except ImportError as error:  # pragma: no cover - environment guard
        raise ImportConfigurationError(
            "openpyxl is required to read .xlsx files but is not installed."
        ) from error

    workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    try:
        sheet = workbook["University Data"] if "University Data" in workbook.sheetnames else workbook.worksheets[0]
        rows_iter = sheet.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            return [], []
        headers = [clean(cell) for cell in header_row]
        rows = []
        for raw_row in rows_iter:
            if raw_row is None or all(cell is None or clean(cell) == "" for cell in raw_row):
                continue
            row = {headers[i]: raw_row[i] if i < len(raw_row) else None for i in range(len(headers))}
            rows.append(row)
        return headers, rows
    finally:
        workbook.close()


def _read_delimited(file_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(file_path, encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = "\t" if file_path.suffix.lower() == ".tsv" else ","
        reader = csv.DictReader(handle, dialect=dialect)
        headers = [clean(h) for h in (reader.fieldnames or [])]
        rows = [row for row in reader if any(clean(value) for value in row.values())]
        return headers, rows


def _build_public_fields(row: dict) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    fields: dict = {}

    for column, attr in PUBLIC_TEXT_FIELD_MAP.items():
        value = clean_public_text(row.get(column))
        if not value:
            continue
        if attr in URL_FIELDS and not looks_like_http_url(value):
            warnings.append(f"{column}: '{value[:60]}' is not a valid http(s) URL; left blank")
            continue
        fields[attr] = value

    majors = split_majors(row.get("Majors"))
    if majors:
        fields["majors_list"] = majors

    # Descriptive prose that doesn't fit a numeric field (e.g. "No fixed IELTS
    # minimum published; English proficiency reviewed if required") must never
    # be silently discarded -- it gets folded into the testing-policy notes
    # instead of just surfacing as a transient CLI warning.
    testing_notes: list[str] = []
    for column, (max_digits, decimal_places) in (
        ("IELTS Minimum", (3, 1)),
        ("IELTS Competitive", (3, 1)),
        ("Average GPA", (4, 2)),
        ("QS Overall Score", (5, 1)),
    ):
        target = {
            "IELTS Minimum": "ielts_minimum",
            "IELTS Competitive": "ielts_competitive",
            "Average GPA": "gpa_average",
            "QS Overall Score": "qs_overall_score",
        }[column]
        parsed, warning = parse_optional_decimal(row.get(column), max_digits=max_digits, decimal_places=decimal_places)
        if warning:
            warnings.append(f"{column}: {warning}")
            raw_text = clean_public_text(row.get(column))
            if raw_text:
                testing_notes.append(f"{column}: {raw_text}")
        elif parsed is not None:
            fields[target] = parsed

    if testing_notes:
        existing_policy = fields.get("standardized_testing_policy_text", "")
        combined = "\n".join(filter(None, [existing_policy, *testing_notes]))
        fields["standardized_testing_policy_text"] = combined[:8000]

    acceptance, warning = parse_optional_decimal(row.get("Acceptance Rate"), max_digits=5, decimal_places=2)
    if warning:
        warnings.append(f"Acceptance Rate: {warning}")
    elif acceptance is not None:
        fields["acceptance_rate"] = acceptance

    for column, target in (("SAT 25th", "sat_p25"), ("SAT 50th", "sat_p50"), ("SAT 75th", "sat_p75")):
        parsed, warning = parse_optional_int(row.get(column))
        if warning:
            warnings.append(f"{column}: {warning}")
        elif parsed is not None:
            fields[target] = parsed

    rank, year, warning = parse_qs_ranking(row.get("QS World University Ranking"))
    if warning:
        warnings.append(f"QS World University Ranking: {warning}")
    if rank is not None:
        fields["qs_ranking"] = rank
    if year is not None:
        fields["qs_ranking_year"] = year

    tuition_text = clean_public_text(row.get("Tuition"))
    if tuition_text:
        amount, warning = parse_optional_decimal(tuition_text, max_digits=12, decimal_places=2)
        if amount is not None:
            fields["tuition_amount"] = amount
        fields["cost_notes"] = tuition_text[:4000]

    return fields, warnings


def _build_guidance_fields(row: dict) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    fields: dict = {}
    raw_context: dict = {}

    for column, attr in GUIDANCE_TEXT_FIELD_MAP.items():
        raw_value = clean(row.get(column))
        if raw_value:
            raw_context[column] = raw_value
        value = clean_public_text(row.get(column))
        if value:
            fields[attr] = value

    verified_date, warning = parse_date_safe(row.get("Last Verified Date"))
    if warning:
        warnings.append(f"Last Verified Date: {warning}")
    if verified_date is not None:
        fields["last_verified_date"] = verified_date

    fields["raw_context_json"] = raw_context
    return fields, warnings


def _build_signal_fields(row: dict) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    fields: dict = {}
    for column, attr in SIGNAL_SCORE_FIELD_MAP.items():
        score, warning = parse_score_0_10(row.get(column))
        if warning:
            warnings.append(f"{column}: {warning}")
        elif score is not None:
            fields[attr] = score
    source_text = clean_public_text(row.get("Profile Scoring Source"))
    if source_text:
        fields["profile_scoring_source"] = source_text
    return fields, warnings


def _process_row(
    row_number: int,
    row: dict,
    *,
    existing_by_key: dict[tuple[str, str], University],
    update_existing: bool,
    summary: ImportSummary,
) -> None:
    name = clean(row.get("Name"))
    country = clean(row.get("Country"))
    city = clean(row.get("City"))

    if not name or not country or not city:
        summary.missing_required += 1
        summary.skipped_errors += 1
        message = f"row {row_number}: missing required Name/Country/City"
        summary.errors.append(message)
        summary.rows.append(RowResult(row_number=row_number, name=name or "(blank)", status="skipped_error", errors=[message]))
        return

    key = normalized_university_key(name, country)
    existing = existing_by_key.get(key)
    public_fields, public_warnings = _build_public_fields(row)
    guidance_fields, guidance_warnings = _build_guidance_fields(row)
    signal_fields, signal_warnings = _build_signal_fields(row)
    row_warnings = public_warnings + guidance_warnings + signal_warnings

    if existing is not None and not update_existing:
        # Never overwrite an already-known university's public data without
        # explicit opt-in -- but still fill in guidance/signal rows if they
        # don't exist yet, since those are brand-new tables with nothing to
        # protect.
        if not hasattr(existing, "guidance_context"):
            UniversityGuidanceContext.objects.create(university=existing, **guidance_fields)
            summary.guidance_contexts_imported += 1
        if not hasattr(existing, "signal_weights"):
            UniversitySignalWeights.objects.create(university=existing, **signal_fields)
            summary.signal_vectors_imported += 1
        summary.skipped_existing += 1
        summary.warnings.extend(f"row {row_number} ({name}): {w}" for w in row_warnings)
        summary.rows.append(RowResult(row_number=row_number, name=name, status="skipped_existing", warnings=row_warnings))
        return

    if existing is None:
        existing = University(
            name=name,
            country=country,
            city=city,
            slug=_unique_slug(name),
            is_published=True,
        )
        status = "created"
    else:
        existing.name = name
        existing.city = city or existing.city
        status = "updated"

    for attr, value in public_fields.items():
        setattr(existing, attr, value)
    existing.save()
    summary.public_fields_imported += len(public_fields)

    UniversityGuidanceContext.objects.update_or_create(university=existing, defaults=guidance_fields)
    summary.guidance_contexts_imported += 1
    UniversitySignalWeights.objects.update_or_create(university=existing, defaults=signal_fields)
    summary.signal_vectors_imported += 1

    if status == "created":
        summary.created += 1
    else:
        summary.updated += 1
    summary.warnings.extend(f"row {row_number} ({name}): {w}" for w in row_warnings)
    summary.rows.append(RowResult(row_number=row_number, name=name, status=status, warnings=row_warnings))


def _unique_slug(name: str) -> str:
    from django.utils.text import slugify

    base = slugify(strip_parenthetical(name) or name)[:250] or "university"
    slug = base
    suffix = 2
    while University.objects.filter(slug=slug).exists():
        slug = f"{base}-{suffix}"[:260]
        suffix += 1
    return slug


def import_universities_data(
    path: str,
    *,
    commit: bool,
    update_existing: bool = False,
    limit: int | None = None,
) -> ImportSummary:
    """Import the three-layer university dataset from `path`.

    Never calls out to any AI provider. Never crashes the whole run because
    one row is malformed -- row-level errors are collected and the row is
    skipped. When `commit` is False, every write happens inside a
    transaction that is rolled back at the end, so nothing is persisted.
    """

    headers, rows = read_rows(path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing_columns:
        raise ImportConfigurationError(f"Missing required column(s): {', '.join(missing_columns)}")

    if limit is not None:
        rows = rows[:limit]

    summary = ImportSummary(rows_read=len(rows))

    # Detect in-file duplicate keys before touching the database.
    seen_keys: set[tuple[str, str]] = set()
    for row in rows:
        name = clean(row.get("Name"))
        country = clean(row.get("Country"))
        if not name or not country:
            continue
        key = normalized_university_key(name, country)
        if key in seen_keys:
            summary.duplicate_keys_in_file += 1
        seen_keys.add(key)

    existing_qs = University.objects.select_related("guidance_context", "signal_weights").all()
    existing_by_key: dict[tuple[str, str], University] = {}
    for university in existing_qs:
        existing_by_key[normalized_university_key(university.name, university.country)] = university

    def run() -> None:
        for index, row in enumerate(rows, start=2):  # spreadsheet row 1 is the header
            try:
                _process_row(
                    index,
                    row,
                    existing_by_key=existing_by_key,
                    update_existing=update_existing,
                    summary=summary,
                )
            except Exception as error:  # noqa: BLE001 - one bad row must never abort the run
                summary.skipped_errors += 1
                message = f"row {index}: unexpected error ({type(error).__name__}): {error}"
                summary.errors.append(message)
                summary.rows.append(RowResult(row_number=index, name=clean(row.get("Name")) or "(unknown)", status="skipped_error", errors=[message]))

    with transaction.atomic():
        run()
        if not commit:
            transaction.set_rollback(True)

    return summary
