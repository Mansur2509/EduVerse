"""022 Phase 9: a single, prioritized, evidence-linked action list spanning
all ten categories the task spec names (Academics, Testing, Extracurriculars,
Research, Essays, Recommendations, Financial planning, University research,
Application timeline, Documents).

This module computes no new profile-strength or fit score. It reuses:
  - compute_profile_recommendations(assessment) for the academic/testing/
    extracurricular/research gap items (the PROTOCOL-008 evidence-gap
    engine -- see docs/RECOMMENDATION_ENGINE_AUDIT_022.md's note that this
    predates 022 and should be extended, not replaced).
  - ApplicationTrackerItem's own per-application status fields
    (essays_status/recommendations_status/documents_status/
    financial_aid_status) for the application-tracked categories.
  - university_list_strategy's schools/missing_preferences/
    missing_profile_signals/financial_risk_warning (022 Phases 4-8) for
    "University research"/"Financial planning" and for cross-referencing
    "affected_universities" against the student's actual candidate list.
  - the deadline-event buckets already built by build_profile_strategy, for
    "Application timeline".

Note on two profile-scoring surfaces: `compute_profile_recommendations`
reads from `AIProfileAssessment` (the older, cached, deterministic+AI
profile-assessment system from PROTOCOL-008) -- a distinct surface from
`profile_strength.py`'s newer, always-deterministic model built for the
Recommendation Engine in 022 Phase 1. Both are real, non-contradictory
systems serving different features (the standalone Profile Assessment page
vs. the Recommendation Engine's composite score); 022 Phase 0's audit
explicitly scoped this module to extend the former rather than migrate it,
to avoid an unrelated, high-risk rewrite of PROTOCOL-008's own pipeline.
"""

from __future__ import annotations

from django.utils import timezone

from services.application_service.timeline import urgency_for_days

from .recommendations import compute_profile_recommendations

CATEGORY_ACADEMICS = "academics"
CATEGORY_TESTING = "testing"
CATEGORY_EXTRACURRICULARS = "extracurriculars"
CATEGORY_RESEARCH = "research"
CATEGORY_ESSAYS = "essays"
CATEGORY_RECOMMENDATIONS = "recommendations"
CATEGORY_FINANCIAL_PLANNING = "financial_planning"
CATEGORY_UNIVERSITY_RESEARCH = "university_research"
CATEGORY_APPLICATION_TIMELINE = "application_timeline"
CATEGORY_DOCUMENTS = "documents"

_DIMENSION_TO_CATEGORY = {
    "academic_readiness": CATEGORY_ACADEMICS,
    "testing_readiness": CATEGORY_TESTING,
    "activities_leadership": CATEGORY_EXTRACURRICULARS,
    "honors_competitions": CATEGORY_EXTRACURRICULARS,
    "research_portfolio": CATEGORY_RESEARCH,
    "application_execution": CATEGORY_DOCUMENTS,
}

# Exact canonical Fit Engine risk codes (services.py's `risks` list) a given
# gap title corresponds to -- lets "affected_universities" cross-reference a
# *specific*, already-computed reason rather than a generic risk level.
_RISK_CODES_BY_TITLE = {
    "gpa_below_benchmark": {"gpa_below_average", "gpa_scale_not_confirmed"},
    "sat_below_benchmark": {"sat_below_p25", "sat_below_average", "sat_partial_fit"},
    "sat_within_range": {"sat_partial_fit"},
    "ielts_below_benchmark": {"ielts_below_minimum", "ielts_below_competitive"},
    "ielts_not_competitive": {"ielts_below_competitive"},
}
# Canonical Fit Engine missing-data codes (services.py's `missing_fields`)
# for gaps that are about absent evidence rather than a confirmed low score.
_MISSING_DATA_BY_TITLE = {
    "gpa_below_benchmark": {"profile_gpa"},
    "sat_below_benchmark": {"profile_sat"},
    "ielts_below_benchmark": {"profile_ielts"},
    "activities_missing": {"profile_activities"},
}

_URGENCY_BY_PRIORITY = {"urgent": "critical", "high": "urgent", "medium": "soon", "low": "far"}

_EFFORT_BY_TITLE = {
    "gpa_below_benchmark": "high",
    "sat_below_benchmark": "high",
    "sat_within_range": "medium",
    "ielts_below_benchmark": "high",
    "ielts_not_competitive": "medium",
    "essays_missing": "medium",
    "recommendation_letters_missing": "low",
    "activities_missing": "high",
    "research_and_portfolio_missing": "high",
    "honors_missing_for_selective_target": "high",
    "specify_budget_and_aid_need": "low",
    "financial_aid_forms_pending": "medium",
    "financial_risk_in_current_list": "medium",
    "clarify_search_preferences": "low",
    "broaden_search_criteria": "low",
}

