"""Deterministic (non-AI) comparisons for the profile assessment / readiness
protocol (HOTFIX-007/PROTOCOL-008 PART 4). Every function here is pure code:
numeric comparisons, evidence-presence checks, and profile-completion math.
No network calls, no AI client imports. AI is reserved for semantic judgement
only (essay/portfolio/activity quality) and is computed elsewhere.
"""

from __future__ import annotations

from services.university_service.benchmark import BenchmarkResult
from services.university_service.fit_vector import (
    SIGNAL_NAMES,
    FitVectorComparison,
    compare_student_vector_to_university_weights,
)
from services.university_service.major_matching import CLUSTER_KEYWORDS, infer_major_clusters
from services.university_service.services import best_ielts_score, best_sat_score
from services.user_profile_service.academic_normalization import normalize_profile_academics
from services.user_profile_service.services import calculate_profile_completion

GAP_MEETS_OR_EXCEEDS = "meets_or_exceeds"
GAP_BELOW = "below_benchmark"
GAP_NO_BENCHMARK = "no_benchmark_data"
GAP_NO_STUDENT_DATA = "no_student_data"


def _gap_status(student_value: float | None, benchmark_value: float | None) -> str:
    if benchmark_value is None:
        return GAP_NO_BENCHMARK
    if student_value is None:
        return GAP_NO_STUDENT_DATA
    return GAP_MEETS_OR_EXCEEDS if student_value >= benchmark_value else GAP_BELOW


def _compare_gpa(profile, benchmark: BenchmarkResult) -> dict:
    normalization = normalize_profile_academics(profile)
    student = float(normalization.normalized_gpa_4) if normalization.normalized_gpa_4 is not None else None
    benchmark_gpa = benchmark.academic.get("gpa_average")
    return {
        "student": student,
        "benchmark": benchmark_gpa,
        "status": _gap_status(student, benchmark_gpa),
    }


def _compare_sat(profile, benchmark: BenchmarkResult) -> dict:
    student = best_sat_score(profile.test_scores)
    p25 = benchmark.academic.get("sat_p25")
    p75 = benchmark.academic.get("sat_p75")
    average = benchmark.academic.get("sat_average")
    reference = average if average is not None else p75
    status = _gap_status(student, reference)
    if status == GAP_BELOW and p25 is not None and student is not None and student >= p25:
        status = "within_range"
    return {
        "student": student,
        "benchmark_p25": p25,
        "benchmark_p75": p75,
        "benchmark_average": average,
        "status": status,
    }


def _compare_ielts(profile, benchmark: BenchmarkResult) -> dict:
    student = best_ielts_score(profile.test_scores)
    minimum = benchmark.academic.get("ielts_minimum")
    competitive = benchmark.academic.get("ielts_competitive")
    reference = competitive if competitive is not None else minimum
    status = _gap_status(student, reference)
    if status == GAP_BELOW and minimum is not None and student is not None and student >= minimum:
        status = "meets_minimum_not_competitive"
    return {
        "student": student,
        "benchmark_minimum": minimum,
        "benchmark_competitive": competitive,
        "status": status,
    }


def _toefl_status(profile) -> dict:
    scores = profile.test_scores if isinstance(profile.test_scores, dict) else {}
    value = scores.get("toefl")
    try:
        numeric = float(value) if value is not None else None
    except (TypeError, ValueError):
        numeric = None
    return {"student": numeric, "present": numeric is not None}


def _ap_status(profile) -> dict:
    count = profile.ap_courses_count or 0
    scores = profile.test_scores if isinstance(profile.test_scores, dict) else {}
    ap_entries = scores.get("ap")
    subjects = []
    if isinstance(ap_entries, list):
        subjects = [
            str(entry.get("subject", "")).strip().lower()
            for entry in ap_entries
            if isinstance(entry, dict) and str(entry.get("subject", "")).strip()
        ]
    inference = infer_major_clusters(profile)
    major_keywords = CLUSTER_KEYWORDS.get(inference.primary_major_cluster, ())
    subject_match = any(keyword in subject for subject in subjects for keyword in major_keywords)
    return {
        "count": count,
        "structured_subjects_available": bool(subjects),
        "subject_matches_major": subject_match if subjects else None,
    }


