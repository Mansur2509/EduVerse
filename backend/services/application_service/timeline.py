"""Derived, read-only application timeline and deadline intelligence.

Nothing here is persisted. Every event is assembled from data that already
exists (the tracker item, the linked university's verified/imported fields,
the user's essays/exam plans, official College Board exam dates, linked
roadmap tasks, and user milestones). Suggested planning dates are always
derived from a *real* reference deadline and are clearly labelled
``estimated`` — UniWay never invents an official university or exam date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from services.exam_content_service.models import OfficialExamDate
from services.exam_content_service.official_links import official_exam_link
from services.university_service.deadline_normalization import (
    normalize_university_deadline,
)
from services.university_service.services import (
    best_sat_score,
    ielts_gap_severity,
    sat_gap_severity,
)

# Date confidence levels, from strongest to weakest.
CONFIDENCE_VERIFIED = "verified"
CONFIDENCE_PARTIAL = "partial"
CONFIDENCE_USER_PROVIDED = "user_provided"
CONFIDENCE_ESTIMATED = "estimated"
CONFIDENCE_MISSING = "missing"

# Urgency buckets derived purely from days remaining.
URGENCY_OVERDUE = "overdue"
URGENCY_CRITICAL = "critical"
URGENCY_URGENT = "urgent"
URGENCY_SOON = "soon"
URGENCY_UPCOMING = "upcoming"
URGENCY_FAR = "far"
URGENCY_UNKNOWN = "unknown"

# Approximate lag between sitting a standardized test and scores being usable.
SCORE_RELEASE_LAG_DAYS = 21


def urgency_for_days(days_remaining: int | None) -> str:
    """Map days-until-deadline to an urgency bucket. No probability language."""
    if days_remaining is None:
        return URGENCY_UNKNOWN
    if days_remaining < 0:
        return URGENCY_OVERDUE
    if days_remaining <= 7:
        return URGENCY_CRITICAL
    if days_remaining <= 14:
        return URGENCY_URGENT
    if days_remaining <= 30:
        return URGENCY_SOON
    if days_remaining <= 90:
        return URGENCY_UPCOMING
    return URGENCY_FAR


def days_between(target: date | None, today: date) -> int | None:
    if target is None:
        return None
    return (target - today).days


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _university_deadline_confidence(university) -> str:
    """Confidence for an imported university.application_deadline value."""
    verification = next(
        (
            record
            for record in university.field_verifications.all()
            if record.field_name == "application_deadline"
        ),
        None,
    )
    if verification and verification.status == "verified":
        return CONFIDENCE_VERIFIED
    # An imported/source-aware deadline with no verified record is "partial",
    # never presented as officially confirmed.
    return CONFIDENCE_PARTIAL


def _source_url_for_field(university, field_name: str) -> str:
    verification = next(
        (
            record
            for record in university.field_verifications.all()
            if record.field_name == field_name
        ),
        None,
    )
    if verification:
        return verification.source_url
    return university.admissions_url or university.official_website or ""


@dataclass(frozen=True)
class _Deadline:
    kind: str
    date: date | None
    confidence: str
    source_url: str
    source_label: str
    last_verified_date: date | None = None
    source_date: date | None = None
    normalized_year: int | None = None
    cycle_label: str | None = None
    cycle_explanation: str | None = None


def _reference_deadline(application, profile) -> tuple[date | None, str]:
    """The date suggested planning checkpoints are measured back from.

    Prefers the user's tracker deadline (their chosen round), then the
    university's imported deadline normalized to the student's own
    graduation cycle. Returns (date, confidence).
    """
    if application.deadline:
        return application.deadline, CONFIDENCE_USER_PROVIDED
    university = application.university
    normalized = normalize_university_deadline(university, profile)
    if normalized.normalized_date:
        return normalized.normalized_date, _university_deadline_confidence(university)
    return None, CONFIDENCE_MISSING


def _collect_deadlines(application, today: date, profile) -> list[_Deadline]:
    university = application.university
    deadlines: list[_Deadline] = []

    # Primary application/submission deadline.
    if application.deadline:
        deadlines.append(
            _Deadline(
                kind="application",
                date=application.deadline,
                confidence=CONFIDENCE_USER_PROVIDED,
                source_url=university.admissions_url or university.official_website or "",
                source_label="tracker",
            )
        )
    elif university.application_deadline:
        normalized = normalize_university_deadline(university, profile)
        deadlines.append(
            _Deadline(
                kind="application",
                date=normalized.normalized_date,
                confidence=_university_deadline_confidence(university),
                source_url=_source_url_for_field(university, "application_deadline"),
                source_label="university",
                source_date=normalized.source_date,
                normalized_year=normalized.normalized_year,
                cycle_label=normalized.cycle_label,
                cycle_explanation=normalized.explanation,
            )
        )
    else:
        deadlines.append(
            _Deadline(
                kind="application",
                date=None,
                confidence=CONFIDENCE_MISSING,
                source_url=university.admissions_url or university.official_website or "",
                source_label="university",
            )
        )

    # Financial aid deadline (user-entered on the tracker only).
    if application.financial_aid_deadline:
        deadlines.append(
            _Deadline(
                kind="financial_aid",
                date=application.financial_aid_deadline,
                confidence=CONFIDENCE_USER_PROVIDED,
                source_url=university.financial_aid_url or university.official_website or "",
                source_label="tracker",
            )
        )

    # Scholarship deadline: tracker value plus any official scholarship dates.
    if application.scholarship_deadline:
        deadlines.append(
            _Deadline(
                kind="scholarship",
                date=application.scholarship_deadline,
                confidence=CONFIDENCE_USER_PROVIDED,
                source_url=university.financial_aid_url or university.official_website or "",
                source_label="tracker",
            )
        )
    for scholarship in university.scholarships.all():
        if scholarship.deadline:
            deadlines.append(
                _Deadline(
                    kind="scholarship",
                    date=scholarship.deadline,
                    confidence=CONFIDENCE_PARTIAL,
                    source_url=scholarship.official_url,
                    source_label=scholarship.name,
                )
            )

    return deadlines


def _deadline_payload(deadline: _Deadline, today: date) -> dict:
    days = days_between(deadline.date, today)
    return {
        "kind": deadline.kind,
        "date": _iso(deadline.date),
        "confidence": deadline.confidence,
        "days_remaining": days,
        "urgency": urgency_for_days(days),
        "source_url": deadline.source_url,
        "source_label": deadline.source_label,
        "last_verified_date": _iso(deadline.last_verified_date),
        "source_date": _iso(deadline.source_date),
        "normalized_year": deadline.normalized_year,
        "cycle_label": deadline.cycle_label,
        "cycle_explanation": deadline.cycle_explanation,
    }


# Suggested planning checkpoints. Each is derived from the reference deadline by
# subtracting ``offset`` days, and only shown when days-until-deadline falls in
# the applicable ``window`` (this is what makes a far-away deadline stay calm and
# a close one escalate). ``requires`` gates on the tracker sub-status.
@dataclass(frozen=True)
class _SuggestedRule:
    event_type: str
    offset: int
    window: tuple[int, int]
    reason_key: str


_SUGGESTED_RULES: tuple[_SuggestedRule, ...] = (
    _SuggestedRule("exam_registration", 120, (90, 400), "exam_planning"),
    _SuggestedRule("essay_start", 75, (45, 300), "essay_brainstorm"),
    _SuggestedRule("essay_draft_due", 45, (30, 300), "essay_draft"),
    _SuggestedRule("recommendation_request", 30, (21, 200), "recommendation"),
    _SuggestedRule("financial_aid", 21, (14, 200), "financial_aid"),
    _SuggestedRule("final_review", 7, (0, 60), "final_review"),
)


def _essays_done(application) -> bool:
    return application.essays_status in {"ready", "submitted"}


def _recs_done(application) -> bool:
    return application.recommendations_status in {"received", "submitted"}


def _aid_active(application) -> bool:
    return application.financial_aid_status in {"researching", "preparing"}


def _suggested_dates(application, today: date, profile) -> list[dict]:
    reference, ref_confidence = _reference_deadline(application, profile)
    if reference is None:
        return []
    days_until = (reference - today).days
    if days_until < 0:
        return []

    suggestions: list[dict] = []
    for rule in _SUGGESTED_RULES:
        low, high = rule.window
        if not (low <= days_until <= high):
            continue
        if rule.event_type in {"essay_start", "essay_draft_due"} and _essays_done(application):
            continue
        if rule.event_type == "recommendation_request" and _recs_done(application):
            continue
        if rule.event_type == "financial_aid" and not _aid_active(application):
            continue
        suggested_date = reference - timedelta(days=rule.offset)
        if suggested_date < today:
            continue
        suggestions.append(
            {
                "type": rule.event_type,
                "date": _iso(suggested_date),
                "days_remaining": (suggested_date - today).days,
                "urgency": urgency_for_days((suggested_date - today).days),
                "reason_key": rule.reason_key,
                "weeks_before": round(rule.offset / 7),
                "reference_deadline": _iso(reference),
                "reference_confidence": ref_confidence,
                "confidence": CONFIDENCE_ESTIMATED,
            }
        )
    return suggestions


def _linked_essays(application, today: date) -> list[dict]:
    # Import here to avoid a module-level cycle through essay_service.
    from services.essay_service.models import EssayWorkspace

    essays = EssayWorkspace.objects.filter(
        user=application.user, university=application.university
    ).order_by("status", "-updated_at")
    payload: list[dict] = []
    for essay in essays:
        word_count = len([w for w in essay.draft_text.split() if w.strip()])
        payload.append(
            {
                "id": essay.id,
                "title": essay.title,
                "essay_type": essay.essay_type,
                "status": essay.status,
                "word_limit": essay.word_limit,
                "word_count": word_count,
                "updated_at": essay.updated_at.isoformat(),
                "source_url": essay.source_url,
            }
        )
    return payload


def _planned_exam_types(exam_plans) -> set[str]:
    planned: set[str] = set()
    if not isinstance(exam_plans, dict):
        return planned

    def _scan(item):
        if not isinstance(item, dict):
            return
        raw = str(item.get("exam_type") or item.get("name") or "").upper()
        if not raw:
            return
        if item.get("planned_retake") or item.get("date") or item.get("planned_date"):
            planned.add(raw)

    for key in ("planned", "retakes", "exams"):
        value = exam_plans.get(key)
        if isinstance(value, list):
            for entry in value:
                _scan(entry)
    _scan(exam_plans)
    for key, value in exam_plans.items():
        if isinstance(value, dict) and str(key).upper() in {"SAT", "AP", "IELTS", "TOEFL", "ACT"}:
            merged = {"exam_type": key}
            merged.update(value)
            _scan(merged)
    return planned


def _profile_score(profile, key: str):
    scores = profile.test_scores
    if not isinstance(scores, dict):
        return None
    for score_key, value in scores.items():
        if str(score_key).lower() == key:
            return value
    return None


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _official_exam_entry(exam_type: str, today: date) -> OfficialExamDate | None:
    return (
        OfficialExamDate.objects.filter(
            exam_type=exam_type,
            event_kind=OfficialExamDate.EventKind.EXAM,
            test_date__gte=today,
        )
        .order_by("test_date")
        .first()
    )


def _exam_after_deadline(official: OfficialExamDate | None, reference: date | None) -> bool | None:
    if official is None or reference is None:
        return None
    usable_from = official.test_date + timedelta(days=SCORE_RELEASE_LAG_DAYS)
    return usable_from <= reference


def _linked_exams(application, profile, today: date) -> list[dict]:
    university = application.university
    reference, _ = _reference_deadline(application, profile)
    planned = _planned_exam_types(profile.exam_plans)
    entries: list[dict] = []

    # SAT — university publishes ranges; profile may hold a score.
    sat_threshold = university.sat_p75 or university.sat_average or university.sat_p25
    sat_threshold_label = (
        "p75"
        if university.sat_p75
        else "average"
        if university.sat_average
        else "p25"
        if university.sat_p25
        else None
    )
    student_sat = best_sat_score(profile.test_scores)
    if sat_threshold or student_sat or "SAT" in planned:
        official = _official_exam_entry(OfficialExamDate.ExamType.SAT, today)
        severity = (
            sat_gap_severity(student_sat, sat_threshold)
            if (student_sat is not None and sat_threshold)
            else None
        )
        entries.append(
            {
                "exam": "SAT",
                "current_score": student_sat,
                "threshold": sat_threshold,
                "threshold_label": sat_threshold_label,
                "severity": severity,
                "planned_retake": "SAT" in planned,
                "official_test_date": _iso(official.test_date if official else None),
                "official_test_date_confidence": official.verification_status if official else None,
                "registration_deadline": _iso(official.registration_deadline if official else None),
                "late_registration_deadline": _iso(
                    official.late_registration_deadline if official else None
                ),
                "late_test_date": _iso(official.late_test_date if official else None),
                "late_test_time": official.late_test_time if official else "",
                "source_url": official.source_url if official else "",
                "scores_arrive_before_deadline": _exam_after_deadline(official, reference),
            }
        )

    # IELTS — threshold from university; no verified official-date dataset,
    # so fall back to the university's own source and then the official
    # IELTS site rather than leaving the student with no link at all.
    ielts_threshold = university.ielts_competitive or university.ielts_minimum
    ielts_threshold_label = "competitive" if university.ielts_competitive else (
        "minimum" if university.ielts_minimum else None
    )
    student_ielts = _to_float(_profile_score(profile, "ielts"))
    if ielts_threshold or student_ielts is not None or "IELTS" in planned:
        severity = (
            ielts_gap_severity(student_ielts, ielts_threshold)
            if (student_ielts is not None and ielts_threshold)
            else None
        )
        ielts_link = official_exam_link("IELTS")
        entries.append(
            {
                "exam": "IELTS",
                "current_score": student_ielts,
                "threshold": float(ielts_threshold) if ielts_threshold else None,
                "threshold_label": ielts_threshold_label,
                "severity": severity,
                "planned_retake": "IELTS" in planned,
                "official_test_date": None,
                "official_test_date_confidence": None,
                "registration_deadline": None,
                "source_url": _source_url_for_field(university, "ielts_minimum")
                or (ielts_link["source_url"] if ielts_link else ""),
                "scores_arrive_before_deadline": None,
            }
        )

    # TOEFL — planning only when a score exists or is planned. No verified
    # official-date dataset; link to the official ETS TOEFL site instead of
    # inventing a date.
    student_toefl = _to_float(_profile_score(profile, "toefl"))
    if student_toefl is not None or "TOEFL" in planned:
        toefl_link = official_exam_link("TOEFL")
        entries.append(
            {
                "exam": "TOEFL",
                "current_score": student_toefl,
                "threshold": None,
                "threshold_label": None,
                "severity": None,
                "planned_retake": "TOEFL" in planned,
                "official_test_date": None,
                "official_test_date_confidence": None,
                "registration_deadline": None,
                "source_url": toefl_link["source_url"] if toefl_link else "",
                "scores_arrive_before_deadline": None,
            }
        )

    # AP — official College Board dates when the student is planning AP.
    if "AP" in planned:
        official_ap = _official_exam_entry(OfficialExamDate.ExamType.AP, today)
        entries.append(
            {
                "exam": "AP",
                "current_score": None,
                "threshold": None,
                "threshold_label": None,
                "severity": None,
                "planned_retake": True,
                "official_test_date": _iso(official_ap.test_date if official_ap else None),
                "official_test_time": official_ap.test_time if official_ap else "",
                "official_test_date_confidence": (
                    official_ap.verification_status if official_ap else None
                ),
                "registration_deadline": _iso(
                    official_ap.registration_deadline if official_ap else None
                ),
                "late_registration_deadline": _iso(
                    official_ap.late_registration_deadline if official_ap else None
                ),
                "late_test_date": _iso(official_ap.late_test_date if official_ap else None),
                "late_test_time": official_ap.late_test_time if official_ap else "",
                "source_url": official_ap.source_url if official_ap else "",
                "scores_arrive_before_deadline": _exam_after_deadline(official_ap, reference),
            }
        )

    return entries


def _linked_roadmap_events(application, today: date) -> list[dict]:
    tasks = application.roadmap_tasks.all()
    events: list[dict] = []
    for task in tasks:
        days = days_between(task.due_date, today)
        events.append(
            {
                "type": "roadmap_task",
                "title": task.title,
                "date": _iso(task.due_date),
                "days_remaining": days,
                "urgency": urgency_for_days(days),
                "confidence": CONFIDENCE_USER_PROVIDED
                if task.source_type == task.SourceType.MANUAL
                else CONFIDENCE_ESTIMATED,
                "status": task.status,
                "is_timeline_marker": task.is_timeline_marker,
                "source_url": task.source_url,
                "linked_roadmap_task": task.id,
            }
        )
    return events


def _milestone_events(application, today: date) -> list[dict]:
    events: list[dict] = []
    for milestone in application.milestones.all():
        days = days_between(milestone.due_date, today)
        events.append(
            {
                "type": "custom_milestone",
                "title": milestone.title,
                "category": milestone.category,
                "date": _iso(milestone.due_date),
                "days_remaining": days,
                "urgency": urgency_for_days(days),
                "confidence": CONFIDENCE_USER_PROVIDED,
                "status": milestone.status,
                "source_url": milestone.source_url,
                "milestone_id": milestone.id,
            }
        )
    return events


def _deadline_events(deadlines: list[_Deadline], today: date) -> list[dict]:
    type_by_kind = {
        "application": "submission_deadline",
        "financial_aid": "financial_aid",
        "scholarship": "scholarship",
    }
    events: list[dict] = []
    for deadline in deadlines:
        if deadline.date is None:
            continue
        days = days_between(deadline.date, today)
        events.append(
            {
                "type": type_by_kind.get(deadline.kind, "custom_milestone"),
                "title": deadline.source_label,
                "date": _iso(deadline.date),
                "days_remaining": days,
                "urgency": urgency_for_days(days),
                "confidence": deadline.confidence,
                "source_url": deadline.source_url,
            }
        )
    return events


def _suggested_events(suggested: list[dict]) -> list[dict]:
    events: list[dict] = []
    for item in suggested:
        events.append(
            {
                "type": item["type"],
                "title": None,
                "reason_key": item["reason_key"],
                "weeks_before": item["weeks_before"],
                "date": item["date"],
                "days_remaining": item["days_remaining"],
                "urgency": item["urgency"],
                "confidence": item["confidence"],
                "reference_deadline": item["reference_deadline"],
            }
        )
    return events


def build_application_timeline(application, profile, *, today: date) -> dict:
    """Assemble the full derived timeline payload for one application."""
    deadlines = _collect_deadlines(application, today, profile)
    suggested = _suggested_dates(application, today, profile)

    events: list[dict] = []
    events.extend(_deadline_events(deadlines, today))
    events.extend(_suggested_events(suggested))
    events.extend(_milestone_events(application, today))
    events.extend(_linked_roadmap_events(application, today))

    # Sort dated events chronologically; undated go last but stay visible.
    events.sort(key=lambda event: (event.get("date") is None, event.get("date") or ""))

    return {
        "deadlines": [_deadline_payload(deadline, today) for deadline in deadlines],
        "events": events,
        "suggested_dates": suggested,
        "linked_essays": _linked_essays(application, today),
        "linked_exams": _linked_exams(application, profile, today),
    }