_TRACKED_STATUS_FIELDS = {
    CATEGORY_ESSAYS: ("essays_status", "not_started", {"ready", "submitted"}),
    CATEGORY_RECOMMENDATIONS: ("recommendations_status", "not_started", {"received", "submitted"}),
    CATEGORY_DOCUMENTS: ("documents_status", "not_started", {"ready", "submitted"}),
}

_DEADLINE_BUCKET_ACTIONS = (
    ("overdue", "deadlines_overdue", "overdue"),
    ("next_7_days", "deadlines_next_7_days", "critical"),
    ("next_30_days", "deadlines_next_30_days", "soon"),
)


def _strategic_value(is_significant: bool, affected_count: int) -> str:
    if is_significant and affected_count >= 3:
        return "high"
    if is_significant or affected_count >= 1:
        return "medium"
    return "low"


def _university_ref(university: dict) -> dict:
    return {"id": university["id"], "name": university["name"], "slug": university["slug"]}


def _schools_for_gap(schools: list[dict], title: str, category: str) -> tuple[list[dict], str]:
    """Cross-reference one profile-gap action against the student's actual
    candidate list (022 Phase 9-10: "affected_universities" must count real
    portfolio items, never a guessed number). Returns (matched schools,
    confidence): "high" only for an exact, named risk/missing-data code; the
    coarser profile_risk fallback (extracurricular/research gaps have no
    single risk code of their own) is reported as "medium" so callers never
    overstate precision they don't have.
    """

    risk_codes = _RISK_CODES_BY_TITLE.get(title)
    missing_codes = _MISSING_DATA_BY_TITLE.get(title)
    if risk_codes or missing_codes:
        matched = [
            school
            for school in schools
            if (risk_codes and risk_codes & set(school.get("main_risks") or ()))
            or (missing_codes and missing_codes & set(school.get("missing_data") or ()))
        ]
        return matched, "high"
    if category in {CATEGORY_EXTRACURRICULARS, CATEGORY_RESEARCH}:
        matched = [school for school in schools if school.get("profile_risk") == "high"]
        return matched, "medium"
    return [], "low"


def _gap_action(item: dict, schools: list[dict]) -> dict:
    title = item["title"]
    category = _DIMENSION_TO_CATEGORY.get(item["linked_dimension"], CATEGORY_ACADEMICS)
    matched_schools, confidence = _schools_for_gap(schools, title, category)
    affected = [_university_ref(school["university"]) for school in matched_schools]
    return {
        "title": title,
        "category": category,
        "reason": item["why_it_matters"],
        "affected_universities": affected,
        "affected_university_count": len(affected),
        "urgency": _URGENCY_BY_PRIORITY.get(item["priority"], "soon"),
        "estimated_effort": _EFFORT_BY_TITLE.get(title, "medium"),
        "expected_strategic_value": _strategic_value(item["priority"] in {"urgent", "high"}, len(affected)),
        "evidence_source": {"source": "profile_assessment", "evidence": item.get("evidence_from_profile", {})},
        "deadline": None,
        "completion_state": "not_started",
        "dependency": None,
        "confidence": confidence,
        "next_action": item["next_action"],
    }


def _tracked_application_action(
    *, category: str, applications: list, title: str, reason: str, not_started_action: str, in_progress_action: str
) -> dict | None:
    if not applications:
        return None
    field_name, not_started_value, done_values = _TRACKED_STATUS_FIELDS[category]
    pending = [application for application in applications if getattr(application, field_name) not in done_values]
    if not pending:
        return None
    started = [
        application for application in pending if getattr(application, field_name) != not_started_value
    ]
    deadlines = [application.deadline for application in pending if application.deadline]
    nearest_deadline = min(deadlines) if deadlines else None
    days_remaining = (nearest_deadline - timezone.localdate()).days if nearest_deadline else None
    affected = [
        {"id": application.university_id, "name": application.university.name, "slug": application.university.slug}
        for application in pending
    ]
    return {
        "title": title,
        "category": category,
        "reason": reason,
        "affected_universities": affected,
        "affected_university_count": len(affected),
        "urgency": urgency_for_days(days_remaining),
        "estimated_effort": _EFFORT_BY_TITLE.get(title, "medium"),
        "expected_strategic_value": _strategic_value(True, len(affected)),
        "evidence_source": {"source": "application_tracker", "field": field_name},
        "deadline": nearest_deadline.isoformat() if nearest_deadline else None,
        "completion_state": "in_progress" if started else "not_started",
        "dependency": None,
        "confidence": "high",
        "next_action": in_progress_action if started else not_started_action,
    }


