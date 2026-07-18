from __future__ import annotations

from datetime import date

from django.db.models import Count, Q

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

from .academic_normalization import (
    BENCHMARK_STATUS_ABOVE,
    BENCHMARK_STATUS_BELOW,
    BENCHMARK_STATUS_UNKNOWN,
    compare_academic_benchmark,
    normalize_university_gpa_benchmark,
)
from .budget import compare_cost_to_budget
from .currency import normalize_university_costs
from .deadline_normalization import normalize_university_deadline
from .fit_vector import (
    FIT_BAND_GOOD,
    FIT_BAND_HIGH_STRETCH,
    FIT_BAND_MODERATE,
    FIT_BAND_STRETCH,
    FIT_BAND_STRONG,
    build_student_signal_vector,
    build_university_signal_weights,
    compare_student_vector_to_university_weights,
)
from .models import University, UniversityProgram

CATEGORY_ORDER = ("reach", "competitive", "target", "safety")
FIT_DISCLAIMER = (
    "This is a fit estimate based on available profile and university data. "
    "It is not an admissions prediction or guarantee."
)

SAT_SIGNIFICANT_DIFF = 100

STATUS_ON_TRACK = "on_track"
STATUS_NEAR_TARGET = "near_target"
STATUS_MODERATE_GAP = "moderate_gap"
STATUS_SUBSTANTIAL_GAP = "substantial_gap"
STATUS_SIGNIFICANT_GAP = "significant_gap"
STATUS_NOT_ENOUGH_DATA = "not_enough_data"

SAT_GAP_PENALTIES = {
    STATUS_NEAR_TARGET: 6,
    STATUS_MODERATE_GAP: 12,
    STATUS_SUBSTANTIAL_GAP: 18,
    STATUS_SIGNIFICANT_GAP: 28,
}
IELTS_COMPETITIVE_GAP_PENALTIES = {
    STATUS_NEAR_TARGET: 4,
    STATUS_MODERATE_GAP: 8,
    STATUS_SUBSTANTIAL_GAP: 12,
    STATUS_SIGNIFICANT_GAP: 16,
}
IELTS_MINIMUM_GAP_PENALTIES = {
    STATUS_NEAR_TARGET: 16,
    STATUS_MODERATE_GAP: 22,
    STATUS_SUBSTANTIAL_GAP: 26,
    STATUS_SIGNIFICANT_GAP: 30,
}


def normalize_gpa_to_4(gpa, gpa_scale) -> float | None:
    """Legacy helper retained for callers; prefer normalize_profile_academics."""

    if gpa is None or gpa_scale is None:
        return None
    try:
        scale = float(gpa_scale)
    except (TypeError, ValueError):
        return None
    if scale <= 0:
        return None
    return float(gpa) / scale * 4.0


