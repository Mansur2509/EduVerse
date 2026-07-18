from __future__ import annotations

import re
from datetime import date

from django.core.cache import cache

from services.application_service.models import ApplicationTrackerItem

from .budget import STATUS_ABOVE_BUDGET
from .deadline_normalization import normalize_university_deadline
from .major_matching import match_programs_to_profile, subject_ranking_context
from .models import ExcludedUniversity, PinnedUniversity, SavedUniversity, University
from .program_display import format_program_display_names
from .recommendation_cache import recommendations_cache_key
from .services import calculate_university_fit

# 022 Phase 12: reason codes for the internal-only diagnostic view. Not all
# of these currently correspond to a live exclusion mechanism in this
# codebase -- PROGRAM_UNAVAILABLE and UNIVERSITY_ARCHIVED are defined for
# schema completeness against the task spec's exact vocabulary even though no
# code path produces PROGRAM_UNAVAILABLE today (program mismatch is a soft
# scoring signal here, never a hard filter -- see docs/RECOMMENDATION_ENGINE_AUDIT_022.md),
# and UNIVERSITY_ARCHIVED is mapped onto `is_published=False` (this catalog
# has no separate archival flag).
REASON_PROGRAM_UNAVAILABLE = "PROGRAM_UNAVAILABLE"
REASON_COUNTRY_EXCLUDED = "COUNTRY_EXCLUDED"
REASON_DEGREE_LEVEL_MISMATCH = "DEGREE_LEVEL_MISMATCH"
REASON_DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
REASON_FINANCIAL_MISMATCH = "FINANCIAL_MISMATCH"
REASON_ACADEMIC_THRESHOLD_GAP = "ACADEMIC_THRESHOLD_GAP"
REASON_DATA_CONFIDENCE_TOO_LOW = "DATA_CONFIDENCE_TOO_LOW"
REASON_UNIVERSITY_ARCHIVED = "UNIVERSITY_ARCHIVED"
REASON_USER_EXCLUDED = "USER_EXCLUDED"
REASON_DUPLICATE_RESULT = "DUPLICATE_RESULT"
REASON_CATEGORY_CAP_REACHED = "CATEGORY_CAP_REACHED"
# Extension beyond the spec's 11 codes, covering 022 Phase 11's own
# institution-type/ranking-range student preference filters.
REASON_PREFERENCE_FILTER_MISMATCH = "PREFERENCE_FILTER_MISMATCH"

REGION_COUNTRIES = {
    "us": {"united states", "usa", "u.s.", "u.s.a."},
    "canada": {"canada"},
    "uk": {"united kingdom", "uk", "england", "scotland", "wales"},
    "asia": {
        "singapore",
        "japan",
        "south korea",
        "hong kong",
        "china",
        "kazakhstan",
        "uzbekistan",
    },
}

GLOBAL_MARKERS = {"global", "worldwide", "anywhere", "all", "international"}

# Category quotas for the balanced 20-25 list (PART 8), now upper bounds
# rather than fixed targets (022 Phase 6): a bucket may come in under quota
# when too few genuinely-aligned candidates exist, but is never padded with
# weak matches to hit the number. "competitive" from the fit engine folds
# into "reach" at the recommendation layer -- the underlying per-university
# fit endpoint is untouched, this bucketing is display-only.
CATEGORY_QUOTAS = {
    "dream": 5,
    "reach": 7,
    "target": 8,
    "safety": 6,
}
CATEGORY_ORDER_FOR_LIST = ("dream", "reach", "target", "safety")

CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}

# Below this overall_confidence (022 Phase 7, Case D), most of the
# profile-strength model is running on missing-evidence defaults rather than
# genuinely weak evidence -- every recommendation's confidence is capped the
# same way a missing country/major preference already caps it, so a sparse
# profile never presents as more certain than the data actually supports.
LOW_PROFILE_CONFIDENCE_THRESHOLD = 0.35

# A candidate scoring more than this many points below the *strongest*
# candidate already picked for the same bucket is too weak to use as a
# quota-filling pad (022 Phase 6: "do not force a category if no suitable
# university exists"). Relative, not absolute: a bucket where every
# candidate is only moderately aligned (e.g. because the student's own
# profile is still sparse, not because the universities themselves are bad
# matches) keeps its full candidate set rather than being emptied out just
# because no candidate clears some fixed "great match" bar. The single best
# candidate in a bucket is always admitted regardless of this gap.
MAX_FIT_SCORE_GAP_FOR_PADDING = 35

# Diversity constraint (022 Phase 6): beyond the first pick in a bucket, no
# single country may claim more than this share of the selected list so far.
# A soft cap (skip and try the next-best candidate), not a hard exclusion --
# the first pick in every bucket is always admitted regardless of country.
MAX_SHARE_PER_COUNTRY = 0.5

# Program-fit clusters (PART 7). Broad, deliberately conservative keyword
# groups used only to find *related* programs when no exact major match
# exists -- never to invent programs a university does not offer.
PROGRAM_CLUSTERS: dict[str, dict[str, tuple[str, ...]]] = {
    "computer_science_engineering": {
        "major_keywords": (
            "computer science",
            "software",
            "engineering",
            "electrical",
            "mechanical",
            "civil engineering",
            "robotics",
        ),
        "program_keywords": (
            "computer science",
            "software",
            "engineering",
            "electrical",
            "mechanical",
            "civil",
            "robotics",
            "information technology",
        ),
    },
    "data_ai": {
        "major_keywords": ("data science", "artificial intelligence", "machine learning", "data analytics"),
        "program_keywords": ("data science", "artificial intelligence", "machine learning", "analytics", "statistics"),
    },
    "business_finance_economics": {
        "major_keywords": ("business", "finance", "economics", "accounting", "management"),
        "program_keywords": ("business", "finance", "economics", "accounting", "management", "commerce"),
    },
    "politics_law_ir": {
        "major_keywords": ("political science", "law", "international relations", "public policy", "government"),
        "program_keywords": ("political science", "law", "international relations", "public policy", "government"),
    },
    "biology_premed_public_health": {
        "major_keywords": ("biology", "pre-med", "medicine", "public health", "biomedical"),
        "program_keywords": ("biology", "medicine", "public health", "biomedical", "health science"),
    },
    "psychology_neuroscience": {
        "major_keywords": ("psychology", "neuroscience", "cognitive science"),
        "program_keywords": ("psychology", "neuroscience", "cognitive science"),
    },
    "social_sciences": {
        "major_keywords": ("sociology", "anthropology", "social science"),
        "program_keywords": ("sociology", "anthropology", "social science"),
    },
    "humanities": {
        "major_keywords": ("history", "literature", "philosophy", "linguistics", "classics"),
        "program_keywords": ("history", "literature", "philosophy", "linguistics", "classics"),
    },
    "arts_design": {
        "major_keywords": ("art", "design", "fine arts", "architecture", "film", "music"),
        "program_keywords": ("art", "design", "fine arts", "architecture", "film", "music"),
    },
    "education": {
        "major_keywords": ("education", "teaching", "pedagogy"),
        "program_keywords": ("education", "teaching", "pedagogy"),
    },
    "environmental_studies": {
        "major_keywords": ("environmental", "sustainability", "earth science", "climate"),
        "program_keywords": ("environmental", "sustainability", "earth science", "climate"),
    },
}