def _financial_planning_action(*, profile, applications: list, university_list_strategy: dict) -> dict | None:
    """Not driven by financial_aid_status alone: a student who has said they
    don't need aid (`ScholarshipNeed.NO`) has a legitimately-complete
    financial plan even if every application shows `financial_aid_status ==
    "not_applying"` -- that status is a real end state for them, not a gap.
    """

    missing_signals = set(university_list_strategy.get("missing_profile_signals") or ())
    if "BUDGET_NOT_SPECIFIED" in missing_signals or "FINANCIAL_NEED_UNSURE" in missing_signals:
        return {
            "title": "specify_budget_and_aid_need",
            "category": CATEGORY_FINANCIAL_PLANNING,
            "reason": "financial_preferences_incomplete",
            "affected_universities": [],
            "affected_university_count": 0,
            "urgency": "soon",
            "estimated_effort": _EFFORT_BY_TITLE["specify_budget_and_aid_need"],
            "expected_strategic_value": "medium",
            "evidence_source": {"source": "profile_strength", "signals": sorted(missing_signals)},
            "deadline": None,
            "completion_state": "not_started",
            "dependency": None,
            "confidence": "high",
            "next_action": "specify_budget_and_aid_need",
        }

    if profile.scholarship_need == profile.ScholarshipNeed.YES:
        pending = [
            application for application in applications if application.financial_aid_status != "submitted"
        ]
        if pending:
            deadlines = [
                application.financial_aid_deadline for application in pending if application.financial_aid_deadline
            ]
            nearest_deadline = min(deadlines) if deadlines else None
            days_remaining = (nearest_deadline - timezone.localdate()).days if nearest_deadline else None
            return {
                "title": "financial_aid_forms_pending",
                "category": CATEGORY_FINANCIAL_PLANNING,
                "reason": "financial_aid_forms_pending",
                "affected_universities": [
                    {
                        "id": application.university_id,
                        "name": application.university.name,
                        "slug": application.university.slug,
                    }
                    for application in pending
                ],
                "affected_university_count": len(pending),
                "urgency": urgency_for_days(days_remaining),
                "estimated_effort": _EFFORT_BY_TITLE["financial_aid_forms_pending"],
                "expected_strategic_value": _strategic_value(True, len(pending)),
                "evidence_source": {"source": "application_tracker", "field": "financial_aid_status"},
                "deadline": nearest_deadline.isoformat() if nearest_deadline else None,
                "completion_state": "not_started",
                "dependency": None,
                "confidence": "high",
                "next_action": "submit_financial_aid_forms",
            }

    financial_risk_warning = university_list_strategy.get("financial_risk_warning") or {}
    if financial_risk_warning.get("active"):
        affected = [
            _university_ref(school["university"])
            for school in university_list_strategy.get("schools", [])
            if school.get("cost_risk") == "high"
        ]
        return {
            "title": "financial_risk_in_current_list",
            "category": CATEGORY_FINANCIAL_PLANNING,
            "reason": "financial_risk_in_current_list",
            "affected_universities": affected,
            "affected_university_count": len(affected),
            "urgency": "soon",
            "estimated_effort": _EFFORT_BY_TITLE["financial_risk_in_current_list"],
            "expected_strategic_value": "high" if len(affected) >= 3 else "medium",
            "evidence_source": {"source": "recommendation_engine", "field": "financial_risk_warning"},
            "deadline": None,
            "completion_state": "not_started",
            "dependency": "specify_budget_and_aid_need" if not missing_signals else None,
            "confidence": "high",
            "next_action": "research_affordable_and_aid_options",
        }
    return None


def _university_research_actions(university_list_strategy: dict) -> list[dict]:
    actions: list[dict] = []
    missing_preferences = set(university_list_strategy.get("missing_preferences") or ())
    if missing_preferences:
        actions.append(
            {
                "title": "clarify_search_preferences",
                "category": CATEGORY_UNIVERSITY_RESEARCH,
                "reason": "search_preferences_incomplete",
                "affected_universities": [],
                "affected_university_count": 0,
                "urgency": "soon",
                "estimated_effort": _EFFORT_BY_TITLE["clarify_search_preferences"],
                "expected_strategic_value": "medium",
                "evidence_source": {"source": "recommendation_engine", "missing_preferences": sorted(missing_preferences)},
                "deadline": None,
                "completion_state": "not_started",
                "dependency": None,
                "confidence": "high",
                "next_action": "clarify_search_preferences",
            }
        )
    if university_list_strategy.get("data_scarcity"):
        actions.append(
            {
                "title": "broaden_search_criteria",
                "category": CATEGORY_UNIVERSITY_RESEARCH,
                "reason": "candidate_list_narrower_than_target",
                "affected_universities": [],
                "affected_university_count": 0,
                "urgency": "far",
                "estimated_effort": _EFFORT_BY_TITLE["broaden_search_criteria"],
                "expected_strategic_value": "low",
                "evidence_source": {"source": "recommendation_engine", "field": "data_scarcity"},
                "deadline": None,
                "completion_state": "not_started",
                "dependency": None,
                "confidence": "high",
                "next_action": "broaden_search_criteria",
            }
        )
    return actions


