"""PROTOCOL-008 PART 9: gap-based recommendations derived purely from an
already-computed `AIProfileAssessment`'s cached benchmark/deterministic/
readiness data. Never calls AI, never re-derives scores, never loops over
universities -- every recommendation here is university-independent by
construction, so there is nothing to deduplicate per-university.
"""

from __future__ import annotations

from .models import AIProfileAssessment

PRIORITY_URGENT = "urgent"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

_PRIORITY_ORDER = {PRIORITY_URGENT: 0, PRIORITY_HIGH: 1, PRIORITY_MEDIUM: 2, PRIORITY_LOW: 3}

# One recommendation per distinct evidence-gap cap reason -- a student sees
# "essays are missing" once, no matter how many sections it capped.
# `testing_below_benchmark` is intentionally absent here: the SAT/IELTS
# academic recommendations below already cover that dimension with a more
# specific, more actionable message.
_CAP_REASON_RECOMMENDATIONS = {
    "essays_missing": {
        "title": "essays_missing",
        "priority": PRIORITY_HIGH,
        "linked_dimension": "application_execution",
        "why_it_matters": "essays_missing",
        "expected_impact": "unlocks_capped_section_score",
        "next_action": "start_essays",
        "evidence_keys": ("essays",),
    },
    "recommendation_letters_missing": {
        "title": "recommendation_letters_missing",
        "priority": PRIORITY_HIGH,
        "linked_dimension": "application_execution",
        "why_it_matters": "recommendation_letters_missing",
        "expected_impact": "unlocks_capped_section_score",
        "next_action": "request_recommendation_letters",
        "evidence_keys": ("recommendation_letters",),
    },
    "activities_missing": {
        "title": "activities_missing",
        "priority": PRIORITY_URGENT,
        "linked_dimension": "activities_leadership",
        "why_it_matters": "activities_missing",
        "expected_impact": "unlocks_capped_section_score",
        "next_action": "add_activities",
        "evidence_keys": ("activities",),
    },
    "research_and_portfolio_missing": {
        "title": "research_and_portfolio_missing",
        "priority": PRIORITY_HIGH,
        "linked_dimension": "research_portfolio",
        "why_it_matters": "research_and_portfolio_missing",
        "expected_impact": "unlocks_capped_section_score",
        "next_action": "start_research_or_portfolio",
        "evidence_keys": ("research", "portfolio"),
    },
    "honors_missing_for_selective_target": {
        "title": "honors_missing_for_selective_target",
        "priority": PRIORITY_MEDIUM,
        "linked_dimension": "honors_competitions",
        "why_it_matters": "honors_missing_for_selective_target",
        "expected_impact": "unlocks_capped_section_score",
        "next_action": "pursue_honors_or_olympiads",
        "evidence_keys": ("honors", "olympiads"),
    },
}

# (deterministic field, gap status) -> recommendation template.
_ACADEMIC_RECOMMENDATIONS = {
    ("gpa", "below_benchmark"): {
        "title": "gpa_below_benchmark",
        "priority": PRIORITY_MEDIUM,
        "linked_dimension": "academic_readiness",
        "why_it_matters": "gpa_below_benchmark",
        "expected_impact": "closes_benchmark_gap",
        "next_action": "strengthen_academic_record",
    },
    ("sat", "below_benchmark"): {
        "title": "sat_below_benchmark",
        "priority": PRIORITY_MEDIUM,
        "linked_dimension": "testing_readiness",
        "why_it_matters": "sat_below_benchmark",
        "expected_impact": "closes_benchmark_gap",
        "next_action": "retake_sat",
    },
    ("sat", "within_range"): {
        "title": "sat_within_range",
        "priority": PRIORITY_LOW,
        "linked_dimension": "testing_readiness",
        "why_it_matters": "sat_within_range",
        "expected_impact": "moves_toward_competitive_range",
        "next_action": "consider_retake_sat",
    },
    ("ielts", "below_benchmark"): {
        "title": "ielts_below_benchmark",
        "priority": PRIORITY_MEDIUM,
        "linked_dimension": "testing_readiness",
        "why_it_matters": "ielts_below_benchmark",
        "expected_impact": "closes_benchmark_gap",
        "next_action": "retake_ielts",
    },
    ("ielts", "meets_minimum_not_competitive"): {
        "title": "ielts_not_competitive",
        "priority": PRIORITY_LOW,
        "linked_dimension": "testing_readiness",
        "why_it_matters": "ielts_not_competitive",
        "expected_impact": "moves_toward_competitive_range",
        "next_action": "consider_retake_ielts",
    },
}