def _missing_evidence(profile) -> dict:
    user = profile.user
    return {
        "essays": user.profile_essays.count() == 0,
        "recommendation_letters": user.profile_recommenders.count() == 0,
        "honors": user.profile_honors.count() == 0,
        "research": user.profile_research_projects.count() == 0,
        "portfolio": user.profile_portfolio_projects.count() == 0,
        "activities": user.profile_activities.count() == 0,
        "olympiads": user.profile_olympiads.count() == 0,
        "volunteering": user.profile_volunteering.count() == 0,
    }


def _profile_completion(profile, preferences) -> int:
    return calculate_profile_completion(profile, preferences).percentage


# Dimensions with an obvious evidence-count proxy. The remaining four
# (profile_evidence, subject_passion, curiosity, originality, research_fit)
# are inherently semantic judgements -- there is no honest deterministic
# substitute, so the fallback scorer below gives them a fixed, conservative
# middle value rather than pretending to measure something it can't.
_COUNT_BASED_DIMENSIONS: dict[str, str] = {
    "activities": "profile_activities",
    "honors_olympiads": "profile_honors",
    "research_experience": "profile_research_projects",
    "portfolio": "profile_portfolio_projects",
    "leadership": "profile_activities",
    "community_impact": "profile_volunteering",
    "olympiads": "profile_olympiads",
}

_SEMANTIC_ONLY_DIMENSIONS = ("profile_evidence", "subject_passion", "curiosity", "originality", "research_fit")
_FALLBACK_SEMANTIC_SCORE = 5


def _count_to_score(count: int) -> int:
    if count <= 0:
        return 1
    if count == 1:
        return 4
    if count == 2:
        return 6
    if count <= 4:
        return 8
    return 10


def compute_deterministic_student_scores(profile) -> dict[str, int]:
    """Conservative, fully deterministic stand-in for the 12-dimension AI
    student vector, used only when the AI provider fails validation twice in
    a row (PART 3's `fallback_used` path). Count-based dimensions come from
    real evidence counts; the four inherently semantic dimensions get a
    fixed neutral score rather than an invented number.
    """

    user = profile.user
    scores: dict[str, int] = {}
    for dimension, related_name in _COUNT_BASED_DIMENSIONS.items():
        count = getattr(user, related_name).count()
        scores[dimension] = _count_to_score(count)
    for dimension in _SEMANTIC_ONLY_DIMENSIONS:
        scores[dimension] = _FALLBACK_SEMANTIC_SCORE
    return scores


def _score_gaps(student_scores: dict, benchmark: BenchmarkResult) -> FitVectorComparison:
    return compare_student_vector_to_university_weights(student_scores, benchmark.scores)


def compute_deterministic_comparisons(
    profile,
    preferences,
    *,
    benchmark: BenchmarkResult,
    student_scores: dict | None = None,
) -> dict:
    """Every field here comes from a pure numeric/count comparison -- never
    an AI call. `student_scores` is the cached 12-dimension AI (or fallback)
    vector; when absent, score-gap comparison reports no student data rather
    than guessing.
    """

    vector = student_scores or dict.fromkeys(SIGNAL_NAMES)
    score_gaps = _score_gaps(vector, benchmark)
    return {
        "gpa": _compare_gpa(profile, benchmark),
        "sat": _compare_sat(profile, benchmark),
        "ielts": _compare_ielts(profile, benchmark),
        "toefl": _toefl_status(profile),
        "ap": _ap_status(profile),
        "missing_evidence": _missing_evidence(profile),
        "profile_completion_percentage": _profile_completion(profile, preferences),
        "score_gaps": {
            "fit_band": score_gaps.fit_band,
            "signals_compared": score_gaps.signals_compared,
            "signals_missing_data": score_gaps.signals_missing_data,
            "counts_by_severity": score_gaps.counts_by_severity,
            "per_signal": {
                gap.signal: {"gap": gap.gap, "severity": gap.severity} for gap in score_gaps.per_signal
            },
        },
    }
