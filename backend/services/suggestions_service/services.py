from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from services.application_service.models import ApplicationTrackerItem
from services.essay_service.models import EssayWorkspace
from services.roadmap_service.models import RoadmapPlan, RoadmapTask
from services.university_service.models import SavedUniversity
from services.university_service.services import best_sat_score
from services.user_profile_service.models import (
    Activity,
    Honor,
    Olympiad,
    PortfolioProject,
    ResearchProject,
)
from services.user_profile_service.services import ensure_profile_records

from .models import SuggestedItem

SuggestionType = SuggestedItem.SuggestionType
Priority = SuggestedItem.Priority
SourceType = SuggestedItem.SourceType
Status = SuggestedItem.Status

DEADLINE_WINDOWS = (60, 30, 14, 7, 0)
SAT_SIGNIFICANT_GAP = 100

EXAM_NAMES = {
    "sat": "SAT",
    "ielts": "IELTS",
    "toefl": "TOEFL",
    "act": "ACT",
    "ap": "AP",
    "duolingo": "Duolingo",
}


@dataclass(frozen=True)
class TargetUniversity:
    university: Any
    application: ApplicationTrackerItem | None = None


def _is_demo_user(user) -> bool:
    return bool(getattr(user, "email", "").endswith("@eduverse.local"))


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _today() -> date:
    return timezone.now().date()


def _source_url_for_university(university, field_name: str) -> str:
    verification = next(
        (record for record in university.field_verifications.all() if record.field_name == field_name),
        None,
    )
    if verification:
        return verification.source_url
    return university.admissions_url or university.official_website


def _deadline_priority(due_date: date | None, today: date, *, blocking: bool = False) -> str:
    if due_date is None:
        return Priority.HIGH if blocking else Priority.MEDIUM
    days = (due_date - today).days
    if days <= 7:
        return Priority.URGENT
    if days <= 30:
        return Priority.HIGH
    if days <= 90:
        return Priority.MEDIUM if not blocking else Priority.HIGH
    return Priority.LOW


def _exam_priority(earliest_deadline: date | None, today: date) -> str:
    if earliest_deadline is None:
        return Priority.MEDIUM
    days = (earliest_deadline - today).days
    if days <= 45:
        return Priority.URGENT
    if days <= 90:
        return Priority.HIGH
    return Priority.MEDIUM


