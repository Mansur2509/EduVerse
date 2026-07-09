"""Schema contract and row-safety helpers for the university workbook importer."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse

CANONICAL_COLUMNS = (
    "Name",
    "Country",
    "City",
    "Official Website",
    "Admissions URL",
    "Admissions Website",
    "Financial Aid Website",
    "Application Portal",
    "International Students Office",
    "Virtual Info Session",
    "Majors",
    "Deadlines",
    "Admissions Cycle Target",
    "Standardized Testing Policy",
    "SAT 25th",
    "SAT 50th",
    "SAT 75th",
    "IELTS Minimum",
    "IELTS Competitive",
    "Average GPA",
    "Acceptance Rate",
    "QS World University Ranking",
    "QS Overall Score",
    "Tuition",
    "Scholarships",
    "Need-based Aid",
    "Merit Scholarship",
    "Other Scholarships",
    "Scholarship Links",
    "AP Recommendations by Major",
    "Application Requirements",
    "Essays",
    "Profile Evidence",
    "Activities",
    "Honors / Olympiads",
    "Research Experience",
    "Portfolio",
    "Essay Drafts",
    "Recommendation Letters",
    "What They Look For",
    "Preferred Student Profile",
    "Who They Seek",
    "Student Traits Mentioned by University",
    "Alumni Profile Evidence",
    "Published Admitted Student Essays",
    "Official Admissions Messaging",
    "Student Life Page Signals",
    "Graduate/Alumni Outcomes",
    "Sample Admitted Essays",
    "Essay Themes",
    "Research/Leadership Themes",
    "Personality Traits Mentioned",
    "Academic Interests Mentioned",
    "Institutional Values",
    "Source URLs",
    "Last Verified Date",
    "Verification Status",
    "Data Source",
    "Notes",
    "Profile Evidence Score",
    "Activities Score",
    "Honors / Olympiads Score",
    "Research Experience Score",
    "Portfolio Score",
    "Subject Passion Score",
    "Curiosity Score",
    "Originality Score",
    "Leadership Score",
    "Community Impact Score",
    "Research Fit Score",
    "Olympiads Score",
    "Profile Scoring Source",
)

ALIGNMENT_ALIGNED = "aligned"
ALIGNMENT_SHIFTED_LEFT_MISSING_NAME = "shifted_left_missing_name"
ALIGNMENT_REPAIRED_SHIFTED_MISSING_NAME = "repaired_shifted_missing_name"
ALIGNMENT_SHIFTED_ROW_UNREPAIRABLE = "shifted_row_unrepairable"

PUBLIC_VISIBILITY = "public"
ADMIN_VISIBILITY = "admin"
AI_ONLY_VISIBILITY = "ai_only"
SYSTEM_VISIBILITY = "system"

TYPE_STRING = "string"
TYPE_URL = "url"
TYPE_LIST_STRING = "list_string"
TYPE_LIST_URL = "list_url"
TYPE_NUMBER = "number"
TYPE_INTEGER_1_10 = "integer_1_10"
TYPE_PERCENT_OR_TEXT = "percent_or_text"
TYPE_NUMBER_OR_TEXT = "number_or_text"
TYPE_DATE = "date"
TYPE_ENUM_STRING = "enum_string"
TYPE_ADMIN_STRING = "admin_string"
TYPE_AI_ONLY_STRING = "ai_only_string"
TYPE_SYSTEM_SCORE = "system_score"

URL_COLUMNS = {
    "Official Website",
    "Admissions URL",
    "Admissions Website",
    "Financial Aid Website",
    "Application Portal",
    "International Students Office",
    "Virtual Info Session",
}

LIST_URL_COLUMNS = {"Scholarship Links", "Source URLs"}
LIST_STRING_COLUMNS = {
    "Majors",
    "AP Recommendations by Major",
    "Application Requirements",
    "Essays",
}
NUMBER_COLUMNS = {
    "SAT 25th",
    "SAT 50th",
    "SAT 75th",
    "IELTS Minimum",
    "IELTS Competitive",
    "Average GPA",
    "QS World University Ranking",
    "QS Overall Score",
    "Tuition",
}
PERCENT_OR_TEXT_COLUMNS = {"Acceptance Rate"}
DATE_COLUMNS = {"Last Verified Date"}
ENUM_COLUMNS = {"Admissions Cycle Target", "Standardized Testing Policy", "Verification Status"}
SYSTEM_SCORE_COLUMNS = {
    "Profile Evidence Score",
    "Activities Score",
    "Honors / Olympiads Score",
    "Research Experience Score",
    "Portfolio Score",
    "Subject Passion Score",
    "Curiosity Score",
    "Originality Score",
    "Leadership Score",
    "Community Impact Score",
    "Research Fit Score",
    "Olympiads Score",
}
AI_ONLY_COLUMNS = {
    "Profile Evidence",
    "Activities",
    "Honors / Olympiads",
    "Research Experience",
    "Portfolio",
    "Essay Drafts",
    "Recommendation Letters",
    "What They Look For",
    "Preferred Student Profile",
    "Who They Seek",
    "Student Traits Mentioned by University",
    "Alumni Profile Evidence",
    "Published Admitted Student Essays",
    "Official Admissions Messaging",
    "Student Life Page Signals",
    "Graduate/Alumni Outcomes",
    "Sample Admitted Essays",
    "Essay Themes",
    "Research/Leadership Themes",
    "Personality Traits Mentioned",
    "Academic Interests Mentioned",
    "Institutional Values",
    "Profile Scoring Source",
}
ADMIN_COLUMNS = {"Source URLs", "Last Verified Date", "Verification Status", "Data Source", "Notes"}

REJECT_PHRASES = (
    "verify exact",
    "verify on official",
    "check official website",
    "check portal",
    "see official website",
    "see university website",
    "source of truth",
    "official website is source of truth",
    "program list varies",
    "deadline varies",
    "country average",
    "average for this country",
    "average in this country",
    "not publicly available",
    "not captured",
    "not verified",
    "not found",
    "needs official",
    "no generated percentage",
    "selection band",
    "competitive profile means",
    "virtual/open-day route",
    "estimated admitted",
    "official catalogue",
    "international tuition uses official fee schedule",
    "planning band should be stored by programme",
    "where applicable",
    "placeholder",
)

GENERATOR_TEMPLATE_FRAGMENTS = (
    "problem/preparation/fit/contribution/reflection",
    "build/test/publish/lead",
    "initiative/curiosity/collaboration",
    "grades+prereqs+outputs+metric",
)

COUNTRY_NAMES = {
    "aland",
    "australia",
    "austria",
    "belgium",
    "brazil",
    "canada",
    "china",
    "denmark",
    "finland",
    "france",
    "germany",
    "hong kong",
    "india",
    "ireland",
    "italy",
    "japan",
    "kazakhstan",
    "malaysia",
    "netherlands",
    "new zealand",
    "norway",
    "singapore",
    "south korea",
    "spain",
    "sweden",
    "switzerland",
    "testland",
    "united arab emirates",
    "united kingdom",
    "uk",
    "united states",
    "united states of america",
    "usa",
    "us",
}

CITY_WORD_RE = re.compile(r"^[a-z][a-z .,'-]*(?:,\s*[a-z]{2,})?$", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)>,]+", re.IGNORECASE)
UNIVERSITY_PREFIX_RE = re.compile(
    r"\b(university|college|institute|school|polytechnic|academy|caltech|harvard|"
    r"stanford|mit|oxford|cambridge|imperial|nus|bocconi|sorbonne|ntnu)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ImportColumnSchema:
    canonical_name: str
    aliases: tuple[str, ...]
    type: str
    example: str
    visibility: str
    required: bool
    validators: tuple[str, ...]
    reject_patterns: tuple[str, ...]
    repair_policy: str


@dataclass(frozen=True)
class RowAlignmentResult:
    status: str
    row: dict
    raw_name: str
    normalized_name: str
    detected_country: str
    detected_city: str
    extracted_possible_name: str = ""
    reason: str = ""
    confidence: str = "high"
    raw_first_5_cells: tuple[str, ...] = field(default_factory=tuple)

    @property
    def repaired(self) -> bool:
        return self.status == ALIGNMENT_REPAIRED_SHIFTED_MISSING_NAME

    @property
    def unrepairable(self) -> bool:
        return self.status == ALIGNMENT_SHIFTED_ROW_UNREPAIRABLE


def normalize_schema_text(value: object) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip().lower()


def _schema_type_for(column: str) -> str:
    if column in URL_COLUMNS:
        return TYPE_URL
    if column in LIST_URL_COLUMNS:
        return TYPE_LIST_URL
    if column in LIST_STRING_COLUMNS:
        return TYPE_LIST_STRING
    if column in SYSTEM_SCORE_COLUMNS:
        return TYPE_SYSTEM_SCORE
    if column in NUMBER_COLUMNS:
        return TYPE_NUMBER
    if column in PERCENT_OR_TEXT_COLUMNS:
        return TYPE_PERCENT_OR_TEXT
    if column in DATE_COLUMNS:
        return TYPE_DATE
    if column in ENUM_COLUMNS:
        return TYPE_ENUM_STRING
    if column in ADMIN_COLUMNS:
        return TYPE_ADMIN_STRING
    if column in AI_ONLY_COLUMNS:
        return TYPE_AI_ONLY_STRING
    return TYPE_STRING


def _visibility_for(column: str) -> str:
    if column in SYSTEM_SCORE_COLUMNS:
        return SYSTEM_VISIBILITY
    if column in AI_ONLY_COLUMNS:
        return AI_ONLY_VISIBILITY
    if column in ADMIN_COLUMNS:
        return ADMIN_VISIBILITY
    return PUBLIC_VISIBILITY


def _example_for(column: str) -> str:
    examples = {
        "Name": "Massachusetts Institute of Technology (MIT)",
        "Country": "USA",
        "City": "Cambridge, MA",
        "Official Website": "https://www.mit.edu/",
        "Admissions URL": "https://mitadmissions.org/",
        "Majors": "Engineering; Computer Science; Physics",
        "Deadlines": "Early Action: Nov 1; Regular Decision: Jan 1",
        "SAT 25th": "1510",
        "IELTS Minimum": "7.0",
        "Average GPA": "3.9",
        "Acceptance Rate": "Not centrally published",
        "QS World University Ranking": "1",
        "Tuition": "USD 61990",
        "Source URLs": "https://mitadmissions.org/apply/",
        "Last Verified Date": "2026-07-08",
        "Verification Status": "verified",
        "Profile Evidence Score": "8",
    }
    return examples.get(column, "University-specific sourced value")


def _validators_for(column: str, column_type: str) -> tuple[str, ...]:
    validators = ["no_placeholder", "no_repeated_template", "no_wrong_university_prefix"]
    if column == "Name":
        validators.extend(["not_country", "not_url", "institution_name"])
    elif column == "Country":
        validators.extend(["country_like", "not_url"])
    elif column == "City":
        validators.extend(["city_like", "not_url", "not_country"])
    elif column_type in {TYPE_URL, TYPE_LIST_URL}:
        validators.extend(["http_url"])
    elif column_type == TYPE_SYSTEM_SCORE:
        validators.extend(["integer", "between_1_and_10"])
    elif column_type == TYPE_NUMBER:
        validators.extend(["numeric_or_controlled_text"])
    elif column_type == TYPE_DATE:
        validators.extend(["iso_or_excel_date"])
    return tuple(validators)


def _repair_policy_for(column: str) -> str:
    if column in {"Name", "Country", "City"} or column in URL_COLUMNS:
        return "row_alignment_only"
    return "skip_or_manual_review; never invent"


def _aliases_for(column: str) -> tuple[str, ...]:
    aliases = {
        "Name": ("University", "University Name", "Institution", "Institution Name"),
        "Country": ("Nation",),
        "City": ("Location",),
        "Official Website": ("Website", "URL"),
        "Admissions URL": ("Admission URL", "Admissions Website", "Admission Website"),
        "Financial Aid Website": ("Financial Aid URL", "Financial Aid"),
        "Majors": ("Programs", "Programmes", "Courses"),
        "Deadlines": ("Application Deadline", "Application Deadlines"),
        "QS World University Ranking": ("QS Ranking", "QS Rank"),
        "IELTS Minimum": ("IELTS",),
    }
    return aliases.get(column, ())


UNIVERSITY_IMPORT_SCHEMA = {
    column: ImportColumnSchema(
        canonical_name=column,
        aliases=_aliases_for(column),
        type=_schema_type_for(column),
        example=_example_for(column),
        visibility=_visibility_for(column),
        required=column in {"Name", "Country"},
        validators=_validators_for(column, _schema_type_for(column)),
        reject_patterns=REJECT_PHRASES,
        repair_policy=_repair_policy_for(column),
    )
    for column in CANONICAL_COLUMNS
}


def looks_like_url(value: object) -> bool:
    text = normalize_schema_text(value)
    if not text:
        return False
    if not URL_RE.search(text):
        return False
    parsed = urlparse(URL_RE.search(text).group(0))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def looks_like_country(value: object) -> bool:
    text = normalize_schema_text(value)
    if not text or looks_like_url(text):
        return False
    normalized = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return normalized in COUNTRY_NAMES


def looks_like_city(value: object) -> bool:
    text = normalize_schema_text(value)
    if not text or looks_like_url(text) or looks_like_country(text):
        return False
    return bool(CITY_WORD_RE.fullmatch(text)) and len(text) <= 80


def has_banned_phrase(value: object) -> bool:
    text = normalize_schema_text(value)
    return any(phrase in text for phrase in REJECT_PHRASES + GENERATOR_TEMPLATE_FRAGMENTS)


def _sentence_chunks(value: object) -> list[str]:
    text = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    pieces = re.split(r"(?<=[.!?])\s+|[\n;]+", text)
    return [normalize_schema_text(piece).strip(" .,:") for piece in pieces if piece.strip()]


def has_repeated_sentence(value: object) -> bool:
    chunks = [chunk for chunk in _sentence_chunks(value) if len(chunk) >= 24]
    counts = Counter(chunks)
    return any(count > 1 for count in counts.values())


def _prefix_before_colon(value: object) -> str:
    text = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    if ":" not in text:
        return ""
    prefix = text.split(":", 1)[0].strip()
    if len(prefix) > 120:
        return ""
    return prefix


def _name_key(value: str) -> str:
    text = normalize_schema_text(value).replace("&", " and ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\b(the|university|college|institute|school|of|and)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_university_prefix(prefix: str) -> bool:
    return bool(prefix and UNIVERSITY_PREFIX_RE.search(prefix))


def wrong_university_prefix(value: object, expected_name: str) -> str:
    prefix = _prefix_before_colon(value)
    if not _looks_like_university_prefix(prefix):
        return ""
    prefix_key = _name_key(prefix)
    expected_key = _name_key(expected_name)
    if not prefix_key or not expected_key:
        return ""
    prefix_tokens = set(prefix_key.split())
    expected_tokens = set(expected_key.split())
    if prefix_tokens & expected_tokens:
        return ""
    expected_acronym = _acronym(expected_name)
    prefix_acronym = _acronym(prefix)
    if prefix_key == expected_acronym or expected_key == prefix_acronym:
        return ""
    return prefix


def boilerplate_signature(value: object) -> str:
    text = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    if not text or len(text) < 40:
        return ""
    prefix = _prefix_before_colon(text)
    if prefix and _looks_like_university_prefix(prefix):
        text = text.split(":", 1)[1].strip()
    signature = normalize_schema_text(text)
    signature = re.sub(r"\b(university|college|institute|school)\b", "institution", signature)
    return signature if len(signature) >= 40 else ""


def detect_repeated_boilerplate_values(
    rows: list[dict],
    *,
    columns: tuple[str, ...] | None = None,
    min_repeats: int = 5,
) -> dict[str, set[str]]:
    checked_columns = columns or tuple(
        column
        for column in CANONICAL_COLUMNS
        if column not in URL_COLUMNS
        and column not in LIST_URL_COLUMNS
        and column not in NUMBER_COLUMNS
        and column not in SYSTEM_SCORE_COLUMNS
        and column not in DATE_COLUMNS
        and column not in {"Name", "Country", "City"}
    )
    counters: dict[str, Counter] = {column: Counter() for column in checked_columns}
    for row in rows:
        for column in checked_columns:
            signature = boilerplate_signature(row.get(column))
            if signature:
                counters[column][signature] += 1
    return {
        column: {signature for signature, count in counter.items() if count >= min_repeats}
        for column, counter in counters.items()
        if any(count >= min_repeats for count in counter.values())
    }


def _extract_repeated_university_name(row: dict) -> str:
    prefixes: list[str] = []
    for key, value in row.items():
        if key.startswith("__"):
            continue
        prefix = _prefix_before_colon(value)
        if _looks_like_university_prefix(prefix):
            prefixes.append(prefix)
    if not prefixes:
        return ""
    counts = Counter(_name_key(prefix) for prefix in prefixes)
    best_key, count = counts.most_common(1)[0]
    if count < 5:
        return ""
    for prefix in prefixes:
        if _name_key(prefix) == best_key:
            return prefix
    return ""


def _acronym(value: str) -> str:
    stop_words = {"of", "and", "the", "for", "in", "at"}
    words = re.findall(r"[A-Za-z]+", value)
    return "".join(word[0].lower() for word in words if word.lower() not in stop_words)


def _domain_matches_name(url_value: object, name: str) -> bool:
    if not looks_like_url(url_value) or not name:
        return False
    parsed = urlparse(URL_RE.search(str(url_value)).group(0))
    host = parsed.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    base_domain = host.split(".")[0]
    parenthetical_acronyms = [
        match.lower()
        for match in re.findall(r"\(([A-Z][A-Z0-9]{2,12})\)", name)
    ]
    if any(acronym in base_domain for acronym in parenthetical_acronyms):
        return True
    name_key = _name_key(name)
    tokens = [token for token in name_key.split() if len(token) >= 4]
    if any(token in base_domain for token in tokens):
        return True
    acronym = _acronym(name)
    return bool(acronym and len(acronym) >= 3 and acronym in base_domain)


def _raw_first_5(row: dict) -> tuple[str, ...]:
    return tuple(str(row.get(column) or "") for column in CANONICAL_COLUMNS[:5])


def validate_and_repair_row_alignment(row: dict) -> RowAlignmentResult:
    raw_name = str(row.get("Name") or "").strip()
    raw_country = str(row.get("Country") or "").strip()
    raw_city = str(row.get("City") or "").strip()
    first_5 = _raw_first_5(row)

    if looks_like_country(raw_name):
        possible_name = _extract_repeated_university_name(row)
        shifted = (
            looks_like_country(raw_name)
            and looks_like_city(raw_country)
            and looks_like_url(raw_city)
        )
        if shifted and possible_name and _domain_matches_name(raw_city, possible_name):
            repaired = dict(row)
            for index in range(len(CANONICAL_COLUMNS) - 1, 0, -1):
                repaired[CANONICAL_COLUMNS[index]] = row.get(CANONICAL_COLUMNS[index - 1], "")
            repaired["Name"] = possible_name
            return RowAlignmentResult(
                status=ALIGNMENT_REPAIRED_SHIFTED_MISSING_NAME,
                row=repaired,
                raw_name=raw_name,
                normalized_name=_name_key(possible_name),
                detected_country=raw_name,
                detected_city=raw_country,
                extracted_possible_name=possible_name,
                reason="high-confidence repair for row shifted left with missing Name",
                confidence="high",
                raw_first_5_cells=first_5,
            )
        return RowAlignmentResult(
            status=ALIGNMENT_SHIFTED_ROW_UNREPAIRABLE,
            row=row,
            raw_name=raw_name,
            normalized_name="",
            detected_country=raw_name if looks_like_country(raw_name) else "",
            detected_city=raw_country if looks_like_city(raw_country) else "",
            extracted_possible_name=possible_name,
            reason=ALIGNMENT_SHIFTED_LEFT_MISSING_NAME,
            confidence="high" if shifted else "medium",
            raw_first_5_cells=first_5,
        )

    if raw_name and looks_like_url(raw_name):
        return RowAlignmentResult(
            status=ALIGNMENT_SHIFTED_ROW_UNREPAIRABLE,
            row=row,
            raw_name=raw_name,
            normalized_name="",
            detected_country=raw_country if looks_like_country(raw_country) else "",
            detected_city=raw_city if looks_like_city(raw_city) else "",
            reason="name_looks_like_url",
            confidence="high",
            raw_first_5_cells=first_5,
        )

    if raw_country and looks_like_url(raw_country):
        return RowAlignmentResult(
            status=ALIGNMENT_SHIFTED_ROW_UNREPAIRABLE,
            row=row,
            raw_name=raw_name,
            normalized_name=_name_key(raw_name),
            detected_country="",
            detected_city=raw_city if looks_like_city(raw_city) else "",
            reason="country_looks_like_url",
            confidence="high",
            raw_first_5_cells=first_5,
        )

    return RowAlignmentResult(
        status=ALIGNMENT_ALIGNED,
        row=row,
        raw_name=raw_name,
        normalized_name=_name_key(raw_name),
        detected_country=raw_country,
        detected_city=raw_city,
        reason="row identity columns aligned",
        confidence="high",
        raw_first_5_cells=first_5,
    )