# Round labels recognized in raw deadline/requirement text. Order matters:
# "ed ii" must be checked before the bare "ed" pattern.
ROUND_PATTERNS = (
    ("REA", r"\brea\b"),
    ("ED II", r"\bed\s*ii\b"),
    ("ED", r"\bed\b"),
    ("EA", r"\bea\b"),
    ("RD", r"\brd\b"),
    ("UCAS", r"\bucas\b"),
    ("ROLLING", r"\brolling\b"),
)


# Degree-level hard filter (022 Phase 4). Both `profile.intended_degree` and
# `UniversityProgram.degree_level` are free text (e.g. "bachelor", "Bachelor's",
# "BSc", "Undergraduate") -- this only recognizes a small set of common
# synonyms and only ever excludes on a *confirmed* mismatch (student intent
# recognized AND university has at least one recognized, non-matching degree
# level on file). Anything unrecognized or blank on either side is treated as
# unknown and never excludes a candidate.
_DEGREE_LEVEL_SYNONYMS = {
    "bachelor": ("bachelor", "undergraduate", "ba", "bs", "bsc", "beng", "bba"),
    "master": ("master", "graduate", "ma ", "ms ", "msc", "meng", "mba"),
    "phd": ("phd", "doctorate", "doctoral", "dphil"),
}


def _degree_bucket(text: str) -> str | None:
    normalized = f" {text.strip().lower()} "
    for bucket, synonyms in _DEGREE_LEVEL_SYNONYMS.items():
        if any(synonym in normalized for synonym in synonyms):
            return bucket
    return None


def _degree_level_excludes(profile, university: University) -> bool:
    student_bucket = _degree_bucket(profile.intended_degree or "")
    if student_bucket is None:
        return False
    program_buckets = {
        bucket
        for bucket in (_degree_bucket(program.degree_level) for program in university.programs.all())
        if bucket is not None
    }
    if not program_buckets:
        return False
    return student_bucket not in program_buckets


# 022 Phase 11: explicit, opt-in hard filters set by the student themselves
# (not scoring outcomes) -- distinct from Phase 4's data-driven hard filters.
# Unknown/unset university data never excludes, same rule as Phase 4.
def _passes_preference_hard_filters(university: University, preferences) -> bool:
    if preferences is None:
        return True

    institution_pref = getattr(preferences, "institution_type_preference", "any") or "any"
    if (
        institution_pref != "any"
        and university.institution_type
        and university.institution_type != institution_pref
    ):
        return False

    ranking_min = getattr(preferences, "preferred_ranking_min", None)
    ranking_max = getattr(preferences, "preferred_ranking_max", None)
    if university.global_rank is not None:
        if ranking_min is not None and university.global_rank < ranking_min:
            return False
        if ranking_max is not None and university.global_rank > ranking_max:
            return False

    return True


def _sanitized_category_distribution(preferences) -> dict[str, int] | None:
    """A user-supplied override for CATEGORY_QUOTAS (022 Phase 11). Returns
    None (meaning "use the engine default") unless the preference is a
    genuinely well-formed, sane override -- malformed input degrades to the
    default rather than crashing or producing an unbounded quota.
    """

    if preferences is None:
        return None
    raw = getattr(preferences, "category_distribution", None)
    if not isinstance(raw, dict) or not raw:
        return None
    result = dict(CATEGORY_QUOTAS)
    changed = False
    for category in CATEGORY_ORDER_FOR_LIST:
        value = raw.get(category)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 50:
            result[category] = value
            changed = True
    return result if changed else None


def _normalized_targets(profile) -> set[str]:
    return {str(value).strip().lower() for value in profile.target_countries if str(value).strip()}


def _country_matches_preference(country: str, targets: set[str]) -> bool:
    if not targets or targets & GLOBAL_MARKERS:
        return True
    normalized_country = country.strip().lower()
    if normalized_country in targets:
        return True
    for target in targets:
        countries = REGION_COUNTRIES.get(target, set())
        if normalized_country in countries:
            return True
    return False


def _user_majors(profile) -> list[str]:
    return [
        str(value).strip().lower()
        for value in (profile.intended_majors or ([profile.intended_major] if profile.intended_major else []))
        if str(value).strip()
    ]


def _clusters_for_majors(majors: list[str]) -> list[str]:
    matches = []
    for cluster_name, config in PROGRAM_CLUSTERS.items():
        if any(keyword in major for major in majors for keyword in config["major_keywords"]):
            matches.append(cluster_name)
    return matches


def _match_programs(profile, university: University) -> tuple[list[dict], bool]:
    """Return (recommended_programs, has_any_program_data)."""

    raw_names = [program.name for program in university.programs.all()]
    if not raw_names:
        return [], False

    display_names = format_program_display_names(raw_names)
    majors = _user_majors(profile)
    if not majors:
        return [], True

    exact = [name for name in display_names if any(major in name.lower() or name.lower() in major for major in majors)]
    if exact:
        return (
            [
                {"name": name, "fit_reason_key": "program_exact_match", "match_type": "exact", "confidence": "high"}
                for name in exact[:4]
            ],
            True,
        )

    clusters = _clusters_for_majors(majors)
    if clusters:
        keywords = {
            keyword
            for cluster_name in clusters
            for keyword in PROGRAM_CLUSTERS[cluster_name]["program_keywords"]
        }
        related = [name for name in display_names if any(keyword in name.lower() for keyword in keywords)]
        if related:
            return (
                [
                    {
                        "name": name,
                        "fit_reason_key": "program_related_match",
                        "match_type": "related",
                        "confidence": "medium",
                    }
                    for name in related[:4]
                ],
                True,
            )

    return [], True


