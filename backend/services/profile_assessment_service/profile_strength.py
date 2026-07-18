"""Canonical, university-independent profile-strength model (022 Phases 1-3).

Four separate dimensions -- academic_strength, extracurricular_strength,
application_readiness, practical_fit -- each with its own 0-100 score, 0-1
confidence, and itemized components. Deliberately never aggregates these
into a single number or an "admission chance": recommendations.py combines
them with per-university fit later (Phase 5), but nothing in this module
expresses a probability or guarantee.

Missing evidence and weak evidence are tracked separately throughout: a
component that has no data returns confidence-reducing "insufficient_data"
notes rather than a low score, per this task's explicit rule that missing
information must never be treated as poor performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from django.utils import timezone

from services.essay_service.models import EssayWorkspace
from services.university_service.benchmark import resolve_benchmark
from services.university_service.major_matching import CLUSTER_KEYWORDS, infer_major_clusters
from services.university_service.services import best_ielts_score, best_sat_score
from services.user_profile_service.academic_normalization import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    normalize_profile_academics,
)
from services.user_profile_service.curriculum_rigor import (
    calculate_curriculum_rigor,
    calculate_major_curriculum_fit,
)
from services.user_profile_service.models import (
    Activity,
    Honor,
    Olympiad,
    PortfolioProject,
    Recommender,
    ResearchProject,
    Sport,
    Volunteer,
)

# ---------------------------------------------------------------------------
# Academic-strength reason codes (Phase 2)
# ---------------------------------------------------------------------------
GPA_ABOVE_VERIFIED_RANGE = "GPA_ABOVE_VERIFIED_RANGE"
GPA_WITHIN_VERIFIED_RANGE = "GPA_WITHIN_VERIFIED_RANGE"
GPA_BELOW_VERIFIED_RANGE = "GPA_BELOW_VERIFIED_RANGE"
GPA_RANGE_UNKNOWN = "GPA_RANGE_UNKNOWN"
TEST_ABOVE_RANGE = "TEST_ABOVE_RANGE"
TEST_WITHIN_RANGE = "TEST_WITHIN_RANGE"
TEST_MISSING = "TEST_MISSING"
TEST_RANGE_UNKNOWN = "TEST_RANGE_UNKNOWN"
CURRICULUM_MATCH = "CURRICULUM_MATCH"
SUBJECT_PREPARATION_GAP = "SUBJECT_PREPARATION_GAP"
ACADEMIC_DATA_INCOMPLETE = "ACADEMIC_DATA_INCOMPLETE"

_GPA_TOLERANCE_PERCENT = 2.0  # within +/-2 percentage points counts as "within range"
_TEST_TOLERANCE_FRACTION = 0.02  # within +/-2% of the benchmark counts as "within range"


@dataclass
class ScoreComponent:
    key: str
    score: int | None
    confidence: float
    reason_codes: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class DimensionResult:
    score: int
    confidence: float
    components: list[ScoreComponent] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "confidence": round(self.confidence, 2),
            "components": [
                {
                    "key": component.key,
                    "score": component.score,
                    "confidence": round(component.confidence, 2),
                    "reason_codes": component.reason_codes,
                    "note": component.note,
                }
                for component in self.components
            ],
        }


def _weighted_average(components: list[ScoreComponent]) -> tuple[int, float]:
    """Confidence-weighted average score, plus a confidence that reflects how
    much of the total possible evidence was actually usable. A component with
    score=None (no evidence at all) contributes nothing to the score average
    but still pulls overall confidence down via the denominator below.
    """

    scored = [component for component in components if component.score is not None]
    if not scored:
        return 50, 0.1

    total_weight = sum(max(component.confidence, 0.05) for component in scored)
    weighted_sum = sum(component.score * max(component.confidence, 0.05) for component in scored)
    score = round(weighted_sum / total_weight) if total_weight else 50

    # Overall confidence reflects both per-component confidence AND how many
    # of the *known* components (scored or not) actually had evidence --
    # missing components are never silently dropped from this average.
    average_confidence = sum(component.confidence for component in components) / len(components)
    return max(1, min(100, score)), round(average_confidence, 3)


# ---------------------------------------------------------------------------
# Academic strength (Phase 2)
# ---------------------------------------------------------------------------


def _gpa_component(profile, benchmark_academic: dict) -> ScoreComponent:
    normalization = normalize_profile_academics(profile)
    if normalization.normalized_percentage is None:
        note = (
            "GPA scale is unconfirmed or missing."
            if normalization.original_gpa_value is not None
            else "No GPA on file yet."
        )
        return ScoreComponent(
            "gpa", None, 0.15, [GPA_RANGE_UNKNOWN, ACADEMIC_DATA_INCOMPLETE], note
        )

    confidence_by_normalization = {
        CONFIDENCE_HIGH: 0.9,
        CONFIDENCE_MEDIUM: 0.65,
        CONFIDENCE_LOW: 0.35,
    }.get(normalization.confidence, 0.5)

    benchmark_percent = benchmark_academic.get("gpa_average_percent")
    if benchmark_percent is None:
        # A confirmed GPA with no comparable benchmark is still real evidence
        # of academic performance -- score it on its own merits (a strong
        # absolute percentage is still strong) rather than reporting nothing.
        student_percent = float(normalization.normalized_percentage)
        score = max(1, min(100, round(student_percent)))
        return ScoreComponent(
            "gpa",
            score,
            confidence_by_normalization * 0.6,
            [GPA_RANGE_UNKNOWN],
            "No comparable benchmark is available yet; score reflects the raw normalized percentage only.",
        )

    student_percent = float(normalization.normalized_percentage)
    diff = student_percent - float(benchmark_percent)
    if diff >= _GPA_TOLERANCE_PERCENT:
        score = max(1, min(100, round(70 + diff)))
        reason = GPA_ABOVE_VERIFIED_RANGE
    elif diff <= -_GPA_TOLERANCE_PERCENT:
        score = max(1, min(100, round(70 + diff)))
        reason = GPA_BELOW_VERIFIED_RANGE
    else:
        score = 70
        reason = GPA_WITHIN_VERIFIED_RANGE

    return ScoreComponent("gpa", score, confidence_by_normalization, [reason])


def _test_component(profile, benchmark_academic: dict) -> ScoreComponent:
    student_sat = best_sat_score(profile.test_scores)
    student_ielts = best_ielts_score(profile.test_scores)
    if student_sat is None and student_ielts is None:
        # A student may simply not have sat a standardized test yet -- this is
        # not the same as a confirmed weak score, so it is never converted to
        # a low score here (see TEST_MISSING_OPTIONAL/TEST_REQUIRED_MISSING at
        # the per-university comparison layer, where a specific school's
        # testing policy is actually known).
        return ScoreComponent(
            "standardized_testing",
            None,
            0.2,
            [TEST_MISSING, ACADEMIC_DATA_INCOMPLETE],
            "No SAT or IELTS score on file yet.",
        )

    scores: list[int] = []
    reasons: list[str] = []
    if student_sat is not None:
        sat_benchmark = benchmark_academic.get("sat_average")
        if sat_benchmark is None:
            scores.append(max(1, min(100, round(student_sat / 16))))
            reasons.append(TEST_RANGE_UNKNOWN)
        else:
            diff_fraction = (student_sat - float(sat_benchmark)) / float(sat_benchmark)
            if diff_fraction >= _TEST_TOLERANCE_FRACTION:
                scores.append(max(1, min(100, round(70 + diff_fraction * 300))))
                reasons.append(TEST_ABOVE_RANGE)
            elif diff_fraction <= -_TEST_TOLERANCE_FRACTION:
                scores.append(max(1, min(100, round(70 + diff_fraction * 300))))
                reasons.append(TEST_WITHIN_RANGE if diff_fraction > -0.08 else GPA_BELOW_VERIFIED_RANGE)
            else:
                scores.append(70)
                reasons.append(TEST_WITHIN_RANGE)
    if student_ielts is not None:
        ielts_benchmark = benchmark_academic.get("ielts_competitive") or benchmark_academic.get(
            "ielts_minimum"
        )
        if ielts_benchmark is None:
            scores.append(max(1, min(100, round(student_ielts / 9 * 100))))
            reasons.append(TEST_RANGE_UNKNOWN)
        else:
            diff = student_ielts - float(ielts_benchmark)
            if diff >= 0.2:
                scores.append(max(1, min(100, round(70 + diff * 20))))
                reasons.append(TEST_ABOVE_RANGE)
            elif diff <= -0.2:
                scores.append(max(1, min(100, round(70 + diff * 20))))
                reasons.append(TEST_WITHIN_RANGE if diff > -1.0 else GPA_BELOW_VERIFIED_RANGE)
            else:
                scores.append(70)
                reasons.append(TEST_WITHIN_RANGE)

    score = round(sum(scores) / len(scores))
    confidence = 0.75 if TEST_RANGE_UNKNOWN not in reasons else 0.5
    return ScoreComponent("standardized_testing", score, confidence, list(dict.fromkeys(reasons)))


def _curriculum_component(profile) -> ScoreComponent:
    rigor = calculate_curriculum_rigor(profile)
    intended_major = profile.intended_major or (
        profile.intended_majors[0] if profile.intended_majors else None
    )
    major_fit = calculate_major_curriculum_fit(profile, intended_major)
    reasons = []
    confidence = 0.8 if not rigor.missing_curriculum_data else 0.45
    if major_fit.get("gap"):
        reasons.append(SUBJECT_PREPARATION_GAP)
    elif profile.curriculum_type != profile.CurriculumType.UNKNOWN:
        reasons.append(CURRICULUM_MATCH)
    else:
        reasons.append(ACADEMIC_DATA_INCOMPLETE)
        confidence = 0.3
    return ScoreComponent("curriculum_rigor", rigor.rigor_score, confidence, reasons)


def _advanced_coursework_component(profile) -> ScoreComponent:
    counts = [
        profile.ap_courses_count,
        profile.ib_courses_count,
        profile.a_level_subjects_count,
        profile.honors_courses_count,
    ]
    known = [value for value in counts if value is not None]
    if not known:
        return ScoreComponent(
            "advanced_coursework", None, 0.2, [ACADEMIC_DATA_INCOMPLETE], "No AP/IB/A-Level/honors count on file."
        )
    total = sum(known)
    score = max(1, min(100, 40 + total * 8))
    return ScoreComponent("advanced_coursework", score, 0.7, [])


def _academic_distinctions_component(user) -> ScoreComponent:
    honors = list(Honor.objects.filter(user=user))
    olympiads = list(Olympiad.objects.filter(user=user))
    if not honors and not olympiads:
        return ScoreComponent(
            "academic_distinctions", None, 0.25, [ACADEMIC_DATA_INCOMPLETE], "No honors or olympiad results on file."
        )

    level_scores = {"international": 95, "national": 82, "regional": 68, "city": 55, "school": 45}
    best = 45
    for record in (*honors, *olympiads):
        level = str(getattr(record, "level", "") or "").strip().lower()
        best = max(best, level_scores.get(level, 55))
    return ScoreComponent("academic_distinctions", best, 0.7, [])


def _academic_research_component(user) -> ScoreComponent:
    projects = list(ResearchProject.objects.filter(user=user))
    if not projects:
        return ScoreComponent(
            "academic_research", None, 0.3, [ACADEMIC_DATA_INCOMPLETE], "No research project on file."
        )
    stage_scores = {"published": 92, "completed": 78, "active": 62, "planning": 48}
    best = max(stage_scores.get(project.current_stage, 55) for project in projects)
    return ScoreComponent("academic_research", best, 0.6, [])


def calculate_academic_strength(profile) -> DimensionResult:
    """Deterministic, university-independent academic-strength dimension.

    Compares GPA/testing against a general benchmark (`resolve_benchmark`,
    the same tiered dream/major-country/country/global-major/global fallback
    already used for the student's own profile assessment) rather than any
    one specific university -- per-university comparison stays in
    `calculate_university_fit` (Phase 5 reuses it, never duplicates it here).
    """

    benchmark = resolve_benchmark(profile)
    components = [
        _gpa_component(profile, benchmark.academic),
        _test_component(profile, benchmark.academic),
        _curriculum_component(profile),
        _advanced_coursework_component(profile),
        _academic_distinctions_component(profile.user),
        _academic_research_component(profile.user),
    ]
    score, confidence = _weighted_average(components)
    return DimensionResult(score=score, confidence=confidence, components=components)


# ---------------------------------------------------------------------------
# Extracurricular strength (Phase 3)
# ---------------------------------------------------------------------------

_SCALE_RECOGNITION = {
    "international": 5,
    "national": 4,
    "regional": 3,
    "city": 2,
    "school": 1,
}
_STRONG_LEADERSHIP_KEYWORDS = (
    "president",
    "founder",
    "co-founder",
    "captain",
    "director",
    "head",
    "chief",
    "chair",
)
_MODERATE_LEADERSHIP_KEYWORDS = ("lead", "coordinator", "officer", "co-lead", "manager")


@dataclass
class _NormalizedRecord:
    source: str
    key: tuple[str, str]
    role: str
    category_text: str
    scale_recognition: int | None
    start_date: date | None
    end_date: date | None
    hours_per_week: float | None
    weeks_per_year: int | None
    has_proof: bool
    has_description: bool
    impact_text: str


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _duration_months(record: _NormalizedRecord) -> float | None:
    if record.start_date is None:
        return None
    end = record.end_date or timezone.localdate()
    months = (end.year - record.start_date.year) * 12 + (end.month - record.start_date.month)
    return max(0.0, float(months))


def _duration_score(months: float | None) -> tuple[int, float]:
    if months is None:
        return 2, 0.4
    if months < 3:
        return 1, 0.85
    if months < 12:
        return 2, 0.85
    if months < 24:
        return 3, 0.85
    if months < 36:
        return 4, 0.85
    return 5, 0.85


def _depth_score(hours_per_week: float | None) -> tuple[int, float]:
    if hours_per_week is None:
        return 2, 0.4
    if hours_per_week < 2:
        return 1, 0.8
    if hours_per_week < 5:
        return 2, 0.8
    if hours_per_week < 10:
        return 3, 0.8
    if hours_per_week < 20:
        return 4, 0.8
    return 5, 0.8


def _leadership_score(record: _NormalizedRecord, duration_months: float | None) -> tuple[int, float]:
    role = record.role.lower()
    corroborated = bool(
        (duration_months and duration_months >= 6) and (record.has_proof or record.has_description)
    )
    if any(keyword in role for keyword in _STRONG_LEADERSHIP_KEYWORDS):
        # A leadership title alone is never enough -- it must be corroborated
        # by sustained duration plus at least some supporting evidence,
        # matching the explicit "founder without activity or impact is not
        # automatically strong" rule.
        if corroborated:
            return 5, 0.75
        return 3, 0.4
    if any(keyword in role for keyword in _MODERATE_LEADERSHIP_KEYWORDS):
        return 3, 0.6
    if role.strip():
        return 1, 0.6
    return 2, 0.3


def _impact_score(record: _NormalizedRecord) -> tuple[int, float]:
    text = record.impact_text.strip()
    if not text:
        return 2, 0.3
    has_digits = any(character.isdigit() for character in text)
    if has_digits and not record.has_proof:
        # Inflated-looking numeric claims with no supporting evidence receive
        # lower confidence, never a silently-boosted score.
        return 4, 0.4
    if has_digits and record.has_proof:
        return 4, 0.8
    return 3, 0.55


def _recognition_score(record: _NormalizedRecord) -> tuple[int, float]:
    if record.scale_recognition is None:
        return 2, 0.4
    return record.scale_recognition, 0.75


def _relevance_score(record: _NormalizedRecord, clusters: list[str], keyword_table: dict) -> tuple[int, float]:
    if not clusters:
        return 2, 0.3
    text = record.category_text.lower()
    for cluster in clusters:
        keywords = keyword_table.get(cluster, ())
        if any(keyword in text for keyword in keywords):
            return 5, 0.7
    return 2, 0.5


def _normalize_key(title: str, organization: str) -> tuple[str, str]:
    return title.strip().lower(), organization.strip().lower()


def _collect_records(user) -> list[_NormalizedRecord]:
    records: list[_NormalizedRecord] = []
    seen_keys: set[tuple[str, str]] = set()

    def _add(source, title, role, category_text, scale_value, start, end, hours, weeks, proof, description, impact):
        key = _normalize_key(title, "")
        # Duplicate-activity collapse: a near-identical (title, source) pair
        # is counted once, keeping whichever instance has the longer
        # description (a proxy for which entry the student actually
        # maintained) rather than double-counting the same activity.
        dedup_key = (source, key[0])
        if dedup_key in seen_keys:
            return
        seen_keys.add(dedup_key)
        records.append(
            _NormalizedRecord(
                source=source,
                key=key,
                role=role or "",
                category_text=category_text or "",
                scale_recognition=_SCALE_RECOGNITION.get(str(scale_value or "").lower()),
                start_date=start,
                end_date=end,
                hours_per_week=_to_float(hours),
                weeks_per_year=weeks,
                has_proof=bool(proof),
                has_description=bool(description and len(description.strip()) > 20),
                impact_text=str(impact or ""),
            )
        )

    for activity in Activity.objects.filter(user=user):
        _add(
            "activity",
            activity.title,
            activity.role,
            f"{activity.category} {activity.title}",
            activity.scale,
            activity.start_date,
            activity.end_date,
            activity.hours_per_week,
            activity.weeks_per_year,
            activity.proof_link,
            activity.description,
            activity.impact_number,
        )
    for volunteer in Volunteer.objects.filter(user=user):
        _add(
            "volunteering",
            volunteer.title,
            volunteer.role,
            f"volunteering community {volunteer.title}",
            volunteer.scale,
            volunteer.start_date,
            volunteer.end_date,
            volunteer.hours_per_week,
            volunteer.weeks_per_year,
            volunteer.proof_link,
            volunteer.description,
            volunteer.impact_number or volunteer.beneficiaries,
        )
    for sport in Sport.objects.filter(user=user):
        _add(
            "sport",
            sport.sport_name,
            "captain" if "captain" in (sport.peak_result or "").lower() else "",
            sport.sport_name,
            sport.level,
            None,
            None,
            None,
            None,
            sport.proof_link,
            sport.description,
            sport.peak_result,
        )
    for project in ResearchProject.objects.filter(user=user):
        _add(
            "research",
            project.title,
            "researcher",
            f"research {project.field}",
            "national" if project.current_stage == ResearchProject.Stage.PUBLISHED else "school",
            None,
            None,
            None,
            None,
            bool(project.manuscript_link),
            project.description,
            project.publication_status,
        )
    for portfolio in PortfolioProject.objects.filter(user=user):
        _add(
            "portfolio",
            portfolio.title,
            "creator",
            f"portfolio {portfolio.project_type}",
            None,
            None,
            None,
            None,
            None,
            bool(portfolio.link),
            portfolio.description,
            portfolio.users_impact,
        )
    return records


def _score_record(record: _NormalizedRecord, clusters: list[str], keyword_table: dict) -> dict:
    duration_months = _duration_months(record)
    duration, duration_confidence = _duration_score(duration_months)
    depth, depth_confidence = _depth_score(record.hours_per_week)
    leadership, leadership_confidence = _leadership_score(record, duration_months)
    impact, impact_confidence = _impact_score(record)
    recognition, recognition_confidence = _recognition_score(record)
    relevance, relevance_confidence = _relevance_score(record, clusters, keyword_table)
    initiative = leadership if any(
        keyword in record.role.lower() for keyword in ("founder", "co-founder", "created", "started")
    ) else 2
    initiative_confidence = leadership_confidence if initiative == leadership else 0.35

    confidences = [
        duration_confidence,
        depth_confidence,
        leadership_confidence,
        impact_confidence,
        recognition_confidence,
        relevance_confidence,
        initiative_confidence,
    ]
    composite = (
        depth * 0.2 + duration * 0.15 + leadership * 0.2 + impact * 0.2 + recognition * 0.15 + relevance * 0.1
    )
    return {
        "source": record.source,
        "depth": depth,
        "duration": duration,
        "leadership": leadership,
        "impact": impact,
        "initiative": initiative,
        "recognition": recognition,
        "major_relevance": relevance,
        "confidence": round(sum(confidences) / len(confidences), 2),
        "composite": round(composite, 2),
    }


def calculate_extracurricular_strength(profile) -> DimensionResult:
    """Depth-based extracurricular scoring (Phase 3) -- never a raw activity
    count. Two students with the same number of activities but different
    depth/duration/leadership/impact evidence will not score the same.
    """

    clusters = infer_major_clusters(profile).clusters
    records = _collect_records(profile.user)
    if not records:
        component = ScoreComponent(
            "extracurricular_portfolio",
            None,
            0.15,
            ["ACTIVITIES_MISSING"],
            "No activities, volunteering, research, portfolio, or sports records on file.",
        )
        return DimensionResult(score=50, confidence=0.15, components=[component])

    scored_records = [_score_record(record, clusters, CLUSTER_KEYWORDS) for record in records]
    scored_records.sort(key=lambda item: item["composite"], reverse=True)

    strongest = scored_records[0]
    second_strongest = scored_records[1] if len(scored_records) > 1 else None
    leadership_breadth = sum(1 for item in scored_records if item["leadership"] >= 4)
    real_outcomes = sum(1 for item in scored_records if item["impact"] >= 4)
    relevant_records = sum(1 for item in scored_records if item["major_relevance"] >= 4)
    thematic_spike = relevant_records >= min(3, len(scored_records))
    community_records = sum(1 for item in scored_records if item["source"] == "volunteering")

    # Portfolio-level score: the strongest 1-2 activities dominate (depth over
    # breadth), with modest credit for leadership breadth and real outcomes
    # across the rest of the portfolio -- never a linear function of count.
    top_average = strongest["composite"] if second_strongest is None else (
        strongest["composite"] * 0.65 + second_strongest["composite"] * 0.35
    )
    breadth_bonus = min(10, leadership_breadth * 2 + real_outcomes * 2)
    score = max(1, min(100, round(top_average / 5 * 80 + breadth_bonus)))
    confidence = round(sum(item["confidence"] for item in scored_records) / len(scored_records), 2)

    components = [
        ScoreComponent(
            "strongest_activity",
            round(strongest["composite"] / 5 * 100),
            strongest["confidence"],
            [f"source:{strongest['source']}"],
        ),
        ScoreComponent(
            "portfolio_breadth",
            min(100, 40 + leadership_breadth * 10 + real_outcomes * 10),
            0.6,
            (["THEMATIC_SPIKE"] if thematic_spike else [])
            + (["COMMUNITY_CONTRIBUTION"] if community_records else []),
            f"{len(scored_records)} record(s), {leadership_breadth} with strong leadership, "
            f"{real_outcomes} with documented outcomes.",
        ),
    ]
    return DimensionResult(score=score, confidence=confidence, components=components)


# ---------------------------------------------------------------------------
# Application readiness (Phase 1)
# ---------------------------------------------------------------------------


def calculate_application_readiness(profile) -> DimensionResult:
    components: list[ScoreComponent] = []

    profile_fields = [
        profile.intended_major or profile.intended_majors,
        profile.target_countries,
        profile.test_scores,
        profile.original_gpa_value,
    ]
    filled = sum(1 for value in profile_fields if value)
    components.append(
        ScoreComponent("profile_completeness", round(filled / len(profile_fields) * 100), 0.9, [])
    )

    essay_count = EssayWorkspace.objects.filter(user=profile.user).count()
    if essay_count == 0:
        components.append(
            ScoreComponent("essay_readiness", None, 0.2, ["ESSAYS_MISSING"], "No essay workspace started yet.")
        )
    else:
        submitted_or_ready = EssayWorkspace.objects.filter(
            user=profile.user, status__in=["submitted", "ready", "reviewed"]
        ).count()
        components.append(
            ScoreComponent(
                "essay_readiness", round(40 + (submitted_or_ready / essay_count) * 60), 0.7, []
            )
        )

    recommenders = list(Recommender.objects.filter(user=profile.user))
    if not recommenders:
        components.append(
            ScoreComponent(
                "recommendation_letters",
                None,
                0.2,
                ["RECOMMENDATION_LETTERS_MISSING"],
                "No recommender on file yet.",
            )
        )
    else:
        confirmed = sum(
            1
            for recommender in recommenders
            if recommender.status in {Recommender.Status.CONFIRMED, Recommender.Status.SUBMITTED}
        )
        components.append(
            ScoreComponent(
                "recommendation_letters", round(40 + (confirmed / len(recommenders)) * 60), 0.7, []
            )
        )

    if profile.scholarship_need == profile.ScholarshipNeed.UNSURE or not profile.annual_budget_amount:
        components.append(
            ScoreComponent(
                "financial_planning", 45, 0.4, ["FINANCIAL_PLANNING_INCOMPLETE"], "Budget or aid need not confirmed."
            )
        )
    else:
        components.append(ScoreComponent("financial_planning", 75, 0.75, []))

    score, confidence = _weighted_average(components)
    return DimensionResult(score=score, confidence=confidence, components=components)


# ---------------------------------------------------------------------------
# Practical fit (Phase 1) -- how specified (not how "good") the student's
# practical constraints are, since these are preferences for filtering
# (Phase 4), not a strength to be judged.
# ---------------------------------------------------------------------------


def calculate_practical_fit(profile) -> DimensionResult:
    components: list[ScoreComponent] = []
    components.append(
        ScoreComponent(
            "major_specified",
            100 if (profile.intended_major or profile.intended_majors) else None,
            0.9 if (profile.intended_major or profile.intended_majors) else 0.2,
            [] if (profile.intended_major or profile.intended_majors) else ["MAJOR_NOT_SPECIFIED"],
        )
    )
    components.append(
        ScoreComponent(
            "country_specified",
            100 if profile.target_countries else None,
            0.9 if profile.target_countries else 0.2,
            [] if profile.target_countries else ["COUNTRY_NOT_SPECIFIED"],
        )
    )
    components.append(
        ScoreComponent(
            "budget_specified",
            100 if profile.annual_budget_amount else None,
            0.85 if profile.annual_budget_amount else 0.2,
            [] if profile.annual_budget_amount else ["BUDGET_NOT_SPECIFIED"],
        )
    )
    components.append(
        ScoreComponent(
            "financial_aid_need_specified",
            100 if profile.scholarship_need != profile.ScholarshipNeed.UNSURE else None,
            0.85 if profile.scholarship_need != profile.ScholarshipNeed.UNSURE else 0.3,
            [] if profile.scholarship_need != profile.ScholarshipNeed.UNSURE else ["FINANCIAL_NEED_UNSURE"],
        )
    )
    score, confidence = _weighted_average(components)
    return DimensionResult(score=score, confidence=confidence, components=components)


# ---------------------------------------------------------------------------
# Top-level entry point (Phase 1)
# ---------------------------------------------------------------------------


def calculate_profile_strength(profile) -> dict:
    """The full four-dimension profile-strength model. Never exposes a
    single overall "chance" figure -- `overall_confidence` describes how much
    of the model is backed by real evidence, not how likely the student is
    to be admitted anywhere.
    """

    academic = calculate_academic_strength(profile)
    extracurricular = calculate_extracurricular_strength(profile)
    readiness = calculate_application_readiness(profile)
    practical = calculate_practical_fit(profile)

    overall_confidence = round(
        (academic.confidence + extracurricular.confidence + readiness.confidence + practical.confidence) / 4,
        3,
    )

    return {
        "academic_strength": academic.as_dict(),
        "extracurricular_strength": extracurricular.as_dict(),
        "application_readiness": readiness.as_dict(),
        "practical_fit": practical.as_dict(),
        "overall_confidence": overall_confidence,
        "disclaimer": (
            "These are relative profile-strength readings based on available, "
            "verifiable evidence -- not an admissions prediction or guarantee."
        ),
    }