def _normal_exam_name(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    for key, label in EXAM_NAMES.items():
        if key in lowered:
            return label
    return raw.upper() if len(raw) <= 8 else raw


def _parse_month_window(value: Any, year_hint: int | None = None) -> tuple[date, date] | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if len(text) == 7 and text[4] == "-":
            year = int(text[:4])
            month = int(text[5:])
            return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    except (ValueError, TypeError):
        return None

    lowered = text.lower()
    for month in range(1, 13):
        month_name = calendar.month_name[month].lower()
        month_abbr = calendar.month_abbr[month].lower()
        if lowered.startswith(month_name) or lowered.startswith(month_abbr):
            year = year_hint or _today().year
            for part in lowered.replace(",", " ").split():
                if part.isdigit() and len(part) == 4:
                    year = int(part)
                    break
            return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    return None


def _target_universities(user) -> list[TargetUniversity]:
    saved_qs = (
        SavedUniversity.objects.filter(user=user)
        .select_related("university")
        .prefetch_related(
            "university__field_verifications",
            "university__scholarships",
            "university__programs",
        )
    )
    applications_qs = (
        ApplicationTrackerItem.objects.filter(user=user)
        .select_related("university")
        .prefetch_related(
            "university__field_verifications",
            "university__scholarships",
            "university__programs",
        )
    )
    if not _is_demo_user(user):
        saved_qs = saved_qs.exclude(university__is_demo=True)
        applications_qs = applications_qs.exclude(university__is_demo=True)

    targets: dict[int, TargetUniversity] = {
        saved.university_id: TargetUniversity(university=saved.university) for saved in saved_qs
    }
    for application in applications_qs:
        targets[application.university_id] = TargetUniversity(
            university=application.university,
            application=application,
        )
    return list(targets.values())


def _future_deadlines(targets: list[TargetUniversity], today: date) -> list[date]:
    deadlines = []
    for target in targets:
        deadline = None
        if target.application and target.application.deadline:
            deadline = target.application.deadline
        elif target.university.application_deadline:
            deadline = target.university.application_deadline
        if deadline and deadline >= today:
            deadlines.append(deadline)
    return sorted(deadlines)


def _word_count(text: str) -> int:
    return len([word for word in text.replace("\n", " ").split(" ") if word.strip()])


def _add(drafts: dict[str, dict], dedup_key: str, **fields) -> None:
    fields["dedup_key"] = dedup_key[:255]
    drafts[fields["dedup_key"]] = fields


def _add_deadline_series(
    drafts: dict[str, dict],
    *,
    key_prefix: str,
    suggestion_type: str,
    university,
    deadline: date,
    today: date,
    source_type: str,
    source_url: str,
    linked_application=None,
    official: bool,
    title_noun: str,
) -> None:
    for days_before in DEADLINE_WINDOWS:
        due_date = deadline - timedelta(days=days_before)
        if due_date < today:
            continue
        if days_before == 0:
            title = f"{university.name}: final {title_noun} deadline"
            description = (
                f"Final deadline day for {title_noun} at {university.name}. "
                "Verify submission rules on the official source before sending."
            )
        else:
            title = f"{university.name}: {days_before} days before {title_noun} deadline"
            description = (
                f"Use this checkpoint to review {title_noun} requirements for "
                f"{university.name} before the deadline."
            )
        _add(
            drafts,
            f"{key_prefix}:{university.id}:{days_before}",
            suggestion_type=suggestion_type,
            title=title,
            description=description,
            priority=_deadline_priority(due_date, today, blocking=days_before == 0),
            source_type=source_type,
            linked_university=university,
            linked_application=linked_application,
            recommended_end_date=due_date,
            official_deadline=deadline if official else None,
            source_url=source_url,
            evidence_note=(
                f"Official deadline: {deadline.isoformat()}."
                if official
                else f"Date from your tracker: {deadline.isoformat()}; verify it with the official source."
            ),
        )


def _add_university_date_suggestions(
    drafts: dict[str, dict],
    targets: list[TargetUniversity],
    today: date,
) -> None:
    for target in targets:
        university = target.university
        application = target.application
        if application and application.deadline:
            _add_deadline_series(
                drafts,
                key_prefix="application_tracker_deadline",
                suggestion_type=SuggestionType.APPLICATION_DEADLINE,
                university=university,
                deadline=application.deadline,
                today=today,
                source_type=SourceType.PROFILE_BASED,
                source_url=university.admissions_url or university.official_website,
                linked_application=application,
                official=False,
                title_noun="application",
            )
        elif university.application_deadline:
            _add_deadline_series(
                drafts,
                key_prefix="application_deadline",
                suggestion_type=SuggestionType.APPLICATION_DEADLINE,
                university=university,
                deadline=university.application_deadline,
                today=today,
                source_type=SourceType.VERIFIED_UNIVERSITY_DATA,
                source_url=_source_url_for_university(university, "application_deadline"),
                linked_application=application,
                official=True,
                title_noun="application",
            )
        else:
            _add(
                drafts,
                f"application_deadline_missing:{university.id}",
                suggestion_type=SuggestionType.APPLICATION_DEADLINE,
                title=f"Verify {university.name}'s official application deadline",
                description=(
                    "No verified application deadline is stored yet. Check the official "
                    "admissions page before planning submission dates."
                ),
                priority=Priority.MEDIUM,
                source_type=SourceType.MISSING_DATA_WARNING,
                linked_university=university,
                linked_application=application,
                source_url=university.admissions_url or university.official_website,
                evidence_note="Missing official deadline. EduVerse will not invent one.",
            )

        deadline_for_documents = (
            application.deadline
            if application and application.deadline
            else university.application_deadline
        )
        if application and deadline_for_documents and application.documents_status not in {
            ApplicationTrackerItem.DocumentsStatus.READY,
            ApplicationTrackerItem.DocumentsStatus.SUBMITTED,
        }:
            doc_due = max(today, deadline_for_documents - timedelta(days=30))
            _add(
                drafts,
                f"document_deadline:{application.id}",
                suggestion_type=SuggestionType.DOCUMENT_DEADLINE,
                title=f"Prepare documents for {university.name}",
                description=(
                    "Use this planning checkpoint for transcripts, recommendations, "
                    "test score reports, and required forms."
                ),
                priority=_deadline_priority(doc_due, today, blocking=True),
                source_type=SourceType.PLANNING_WINDOW,
                linked_university=university,
                linked_application=application,
                recommended_end_date=doc_due,
                official_deadline=(
                    university.application_deadline if university.application_deadline else None
                ),
                source_url=university.admissions_url or university.official_website,
                evidence_note=(
                    "Suggested planning date derived from the application deadline; "
                    "not a separate official document deadline."
                ),
            )


def _add_scholarship_suggestions(
    drafts: dict[str, dict],
    profile,
    targets: list[TargetUniversity],
    today: date,
) -> None:
    if profile.scholarship_need not in {"yes", "unsure"}:
        return
    for target in targets:
        university = target.university
        application = target.application

        if application and application.financial_aid_deadline:
            _add_deadline_series(
                drafts,
                key_prefix="financial_aid_deadline",
                suggestion_type=SuggestionType.SCHOLARSHIP_DEADLINE,
                university=university,
                deadline=application.financial_aid_deadline,
                today=today,
                source_type=SourceType.PROFILE_BASED,
                source_url=university.financial_aid_url or university.official_website,
                linked_application=application,
                official=False,
                title_noun="financial aid",
            )
        if application and application.scholarship_deadline:
            _add_deadline_series(
                drafts,
                key_prefix="application_scholarship_deadline",
                suggestion_type=SuggestionType.SCHOLARSHIP_DEADLINE,
                university=university,
                deadline=application.scholarship_deadline,
                today=today,
                source_type=SourceType.PROFILE_BASED,
                source_url=university.financial_aid_url or university.official_website,
                linked_application=application,
                official=False,
                title_noun="scholarship",
            )

        scholarships = list(university.scholarships.all())
        for scholarship in scholarships:
            if scholarship.deadline and scholarship.deadline >= today:
                _add_deadline_series(
                    drafts,
                    key_prefix=f"scholarship_deadline:{scholarship.id}",
                    suggestion_type=SuggestionType.SCHOLARSHIP_DEADLINE,
                    university=university,
                    deadline=scholarship.deadline,
                    today=today,
                    source_type=SourceType.OFFICIAL,
                    source_url=scholarship.official_url,
                    linked_application=application,
                    official=True,
                    title_noun=scholarship.name,
                )

        has_aid_signal = bool(
            university.scholarship_available or scholarships or university.financial_aid_url
        )
        if has_aid_signal:
            _add(
                drafts,
                f"scholarship_type:aid_documents:{university.id}",
                suggestion_type=SuggestionType.SCHOLARSHIP_TYPE,
                title=f"Check need-based and international aid at {university.name}",
                description=(
                    "Review whether need-based aid, international-student aid, "
                    "external scholarships, or university-specific awards fit your situation."
                ),
                priority=Priority.MEDIUM,
                source_type=SourceType.VERIFIED_UNIVERSITY_DATA,
                linked_university=university,
                linked_application=application,
                source_url=university.financial_aid_url or university.official_website,
                evidence_note=(
                    "Your profile says scholarship support is needed or uncertain. "
                    "This is an eligibility check, not an award estimate."
                ),
            )
            _add(
                drafts,
                f"scholarship_type:merit_check:{university.id}",
                suggestion_type=SuggestionType.SCHOLARSHIP_TYPE,
                title=f"Check merit scholarship eligibility at {university.name}",
                description=(
                    "Look for merit, partial, full-tuition, full-ride, government, "
                    "or national scholarship routes that have official criteria."
                ),
                priority=Priority.LOW,
                source_type=SourceType.VERIFIED_UNIVERSITY_DATA,
                linked_university=university,
                linked_application=application,
                source_url=university.financial_aid_url or university.official_website,
                evidence_note="No scholarship probability is estimated or promised.",
            )
        else:
            _add(
                drafts,
                f"scholarship_type:missing:{university.id}",
                suggestion_type=SuggestionType.SCHOLARSHIP_TYPE,
                title=f"Verify scholarship eligibility for {university.name}",
                description=(
                    "No scholarship source is stored for this university yet. Check the "
                    "official financial aid page before assuming aid is or is not available."
                ),
                priority=Priority.MEDIUM,
                source_type=SourceType.MISSING_DATA_WARNING,
                linked_university=university,
                linked_application=application,
                source_url=university.financial_aid_url or university.official_website,
                evidence_note="Missing scholarship source data; EduVerse does not infer award availability.",
            )


def _deadline_for_university(targets: list[TargetUniversity], university_id: int | None) -> date | None:
    for target in targets:
        if target.university.id != university_id:
            continue
        if target.application and target.application.deadline:
            return target.application.deadline
        return target.university.application_deadline
    return None


def _add_essay_suggestions(
    drafts: dict[str, dict],
    user,
    targets: list[TargetUniversity],
    today: date,
) -> None:
    essays = EssayWorkspace.objects.filter(user=user).select_related("university")
    if not _is_demo_user(user):
        essays = essays.filter(Q(university__isnull=True) | Q(university__is_demo=False))

    for essay in essays:
        university = essay.university
        word_count = _word_count(essay.draft_text)
        source_url = essay.source_url or (
            (university.admissions_url or university.official_website) if university else ""
        )
        if essay.word_limit:
            target_min = max(1, int(Decimal(essay.word_limit) * Decimal("0.85")))
            if word_count > essay.word_limit:
                title = f"{essay.title}: trim draft to the word limit"
                priority = Priority.HIGH
            elif word_count < target_min:
                title = f"{essay.title}: expand toward the target range"
                priority = Priority.MEDIUM
            else:
                title = f"{essay.title}: word range looks on track"
                priority = Priority.LOW
            _add(
                drafts,
                f"essay_word_limit:{essay.id}",
                suggestion_type=SuggestionType.ESSAY_WORD_LIMIT,
                title=title,
                description=(
                    f"Current draft is about {word_count} words. Target range is "
                    f"{target_min}-{essay.word_limit} words."
                ),
                priority=priority,
                source_type=SourceType.OFFICIAL if essay.source_url else SourceType.PROFILE_BASED,
                linked_university=university,
                linked_essay=essay,
                word_limit=essay.word_limit,
                source_url=source_url,
                evidence_note=(
                    "Word limit is stored on this essay workspace. Verify it against "
                    "the official prompt if the source is missing."
                ),
            )
        else:
            _add(
                drafts,
                f"essay_word_limit_missing:{essay.id}",
                suggestion_type=SuggestionType.ESSAY_WORD_LIMIT,
                title=f"Verify word limit for {essay.title}",
                description="No word limit is stored for this essay prompt yet.",
                priority=Priority.MEDIUM,
                source_type=SourceType.MISSING_DATA_WARNING,
                linked_university=university,
                linked_essay=essay,
                source_url=source_url,
                evidence_note="Missing word limit. EduVerse will not guess it.",
            )

        deadline = _deadline_for_university(targets, university.id if university else None)
        if deadline and deadline >= today:
            for days_before in (30, 14, 7):
                checkpoint = deadline - timedelta(days=days_before)
                if checkpoint < today:
                    continue
                _add(
                    drafts,
                    f"essay_deadline:{essay.id}:{days_before}",
                    suggestion_type=SuggestionType.ESSAY_DEADLINE,
                    title=f"{essay.title}: revision checkpoint",
                    description=(
                        f"Suggested essay checkpoint {days_before} days before the "
                        "application deadline."
                    ),
                    priority=_deadline_priority(checkpoint, today),
                    source_type=SourceType.PLANNING_WINDOW,
                    linked_university=university,
                    linked_essay=essay,
                    recommended_end_date=checkpoint,
                    official_deadline=deadline if university and university.application_deadline else None,
                    source_url=source_url,
                    evidence_note=(
                        "Suggested planning checkpoint based on application timing; "
                        "not a separate official essay deadline."
                    ),
                )

    target_essay_universities = [target.university for target in targets if target.university.essay_requirements]
    if target_essay_universities and not essays.exists():
        university = target_essay_universities[0]
        _add(
            drafts,
            f"essay_workspace_missing:{university.id}",
            suggestion_type=SuggestionType.PROFILE_GAP,
            title=f"Create an essay workspace for {university.name}",
            description="This university has stored essay requirements, but you do not have an essay workspace yet.",
            priority=Priority.HIGH,
            source_type=SourceType.VERIFIED_UNIVERSITY_DATA,
            linked_university=university,
            source_url=university.admissions_url or university.official_website,
            evidence_note=university.essay_requirements[:400],
        )


def _iter_exam_plans(exam_plans) -> list[dict]:
    if not isinstance(exam_plans, dict):
        return []
    plans: list[dict] = []
    for key in ("planned", "retakes", "exams"):
        for item in _as_list(exam_plans.get(key)):
            if isinstance(item, dict):
                plans.append(item)
    if exam_plans.get("planned_retake") or exam_plans.get("exam_type"):
        plans.append(exam_plans)
    for key, value in exam_plans.items():
        if key.lower() in EXAM_NAMES and isinstance(value, dict):
            plan = {"exam_type": key}
            plan.update(value)
            plans.append(plan)
    return plans


def _exam_window(
    plan: dict,
    profile,
    earliest_deadline: date | None,
    today: date,
) -> tuple[date | None, date | None]:
    exam_date_raw = plan.get("date") or plan.get("planned_date") or plan.get("exam_date")
    if exam_date_raw:
        try:
            exam_date = date.fromisoformat(str(exam_date_raw))
            return max(today, exam_date - timedelta(days=35)), exam_date
        except ValueError:
            pass
    month_window = _parse_month_window(
        plan.get("planned_retake_month") or plan.get("month"),
        profile.expected_graduation_year,
    )
    if month_window:
        return month_window
    if earliest_deadline:
        end = max(today, earliest_deadline - timedelta(days=45))
        return max(today, end - timedelta(days=35)), end
    if profile.expected_graduation_year:
        year = profile.expected_graduation_year - 1
        return date(year, 5, 1), date(year, 6, 30)
    return None, None


def _add_exam_plan(
    drafts: dict[str, dict],
    *,
    exam_name: str,
    reason: str,
    profile,
    earliest_deadline: date | None,
    today: date,
    plan: dict | None = None,
) -> None:
    plan = plan or {}
    start, end = _exam_window(plan, profile, earliest_deadline, today)
    priority = _exam_priority(earliest_deadline, today)
    base = f"exam_plan:{exam_name.lower()}:{reason.lower().replace(' ', '_')}"
    evidence = (
        f"Planning window only for {exam_name}; verify official test dates and registration "
        "deadlines with the exam provider."
    )
    if earliest_deadline and (earliest_deadline - today).days <= 45:
        evidence += " Current application timing may be too close for a realistic retake cycle."

    steps = (
        ("diagnostic", "Take a diagnostic test", 0),
        ("registration", f"Choose and register for a {exam_name} date", 7),
        ("weekly_practice", f"Schedule weekly {exam_name} practice milestones", 14),
        ("final_mock", f"Take a final {exam_name} mock exam", 28),
        ("exam_window", f"Use this {exam_name} exam window", 35),
        ("score_sending", f"Plan {exam_name} score sending", 42),
    )
    for step_key, title, offset in steps:
        due = None
        if start and end:
            due = min(end, start + timedelta(days=offset))
        suggestion_type = SuggestionType.EXAM_DATE if step_key == "exam_window" else SuggestionType.EXAM_PLAN
        _add(
            drafts,
            f"{base}:{step_key}",
            suggestion_type=suggestion_type,
            title=title,
            description=(
                f"{reason}. This is a suggested planning item, not an official "
                f"{exam_name} test date."
            ),
            priority=priority,
            source_type=SourceType.PLANNING_WINDOW,
            recommended_start_date=start,
            recommended_end_date=due or end,
            evidence_note=evidence,
        )


def _decimal_score(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _score_from_profile(profile, key: str):
    if not isinstance(profile.test_scores, dict):
        return None
    for score_key, value in profile.test_scores.items():
        if str(score_key).lower() == key:
            return value
    return None


def _add_exam_suggestions(
    drafts: dict[str, dict],
    profile,
    preferences,
    targets: list[TargetUniversity],
    today: date,
) -> None:
    earliest_deadline = (_future_deadlines(targets, today) or [None])[0]
    planned_exams = set()
    for plan in _iter_exam_plans(profile.exam_plans):
        exam_name = _normal_exam_name(plan.get("exam_type") or plan.get("name"))
        if not exam_name:
            continue
        planned_retake = bool(plan.get("planned_retake"))
        test_status = str(plan.get("test_status") or "").lower()
        has_date = bool(plan.get("date") or plan.get("planned_date") or plan.get("planned_retake_month"))
        if not (planned_retake or has_date or test_status in {"preparing", "registered", "retaking"}):
            continue
        planned_exams.add(exam_name.upper())
        _add_exam_plan(
            drafts,
            exam_name=exam_name,
            reason=f"Your profile says you are planning or preparing for {exam_name}",
            profile=profile,
            earliest_deadline=earliest_deadline,
            today=today,
            plan=plan,
        )

    student_sat = best_sat_score(profile.test_scores)
    sat_targets = [
        target.university.sat_p75 or target.university.sat_average
        for target in targets
        if target.university.sat_p75 or target.university.sat_average
    ]
    if sat_targets and "SAT" not in planned_exams:
        strongest_target = max(sat_targets)
        if student_sat is None:
            _add_exam_plan(
                drafts,
                exam_name="SAT",
                reason="Shortlisted universities publish SAT ranges, but no SAT score is in your profile",
                profile=profile,
                earliest_deadline=earliest_deadline,
                today=today,
            )
        elif student_sat < strongest_target - SAT_SIGNIFICANT_GAP:
            _add_exam_plan(
                drafts,
                exam_name="SAT",
                reason=(
                    f"Your SAT score ({student_sat}) is below a competitive published range "
                    f"({strongest_target})"
                ),
                profile=profile,
                earliest_deadline=earliest_deadline,
                today=today,
            )

    ielts_targets = [
        Decimal(str(target.university.ielts_minimum))
        for target in targets
        if target.university.ielts_minimum is not None
    ]
    ielts_score = _decimal_score(_score_from_profile(profile, "ielts"))
    toefl_score = _score_from_profile(profile, "toefl")
    if ielts_targets and "IELTS" not in planned_exams and "TOEFL" not in planned_exams:
        required = max(ielts_targets)
        if ielts_score is None and toefl_score is None:
            _add_exam_plan(
                drafts,
                exam_name="IELTS/TOEFL",
                reason="A target university publishes an English-language requirement, but no score is recorded",
                profile=profile,
                earliest_deadline=earliest_deadline,
                today=today,
            )
        elif ielts_score is not None and ielts_score < required:
            _add_exam_plan(
                drafts,
                exam_name="IELTS",
                reason=f"Your IELTS score ({ielts_score}) is below a published minimum ({required})",
                profile=profile,
                earliest_deadline=earliest_deadline,
                today=today,
            )

    majors = " ".join(_as_list(profile.intended_majors) + _as_list(profile.intended_major)).lower()
    ap_relevant = any(keyword in majors for keyword in ("computer", "data", "engineering", "finance", "economics"))
    if (ap_relevant or preferences.ap_interests) and "AP" not in planned_exams:
        _add_exam_plan(
            drafts,
            exam_name="AP",
            reason="Your intended major or AP interests make AP planning worth reviewing",
            profile=profile,
            earliest_deadline=earliest_deadline,
            today=today,
        )


COURSE_RULES = (
    (
        ("finance", "economics", "business"),
        (
            ("AP Microeconomics", SuggestionType.AP_RECOMMENDATION),
            ("AP Macroeconomics", SuggestionType.AP_RECOMMENDATION),
            ("AP Statistics", SuggestionType.AP_RECOMMENDATION),
            ("AP Calculus", SuggestionType.AP_RECOMMENDATION),
            ("Economics fundamentals", SuggestionType.COURSE_RECOMMENDATION),
            ("Programming/Data analysis", SuggestionType.COURSE_RECOMMENDATION),
        ),
    ),
    (
        ("computer", "data", "ai", "software"),
        (
            ("AP Computer Science", SuggestionType.AP_RECOMMENDATION),
            ("AP Calculus", SuggestionType.AP_RECOMMENDATION),
            ("AP Statistics", SuggestionType.AP_RECOMMENDATION),
            ("Programming/Data analysis", SuggestionType.COURSE_RECOMMENDATION),
            ("Research methods", SuggestionType.COURSE_RECOMMENDATION),
        ),
    ),
    (
        ("psychology", "behavioral"),
        (
            ("AP Psychology", SuggestionType.AP_RECOMMENDATION),
            ("AP Statistics", SuggestionType.AP_RECOMMENDATION),
            ("Research methods", SuggestionType.COURSE_RECOMMENDATION),
            ("Academic writing", SuggestionType.COURSE_RECOMMENDATION),
        ),
    ),
    (
        ("engineering", "physics"),
        (
            ("AP Calculus", SuggestionType.AP_RECOMMENDATION),
            ("AP Physics", SuggestionType.AP_RECOMMENDATION),
            ("AP Computer Science", SuggestionType.AP_RECOMMENDATION),
            ("Programming/Data analysis", SuggestionType.COURSE_RECOMMENDATION),
        ),
    ),
    (
        ("medicine", "biology", "biomedical", "chemistry"),
        (
            ("AP Biology", SuggestionType.AP_RECOMMENDATION),
            ("AP Chemistry", SuggestionType.AP_RECOMMENDATION),
            ("Research methods", SuggestionType.COURSE_RECOMMENDATION),
            ("Academic writing", SuggestionType.COURSE_RECOMMENDATION),
        ),
    ),
    (
        ("law", "policy", "international relations", "ir"),
        (
            ("Academic writing", SuggestionType.COURSE_RECOMMENDATION),
            ("Research methods", SuggestionType.COURSE_RECOMMENDATION),
            ("Economics fundamentals", SuggestionType.COURSE_RECOMMENDATION),
            ("AP Psychology", SuggestionType.AP_RECOMMENDATION),
        ),
    ),
)


def _add_course_suggestions(drafts: dict[str, dict], profile, preferences) -> None:
    majors = [str(major) for major in _as_list(profile.intended_majors)]
    if profile.intended_major:
        majors.append(profile.intended_major)
    major_text = " ".join(majors).lower()
    if not major_text:
        return

    added_courses: set[str] = set()
    for keywords, courses in COURSE_RULES:
        if not any(keyword in major_text for keyword in keywords):
            continue
        for course, suggestion_type in courses:
            if course in added_courses:
                continue
            added_courses.add(course)
            _add(
                drafts,
                f"course:{course.lower().replace('/', '_').replace(' ', '_')}",
                suggestion_type=suggestion_type,
                title=f"Consider {course}",
                description=(
                    f"Suggested because your intended major includes {', '.join(majors[:3])}. "
                    "This is preparation guidance, not an admissions outcome claim."
                ),
                priority=Priority.MEDIUM,
                source_type=SourceType.PROFILE_BASED,
                evidence_note=(
                    "Linked to intended major/profile preparation. Add it to roadmap if it fits "
                    "your school schedule and official application requirements."
                ),
            )

    if profile.scholarship_need in {"yes", "unsure"} or preferences.finance_literacy_interest:
        _add(
            drafts,
            "course:financial_literacy",
            suggestion_type=SuggestionType.COURSE_RECOMMENDATION,
            title="Consider financial literacy",
            description=(
                "Useful for understanding aid terminology, scholarship documents, and cost "
                "comparisons. This is educational, not financial advice."
            ),
            priority=Priority.LOW,
            source_type=SourceType.PROFILE_BASED,
            evidence_note="Linked to scholarship need or finance-literacy interest.",
        )


def _add_profile_gap_suggestions(drafts: dict[str, dict], user, profile) -> None:
    if not Activity.objects.filter(user=user).exists():
        _add(
            drafts,
            "profile_gap:activities",
            suggestion_type=SuggestionType.PROFILE_GAP,
            title="Add your extracurricular activities",
            description="Record clubs, leadership roles, work, volunteering, and sustained interests.",
            priority=Priority.MEDIUM,
            source_type=SourceType.PROFILE_BASED,
            evidence_note="No structured activity records found.",
        )
    if not (Honor.objects.filter(user=user).exists() or Olympiad.objects.filter(user=user).exists()):
        _add(
            drafts,
            "profile_gap:honors",
            suggestion_type=SuggestionType.PROFILE_GAP,
            title="Add academic honors or competitions",
            description="Add awards, olympiads, distinctions, or note that you do not have them yet.",
            priority=Priority.LOW,
            source_type=SourceType.PROFILE_BASED,
            evidence_note="No honor or olympiad records found.",
        )
    majors = " ".join(_as_list(profile.intended_majors) + _as_list(profile.intended_major)).lower()
    if any(keyword in majors for keyword in ("research", "biology", "data", "economics", "psychology")):
        if not ResearchProject.objects.filter(user=user).exists():
            _add(
                drafts,
                "profile_gap:research",
                suggestion_type=SuggestionType.PROFILE_GAP,
                title="Plan a research project",
                description="Your intended field is research-heavy; record an existing project or plan one.",
                priority=Priority.MEDIUM,
                source_type=SourceType.PROFILE_BASED,
                evidence_note="No structured research project records found.",
            )
    if any(keyword in majors for keyword in ("computer", "data", "engineering", "design")):
        if not PortfolioProject.objects.filter(user=user).exists():
            _add(
                drafts,
                "profile_gap:portfolio",
                suggestion_type=SuggestionType.PROFILE_GAP,
                title="Build or record a portfolio project",
                description="Project evidence can support portfolio-driven fields when relevant.",
                priority=Priority.MEDIUM,
                source_type=SourceType.PROFILE_BASED,
                evidence_note="No structured portfolio project records found.",
            )


def _add_roadmap_instruction(drafts: dict[str, dict]) -> None:
    _add(
        drafts,
        "roadmap_instruction:source_aware",
        suggestion_type=SuggestionType.ROADMAP_INSTRUCTION,
        title="Use official deadlines differently from planning windows",
        description=(
            "Official deadlines come from stored university/source data. Planning windows are "
            "suggested checkpoints created from your profile, essays, applications, and exam plans."
        ),
        priority=Priority.LOW,
        source_type=SourceType.ROADMAP_BASED,
        evidence_note=(
            "Roadmap refresh is idempotent: generated items use stable keys, so repeated refreshes "
            "add new relevant tasks without duplicating existing ones."
        ),
    )


def _save_drafts(user, drafts: dict[str, dict]) -> list[SuggestedItem]:
    dedup_keys = list(drafts)
    existing = {
        item.dedup_key: item for item in SuggestedItem.objects.filter(user=user, dedup_key__in=dedup_keys)
    }
    touched: list[SuggestedItem] = []
    for dedup_key, fields in drafts.items():
        item = existing.get(dedup_key)
        if item is None:
            touched.append(SuggestedItem.objects.create(user=user, status=Status.ACTIVE, **fields))
            continue
        update_fields = []
        for field_name, value in fields.items():
            if getattr(item, field_name) != value:
                setattr(item, field_name, value)
                update_fields.append(field_name)
        if update_fields:
            update_fields.append("updated_at")
            item.save(update_fields=update_fields)
        touched.append(item)

    return list(
        SuggestedItem.objects.filter(
            user=user,
            dedup_key__in=[item.dedup_key for item in touched],
            status=Status.ACTIVE,
        ).select_related(
            "linked_university",
            "linked_application__university",
            "linked_essay",
            "linked_roadmap_task",
        )
    )


@transaction.atomic
def generate_suggestions(user) -> list[SuggestedItem]:
    profile, preferences = ensure_profile_records(user)
    today = _today()
    targets = _target_universities(user)
    drafts: dict[str, dict] = {}

    _add_university_date_suggestions(drafts, targets, today)
    _add_scholarship_suggestions(drafts, profile, targets, today)
    _add_essay_suggestions(drafts, user, targets, today)
    _add_exam_suggestions(drafts, profile, preferences, targets, today)
    _add_course_suggestions(drafts, profile, preferences)
    _add_profile_gap_suggestions(drafts, user, profile)
    _add_roadmap_instruction(drafts)

    return _save_drafts(user, drafts)


def _category_for_suggestion(suggestion: SuggestedItem) -> str:
    mapping = {
        SuggestionType.EXAM_DATE: RoadmapTask.Category.EXAMS,
        SuggestionType.EXAM_PLAN: RoadmapTask.Category.EXAMS,
        SuggestionType.ESSAY_DEADLINE: RoadmapTask.Category.ESSAYS,
        SuggestionType.ESSAY_WORD_LIMIT: RoadmapTask.Category.ESSAYS,
        SuggestionType.APPLICATION_DEADLINE: RoadmapTask.Category.DEADLINES,
        SuggestionType.SCHOLARSHIP_DEADLINE: RoadmapTask.Category.SCHOLARSHIPS,
        SuggestionType.SCHOLARSHIP_TYPE: RoadmapTask.Category.SCHOLARSHIPS,
        SuggestionType.COURSE_RECOMMENDATION: RoadmapTask.Category.PROFILE,
        SuggestionType.AP_RECOMMENDATION: RoadmapTask.Category.EXAMS,
        SuggestionType.DOCUMENT_DEADLINE: RoadmapTask.Category.DEADLINES,
        SuggestionType.PROFILE_GAP: RoadmapTask.Category.PROFILE,
        SuggestionType.ROADMAP_INSTRUCTION: RoadmapTask.Category.PROFILE,
    }
    return mapping.get(suggestion.suggestion_type, RoadmapTask.Category.PROFILE)


def _source_for_task(suggestion: SuggestedItem) -> str:
    if suggestion.source_type == SourceType.PLANNING_WINDOW:
        return RoadmapTask.SourceType.PLANNING_WINDOW
    if suggestion.source_type == SourceType.MISSING_DATA_WARNING:
        return RoadmapTask.SourceType.PROFILE_GAP
    if suggestion.source_type == SourceType.PROFILE_BASED:
        return RoadmapTask.SourceType.PROFILE_GAP
    if suggestion.suggestion_type in {
        SuggestionType.APPLICATION_DEADLINE,
        SuggestionType.SCHOLARSHIP_DEADLINE,
    }:
        return RoadmapTask.SourceType.UNIVERSITY_DEADLINE
    return RoadmapTask.SourceType.GENERATED


@transaction.atomic
def add_suggestion_to_roadmap(suggestion: SuggestedItem) -> RoadmapTask:
    plan, _ = RoadmapPlan.objects.get_or_create(
        user=suggestion.user,
        active=True,
        defaults={"title": "My admissions roadmap"},
    )
    due_date = (
        suggestion.recommended_end_date
        or suggestion.official_deadline
        or suggestion.recommended_start_date
    )
    task, _ = RoadmapTask.objects.get_or_create(
        user=suggestion.user,
        plan=plan,
        dedup_key=f"suggestion:{suggestion.id}",
        defaults={
            "title": suggestion.title,
            "description": suggestion.description,
            "category": _category_for_suggestion(suggestion),
            "priority": suggestion.priority,
            "due_date": due_date,
            "source_type": _source_for_task(suggestion),
            "linked_university": suggestion.linked_university,
            "generated_reason": f"Added from suggestion #{suggestion.id}.",
            "evidence_note": suggestion.evidence_note,
            "source_url": suggestion.source_url,
        },
    )
    suggestion.linked_roadmap_task = task
    suggestion.status = Status.ADDED_TO_ROADMAP
    suggestion.added_to_roadmap_at = timezone.now()
    suggestion.save(
        update_fields=(
            "linked_roadmap_task",
            "status",
            "added_to_roadmap_at",
            "updated_at",
        )
    )
    return task