def _risk_level_from_score(score: int) -> str:
    if score >= 70:
        return "low"
    if score >= 50:
        return "moderate"
    return "high"


def _has_aid_signal(university: University) -> bool:
    return bool(
        university.scholarship_available or university.financial_aid_url or university.scholarships.all()
    )


def _cost_risk(profile, university: University) -> str:
    has_cost = university.tuition_usd_amount is not None or university.total_cost_usd_amount is not None
    if not has_cost:
        return "unknown"
    if profile.scholarship_need == profile.ScholarshipNeed.YES and not _has_aid_signal(university):
        return "high"
    if profile.scholarship_need in {profile.ScholarshipNeed.YES, profile.ScholarshipNeed.UNSURE} and not (
        university.scholarship_available
    ):
        return "moderate"
    return "low"


def _deadline_confidence(university: University) -> str:
    if university.application_deadline is None:
        return "missing"
    verification = next(
        (
            record
            for record in university.field_verifications.all()
            if record.field_name == "application_deadline"
        ),
        None,
    )
    if verification and verification.status == "verified":
        return "verified"
    return "partial"


def _urgency_for_days(days: int | None) -> str:
    # Mirrors services/application_service/timeline.py:urgency_for_days. Kept as
    # a local copy to avoid a university_service -> application_service import
    # (application_service already imports university_service, so the reverse
    # import would be circular).
    if days is None:
        return "unknown"
    if days < 0:
        return "overdue"
    if days <= 7:
        return "critical"
    if days <= 14:
        return "urgent"
    if days <= 30:
        return "soon"
    if days <= 90:
        return "upcoming"
    return "far"


def _available_rounds(university: University) -> list[str]:
    text = f"{university.deadlines_text} {university.application_requirements}".lower()
    found = []
    for label, pattern in ROUND_PATTERNS:
        if re.search(pattern, text):
            found.append(label)
    return found


def _application_round_info(university: University, *, essay_ready: bool, exam_ready: bool, days_remaining: int | None) -> dict:
    rounds = _available_rounds(university)
    if days_remaining is not None and days_remaining < 0:
        return {
            "available_rounds": rounds,
            "recommended_round": "unknown",
            "reason_key": "round_deadline_passed",
            "reason_params": {},
        }
    if not rounds:
        return {
            "available_rounds": [],
            "recommended_round": "unknown",
            "reason_key": "round_not_verified",
            "reason_params": {},
        }
    if len(rounds) == 1:
        return {
            "available_rounds": rounds,
            "recommended_round": rounds[0],
            "reason_key": "round_single_available",
            "reason_params": {"round": rounds[0]},
        }

    early_rounds = [label for label in rounds if label in {"REA", "ED", "ED II", "EA"}]
    if days_remaining is not None and days_remaining <= 21 and (not essay_ready or not exam_ready):
        fallback = "RD" if "RD" in rounds else rounds[-1]
        return {
            "available_rounds": rounds,
            "recommended_round": fallback,
            "reason_key": "round_early_too_close",
            "reason_params": {"round": fallback},
        }
    if early_rounds and essay_ready and exam_ready:
        return {
            "available_rounds": rounds,
            "recommended_round": early_rounds[0],
            "reason_key": "round_early_recommended_ready",
            "reason_params": {"round": early_rounds[0]},
        }
    return {
        "available_rounds": rounds,
        "recommended_round": rounds[0],
        "reason_key": "round_multiple_available",
        "reason_params": {"round": rounds[0]},
    }


def _is_international(profile, university: University) -> bool | None:
    home_country = str(profile.country or "").strip().lower()
    if not home_country:
        return None
    return university.country.strip().lower() != home_country


def _why_recommended_keys(
    *, category: str, targets: set[str], programs: list[dict], has_program_data: bool
) -> list[str]:
    keys: list[str] = []
    if targets:
        keys.append("region_preference_match")
    else:
        keys.append("region_broad_default")
    if programs:
        keys.append(programs[0]["fit_reason_key"])
    elif not has_program_data:
        keys.append("program_not_verified")
    if category in {"dream", "reach", "target", "safety"}:
        keys.append(f"category_{category}")
    return keys


def _holistic_context_key(profile_strength: dict) -> str | None:
    """EC/holistic context (022 Phase 8) -- a deliberately coarse signal from
    the university-independent extracurricular_strength dimension, gated by
    its own confidence: a low-confidence read (no activities on file yet)
    makes no claim at all rather than reporting a silently-neutral "average",
    per the same missing-vs-weak distinction profile_strength already draws.
    """

    dimension = profile_strength["extracurricular_strength"]
    if dimension["confidence"] < 0.35:
        return None
    if dimension["score"] >= 70:
        return "extracurricular_strong_evidence"
    if dimension["score"] < 40:
        return "extracurricular_limited_evidence"
    return None


def _cap_confidence(confidence: str, cap: str) -> str:
    if CONFIDENCE_RANK.get(confidence, 1) > CONFIDENCE_RANK.get(cap, 1):
        return cap
    return confidence


# ---------------------------------------------------------------------------
# Category derivation (022 Phase 5-6). Replaces the old
# `"reach" if fit["category"] == "competitive" else fit["category"]` mapping,
# which could never actually produce "dream" (see
# docs/RECOMMENDATION_ENGINE_AUDIT_022.md) and let acceptance rate alone
# decide category with academic-only adjustment. This derivation combines
# selectivity context with a weighted composite of academic, program,
# financial, extracurricular, preference-match, and readiness signals so a
# weak-extracurricular or high-financial-need profile can no longer land an
# elite school in "reach" just because its academic numbers are in range.
# ---------------------------------------------------------------------------

SELECTIVITY_ULTRA = "ultra_selective"
SELECTIVITY_HIGH = "highly_selective"
SELECTIVITY_MODERATE = "selective"
SELECTIVITY_ACCESSIBLE = "accessible"
SELECTIVITY_UNKNOWN = "unknown"