# Plain fit_vector.SIGNAL_NAMES -> the readiness section each belongs to.
_SIGNAL_DIMENSIONS = {
    "profile_evidence": "academic_readiness",
    "activities": "activities_leadership",
    "honors_olympiads": "honors_competitions",
    "research_experience": "research_portfolio",
    "portfolio": "research_portfolio",
    "subject_passion": "academic_readiness",
    "curiosity": "academic_readiness",
    "originality": "research_portfolio",
    "leadership": "activities_leadership",
    "community_impact": "activities_leadership",
    "research_fit": "research_portfolio",
    "olympiads": "honors_competitions",
}

_SEVERITY_PRIORITY = {
    "significant_gap": PRIORITY_HIGH,
    "important_gap": PRIORITY_MEDIUM,
    "minor_gap": PRIORITY_LOW,
}


def _cap_reason_recommendations(readiness_scores: dict, deterministic_scores: dict) -> list[dict]:
    missing_evidence = deterministic_scores.get("missing_evidence", {})
    seen_reasons: set[str] = set()
    recommendations = []
    for section in readiness_scores.get("sections", []):
        for reason in section.get("cap_reasons", []):
            template = _CAP_REASON_RECOMMENDATIONS.get(reason)
            if reason in seen_reasons or template is None:
                continue
            seen_reasons.add(reason)
            evidence_keys = template["evidence_keys"]
            recommendations.append(
                {
                    "title": template["title"],
                    "priority": template["priority"],
                    "linked_dimension": template["linked_dimension"],
                    "why_it_matters": template["why_it_matters"],
                    "evidence_from_profile": {key: missing_evidence.get(key) for key in evidence_keys},
                    "expected_impact": template["expected_impact"],
                    "next_action": template["next_action"],
                }
            )
    return recommendations


def _academic_recommendations(deterministic_scores: dict) -> list[dict]:
    recommendations = []
    for field_name in ("gpa", "sat", "ielts"):
        entry = deterministic_scores.get(field_name, {})
        status = entry.get("status")
        template = _ACADEMIC_RECOMMENDATIONS.get((field_name, status))
        if template is None:
            continue
        recommendations.append(
            {
                "title": template["title"],
                "priority": template["priority"],
                "linked_dimension": template["linked_dimension"],
                "why_it_matters": template["why_it_matters"],
                "evidence_from_profile": {key: value for key, value in entry.items() if key != "status"},
                "expected_impact": template["expected_impact"],
                "next_action": template["next_action"],
            }
        )
    return recommendations


def _signal_gap_recommendations(deterministic_scores: dict, *, exclude_dimensions: set[str]) -> list[dict]:
    per_signal = deterministic_scores.get("score_gaps", {}).get("per_signal", {})
    recommendations = []
    covered_dimensions: set[str] = set()
    for signal, info in per_signal.items():
        severity = info.get("severity")
        dimension = _SIGNAL_DIMENSIONS.get(signal)
        if severity not in _SEVERITY_PRIORITY or dimension is None:
            continue
        if dimension in exclude_dimensions or dimension in covered_dimensions:
            continue
        covered_dimensions.add(dimension)
        recommendations.append(
            {
                "title": f"{signal}_gap",
                "priority": _SEVERITY_PRIORITY[severity],
                "linked_dimension": dimension,
                "why_it_matters": f"{signal}_gap",
                "evidence_from_profile": {"gap": info.get("gap"), "severity": severity},
                "expected_impact": "reduces_score_gap",
                "next_action": f"improve_{dimension}",
            }
        )
    return recommendations


def compute_profile_recommendations(assessment: AIProfileAssessment) -> list[dict]:
    """Priority-sorted, deduplicated recommendation list built only from data
    already cached on `assessment` -- no AI call, no per-university loop.
    """

    deterministic_scores = assessment.deterministic_scores or {}
    readiness_scores = assessment.readiness_scores or {}

    recommendations = _cap_reason_recommendations(readiness_scores, deterministic_scores)
    recommendations.extend(_academic_recommendations(deterministic_scores))
    covered_dimensions = {item["linked_dimension"] for item in recommendations}
    recommendations.extend(
        _signal_gap_recommendations(deterministic_scores, exclude_dimensions=covered_dimensions)
    )
    recommendations.sort(key=lambda item: _PRIORITY_ORDER[item["priority"]])
    return recommendations
