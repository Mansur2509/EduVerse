"""PROTOCOL-008 PART 10: a student-level 7/30/90-day + before-deadline action
plan. Never calls AI, never invents a date -- every dated item here comes
from `application_service.timeline.build_application_timeline` (itself
sourced from tracker deadlines, official exam dates, and verified university
fields), aggregated across every one of the student's tracked applications.
When no verified date exists, the item is still surfaced with
confidence="missing" so the caller can render "Deadline not verified yet"
instead of a guess.
"""

from __future__ import annotations

from datetime import date

from services.application_service.models import ApplicationTrackerItem
from services.application_service.timeline import (
    CONFIDENCE_MISSING,
    build_application_timeline,
)
from services.university_service.strategy import build_application_strategy
from services.user_profile_service.models import Recommender

# Mirrors application_service.timeline._deadline_events's private kind->type
# mapping so an undated deadline (see the loop in `build_profile_strategy`
# below) reads the same "type" as its dated counterpart would have.
_DEADLINE_KIND_TO_EVENT_TYPE = {
    "application": "submission_deadline",
    "financial_aid": "financial_aid",
    "scholarship": "scholarship",
}

_BUCKET_NEXT_7_DAYS = "next_7_days"
_BUCKET_NEXT_30_DAYS = "next_30_days"
_BUCKET_NEXT_90_DAYS = "next_90_days"
_BUCKET_BEFORE_DEADLINE = "before_deadline"
_BUCKET_OVERDUE = "overdue"
_BUCKET_UNSCHEDULED = "unscheduled"

_BUCKET_KEYS = (
    _BUCKET_OVERDUE,
    _BUCKET_NEXT_7_DAYS,
    _BUCKET_NEXT_30_DAYS,
    _BUCKET_NEXT_90_DAYS,
    _BUCKET_BEFORE_DEADLINE,
    _BUCKET_UNSCHEDULED,
)


def _bucket_for_days(days_remaining: int | None) -> str:
    if days_remaining is None:
        return _BUCKET_UNSCHEDULED
    if days_remaining < 0:
        return _BUCKET_OVERDUE
    if days_remaining <= 7:
        return _BUCKET_NEXT_7_DAYS
    if days_remaining <= 30:
        return _BUCKET_NEXT_30_DAYS
    if days_remaining <= 90:
        return _BUCKET_NEXT_90_DAYS
    return _BUCKET_BEFORE_DEADLINE