ALIGNMENT_STRONG = "strong"
ALIGNMENT_GOOD = "good"
ALIGNMENT_MODERATE = "moderate"
ALIGNMENT_WEAK = "weak"

# selectivity_band -> alignment_band -> category. Table-driven and testable
# cell-by-cell rather than a formula, per this task's explainability
# requirement. "dream" only appears where selectivity is genuinely severe or
# the profile gap is itself severe -- never as a permanently-empty bucket.
_CATEGORY_MATRIX: dict[str, dict[str, str]] = {
    SELECTIVITY_ULTRA: {
        ALIGNMENT_STRONG: "reach",
        ALIGNMENT_GOOD: "dream",
        ALIGNMENT_MODERATE: "dream",
        ALIGNMENT_WEAK: "dream",
    },
    SELECTIVITY_HIGH: {
        ALIGNMENT_STRONG: "target",
        ALIGNMENT_GOOD: "reach",
        ALIGNMENT_MODERATE: "reach",
        ALIGNMENT_WEAK: "dream",
    },
    SELECTIVITY_MODERATE: {
        ALIGNMENT_STRONG: "safety",
        ALIGNMENT_GOOD: "target",
        ALIGNMENT_MODERATE: "reach",
        ALIGNMENT_WEAK: "reach",
    },
    SELECTIVITY_ACCESSIBLE: {
        ALIGNMENT_STRONG: "safety",
        ALIGNMENT_GOOD: "safety",
        ALIGNMENT_MODERATE: "target",
        ALIGNMENT_WEAK: "reach",
    },
    SELECTIVITY_UNKNOWN: {
        ALIGNMENT_STRONG: "target",
        ALIGNMENT_GOOD: "target",
        ALIGNMENT_MODERATE: "reach",
        ALIGNMENT_WEAK: "reach",
    },
}


def _selectivity_band(acceptance_rate) -> str:
    if acceptance_rate is None:
        return SELECTIVITY_UNKNOWN
    rate = float(acceptance_rate)
    if rate < 10:
        return SELECTIVITY_ULTRA
    if rate < 25:
        return SELECTIVITY_HIGH
    if rate < 50:
        return SELECTIVITY_MODERATE
    return SELECTIVITY_ACCESSIBLE


def _alignment_band(composite_score: float) -> str:
    if composite_score >= 78:
        return ALIGNMENT_STRONG
    if composite_score >= 60:
        return ALIGNMENT_GOOD
    if composite_score >= 42:
        return ALIGNMENT_MODERATE
    return ALIGNMENT_WEAK


def _program_preference_score(program_summary: dict, best_program: dict | None) -> int:
    if best_program is not None:
        return best_program["program_fit_score"]
    if program_summary["program_data_verified"]:
        # Verified program data exists but nothing matched the student's
        # stated major -- a real (if soft) preference mismatch, not missing
        # data, so this scores lower than "no data at all".
        return 40
    return 55


def calculate_composite_score(
    *, fit: dict, profile_strength: dict, program_summary: dict, best_program: dict | None
) -> int:
    """Explainable weighted blend (022 Phase 5). Starting weights per this
    task's own framework: academic 30%, program 20%, financial 15%,
    extracurricular/holistic 15%, preference match 10%, readiness 10%.

    Reuses calculate_university_fit's subscores directly -- never
    recomputes GPA/test/major/finance calculations. Extracurricular and
    readiness each blend the university-aware existing subscore with the
    new university-independent profile-strength dimension, so neither a
    thin per-university evidence check nor a thin general profile check
    alone can dominate.
    """

    extracurricular_blend = round(
        (fit["profile_subscore"] + profile_strength["extracurricular_strength"]["score"]) / 2
    )
    readiness_blend = round(
        (fit["deadline_subscore"] + profile_strength["application_readiness"]["score"]) / 2
    )
    preference_score = _program_preference_score(program_summary, best_program)

    composite = (
        fit["academic_subscore"] * 0.30
        + fit["program_subscore"] * 0.20
        + fit["cost_subscore"] * 0.15
        + extracurricular_blend * 0.15
        + preference_score * 0.10
        + readiness_blend * 0.10
    )
    return max(1, min(100, round(composite)))


def derive_recommendation_category(
    *,
    university: University,
    composite_score: int,
    is_deadline_overdue: bool,
    is_confirmed_unaffordable: bool,
    is_severe_academic_gap: bool = False,
) -> str:
    """Selectivity x alignment -> category (022 Phase 6), replacing the old
    acceptance-rate-baseline + academic-only index shift. `safety` is the
    internal/wire value for the "Likely" tier (never renamed at the data
    layer -- see docs/RECOMMENDATION_ENGINE_AUDIT_022.md -- only the
    user-facing label changes).

    A confirmed-unaffordable-with-no-aid-signal, a current-cycle-overdue
    item, or a confirmed severe SAT/IELTS shortfall (022 Phase 7, Case B) can
    never resolve to "target" or "safety" (the practical/apply-now tiers): it
    is capped to "reach" at worst. For the academic-gap case specifically,
    this stops a strong extracurricular, program, or financial-fit signal
    from mathematically outweighing a real academic-minimum failure in the
    composite blend -- a genuine gap is never "erased" by unrelated strengths.
    """

    selectivity = _selectivity_band(
        float(university.acceptance_rate) if university.acceptance_rate is not None else None
    )
    alignment = _alignment_band(composite_score)
    category = _CATEGORY_MATRIX[selectivity][alignment]

    if (
        is_deadline_overdue or is_confirmed_unaffordable or is_severe_academic_gap
    ) and category in {"target", "safety"}:
        category = "reach"

    return category