def _application_timeline_actions(buckets: dict[str, list[dict]], applications_by_id: dict[int, object]) -> list[dict]:
    actions: list[dict] = []
    for bucket_key, title, urgency in _DEADLINE_BUCKET_ACTIONS:
        bucket_events = buckets.get(bucket_key) or []
        if not bucket_events:
            continue
        affected_ids: dict[int, dict] = {}
        for event in bucket_events:
            application_id = event.get("application_id")
            application = applications_by_id.get(application_id)
            if application is None or application.university_id in affected_ids:
                continue
            affected_ids[application.university_id] = {
                "id": application.university_id,
                "name": application.university.name,
                "slug": application.university.slug,
            }
        dated_events = [event for event in bucket_events if event.get("date")]
        nearest_date = min(event["date"] for event in dated_events) if dated_events else None
        all_verified = bool(bucket_events) and all(
            event.get("confidence") == "verified" for event in bucket_events
        )
        actions.append(
            {
                "title": title,
                "category": CATEGORY_APPLICATION_TIMELINE,
                "reason": title,
                "affected_universities": list(affected_ids.values()),
                "affected_university_count": len(affected_ids),
                "urgency": urgency,
                "estimated_effort": "medium",
                "expected_strategic_value": _strategic_value(True, len(affected_ids)),
                "evidence_source": {"source": "application_timeline", "bucket": bucket_key},
                "deadline": nearest_date,
                "completion_state": "not_started",
                "dependency": None,
                "confidence": "high" if all_verified else "medium",
                "next_action": "review_upcoming_deadlines",
            }
        )
    return actions


def build_strategy_action_list(
    *,
    assessment,
    profile,
    applications: list,
    university_list_strategy: dict,
    buckets: dict[str, list[dict]],
) -> list[dict]:
    """The unified, prioritized action list (022 Phase 9). Every action has
    the same shape regardless of category: title, category, reason,
    affected_universities (+count), urgency, estimated_effort,
    expected_strategic_value, evidence_source, deadline, completion_state,
    dependency, confidence, next_action. Sorted by a priority derived from
    (urgency, expected_strategic_value, confidence) -- the raw weighting is
    an implementation detail, not part of the public contract.
    """

    schools = university_list_strategy.get("schools", [])
    actions: list[dict] = []

    if assessment is not None:
        actions.extend(_gap_action(item, schools) for item in compute_profile_recommendations(assessment))

    applications_by_id = {application.id: application for application in applications}

    essays_action = _tracked_application_action(
        category=CATEGORY_ESSAYS,
        applications=applications,
        title="essays_in_progress",
        reason="essays_in_progress",
        not_started_action="start_essays",
        in_progress_action="continue_essays",
    )
    if essays_action:
        actions.append(essays_action)

    recommendations_action = _tracked_application_action(
        category=CATEGORY_RECOMMENDATIONS,
        applications=applications,
        title="recommendation_letters_in_progress",
        reason="recommendation_letters_in_progress",
        not_started_action="request_recommendation_letters",
        in_progress_action="follow_up_recommendation_letters",
    )
    if recommendations_action:
        actions.append(recommendations_action)

    documents_action = _tracked_application_action(
        category=CATEGORY_DOCUMENTS,
        applications=applications,
        title="documents_in_progress",
        reason="documents_in_progress",
        not_started_action="collect_documents",
        in_progress_action="finish_collecting_documents",
    )
    if documents_action:
        actions.append(documents_action)

    financial_action = _financial_planning_action(
        profile=profile, applications=applications, university_list_strategy=university_list_strategy
    )
    if financial_action:
        actions.append(financial_action)

    actions.extend(_university_research_actions(university_list_strategy))
    actions.extend(_application_timeline_actions(buckets, applications_by_id))

    _URGENCY_RANK = {"overdue": 0, "critical": 1, "urgent": 2, "soon": 3, "upcoming": 4, "far": 5, "unknown": 6}
    _VALUE_RANK = {"high": 0, "medium": 1, "low": 2}
    _CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
    actions.sort(
        key=lambda action: (
            _URGENCY_RANK.get(action["urgency"], 6),
            _VALUE_RANK.get(action["expected_strategic_value"], 2),
            _CONFIDENCE_RANK.get(action["confidence"], 2),
        )
    )
    return actions