def _bucket_events(events: list[dict]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {key: [] for key in _BUCKET_KEYS}
    for event in events:
        buckets[_bucket_for_days(event.get("days_remaining"))].append(event)
    return buckets


def _essay_plan(timelines: list[dict], events: list[dict], missing_evidence: dict) -> dict:
    essay_events = [event for event in events if event.get("type") in {"essay_start", "essay_draft_due"}]
    linked_essays: list[dict] = []
    seen_ids: set[int] = set()
    for timeline in timelines:
        for essay in timeline["linked_essays"]:
            if essay["id"] in seen_ids:
                continue
            seen_ids.add(essay["id"])
            linked_essays.append(essay)
    return {
        "essays_missing": bool(missing_evidence.get("essays")),
        "planned_dates": essay_events,
        "workspaces": linked_essays,
        "next_action": "start_essays" if missing_evidence.get("essays") else "continue_essays",
    }


def _recommendation_letter_plan(user, events: list[dict], missing_evidence: dict) -> dict:
    request_events = [event for event in events if event.get("type") == "recommendation_request"]
    recommenders = [
        {
            "id": recommender.id,
            "relationship_role": recommender.relationship_role,
            "status": recommender.status,
            "requested_date": recommender.requested_date.isoformat()
            if recommender.requested_date
            else None,
            "submitted_date": recommender.submitted_date.isoformat()
            if recommender.submitted_date
            else None,
        }
        for recommender in Recommender.objects.filter(user=user).order_by("-created_at")[:12]
    ]
    return {
        "recommendation_letters_missing": bool(missing_evidence.get("recommendation_letters")),
        "planned_dates": request_events,
        "recommenders": recommenders,
        "next_action": (
            "request_recommendation_letters"
            if missing_evidence.get("recommendation_letters")
            else "follow_up_recommendation_letters"
        ),
    }


def _testing_plan(timelines: list[dict], deterministic_scores: dict) -> dict:
    """One entry per exam type, deduplicated across applications -- a
    student sits the SAT once, even if five universities ask for it.
    """

    by_exam: dict[str, dict] = {}
    for timeline in timelines:
        for entry in timeline["linked_exams"]:
            by_exam.setdefault(entry["exam"], entry)
    return {
        "exams": list(by_exam.values()),
        "gpa": deterministic_scores.get("gpa", {}),
        "sat": deterministic_scores.get("sat", {}),
        "ielts": deterministic_scores.get("ielts", {}),
        "toefl": deterministic_scores.get("toefl", {}),
        "ap": deterministic_scores.get("ap", {}),
    }


def _activities_research_plan(missing_evidence: dict) -> dict:
    gaps = {
        key: bool(missing_evidence.get(key))
        for key in ("activities", "research", "portfolio", "honors", "olympiads", "volunteering")
    }
    next_actions = [f"add_{key}" for key, missing in gaps.items() if missing]
    return {"missing_evidence": gaps, "next_actions": next_actions}


def build_profile_strategy(user, profile, preferences, assessment) -> dict:
    """The full PART 10 action plan: time-bucketed events across every
    tracked application, plus testing/essay/recommendation-letter/
    activities-research plans and the existing university-list strategy.
    `assessment` may be `None` when the student has no cached assessment
    yet -- every gap-derived section degrades to empty/False rather than
    guessing.
    """

    today = date.today()
    applications = list(
        ApplicationTrackerItem.objects.filter(user=user).select_related("university")
    )
    timelines = [build_application_timeline(application, profile, today=today) for application in applications]

    events: list[dict] = []
    for application, timeline in zip(applications, timelines, strict=True):
        for event in timeline["events"]:
            event = dict(event)
            event["university"] = application.university.name
            event["application_id"] = application.id
            events.append(event)
        # `timeline["events"]` drops undated deadlines entirely (it's built
        # for chronological display). A deadline the student hasn't set and
        # the university hasn't published still needs to reach the student
        # as "not verified yet" rather than silently vanishing, so pull it
        # back in from `timeline["deadlines"]` here.
        for deadline in timeline["deadlines"]:
            if deadline["date"] is not None:
                continue
            events.append(
                {
                    "type": _DEADLINE_KIND_TO_EVENT_TYPE.get(deadline["kind"], deadline["kind"]),
                    "date": None,
                    "days_remaining": None,
                    "urgency": deadline["urgency"],
                    "confidence": deadline["confidence"],
                    "source_url": deadline["source_url"],
                    "university": application.university.name,
                    "application_id": application.id,
                }
            )
    events.sort(key=lambda event: (event.get("date") is None, event.get("date") or ""))

    buckets = _bucket_events(events)

    deterministic_scores = assessment.deterministic_scores if assessment else {}
    missing_evidence = deterministic_scores.get("missing_evidence", {}) if assessment else {}

    has_any_verified_deadline = any(
        event.get("type") == "submission_deadline" and event.get("confidence") != CONFIDENCE_MISSING
        for event in events
    )

    return {
        "generated_at": today.isoformat(),
        "has_tracked_applications": bool(applications),
        "has_verified_deadlines": has_any_verified_deadline,
        **buckets,
        "testing_plan": _testing_plan(timelines, deterministic_scores),
        "essay_plan": _essay_plan(timelines, events, missing_evidence),
        "recommendation_letter_plan": _recommendation_letter_plan(user, events, missing_evidence),
        "activities_research_plan": _activities_research_plan(missing_evidence),
        "university_list_strategy": build_application_strategy(profile, preferences),
    }