def _build_recommendation_item(
    *,
    profile,
    university: University,
    targets: set[str],
    confidence_cap: str | None,
    shortlisted_ids: set[int],
    tracked_by_university: dict[int, int],
    profile_strength: dict,
    preferences=None,
) -> dict | None:
    fit = calculate_university_fit(profile, university)
    if fit["category"] is None:
        return None

    program_summary = match_programs_to_profile(profile, university)
    programs = [
        {
            "name": program["display_name"],
            "fit_reason_key": program["fit_reason_key"],
            # "keyword" is renamed "related" for this public shape; "exact" and
            # "cluster" pass through unchanged so match_type stays consistent
            # with fit_reason_key (program_exact_match/program_cluster_match/
            # program_related_match) instead of collapsing a real cluster match
            # into the weaker "related" bucket.
            "match_type": "related" if program["match_type"] == "keyword" else program["match_type"],
            "confidence": program["confidence"],
            "program_fit_score": program["program_fit_score"],
            "major_cluster": program["major_cluster"],
            "subject_ranking": program["subject_ranking"],
        }
        for program in program_summary["recommended_programs"]
    ]
    has_program_data = program_summary["program_data_verified"]
    best_program = program_summary["recommended_programs"][0] if program_summary["recommended_programs"] else None
    inferred_clusters = program_summary["major_inference"].get("clusters", [])
    subject_context = subject_ranking_context(university, inferred_clusters)

    essay_ready = profile.essay_status == profile.EssayStatus.YES
    exam_ready = not any(
        risk in fit["risks"] for risk in ("sat_below_p25", "sat_below_average", "ielts_below_minimum")
    )
    normalized_deadline = normalize_university_deadline(university, profile)
    deadline = normalized_deadline.normalized_date
    days_remaining = (deadline - date.today()).days if deadline else None

    confidence = fit["confidence"]
    if confidence_cap:
        confidence = _cap_confidence(confidence, confidence_cap)

    aid_note_key = "aid_signal_available" if _has_aid_signal(university) else "aid_not_verified"
    missing_data = list(fit["missing_data"])[:5]

    composite_score = calculate_composite_score(
        fit=fit, profile_strength=profile_strength, program_summary=program_summary, best_program=best_program
    )
    # 022 Phase 11: a soft, opt-in preference (never a penalty for schools
    # that require testing -- only a small bonus for schools that match a
    # stated test-optional preference), unlike the hard institution-type/
    # ranking-range filters applied earlier in candidate selection.
    if (
        preferences is not None
        and getattr(preferences, "test_optional_preference", False)
        and university.test_policy in {University.TestPolicy.OPTIONAL, University.TestPolicy.BLIND}
    ):
        composite_score = min(100, composite_score + 3)
    category = derive_recommendation_category(
        university=university,
        composite_score=composite_score,
        is_deadline_overdue=days_remaining is not None and days_remaining < 0,
        is_confirmed_unaffordable=fit["cost_context"]["budget_comparison"]["status"] == STATUS_ABOVE_BUDGET,
        is_severe_academic_gap=fit["severe_academic_gap"],
    )

    return {
        "university": {
            "id": university.id,
            "name": university.name,
            "slug": university.slug,
            "country": university.country,
            "city": university.city,
        },
        "category": category,
        # The underlying canonical Fit Engine's own independent tier
        # (reach/competitive/target/safety/None -- see CATEGORY_ORDER in
        # services.py), surfaced alongside the adaptive "category" above for
        # transparency (022 Phase 8): the two are allowed to disagree, since
        # "category" additionally weighs program/cost/EC/preference/readiness
        # and diversity, not just acceptance-rate-anchored academic fit.
        "canonical_fit_tier": fit["category"],
        "is_international": _is_international(profile, university),
        "fit_score": composite_score,
        "canonical_fit_score": fit["fit_score"],
        "confidence": confidence,
        "recommended_programs": programs,
        "matched_programs": programs,
        "program_data_verified": has_program_data,
        "best_program_fit_score": best_program["program_fit_score"] if best_program else None,
        "major_cluster_match": bool(best_program and best_program["major_cluster"] in inferred_clusters),
        "program_fit_confidence": program_summary["confidence"],
        "program_strengths": best_program["preparation_strengths"] if best_program else [],
        "program_gaps": best_program["preparation_gaps"] if best_program else [],
        "subject_ranking_context": subject_context,
        "missing_program_data": program_summary["missing_data"],
        "major_inference": program_summary["major_inference"],
        "application_round": _application_round_info(
            university, essay_ready=essay_ready, exam_ready=exam_ready, days_remaining=days_remaining
        ),
        "deadline": deadline,
        "deadline_confidence": _deadline_confidence(university),
        "deadline_cycle_label": normalized_deadline.cycle_label,
        "days_remaining": days_remaining,
        "urgency": _urgency_for_days(days_remaining),
        "estimated_total_cost_usd": fit["cost_context"]["total_cost_usd_amount"]
        or fit["cost_context"]["tuition_usd_amount"],
        "tuition_usd": fit["cost_context"]["tuition_usd_amount"],
        "aid_scholarship_note_key": aid_note_key,
        "cost_risk": _cost_risk(profile, university),
        "academic_risk": _risk_level_from_score(fit["academic_subscore"]),
        "profile_risk": _risk_level_from_score(fit["profile_subscore"]),
        "deadline_risk": _risk_level_from_score(fit["deadline_subscore"]),
        "main_strength": fit["strengths"][0] if fit["strengths"] else None,
        "main_risk": fit["risks"][0] if fit["risks"] else (missing_data[0] if missing_data else None),
        # Bounded, deduplicated lists (022 Phase 8) -- "top reasons" and "main
        # risks" plural, extending the single main_strength/main_risk above
        # without replacing them (existing consumers of the singular fields
        # are unaffected).
        "top_reason_keys": list(dict.fromkeys(fit["strengths"]))[:3],
        "main_risks": list(dict.fromkeys([*fit["risks"], *missing_data]))[:3],
        "holistic_context_key": _holistic_context_key(profile_strength),
        "why_recommended_keys": _why_recommended_keys(
            category=category, targets=targets, programs=programs, has_program_data=has_program_data
        ),
        "next_action": fit["next_actions"][0] if fit["next_actions"] else "verify_official_sources",
        "missing_data": missing_data,
        "current_academic_subscore": fit["academic_subscore"],
        "conditional_notes": fit["conditional_notes"],
        "conditional_fit_score": fit["conditional_fit_score"],
        "conditional_targets": fit["conditional_targets"],
        "source_notes": fit["source_notes"],
        "is_shortlisted": university.id in shortlisted_ids,
        "application_id": tracked_by_university.get(university.id),
    }