def _number(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def ielts_gap_severity(student_score, benchmark) -> str:
    student = _number(student_score)
    target = _number(benchmark)
    if student is None or target is None:
        return STATUS_NOT_ENOUGH_DATA
    gap = target - student
    if gap <= 0:
        return STATUS_ON_TRACK
    if gap <= 0.5:
        return STATUS_NEAR_TARGET
    if gap <= 1.0:
        return STATUS_MODERATE_GAP
    if gap < 1.5:
        return STATUS_SUBSTANTIAL_GAP
    return STATUS_SIGNIFICANT_GAP


def sat_gap_severity(student_score, benchmark) -> str:
    student = _number(student_score)
    target = _number(benchmark)
    if student is None or target is None:
        return STATUS_NOT_ENOUGH_DATA
    gap = target - student
    if gap <= 0:
        return STATUS_ON_TRACK
    if gap <= 50:
        return STATUS_NEAR_TARGET
    if gap <= 100:
        return STATUS_MODERATE_GAP
    if gap <= 150:
        return STATUS_SUBSTANTIAL_GAP
    return STATUS_SIGNIFICANT_GAP


def best_sat_score(test_scores) -> int | None:
    if not isinstance(test_scores, dict):
        return None
    value = test_scores.get("sat") or test_scores.get("SAT")
    number = _number(value)
    return int(number) if number is not None else None


def best_ielts_score(test_scores) -> float | None:
    if not isinstance(test_scores, dict):
        return None
    return _number(test_scores.get("ielts") or test_scores.get("IELTS"))


def _acceptance_rate_baseline_index(acceptance_rate: float) -> int:
    if acceptance_rate <= 15:
        return 0
    if acceptance_rate <= 35:
        return 1
    if acceptance_rate <= 60:
        return 2
    return 3


def _confidence_from_missing(missing_fields: list[str], normalization_confidence: str) -> str:
    if normalization_confidence == CONFIDENCE_LOW or len(missing_fields) >= 6:
        return CONFIDENCE_LOW
    if normalization_confidence == CONFIDENCE_HIGH and len(missing_fields) <= 2:
        return CONFIDENCE_HIGH
    return CONFIDENCE_MEDIUM


def _planned_exam_notes(profile, deadline: date | None) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    next_actions: list[str] = []
    plans = profile.exam_plans.get("planned", []) if isinstance(profile.exam_plans, dict) else []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        exam_name = str(plan.get("exam_type") or plan.get("name") or "").upper()
        if not any(token in exam_name for token in ("SAT", "AP")):
            continue
        target_score = str(plan.get("target_score") or "").strip()
        note = "Planned retake may improve fit only if the target score is achieved"
        if target_score:
            note = f"{note} ({target_score})"
        exam_date = str(plan.get("date") or "").strip()
        if exam_date and deadline:
            try:
                parsed_date = date.fromisoformat(exam_date)
            except ValueError:
                parsed_date = None
            if parsed_date and parsed_date > deadline:
                notes.append(
                    f"{note}; current planned date is after the application deadline."
                )
                next_actions.append("verify_exam_date_before_deadline")
                continue
        notes.append(f"{note}.")
        next_actions.append("plan_exam_retake")
    return notes, next_actions


def _score_program_fit(profile, university: University, strengths: list[str], missing: list[str]) -> int:
    majors = [
        str(value).strip().lower()
        for value in (profile.intended_majors or ([profile.intended_major] if profile.intended_major else []))
        if str(value).strip()
    ]
    if not majors:
        missing.append("profile_intended_major")
        return 45

    programs = [program.name.lower() for program in university.programs.all()]
    if not programs:
        missing.append("university_programs")
        return 55

    if any(major in program or program in major for major in majors for program in programs):
        strengths.append("major_matches_program")
        return 82
    return 58


def _structured_evidence_count(profile) -> int:
    """Total structured admissions-profile entries (activities, honors,
    olympiads, sports, research, portfolio, volunteering) for this profile's
    user. Callers such as the recommendation engine invoke the surrounding
    fit calculation once per candidate university with the *same* profile
    instance, so the count is cached on that instance to avoid re-querying it
    once per candidate.
    """

    cached = getattr(profile, "_structured_evidence_count_cache", None)
    if cached is not None:
        return cached
    user = profile.user
    count = (
        user.profile_activities.count()
        + user.profile_honors.count()
        + user.profile_olympiads.count()
        + user.profile_sports.count()
        + user.profile_research_projects.count()
        + user.profile_portfolio_projects.count()
        + user.profile_volunteering.count()
    )
    profile._structured_evidence_count_cache = count
    return count


OPTIONAL_EVIDENCE_WEIGHTS = {
    "activities": 0.10,
    "honors": 0.09,
    "olympiads": 0.10,
    "sports": 0.05,
    "research": 0.12,
    "essays": 0.11,
    "portfolio": 0.10,
    "volunteering": 0.07,
    "recommenders": 0.08,
}


def _has_prefetched_programs(university: University) -> bool:
    prefetched = getattr(university, "_prefetched_objects_cache", {})
    if "programs" in prefetched:
        return bool(prefetched["programs"])
    return university.programs.exists()


RESEARCH_KEYWORDS = {
    "research",
    "science",
    "engineering",
    "economics",
    "policy",
    "psychology",
    "biology",
    "chemistry",
    "physics",
    "math",
    "mathematics",
    "social science",
}
PORTFOLIO_KEYWORDS = {
    "computer science",
    "cs",
    "design",
    "architecture",
    "art",
    "media",
    "engineering",
    "entrepreneurship",
}
OLYMPIAD_KEYWORDS = {
    "math",
    "mathematics",
    "physics",
    "chemistry",
    "biology",
    "computer science",
    "engineering",
}
VOLUNTEERING_KEYWORDS = {
    "policy",
    "public",
    "social",
    "education",
    "health",
    "community",
    "development",
}


def _optional_evidence_counts(profile) -> dict[str, int]:
    cached = getattr(profile, "_optional_evidence_counts_cache", None)
    if cached is not None:
        return cached
    user = profile.user
    summary = (
        user.__class__.objects.filter(pk=user.pk)
        .annotate(
            activities_count=Count("profile_activities", distinct=True),
            honors_count=Count("profile_honors", distinct=True),
            olympiads_count=Count("profile_olympiads", distinct=True),
            sports_count=Count("profile_sports", distinct=True),
            research_count=Count("profile_research_projects", distinct=True),
            profile_essays_count=Count("profile_essays", distinct=True),
            active_essay_workspaces_count=Count(
                "essay_workspaces",
                filter=~Q(essay_workspaces__status="skipped"),
                distinct=True,
            ),
            portfolio_count=Count("profile_portfolio_projects", distinct=True),
            volunteering_count=Count("profile_volunteering", distinct=True),
            active_recommenders_count=Count(
                "profile_recommenders",
                filter=~Q(profile_recommenders__status="not_started"),
                distinct=True,
            ),
        )
        .values(
            "activities_count",
            "honors_count",
            "olympiads_count",
            "sports_count",
            "research_count",
            "profile_essays_count",
            "active_essay_workspaces_count",
            "portfolio_count",
            "volunteering_count",
            "active_recommenders_count",
        )
        .get()
    )
    counts = {
        "activities": summary["activities_count"],
        "honors": summary["honors_count"],
        "olympiads": summary["olympiads_count"],
        "sports": summary["sports_count"],
        "research": summary["research_count"],
        "essays": summary["profile_essays_count"] + summary["active_essay_workspaces_count"],
        "portfolio": summary["portfolio_count"],
        "volunteering": summary["volunteering_count"],
        "recommenders": summary["active_recommenders_count"],
    }
    profile._optional_evidence_counts_cache = counts
    return counts


def _program_context_text(profile, university: University, program: str | None = None) -> str:
    majors = profile.intended_majors or ([profile.intended_major] if profile.intended_major else [])
    parts = [str(value) for value in majors if value]
    if program:
        parts.append(program)
    parts.extend(program_obj.name for program_obj in university.programs.all())
    return " ".join(parts).lower()


def _keyword_relevance(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _evidence_relevance(category: str, context_text: str) -> tuple[float, str]:
    if category == "research" and _keyword_relevance(context_text, RESEARCH_KEYWORDS):
        return 1.25, "research_relevant_to_program_context"
    if category == "portfolio" and _keyword_relevance(context_text, PORTFOLIO_KEYWORDS):
        return 1.18, "portfolio_relevant_to_program_context"
    if category == "olympiads" and _keyword_relevance(context_text, OLYMPIAD_KEYWORDS):
        return 1.18, "olympiads_relevant_to_program_context"
    if category == "volunteering" and _keyword_relevance(context_text, VOLUNTEERING_KEYWORDS):
        return 1.12, "volunteering_relevant_to_program_context"
    return 1.0, "general_conservative_weight"


def calculate_optional_evidence_fit(
    profile, university: University, program: str | None = None
) -> dict:
    """Conservative fit contribution from optional profile evidence.

    This is deliberately a lower-weight readiness signal. It uses broad
    program/major context only when available and never invents a university's
    evidence policy.
    """

    counts = _optional_evidence_counts(profile)
    context_text = _program_context_text(profile, university, program)
    has_context = bool(context_text.strip())
    contributions: list[dict] = []
    weighted_total = 0.0
    max_weight = sum(OPTIONAL_EVIDENCE_WEIGHTS.values())
    missing: list[str] = []
    notes: list[str] = []

    for category, weight in OPTIONAL_EVIDENCE_WEIGHTS.items():
        count = counts.get(category, 0)
        if count <= 0:
            missing.append(category)
        base_score = 38 if count <= 0 else 56 if count == 1 else 70 if count == 2 else 82
        multiplier, note = _evidence_relevance(category, context_text)
        if note not in notes:
            notes.append(note)
        adjusted_score = _as_int_score(base_score * multiplier)
        weighted_total += adjusted_score * weight
        contributions.append(
            {
                "category": category,
                "count": count,
                "score": adjusted_score,
                "weight": weight,
                "relevance_note": note,
            }
        )

    evidence_subscore = _as_int_score(weighted_total / max_weight)
    if not has_context:
        confidence = CONFIDENCE_LOW
        notes.append("evidence_weighting_needs_verification")
    elif _has_prefetched_programs(university):
        confidence = CONFIDENCE_MEDIUM
        notes.append("no_verified_university_specific_evidence_policy")
    else:
        confidence = CONFIDENCE_LOW
        notes.append("evidence_weighting_needs_verification")

    # Present-evidence categories first, ranked by actual contribution — a
    # frontend "top 5" slice must reflect the strongest signals, not whatever
    # order OPTIONAL_EVIDENCE_WEIGHTS happens to be defined in.
    contributions.sort(key=lambda item: (item["count"] > 0, item["score"]), reverse=True)
    assessment_context = {
        "available": False,
        "source": "rule_based_profile_evidence",
        "confidence": confidence,
        "overall_profile_score": None,
        "profile_evidence_score": None,
        "assessed_at": None,
        "missing_data": [],
    }
    try:
        from services.profile_assessment_service.services import (
            get_current_assessment_for_profile,
        )

        assessment = get_current_assessment_for_profile(profile)
    except Exception:
        assessment = None

    if assessment is not None:
        ai_profile_score = _as_int_score(assessment.profile_evidence_score * 10)
        evidence_subscore = _as_int_score(evidence_subscore * 0.55 + ai_profile_score * 0.45)
        notes.append("cached_profile_assessment_used")
        if assessment.confidence == CONFIDENCE_LOW:
            confidence = CONFIDENCE_LOW
        elif assessment.confidence == CONFIDENCE_HIGH and confidence != CONFIDENCE_LOW:
            confidence = CONFIDENCE_HIGH
        assessment_context = {
            "available": True,
            "source": "cached_profile_assessment",
            "confidence": assessment.confidence,
            "overall_profile_score": assessment.overall_profile_score,
            "profile_evidence_score": assessment.profile_evidence_score,
            "assessed_at": assessment.created_at,
            "missing_data": assessment.missing_data[:5],
        }
    else:
        notes.append("profile_assessment_not_run")

    benchmark_comparison = _compare_to_university_benchmark(assessment, university)
    if benchmark_comparison["available"]:
        evidence_subscore = _as_int_score(
            evidence_subscore + _FIT_BAND_SCORE_ADJUSTMENT[benchmark_comparison["fit_band"]]
        )
        notes.append("university_benchmark_compared")
    elif benchmark_comparison["reason"] == "university_benchmark_not_published":
        notes.append("university_benchmark_not_available")
    elif benchmark_comparison["reason"] == "insufficient_comparable_signals":
        notes.append("university_benchmark_limited_data")

    return {
        "evidence_subscore": evidence_subscore,
        "category_contributions": contributions,
        "confidence": confidence,
        "missing_evidence": missing,
        "program_relevance_notes": list(dict.fromkeys(notes)),
        "assessment_context": assessment_context,
        "benchmark_comparison": benchmark_comparison,
        "weighting_note": (
            "Optional evidence uses conservative general weights unless verified "
            "university or program evidence-weight metadata exists."
        ),
    }


# Below this count of comparable signals (out of 12), a fit-band verdict is
# too thin on data to move the score -- reported as limited-data instead.
_MIN_COMPARABLE_SIGNALS = 6

_FIT_BAND_SCORE_ADJUSTMENT = {
    FIT_BAND_STRONG: 5,
    FIT_BAND_GOOD: 0,
    FIT_BAND_MODERATE: -5,
    FIT_BAND_STRETCH: -12,
    FIT_BAND_HIGH_STRETCH: -20,
}


def _compare_to_university_benchmark(assessment, university: University) -> dict:
    """Compare the student's cached profile-assessment vector against this
    university's published signal weights (`UniversitySignalWeights`).

    Never returns raw per-signal scores or weights -- those are system-only
    (see `UniversitySignalWeights` docstring) -- only a descriptive band and
    comparability counts safe to fold into the public fit response.
    """

    signal_weights = getattr(university, "signal_weights", None)
    if signal_weights is None:
        return {"available": False, "reason": "university_benchmark_not_published"}
    if assessment is None:
        return {"available": False, "reason": "profile_assessment_not_run"}

    student_vector = build_student_signal_vector(assessment)
    university_weights = build_university_signal_weights(signal_weights)
    comparison = compare_student_vector_to_university_weights(student_vector, university_weights)
    if comparison.signals_compared < _MIN_COMPARABLE_SIGNALS:
        return {"available": False, "reason": "insufficient_comparable_signals"}

    return {
        "available": True,
        "fit_band": comparison.fit_band,
        "signals_compared": comparison.signals_compared,
    }


def _score_profile_fit(profile, strengths: list[str], missing: list[str]) -> int:
    activities = profile.activities if isinstance(profile.activities, dict) else {}
    evidence_count = sum(len(value) for value in activities.values() if isinstance(value, list))
    # Structured admissions-profile entries are richer evidence than the
    # legacy free-text lists, so a profile that has moved to the structured
    # form is not scored as if it were empty. Weighted like ~2 legacy items
    # each; this only broadens what counts as evidence, it does not change
    # the thresholds below.
    evidence_count += _structured_evidence_count(profile) * 2
    if evidence_count >= 6:
        strengths.append("profile_depth")
        return 82
    if evidence_count >= 2:
        return 65
    missing.append("profile_activities")
    return 45


ESSAY_STATUS_READINESS = {
    "submitted": 95,
    "ready": 88,
    "reviewed": 80,
    "needs_revision": 68,
    "drafting": 58,
    "planned": 48,
    "suggested": 42,
    "not_started": 38,
    "skipped": 38,
}


def _score_essay_fit(profile, university: University, missing: list[str]) -> int:
    """Essay readiness: prefers real per-university essay-workspace evidence
    (draft status, prompt verification, word count, due date) and only falls
    back to the coarse self-reported essay_status when no workspace exists
    for this university yet.
    """

    from services.essay_service.models import EssayWorkspace

    workspace_cache = getattr(profile, "_essay_workspaces_by_university_cache", None)
    if workspace_cache is None:
        workspace_cache = {}
        for workspace in EssayWorkspace.objects.filter(user_id=profile.user_id, university_id__isnull=False):
            workspace_cache.setdefault(workspace.university_id, []).append(workspace)
        profile._essay_workspaces_by_university_cache = workspace_cache
    workspaces = workspace_cache.get(university.id, [])
    if not workspaces:
        if profile.essay_status == profile.EssayStatus.YES:
            return 78
        missing.append("profile_essays")
        return 45

    scores: list[int] = []
    for workspace in workspaces:
        readiness = ESSAY_STATUS_READINESS.get(workspace.status, 50)
        if workspace.prompt_verification_status == EssayWorkspace.VerificationStatus.VERIFIED:
            readiness += 4
        elif workspace.prompt_verification_status == EssayWorkspace.VerificationStatus.MISSING:
            readiness -= 4
        if workspace.word_limit and workspace.draft_text:
            word_count = len(workspace.draft_text.split())
            if word_count >= workspace.word_limit * 0.8:
                readiness += 3
        if workspace.due_date and workspace.status not in {
            EssayWorkspace.Status.SUBMITTED,
            EssayWorkspace.Status.SKIPPED,
        }:
            days_left = (workspace.due_date - date.today()).days
            if days_left < 0:
                readiness -= 10
        scores.append(max(1, min(100, readiness)))

    if not scores:
        missing.append("profile_essays")
        return 45
    return round(sum(scores) / len(scores))


def _score_deadline_fit(
    university: University, risks: list[str], missing: list[str], profile=None
) -> int:
    deadline = normalize_university_deadline(university, profile).normalized_date
    if deadline is None:
        missing.append("university_application_deadline")
        return 52
    days = (deadline - date.today()).days
    if days < 0:
        risks.append("deadline_passed")
        return 20
    if days <= 14:
        risks.append("deadline_close")
        return 38
    if days <= 60:
        return 62
    return 78


def _score_cost_fit(profile, university: University, risks: list[str], missing: list[str]) -> int:
    normalize_university_costs(university)
    if university.tuition_original_amount is not None and university.tuition_usd_amount is None:
        risks.append("cost_conversion_missing")
        missing.append("currency_conversion")
        return 45
    if university.tuition_usd_amount is None and university.total_cost_usd_amount is None:
        missing.append("university_cost")
        return 52
    if profile.scholarship_need == profile.ScholarshipNeed.YES and not (
        university.scholarship_available or university.financial_aid_url or university.scholarships.all()
    ):
        risks.append("aid_data_missing")
        return 50
    return 70


def _fit_score_category(score: int, current_category: str | None, university: University) -> str | None:
    if current_category is None:
        return None

    rate = float(university.acceptance_rate) if university.acceptance_rate is not None else None
    if rate is not None and rate < 5:
        return "reach" if score >= 78 else "dream"
    if rate is not None and rate < 10 and current_category == "safety":
        return "target"
    return current_category


def _source_notes(university: University) -> list[dict]:
    notes = [
        {
            "title": source.source_title,
            "url": source.source_url,
            "is_official": source.is_official,
        }
        for source in university.data_sources.all()
    ]
    if not notes:
        notes = [
            {
                "title": university.name,
                "url": university.official_website,
                "is_official": True,
            }
        ]
    return notes


def _as_int_score(value: float) -> int:
    return max(1, min(100, round(value)))


# PERFORMANCE-012 PART 5: personal/qualitative fit -- compares the cached
# AIProfileFitCache-style dimension scores (`AIProfileAssessment.
# qualitative_fit_scores`, see profile_assessment_service) against per-major
# weight profiles. Purely deterministic: this module never calls AI, it only
# reads whatever the cache already has and applies fixed weights/thresholds.
_QUALITATIVE_DEFAULT_WEIGHT = 0.08
_QUALITATIVE_HIGH_WEIGHT = 0.16
_QUALITATIVE_MEDIUM_HIGH_WEIGHT = 0.13
_QUALITATIVE_MEDIUM_WEIGHT = 0.10


def _build_qualitative_weight_profile(emphasis: dict[str, float]) -> dict[str, float]:
    from services.profile_assessment_service.services import QUALITATIVE_FIT_DIMENSIONS

    profile = dict.fromkeys(QUALITATIVE_FIT_DIMENSIONS, _QUALITATIVE_DEFAULT_WEIGHT)
    profile.update(emphasis)
    return profile


def _qualitative_weight_profiles() -> dict[str, dict[str, float]]:
    # Built lazily (not at import time) since it needs QUALITATIVE_FIT_DIMENSIONS
    # from profile_assessment_service, and that module imports from this one
    # (get_current_assessment_for_profile) -- a top-level cross-import would
    # be circular, matching the existing local-import pattern in this file.
    cluster = UniversityProgram.MajorCluster
    return {
        cluster.BUSINESS_ECONOMICS_FINANCE: _build_qualitative_weight_profile(
            {
                "quantitative_readiness": _QUALITATIVE_HIGH_WEIGHT,
                "leadership_initiative": _QUALITATIVE_HIGH_WEIGHT,
                "major_alignment": _QUALITATIVE_HIGH_WEIGHT,
                "writing_communication": _QUALITATIVE_MEDIUM_WEIGHT,
                "service_impact": _QUALITATIVE_MEDIUM_WEIGHT,
                "research_orientation": _QUALITATIVE_MEDIUM_WEIGHT,
            }
        ),
        cluster.COMPUTER_SCIENCE_AI_DATA: _build_qualitative_weight_profile(
            {
                "quantitative_readiness": _QUALITATIVE_HIGH_WEIGHT,
                "research_orientation": _QUALITATIVE_HIGH_WEIGHT,
                "major_alignment": _QUALITATIVE_HIGH_WEIGHT,
                "extracurricular_depth": _QUALITATIVE_MEDIUM_HIGH_WEIGHT,
            }
        ),
        cluster.ENGINEERING: _build_qualitative_weight_profile(
            {
                "quantitative_readiness": _QUALITATIVE_HIGH_WEIGHT,
                "research_orientation": _QUALITATIVE_MEDIUM_HIGH_WEIGHT,
                "major_alignment": _QUALITATIVE_HIGH_WEIGHT,
                "resilience_independence": _QUALITATIVE_MEDIUM_WEIGHT,
            }
        ),
        cluster.HUMANITIES: _build_qualitative_weight_profile(
            {
                "writing_communication": _QUALITATIVE_HIGH_WEIGHT,
                "intellectual_curiosity": _QUALITATIVE_HIGH_WEIGHT,
                "leadership_initiative": _QUALITATIVE_MEDIUM_HIGH_WEIGHT,
                "service_impact": _QUALITATIVE_MEDIUM_HIGH_WEIGHT,
            }
        ),
        cluster.LAW_POLITICS_IR: _build_qualitative_weight_profile(
            {
                "writing_communication": _QUALITATIVE_HIGH_WEIGHT,
                "intellectual_curiosity": _QUALITATIVE_HIGH_WEIGHT,
                "leadership_initiative": _QUALITATIVE_MEDIUM_HIGH_WEIGHT,
                "service_impact": _QUALITATIVE_MEDIUM_HIGH_WEIGHT,
            }
        ),
        cluster.PSYCHOLOGY_COGNITIVE_SCIENCE: _build_qualitative_weight_profile(
            {
                "research_orientation": _QUALITATIVE_HIGH_WEIGHT,
                "writing_communication": _QUALITATIVE_HIGH_WEIGHT,
                "intellectual_curiosity": _QUALITATIVE_HIGH_WEIGHT,
                "service_impact": _QUALITATIVE_MEDIUM_WEIGHT,
            }
        ),
        cluster.SOCIAL_SCIENCES: _build_qualitative_weight_profile(
            {
                "research_orientation": _QUALITATIVE_HIGH_WEIGHT,
                "writing_communication": _QUALITATIVE_HIGH_WEIGHT,
                "intellectual_curiosity": _QUALITATIVE_HIGH_WEIGHT,
                "service_impact": _QUALITATIVE_MEDIUM_WEIGHT,
            }
        ),
    }


_QUALITATIVE_GENERIC_WEIGHT_PROFILE_EMPHASIS: dict[str, float] = {}

# University-selectivity context shifts what a given qualitative score "counts
# for" -- the same cached dimension scores read as a stronger personal fit at
# a less selective school and a more demanding one at an ultra-selective
# school. Never changes the underlying 1-10 scores themselves, only how they
# translate into a 0-100 personal_fit_score.
SELECTIVITY_ULTRA_SELECTIVE = "ultra_selective"
SELECTIVITY_ELITE = "elite"
SELECTIVITY_STRONG = "strong"
SELECTIVITY_STANDARD = "standard"
SELECTIVITY_ACCESSIBLE = "accessible"
SELECTIVITY_UNKNOWN = "unknown"

_SELECTIVITY_ADJUSTMENT = {
    SELECTIVITY_ULTRA_SELECTIVE: -12,
    SELECTIVITY_ELITE: -6,
    SELECTIVITY_STRONG: 0,
    SELECTIVITY_STANDARD: 4,
    SELECTIVITY_ACCESSIBLE: 8,
    SELECTIVITY_UNKNOWN: 0,
}


def _selectivity_tier(university: University) -> str:
    if university.acceptance_rate is None:
        return SELECTIVITY_UNKNOWN
    rate = float(university.acceptance_rate)
    if rate < 5:
        return SELECTIVITY_ULTRA_SELECTIVE
    if rate < 15:
        return SELECTIVITY_ELITE
    if rate < 35:
        return SELECTIVITY_STRONG
    if rate < 60:
        return SELECTIVITY_STANDARD
    return SELECTIVITY_ACCESSIBLE


def _score_personal_fit(profile, university: University, assessment) -> tuple[int | None, dict]:
    """Weighted comparison of cached qualitative_fit_scores against this
    major's weight profile, adjusted for university selectivity. Returns
    (personal_fit_score or None, detail dict). Never calls AI -- `assessment`
    is whatever `qualitative_fit_status()` already read.
    """
    if assessment is None:
        return None, {}
    scores = assessment.qualitative_fit_scores
    if not scores:
        return None, {}

    from services.profile_assessment_service.services import QUALITATIVE_FIT_DIMENSIONS

    from .major_matching import infer_major_clusters

    inference = infer_major_clusters(profile)
    cluster = inference.primary_major_cluster
    weight_profiles = _qualitative_weight_profiles()
    weights = weight_profiles.get(cluster) or _build_qualitative_weight_profile(
        _QUALITATIVE_GENERIC_WEIGHT_PROFILE_EMPHASIS
    )

    weighted_sum = 0.0
    total_weight = 0.0
    dimensions_used = 0
    for dimension in QUALITATIVE_FIT_DIMENSIONS:
        entry = scores.get(dimension)
        weight = weights.get(dimension, _QUALITATIVE_DEFAULT_WEIGHT)
        if not isinstance(entry, dict) or not isinstance(entry.get("score"), int):
            continue
        weighted_sum += entry["score"] * weight
        total_weight += weight
        dimensions_used += 1

    if total_weight <= 0 or dimensions_used == 0:
        return None, {}

    weighted_average_10 = weighted_sum / total_weight
    tier = _selectivity_tier(university)
    personal_fit_score = _as_int_score(weighted_average_10 * 10 + _SELECTIVITY_ADJUSTMENT[tier])
    return personal_fit_score, {
        "major_cluster": cluster,
        "selectivity_tier": tier,
        "dimensions_used": dimensions_used,
    }


def _curriculum_note_slug(profile, curriculum_rigor) -> str:
    """Short, enum-like reason for the `academic_fit.curriculum_note` field
    (PERFORMANCE-012 PART 3) -- curriculum context adjusts confidence and
    interpretation, never a claim that one diploma outranks another, so this
    is always one of a fixed set of slugs the frontend translates, never a
    generated sentence.
    """
    if profile.curriculum_type == profile.CurriculumType.UNKNOWN:
        return "curriculum_type_unknown"
    if curriculum_rigor.missing_curriculum_data:
        return "curriculum_context_partial"
    return "curriculum_context_available"


def _assess_academics(
    profile,
    university: University,
    *,
    student_gpa,
    student_sat,
    student_ielts,
    academic_benchmark: dict,
    uni_sat_midpoint,
    strengths: list[str],
    risks: list[str],
    missing_fields: list[str],
    next_actions: list[str],
) -> tuple[float, int, bool, bool]:
    """Score one set of student scores against this university's published data.

    Returns (academic_score, index_shift, compared_any, severe_academic_gap).
    Callers pass throwaway lists when re-running with hypothetical scores so
    that bookkeeping from the hypothetical pass never leaks into the response.
    """
    index_shift = 0
    compared_any = False
    academic_score = 60
    severe_academic_gap = False

    # Compares normalized percentages (PERFORMANCE-012 PART 2), never a raw
    # student GPA (0-4.0) diffed against a university benchmark that might be
    # on a different scale -- that mismatch previously flagged clearly strong
    # students (e.g. 4.9/5.0) as "below average" against benchmarks like
    # 88/100. `academic_benchmark` is computed once in `calculate_university_fit`.
    if academic_benchmark["status"] != BENCHMARK_STATUS_UNKNOWN:
        compared_any = True
        if academic_benchmark["status"] == BENCHMARK_STATUS_ABOVE:
            index_shift += 1
            academic_score += 10
            strengths.append("gpa_above_average")
        elif academic_benchmark["status"] == BENCHMARK_STATUS_BELOW:
            index_shift -= 1
            academic_score -= 18
            risks.append("gpa_below_average")
    elif student_gpa is None:
        academic_score -= 14

    if student_sat is not None:
        if university.sat_p25 and university.sat_p75:
            compared_any = True
            sat_p50 = uni_sat_midpoint or round((university.sat_p25 + university.sat_p75) / 2)
            if student_sat < university.sat_p25:
                severity = sat_gap_severity(student_sat, university.sat_p25)
                index_shift -= 1
                academic_score -= SAT_GAP_PENALTIES.get(severity, 24)
                severe_academic_gap = severity in {
                    STATUS_SUBSTANTIAL_GAP,
                    STATUS_SIGNIFICANT_GAP,
                }
                risks.append("sat_below_p25")
            elif student_sat < sat_p50:
                severity = sat_gap_severity(student_sat, sat_p50)
                academic_score -= min(SAT_GAP_PENALTIES.get(severity, 10), 14)
                risks.append("sat_partial_fit")
            elif student_sat < university.sat_p75:
                academic_score += 7
                strengths.append("sat_competitive")
            else:
                index_shift += 1
                academic_score += 12
                strengths.append("sat_above_p75")
        elif uni_sat_midpoint is not None:
            compared_any = True
            sat_diff = student_sat - uni_sat_midpoint
            if sat_diff >= SAT_SIGNIFICANT_DIFF:
                index_shift += 1
                academic_score += 10
                strengths.append("sat_above_average")
            elif sat_diff < 0:
                severity = sat_gap_severity(student_sat, uni_sat_midpoint)
                if severity in {STATUS_MODERATE_GAP, STATUS_SUBSTANTIAL_GAP, STATUS_SIGNIFICANT_GAP}:
                    index_shift -= 1
                if severity in {STATUS_SUBSTANTIAL_GAP, STATUS_SIGNIFICANT_GAP}:
                    severe_academic_gap = True
                academic_score -= SAT_GAP_PENALTIES.get(severity, 12)
                risks.append("sat_below_average")
    elif uni_sat_midpoint is not None or university.sat_p25 or university.sat_p75:
        academic_score -= 10

    if university.ielts_minimum is not None or university.ielts_competitive is not None:
        if student_ielts is None:
            missing_fields.append("profile_ielts")
            next_actions.append("add_ielts_to_profile")
            academic_score -= 8
        else:
            minimum = float(university.ielts_minimum) if university.ielts_minimum else None
            competitive = (
                float(university.ielts_competitive) if university.ielts_competitive else minimum
            )
            if minimum is not None and student_ielts < minimum:
                severity = ielts_gap_severity(student_ielts, minimum)
                academic_score -= IELTS_MINIMUM_GAP_PENALTIES.get(severity, 28)
                severe_academic_gap = True
                risks.append("ielts_below_minimum")
            elif competitive is not None and student_ielts < competitive:
                severity = ielts_gap_severity(student_ielts, competitive)
                academic_score -= IELTS_COMPETITIVE_GAP_PENALTIES.get(severity, 12)
                risks.append("ielts_below_competitive")
            else:
                academic_score += 7
                strengths.append("ielts_meets_competitive")

    if profile.curriculum_type in {
        profile.CurriculumType.IB,
        profile.CurriculumType.A_LEVEL,
        profile.CurriculumType.AP,
        profile.CurriculumType.ACADEMIC_LYCEUM,
    }:
        strengths.append("curriculum_context_available")
        academic_score += 4
    elif profile.curriculum_type == profile.CurriculumType.UNKNOWN:
        academic_score -= 5

    return academic_score, index_shift, compared_any, severe_academic_gap


def _planned_target_scores(profile) -> dict[str, float]:
    """Parseable target scores from planned exams; used for conditional fit only."""
    targets: dict[str, float] = {}
    plans = profile.exam_plans.get("planned", []) if isinstance(profile.exam_plans, dict) else []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        exam_name = str(plan.get("exam_type") or plan.get("name") or "").upper()
        target = _number(str(plan.get("target_score") or "").replace("+", "").strip())
        if target is None:
            continue
        if "SAT" in exam_name and 400 <= target <= 1600:
            targets["sat"] = max(targets.get("sat", 0), target)
        elif "IELTS" in exam_name and 0 < target <= 9:
            targets["ielts"] = max(targets.get("ielts", 0), target)
    return targets


def calculate_university_fit(profile, university: University) -> dict:
    missing_fields: list[str] = []
    strengths: list[str] = []
    risks: list[str] = []
    next_actions: list[str] = []

    normalization = normalize_profile_academics(profile)
    student_gpa = normalization.normalized_gpa_4
    if student_gpa is None:
        missing_fields.append("profile_gpa")
        next_actions.append("add_gpa_to_profile")
        if normalization.original_gpa_value is not None:
            risks.append("gpa_scale_not_confirmed")

    student_sat = best_sat_score(profile.test_scores)
    if student_sat is None:
        missing_fields.append("profile_sat")
        next_actions.append("add_sat_to_profile")

    student_ielts = best_ielts_score(profile.test_scores)

    if profile.curriculum_type == profile.CurriculumType.UNKNOWN:
        missing_fields.append("profile_curriculum")
        next_actions.append("add_curriculum_context")

    curriculum_rigor = calculate_curriculum_rigor(profile)
    major_curriculum_fit = calculate_major_curriculum_fit(
        profile, profile.intended_major or (profile.intended_majors[0] if profile.intended_majors else None)
    )
    curriculum_score = curriculum_rigor.rigor_score

    # PERFORMANCE-012 PART 5: pure cache read, never calls AI. `qualitative_fit_status`
    # tells the caller whether the cached personal-fit scores (if any) are
    # fresh/stale/pending_daily_refresh/missing/failed; `_score_personal_fit`
    # uses whatever is cached (fresh or stale) so a student never loses their
    # existing personal-fit read just because a refresh is due.
    from services.profile_assessment_service.services import qualitative_fit_status

    if hasattr(profile, "_qualitative_fit_status_cache"):
        fit_status_value, qualitative_assessment = profile._qualitative_fit_status_cache
    else:
        fit_status_value, qualitative_assessment = qualitative_fit_status(profile.user)
        profile._qualitative_fit_status_cache = (fit_status_value, qualitative_assessment)
    personal_fit_score, personal_fit_detail = _score_personal_fit(
        profile, university, qualitative_assessment
    )

    university_gpa_benchmark = normalize_university_gpa_benchmark(university)
    academic_benchmark = compare_academic_benchmark(normalization, university_gpa_benchmark)
    if university.gpa_average is None:
        missing_fields.append("university_gpa_average")

    uni_sat_midpoint = university.sat_average
    if uni_sat_midpoint is None and university.sat_p25 and university.sat_p75:
        uni_sat_midpoint = round((university.sat_p25 + university.sat_p75) / 2)
    if uni_sat_midpoint is None:
        missing_fields.append("university_sat_average")

    uni_rate = (
        float(university.acceptance_rate) if university.acceptance_rate is not None else None
    )
    if uni_rate is None:
        missing_fields.append("university_acceptance_rate")

    baseline_index = _acceptance_rate_baseline_index(uni_rate) if uni_rate is not None else None

    academic_score, index_shift, compared_any, severe_academic_gap = _assess_academics(
        profile,
        university,
        student_gpa=student_gpa,
        student_sat=student_sat,
        student_ielts=student_ielts,
        academic_benchmark=academic_benchmark,
        uni_sat_midpoint=uni_sat_midpoint,
        strengths=strengths,
        risks=risks,
        missing_fields=missing_fields,
        next_actions=next_actions,
    )

    conditional_notes, planned_actions = _planned_exam_notes(
        profile,
        normalize_university_deadline(university, profile).normalized_date,
    )
    next_actions.extend(action for action in planned_actions if action not in next_actions)

    category: str | None
    if baseline_index is None and not compared_any:
        category = None
        next_actions.append("verify_university_data")
    else:
        index = baseline_index if baseline_index is not None else 2
        index = max(0, min(3, index + index_shift))
        category = CATEGORY_ORDER[index]
        if uni_rate is None and university.gpa_average is None and uni_sat_midpoint is None:
            next_actions.append("verify_university_data")
        elif uni_rate is None or university.gpa_average is None or uni_sat_midpoint is None:
            next_actions.append("limited_data_for_category")

    program_score = _score_program_fit(profile, university, strengths, missing_fields)
    profile_evidence = calculate_optional_evidence_fit(profile, university)
    profile_score = profile_evidence["evidence_subscore"]
    if profile_score >= 75:
        strengths.append("profile_depth")
    elif profile_score < 50:
        missing_fields.append("profile_activities")
    benchmark_comparison = profile_evidence["benchmark_comparison"]
    if benchmark_comparison["available"]:
        if benchmark_comparison["fit_band"] in (FIT_BAND_STRONG, FIT_BAND_GOOD):
            strengths.append("benchmark_alignment_strong")
        elif benchmark_comparison["fit_band"] in (FIT_BAND_STRETCH, FIT_BAND_HIGH_STRETCH):
            risks.append("benchmark_alignment_stretch")
    essay_score = _score_essay_fit(profile, university, missing_fields)
    deadline_score = _score_deadline_fit(university, risks, missing_fields, profile)
    cost_score = _score_cost_fit(profile, university, risks, missing_fields)

    academic_subscore = _as_int_score(academic_score)
    completeness_score = 70 if len(missing_fields) <= 3 else 45
    if personal_fit_score is not None:
        # personal_fit_score gets its own 0.10 slice; profile_score's slice
        # shrinks slightly to make room without changing any other weight.
        raw_score = (
            academic_subscore * 0.30
            + program_score * 0.12
            + profile_score * 0.13
            + personal_fit_score * 0.10
            + essay_score * 0.10
            + deadline_score * 0.10
            + cost_score * 0.10
            + completeness_score * 0.05
        )
    else:
        # No usable cached personal-fit scores yet (PART 5 rule: still return
        # a full deterministic fit) -- personal_fit's weight folds back into
        # profile_score rather than leaving a gap or silently lowering the score.
        raw_score = (
            academic_subscore * 0.30
            + program_score * 0.12
            + profile_score * 0.23
            + essay_score * 0.10
            + deadline_score * 0.10
            + cost_score * 0.10
            + completeness_score * 0.05
        )
    fit_score = _as_int_score(raw_score)
    if severe_academic_gap:
        fit_score = min(fit_score, 55)
    if normalization.confidence == CONFIDENCE_LOW:
        fit_score = min(fit_score, 72)

    # Conditional fit: same estimate re-run with planned retake target scores.
    # Only exposed when it would actually improve on the current estimate, so
    # a planned retake never silently lowers or replaces the current fit.
    conditional_fit_score = None
    conditional_targets: dict[str, float] = {}
    planned_targets = _planned_target_scores(profile)
    conditional_sat = student_sat
    conditional_ielts = student_ielts
    if "sat" in planned_targets and (
        student_sat is None or planned_targets["sat"] > student_sat
    ):
        conditional_sat = int(planned_targets["sat"])
        conditional_targets["sat"] = conditional_sat
    if "ielts" in planned_targets and (
        student_ielts is None or planned_targets["ielts"] > student_ielts
    ):
        conditional_ielts = planned_targets["ielts"]
        conditional_targets["ielts"] = planned_targets["ielts"]
    if conditional_targets:
        scratch_a: list[str] = []
        scratch_b: list[str] = []
        scratch_c: list[str] = []
        scratch_d: list[str] = []
        conditional_academic_raw, _shift, _compared, conditional_severe = _assess_academics(
            profile,
            university,
            student_gpa=student_gpa,
            student_sat=conditional_sat,
            student_ielts=conditional_ielts,
            academic_benchmark=academic_benchmark,
            uni_sat_midpoint=uni_sat_midpoint,
            strengths=scratch_a,
            risks=scratch_b,
            missing_fields=scratch_c,
            next_actions=scratch_d,
        )
        if personal_fit_score is not None:
            conditional_raw_score = (
                _as_int_score(conditional_academic_raw) * 0.30
                + program_score * 0.12
                + profile_score * 0.13
                + personal_fit_score * 0.10
                + essay_score * 0.10
                + deadline_score * 0.10
                + cost_score * 0.10
                + completeness_score * 0.05
            )
        else:
            conditional_raw_score = (
                _as_int_score(conditional_academic_raw) * 0.30
                + program_score * 0.12
                + profile_score * 0.23
                + essay_score * 0.10
                + deadline_score * 0.10
                + cost_score * 0.10
                + completeness_score * 0.05
            )
        conditional_candidate = _as_int_score(conditional_raw_score)
        if conditional_severe:
            conditional_candidate = min(conditional_candidate, 55)
        if normalization.confidence == CONFIDENCE_LOW:
            conditional_candidate = min(conditional_candidate, 72)
        if conditional_candidate > fit_score:
            conditional_fit_score = conditional_candidate
        else:
            conditional_targets = {}

    category = _fit_score_category(fit_score, category, university)
    confidence = _confidence_from_missing(missing_fields, normalization.confidence)

    missing_fields = list(dict.fromkeys(missing_fields))
    strengths = list(dict.fromkeys(strengths))
    risks = list(dict.fromkeys(risks))
    next_actions = list(dict.fromkeys(next_actions))

    return {
        "fit_score": fit_score,
        "category": category,
        "confidence": confidence,
        "academic_subscore": academic_subscore,
        "program_subscore": program_score,
        "profile_subscore": profile_score,
        "essay_subscore": essay_score,
        "deadline_subscore": deadline_score,
        "cost_subscore": cost_score,
        # A confirmed (not missing-data) severe SAT/IELTS shortfall -- already
        # used above to cap fit_score, now also surfaced so the recommendation
        # layer (022 Phase 7, Case B) can stop a strong extracurricular or
        # financial-fit score from "erasing" a real academic-minimum gap.
        "severe_academic_gap": severe_academic_gap,
        "profile_evidence": profile_evidence,
        # Additive, spec-friendly aliases for the same subscores above, plus a
        # data_confidence readout — never a second, differently-weighted score.
        "subscores": {
            "academic_fit": academic_subscore,
            "program_fit": program_score,
            "profile_depth_fit": profile_score,
            "profile_evidence": profile_score,
            "essay_readiness": essay_score,
            "timeline_readiness": deadline_score,
            "cost_context": cost_score,
            "data_confidence": _confidence_from_missing(missing_fields, normalization.confidence),
        },
        # PERFORMANCE-012 PART 5: named subscore breakdown separating
        # quantitative academic/test fit, program/profile alignment, and
        # personal/qualitative fit (cached-AI-scores-vs-major-weights, never
        # an AI call from this GET) into their own labeled fields.
        "fit_breakdown": {
            "academic_score": academic_subscore,
            "testing_score": academic_subscore,
            "curriculum_score": curriculum_score,
            "program_alignment_score": program_score,
            "extracurricular_profile_score": profile_score,
            "personal_fit_score": personal_fit_score,
            "timeline_score": deadline_score,
            "cost_score": cost_score,
        },
        "personal_fit_score": personal_fit_score,
        "personal_fit_context": personal_fit_detail or None,
        # fresh/stale/missing/pending_daily_refresh/failed -- a pure cache
        # read (see qualitative_fit_status), never triggers AI from this GET.
        "qualitative_fit_status": fit_status_value,
        "curriculum_score": curriculum_score,
        "strengths": strengths,
        "risks": risks,
        "main_strength": strengths[0] if strengths else None,
        "main_risk": risks[0] if risks else None,
        "missing_fields": missing_fields,
        "missing_data": missing_fields,
        "next_actions": next_actions,
        "conditional_notes": conditional_notes,
        "conditional_fit_score": conditional_fit_score,
        "conditional_targets": conditional_targets or None,
        # Percentage-normalized GPA comparison (PERFORMANCE-012 PART 2/3) --
        # never a raw scale-mismatched diff. `status` is meets/above/
        # slightly_below/below_benchmark or unknown; a low confidence or
        # unknown status means "not enough data", not "behind".
        "academic_fit": {
            **academic_benchmark,
            "curriculum_type": profile.curriculum_type,
            "curriculum_note": _curriculum_note_slug(profile, curriculum_rigor),
        },
        "student_academic_context": {
            "original_gpa_value": normalization.original_gpa_value,
            "original_gpa_scale": normalization.original_gpa_scale,
            "original_gpa_scale_type": normalization.original_gpa_scale_type,
            "normalized_gpa_4": normalization.normalized_gpa_4,
            "normalized_percentage": normalization.normalized_percentage,
            "confidence": normalization.confidence,
            "note": normalization.note,
            "curriculum_type": profile.curriculum_type,
            "curriculum_country": profile.curriculum_country,
            "curriculum_rigor": vars(curriculum_rigor),
            "major_curriculum_fit": major_curriculum_fit,
        },
        "cost_context": {
            "tuition_original_amount": university.tuition_original_amount
            if university.tuition_original_amount is not None
            else university.tuition_amount,
            "tuition_original_currency": university.tuition_original_currency
            or university.tuition_currency,
            "tuition_usd_amount": university.tuition_usd_amount,
            "total_cost_original_amount": university.total_cost_original_amount,
            "total_cost_original_currency": university.total_cost_original_currency,
            "total_cost_usd_amount": university.total_cost_usd_amount,
            "conversion_rate": university.currency_conversion_rate,
            "conversion_date": university.currency_conversion_date,
            "conversion_source": university.currency_conversion_source,
            "conversion_confidence": university.currency_conversion_confidence,
            "cost_notes": university.cost_notes,
            "budget_comparison": compare_cost_to_budget(university, profile),
        },
        "source_notes": _source_notes(university),
        "disclaimer": FIT_DISCLAIMER,
    }