def _bucket_and_balance(
    items: list[dict], category_quotas: dict[str, int] | None = None
) -> tuple[list[dict], dict]:
    """Adaptive, diversity-aware selection (022 Phase 6). Quotas are upper
    bounds, not targets: a bucket comes back short rather than padded with
    weak matches (the fit-score gap below is the only hard cutoff -- a real
    quality bar). Country diversity is a *preference* applied only when
    choosing among otherwise-eligible candidates: it never shrinks a bucket
    below what its eligible candidates could fill, so 3 equally-good
    same-country universities are never reduced to 2 just because no
    other-country alternative exists.

    `category_quotas` overrides CATEGORY_QUOTAS (022 Phase 11: a student's
    own "preferred category distribution" control) -- still upper bounds,
    still never padded.
    """

    quotas = category_quotas or CATEGORY_QUOTAS
    buckets: dict[str, list[dict]] = {category: [] for category in CATEGORY_ORDER_FOR_LIST}
    for item in items:
        buckets.setdefault(item["category"], []).append(item)
    for bucket in buckets.values():
        bucket.sort(key=lambda item: (item["fit_score"], CONFIDENCE_RANK.get(item["confidence"], 1)), reverse=True)

    selected: list[dict] = []
    country_counts: dict[str, int] = {}
    counts = {"dream": 0, "reach": 0, "target": 0, "safety": 0, "international": 0}
    for category in CATEGORY_ORDER_FOR_LIST:
        quota = quotas.get(category, CATEGORY_QUOTAS[category])

        eligible: list[dict] = []
        for item in buckets.get(category, []):
            if eligible and (eligible[0]["fit_score"] - item["fit_score"]) > MAX_FIT_SCORE_GAP_FOR_PADDING:
                # Sorted by fit_score descending, so once one candidate falls
                # too far behind the bucket's own top pick, every remaining
                # candidate is at least as far behind.
                break
            eligible.append(item)

        chosen: list[dict] = []
        deferred: list[dict] = []
        for item in eligible:
            if len(chosen) >= quota:
                break
            country = item["university"]["country"]
            projected_total = len(selected) + len(chosen) + 1
            country_cap = max(2, round(projected_total * MAX_SHARE_PER_COUNTRY))
            if chosen and country_counts.get(country, 0) + 1 > country_cap:
                deferred.append(item)
                continue
            chosen.append(item)
            country_counts[country] = country_counts.get(country, 0) + 1

        # Diversity is a preference, not a hard cap: backfill from the
        # over-cap candidates (still fit-score-eligible) if quota isn't met
        # and no more-diverse alternative exists.
        for item in deferred:
            if len(chosen) >= quota:
                break
            chosen.append(item)
            country_counts[item["university"]["country"]] = (
                country_counts.get(item["university"]["country"], 0) + 1
            )
        chosen.sort(key=lambda item: (item["fit_score"], CONFIDENCE_RANK.get(item["confidence"], 1)), reverse=True)

        selected.extend(chosen)
        counts[category] = len(chosen)
    counts["international"] = sum(1 for item in selected if item["is_international"])
    counts["total"] = len(selected)
    return selected, counts


# Substrings shared by every profile_strength reason code that means "we have
# no evidence" rather than "the evidence is weak" (022 Phase 7, Case D) --
# e.g. TEST_MISSING, ACTIVITIES_MISSING, FINANCIAL_PLANNING_INCOMPLETE,
# GPA_RANGE_UNKNOWN, COUNTRY_NOT_SPECIFIED, FINANCIAL_NEED_UNSURE. Deliberately
# excludes genuine-weakness codes like SUBJECT_PREPARATION_GAP, which must
# never be reframed as a missing-data problem.
_MISSING_SIGNAL_MARKERS = ("MISSING", "INCOMPLETE", "UNKNOWN", "NOT_SPECIFIED", "UNSURE")


def _missing_profile_signals(profile_strength: dict) -> list[str]:
    """A deduplicated missing-info checklist (022 Phase 7, Case D) built by
    reusing the reason codes calculate_profile_strength already produces,
    rather than inventing a second missing-data vocabulary.
    """

    codes: list[str] = []
    for dimension in (
        "academic_strength",
        "extracurricular_strength",
        "application_readiness",
        "practical_fit",
    ):
        for component in profile_strength[dimension]["components"]:
            for code in component["reason_codes"]:
                if code not in codes and any(marker in code for marker in _MISSING_SIGNAL_MARKERS):
                    codes.append(code)
    return codes


def _financial_risk_warning(profile, selected: list[dict]) -> dict:
    """Case E (022 Phase 7): a student who has declared financial need but
    whose current list is dominated by confirmed-high cost risk gets an
    explicit warning rather than a silently unaffordable-looking list. Never
    fires for a profile that hasn't declared need, and never fires from an
    empty list -- this is a signal about the *list*, not a judgment about any
    one university.
    """

    if profile.scholarship_need != profile.ScholarshipNeed.YES or not selected:
        return {"active": False, "high_cost_risk_count": 0, "total": len(selected)}
    high_risk_count = sum(1 for item in selected if item["cost_risk"] == "high")
    return {
        "active": high_risk_count > len(selected) / 2,
        "high_cost_risk_count": high_risk_count,
        "total": len(selected),
    }


def calculate_university_recommendations(profile, preferences=None, *, limit: int = 25) -> dict:
    # Local import: profile_assessment_service.profile_strength imports back
    # from university_service.benchmark/major_matching/services, and
    # benchmark.py already imports from this module -- a module-level import
    # here would be circular. profile_strength is university-independent, so
    # it is computed once per request, never once per candidate.
    from services.profile_assessment_service.profile_strength import calculate_profile_strength

    profile_strength = calculate_profile_strength(profile)
    targets = _normalized_targets(profile)

    # 022 Phase 11: desired-count override (sane-bounded; malformed/absent
    # falls back to the caller's own `limit`).
    candidate_limit = limit
    desired_count = getattr(preferences, "desired_recommendation_count", None) if preferences else None
    if isinstance(desired_count, int) and desired_count > 0:
        candidate_limit = min(100, desired_count)

    excluded_ids = set(
        ExcludedUniversity.objects.filter(user_id=profile.user_id).values_list("university_id", flat=True)
    )
    # An explicit exclusion always wins over a pin for the same school.
    pinned_ids = (
        set(
            PinnedUniversity.objects.filter(user_id=profile.user_id).values_list("university_id", flat=True)
        )
        - excluded_ids
    )

    queryset = (
        University.objects.filter(is_published=True, is_demo=False)
        .select_related("signal_weights")
        .prefetch_related(
            "programs",
            "subject_rankings",
            "scholarships",
            "data_sources",
            "field_verifications",
        )
        .order_by("name")
    )
    candidates = [
        university for university in queryset if _country_matches_preference(university.country, targets)
    ]

    missing_preferences = []
    if not targets:
        missing_preferences.append("preferred_countries")
    if not (profile.intended_majors or profile.intended_major):
        missing_preferences.append("intended_major")

    confidence_caps = []
    if not targets:
        confidence_caps.append("medium")
    if profile_strength["overall_confidence"] < LOW_PROFILE_CONFIDENCE_THRESHOLD:
        confidence_caps.append("low")
    confidence_cap = (
        min(confidence_caps, key=lambda cap: CONFIDENCE_RANK.get(cap, 1)) if confidence_caps else None
    )

    # Two bulk queries instead of one query per candidate university.
    shortlisted_ids = set(
        SavedUniversity.objects.filter(user_id=profile.user_id).values_list("university_id", flat=True)
    )
    tracked_by_university: dict[int, int] = dict(
        ApplicationTrackerItem.objects.filter(user_id=profile.user_id).values_list("university_id", "id")
    )

    items: list[dict] = []
    pinned_items: list[dict] = []
    excluded_low_data_count = 0
    excluded_degree_mismatch_count = 0
    excluded_by_user_count = 0
    for university in candidates:
        # 022 Phase 11: an explicit student exclusion is an unconditional
        # veto, checked first (cheapest, and wins even over a pin above).
        if university.id in excluded_ids:
            excluded_by_user_count += 1
            continue

        # Hard filter (022 Phase 4): only a *confirmed* degree-level mismatch
        # excludes -- unknown/unrecognized data on either side never does.
        # Cheaper than a full fit calculation, so checked first.
        #
        # A hard exclusion for expired deadlines was deliberately NOT added
        # here: this codebase already shows a past-deadline university with
        # urgency="overdue" and application_round.recommended_round="unknown"
        # (see test_past_deadline_does_not_recommend_current_cycle_round)
        # rather than removing it outright, so a student planning for next
        # cycle isn't denied a school that's still relevant. "Must not appear
        # as an active recommendation" is satisfied by never letting an
        # overdue item resolve to a "practical/apply-now" category -- see the
        # category-capping logic added in Phase 6.
        if _degree_level_excludes(profile, university):
            excluded_degree_mismatch_count += 1
            continue

        # A pin is a stronger, more specific signal than a general
        # institution-type/ranking-range preference, so pinned universities
        # skip those two (opt-in, general) hard filters -- they never skip
        # the data-driven checks above, since pinning cannot manufacture
        # evidence that doesn't exist.
        is_pinned = university.id in pinned_ids
        if not is_pinned and not _passes_preference_hard_filters(university, preferences):
            continue

        item = _build_recommendation_item(
            profile=profile,
            university=university,
            targets=targets,
            confidence_cap=confidence_cap,
            shortlisted_ids=shortlisted_ids,
            tracked_by_university=tracked_by_university,
            profile_strength=profile_strength,
            preferences=preferences,
        )
        if item is None:
            excluded_low_data_count += 1
            continue

        item["is_pinned"] = is_pinned
        (pinned_items if is_pinned else items).append(item)

    category_quotas = _sanitized_category_distribution(preferences)
    selected, counts = _bucket_and_balance(items, category_quotas)

    # Pinned universities are always included, with the same honestly
    # computed category as everything else (022 Phase 11) -- they bypass
    # quota/diversity capping entirely, never the fit computation itself.
    # Already excluded from `items` above, so this can never duplicate.
    if pinned_items:
        selected = pinned_items + selected
        for item in pinned_items:
            counts[item["category"]] = counts.get(item["category"], 0) + 1
        counts["total"] = len(selected)
        counts["international"] = sum(1 for item in selected if item["is_international"])

    list_size_limited = counts["total"] < min(candidate_limit, 20) and counts["total"] == len(items) + len(
        pinned_items
    )
    # Pinned items are never dropped by the desired-count limit -- the limit
    # only ever caps how many *additional*, non-pinned items are shown.
    effective_limit = max(candidate_limit, len(pinned_items))
    limited_selection = selected[:effective_limit]

    return {
        "recommendations": limited_selection,
        "counts": counts,
        "missing_preferences": missing_preferences,
        "missing_profile_signals": _missing_profile_signals(profile_strength),
        "financial_risk_warning": _financial_risk_warning(profile, limited_selection),
        "excluded_low_data_count": excluded_low_data_count,
        "excluded_degree_mismatch_count": excluded_degree_mismatch_count,
        "excluded_by_user_count": excluded_by_user_count,
        "list_size_limited": list_size_limited,
        "disclaimer": (
            "This is a fit estimate based on available profile and university data. "
            "It is not an admissions prediction or guarantee."
        ),
    }


def explain_recommendation_for_university(profile, university: University, preferences=None) -> dict:
    """022 Phase 11 explain endpoint: answers "why is this recommended?",
    "why is this category?", "what would move this to Target?", and "why
    was this university excluded?" from deterministic reason codes and
    already-computed data only -- never AI, never a fabricated explanation.
    Deliberately still computes a fit/category even for an excluded
    university (unless there truly isn't enough comparable data), so
    "why was this excluded" can be answered alongside "what would its fit
    have looked like."
    """

    from services.profile_assessment_service.profile_strength import calculate_profile_strength

    targets = _normalized_targets(profile)

    exclusion_reason: str | None = None
    if not _country_matches_preference(university.country, targets):
        exclusion_reason = "country_preference_mismatch"
    elif _degree_level_excludes(profile, university):
        exclusion_reason = "degree_level_mismatch"
    elif ExcludedUniversity.objects.filter(user_id=profile.user_id, university_id=university.id).exists():
        exclusion_reason = "user_excluded"
    elif not _passes_preference_hard_filters(university, preferences):
        exclusion_reason = "preference_filter_mismatch"

    profile_strength = calculate_profile_strength(profile)
    shortlisted_ids = set(
        SavedUniversity.objects.filter(user_id=profile.user_id).values_list("university_id", flat=True)
    )
    tracked_by_university: dict[int, int] = dict(
        ApplicationTrackerItem.objects.filter(user_id=profile.user_id).values_list("university_id", "id")
    )
    item = _build_recommendation_item(
        profile=profile,
        university=university,
        targets=targets,
        confidence_cap=None,
        shortlisted_ids=shortlisted_ids,
        tracked_by_university=tracked_by_university,
        profile_strength=profile_strength,
        preferences=preferences,
    )

    university_ref = {"id": university.id, "name": university.name, "slug": university.slug}

    if item is None:
        return {
            "university": university_ref,
            "is_recommendable": False,
            "excluded_reason_key": exclusion_reason or "insufficient_comparable_data",
            "category": None,
            "canonical_fit_tier": None,
            "fit_score": None,
            "why_recommended_keys": [],
            "category_explanation_keys": [],
            "improvement_reason_keys": [],
        }

    category = item["category"]
    selectivity = _selectivity_band(
        float(university.acceptance_rate) if university.acceptance_rate is not None else None
    )
    category_explanation_keys = [f"selectivity_{selectivity}", f"category_{category}"]
    if item["canonical_fit_tier"] is not None and item["canonical_fit_tier"] != category:
        category_explanation_keys.append("category_adjusted_from_canonical_tier")

    # "What would move this to Target?" -- the same, already-computed risk/
    # missing-data codes already shown as this item's main_risks; never a
    # new computation, so the answer can never drift from what the list
    # itself already says about this university.
    improvement_reason_keys = list(item["main_risks"]) if category not in {"target", "safety"} else []

    return {
        "university": university_ref,
        "is_recommendable": exclusion_reason is None,
        "excluded_reason_key": exclusion_reason,
        "category": category,
        "canonical_fit_tier": item["canonical_fit_tier"],
        "fit_score": item["fit_score"],
        "why_recommended_keys": list(dict.fromkeys([*item["why_recommended_keys"], *item["top_reason_keys"]])),
        "category_explanation_keys": category_explanation_keys,
        "improvement_reason_keys": improvement_reason_keys,
    }


def diagnose_university_recommendations(profile, preferences=None, *, limit: int = 25) -> dict:
    """022 Phase 12: an authorized-internal-only diagnostic trace of how a
    student's recommendation list was built -- candidate pool size,
    hard-filter removals with reason codes, category-cap outcomes, and the
    current recommendation cache's hit/miss state. Never exposed to ordinary
    users or across users (the caller must be admin-gated).

    Calls `calculate_university_recommendations` exactly once -- the single
    source of truth for scoring -- then re-derives *why* using the same
    small, pure, already-unit-tested filter helpers the real engine calls
    (never a second, divergent implementation). The one deliberate exception
    is `calculate_university_fit` itself, called again only for the subset of
    candidates that passed every hard filter but didn't appear in the final
    list -- this reuses the canonical Fit Engine a second time rather than
    reimplementing it, the same accepted pattern already used by
    `explain_recommendation_for_university`.
    """

    result = calculate_university_recommendations(profile, preferences, limit=limit)
    included_slugs = {item["university"]["slug"] for item in result["recommendations"]}

    targets = _normalized_targets(profile)
    excluded_ids = set(
        ExcludedUniversity.objects.filter(user_id=profile.user_id).values_list("university_id", flat=True)
    )
    pinned_ids = (
        set(PinnedUniversity.objects.filter(user_id=profile.user_id).values_list("university_id", flat=True))
        - excluded_ids
    )

    removal_counts: dict[str, int] = {}
    removed_universities: list[dict] = []
    remaining_candidates: list[University] = []

    def _university_ref(university: University) -> dict:
        return {"id": university.id, "slug": university.slug, "name": university.name}

    def _record_removal(university: University, reason_code: str) -> None:
        removal_counts[reason_code] = removal_counts.get(reason_code, 0) + 1
        if len(removed_universities) < 50:
            removed_universities.append({**_university_ref(university), "reason_code": reason_code})

    unpublished_count = University.objects.filter(is_demo=False, is_published=False).count()

    published_queryset = University.objects.filter(is_published=True, is_demo=False).prefetch_related("programs")
    candidate_pool_count = published_queryset.count()

    for university in published_queryset:
        if university.id in excluded_ids:
            _record_removal(university, REASON_USER_EXCLUDED)
            continue
        if not _country_matches_preference(university.country, targets):
            _record_removal(university, REASON_COUNTRY_EXCLUDED)
            continue
        if _degree_level_excludes(profile, university):
            _record_removal(university, REASON_DEGREE_LEVEL_MISMATCH)
            continue
        if university.id not in pinned_ids and not _passes_preference_hard_filters(university, preferences):
            _record_removal(university, REASON_PREFERENCE_FILTER_MISMATCH)
            continue
        remaining_candidates.append(university)

    # Anything left passed every hard filter above. If it's in the final
    # list, it was included; otherwise it either had no comparable fit data
    # (the canonical Fit Engine's own category is None) or was cut by
    # category-quota/diversity capping inside _bucket_and_balance.
    for university in remaining_candidates:
        if university.slug in included_slugs:
            continue
        fit = calculate_university_fit(profile, university)
        if fit["category"] is None:
            _record_removal(university, REASON_DATA_CONFIDENCE_TOO_LOW)
        else:
            _record_removal(university, REASON_CATEGORY_CAP_REACHED)

    cache_key = recommendations_cache_key(profile.user)
    cache_status = "hit" if cache.get(cache_key) is not None else "miss"

    return {
        "candidate_pool_count": candidate_pool_count,
        "unpublished_or_demo_excluded_count": unpublished_count,
        "hard_filter_removal_counts": removal_counts,
        "removed_universities_sample": removed_universities,
        "final_counts": result["counts"],
        "final_recommendation_count": len(result["recommendations"]),
        "pinned_count": len(pinned_ids),
        "user_excluded_count": len(excluded_ids),
        "cache_status": cache_status,
        "cache_key": cache_key,
        "disclaimer": "Internal diagnostic view -- not shown to ordinary users, never cross-user.",
    }
