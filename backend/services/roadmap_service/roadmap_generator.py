"""Deterministic, rule-based admissions roadmap generation.

No AI is used here. Every generated task must be traceable to a concrete
piece of data the student or an official source provided: a profile gap,
a verified university statistic, a planned exam date, or a real deadline.
Dates that are not backed by an official source are explicitly marked as
estimated planning windows rather than presented as real deadlines.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from django.db.models import Q
from django.utils import timezone

from services.application_service.models import ApplicationTrackerItem
from services.essay_service.models import EssayWorkspace
from services.event_service.models import EventRegistration
from services.event_service.services import ACTIVE_REGISTRATION_STATUSES
from services.university_service.models import SavedUniversity
from services.university_service.services import best_sat_score, calculate_university_fit
from services.user_profile_service.models import (
    Activity,
    EssayDraft,
    Honor,
    Olympiad,
    PortfolioProject,
    ResearchProject,
)
from services.user_profile_service.services import ensure_profile_records

from .models import RoadmapPlan, RoadmapTask

Category = RoadmapTask.Category
Priority = RoadmapTask.Priority
SourceType = RoadmapTask.SourceType

RESEARCH_HEAVY_KEYWORDS = (
    "computer science",
    "data science",
    "biology",
    "chemistry",
    "physics",
    "neuroscience",
    "research",
    "medicine",
    "biomedical",
    "economics",
    "psychology",
)

PORTFOLIO_KEYWORDS = (
    "computer science",
    "data science",
    "design",
    "engineering",
    "art",
    "architecture",
    "film",
    "media",
    "ux",
    "ui",
    "software",
)

TOP_UNIVERSITY_QS_THRESHOLD = 50
TOP_UNIVERSITY_ACCEPTANCE_THRESHOLD = 15.0
SAT_SIGNIFICANT_GAP = 100
DEADLINE_REMINDER_WINDOWS = (60, 30, 14, 7)


def _is_demo_user(user) -> bool:
    return bool(getattr(user, "email", "").endswith("@eduverse.local"))


def _priority_for_due_date(due_date: date | None, today: date, *, blocking: bool = False) -> str:
    if due_date is not None:
        days = (due_date - today).days
        if days <= 14:
            return Priority.URGENT
        if days <= 60:
            return Priority.HIGH
        return Priority.MEDIUM
    return Priority.HIGH if blocking else Priority.MEDIUM


def _matches_keywords(majors: list[str], keywords: tuple[str, ...]) -> bool:
    lowered = [major.lower() for major in majors if major]
    return any(keyword in major for major in lowered for keyword in keywords)


def _is_top_university(universities) -> bool:
    for university in universities:
        if university.qs_ranking and university.qs_ranking <= TOP_UNIVERSITY_QS_THRESHOLD:
            return True
        if (
            university.acceptance_rate is not None
            and float(university.acceptance_rate) <= TOP_UNIVERSITY_ACCEPTANCE_THRESHOLD
        ):
            return True
    return False


def _verified_source_url(university, field_name: str) -> str:
    verification = next(
        (v for v in university.field_verifications.all() if v.field_name == field_name), None
    )
    if verification:
        return verification.source_url
    return university.admissions_url or university.official_website


class RoadmapBuilder:
    def __init__(self, user, plan: RoadmapPlan):
        self.user = user
        self.plan = plan
        self.today = timezone.now().date()
        self.existing_keys = set(
            RoadmapTask.objects.filter(plan=plan).values_list("dedup_key", flat=True)
        )
        self.new_tasks: list[RoadmapTask] = []

    def add(self, dedup_key: str, **kwargs) -> None:
        if dedup_key in self.existing_keys:
            return
        self.existing_keys.add(dedup_key)
        kwargs.setdefault("priority", Priority.MEDIUM)
        kwargs.setdefault("status", RoadmapTask.Status.TODO)
        kwargs.setdefault("source_type", SourceType.GENERATED)
        self.new_tasks.append(
            RoadmapTask(user=self.user, plan=self.plan, dedup_key=dedup_key, **kwargs)
        )

    def estimated_anchor(self, lead_days: int) -> date | None:
        grad_year = self.profile.expected_graduation_year
        if not grad_year:
            return None
        application_season_start = date(grad_year - 1, 9, 1)
        anchor = application_season_start - timedelta(days=lead_days)
        return anchor if anchor > self.today else None

    def build(self, profile, preferences) -> list[str]:
        self.profile = profile
        self.preferences = preferences
        warnings: list[str] = []

        if not profile.expected_graduation_year:
            warnings.append("no_graduation_year")
        if not profile.target_countries:
            warnings.append("no_target_countries")
        if not (profile.intended_majors or profile.intended_major):
            warnings.append("no_intended_majors")
        if profile.gpa is None:
            warnings.append("no_gpa")
        if not profile.test_scores:
            warnings.append("no_test_scores")

        shortlisted_qs = (
            SavedUniversity.objects.filter(user=self.user)
            .select_related("university")
            .prefetch_related("university__field_verifications", "university__scholarships")
        )
        tracked_applications_qs = (
            ApplicationTrackerItem.objects.filter(user=self.user)
            .select_related("university")
            .prefetch_related("university__field_verifications", "university__scholarships")
        )
        if not _is_demo_user(self.user):
            shortlisted_qs = shortlisted_qs.exclude(university__is_demo=True)
            tracked_applications_qs = tracked_applications_qs.exclude(university__is_demo=True)

        shortlisted = list(shortlisted_qs)
        tracked_applications = list(tracked_applications_qs)
        target_universities = {saved.university_id: saved for saved in shortlisted}
        for application in tracked_applications:
            if application.university_id not in target_universities:
                target_universities[application.university_id] = SimpleNamespace(
                    university=application.university
                )
        targets = list(target_universities.values())

        if not targets:
            warnings.append("no_shortlisted_universities")

        self._profile_gaps(profile, targets)
        self._exam_gaps(profile, preferences, targets)
        self._university_deadlines(targets)
        self._scholarships(profile, targets)
        self._fit_analysis(profile, targets)
        self._events()
        self._essay_workspace_tasks()

        return warnings

    def _profile_gaps(self, profile, shortlisted):
        majors = list(profile.intended_majors or ([profile.intended_major] if profile.intended_major else []))
        universities = [s.university for s in shortlisted]

        if not Activity.objects.filter(user=self.user).exists():
            self.add(
                "profile_gap:activities",
                title="Add your extracurricular activities",
                description="List clubs, leadership roles, and other involvement in your profile.",
                category=Category.ACTIVITIES,
                priority=Priority.MEDIUM,
                source_type=SourceType.PROFILE_GAP,
                linked_profile_section="activities",
                generated_reason="Your structured profile has no recorded activities yet.",
                evidence_note="No Activity records found in your profile.",
            )

        if not (
            Honor.objects.filter(user=self.user).exists()
            or Olympiad.objects.filter(user=self.user).exists()
        ):
            self.add(
                "profile_gap:honors_olympiads",
                title="Add academic honors or olympiad results",
                description="Record awards, distinctions, or competition results, or note that you don't have any yet.",
                category=Category.ACTIVITIES,
                priority=Priority.LOW,
                source_type=SourceType.PROFILE_GAP,
                linked_profile_section="honors",
                generated_reason="Your structured profile has no honors or olympiad results yet.",
                evidence_note="No Honor or Olympiad records found in your profile.",
            )

        is_research_heavy = _matches_keywords(majors, RESEARCH_HEAVY_KEYWORDS) or _is_top_university(
            universities
        )
        if is_research_heavy and not ResearchProject.objects.filter(user=self.user).exists():
            due_date = self.estimated_anchor(lead_days=240)
            self.add(
                "profile_gap:research",
                title="Start a research project",
                description="Your intended major or shortlisted universities are research-competitive; a research project strengthens your profile.",
                category=Category.RESEARCH,
                priority=Priority.MEDIUM,
                source_type=SourceType.GENERATED if due_date else SourceType.PROFILE_GAP,
                due_date=due_date,
                linked_profile_section="research",
                generated_reason="Intended major or shortlisted universities are research-heavy or highly selective, and no research project is recorded.",
                evidence_note=(
                    "Estimated planning window based on your expected graduation year; not an official deadline."
                    if due_date
                    else "No ResearchProject records found in your profile."
                ),
            )

        if _matches_keywords(majors, PORTFOLIO_KEYWORDS) and not PortfolioProject.objects.filter(
            user=self.user
        ).exists():
            due_date = self.estimated_anchor(lead_days=180)
            self.add(
                "profile_gap:portfolio",
                title="Build a portfolio project",
                description="Your intended major typically expects applicants to show a project portfolio.",
                category=Category.PORTFOLIO,
                priority=Priority.MEDIUM,
                source_type=SourceType.GENERATED if due_date else SourceType.PROFILE_GAP,
                due_date=due_date,
                linked_profile_section="portfolio",
                generated_reason="Intended major matches a portfolio-driven field and no portfolio project is recorded.",
                evidence_note=(
                    "Estimated planning window based on your expected graduation year; not an official deadline."
                    if due_date
                    else "No PortfolioProject records found in your profile."
                ),
            )

        universities_needing_essays = [u for u in universities if u.essay_requirements]
        if universities_needing_essays and not EssayDraft.objects.filter(user=self.user).exists():
            self.add(
                "profile_gap:essays",
                title="Start planning your application essays",
                description="At least one shortlisted university has published essay requirements.",
                category=Category.ESSAYS,
                priority=Priority.HIGH,
                source_type=SourceType.ESSAY_STATUS,
                linked_university=universities_needing_essays[0],
                linked_profile_section="essays",
                generated_reason=f"{universities_needing_essays[0].name} has published essay requirements and you have no essay drafts yet.",
                evidence_note=universities_needing_essays[0].essay_requirements[:280],
            )

    def _exam_gaps(self, profile, preferences, target_universities):
        student_sat = best_sat_score(profile.test_scores)
        student_ielts = profile.test_scores.get("ielts") if isinstance(profile.test_scores, dict) else None

        shortlisted_universities = [target.university for target in target_universities]
        sat_targets = [
            u.sat_p75 or u.sat_average for u in shortlisted_universities if (u.sat_p75 or u.sat_average)
        ]
        if sat_targets:
            strongest_target = max(sat_targets)
            if student_sat is None:
                self.add(
                    "exam_gap:sat_missing",
                    title="Add your SAT score",
                    description="Your shortlisted universities publish SAT ranges, but your profile has no SAT score yet.",
                    category=Category.EXAMS,
                    due_date=self.estimated_anchor(lead_days=120),
                    priority=Priority.HIGH,
                    source_type=SourceType.PLANNING_WINDOW,
                    generated_reason="No SAT score recorded while shortlisted universities publish SAT data.",
                    evidence_note="Planning window only: add or schedule an SAT score check; this is not an official test date.",
                )
            elif student_sat < strongest_target - SAT_SIGNIFICANT_GAP:
                self.add(
                    "exam_gap:sat_improve",
                    title="Plan an SAT retake window",
                    description="Your current SAT score is below the range your shortlisted universities report.",
                    category=Category.EXAMS,
                    due_date=self.estimated_anchor(lead_days=120),
                    priority=Priority.HIGH,
                    source_type=SourceType.PLANNING_WINDOW,
                    generated_reason="Your SAT score is more than 100 points below a shortlisted university's reported range.",
                    evidence_note=f"Planning window only: your SAT score ({student_sat}) is below the strongest verified target ({strongest_target}) among your shortlisted universities; verify official SAT dates separately.",
                )

        ielts_targets = [
            float(u.ielts_minimum) for u in shortlisted_universities if u.ielts_minimum is not None
        ]
        if ielts_targets:
            required = max(ielts_targets)
            if student_ielts is None:
                self.add(
                    "exam_gap:ielts_missing",
                    title="Add your IELTS score",
                    description="A shortlisted university publishes a minimum IELTS requirement.",
                    category=Category.EXAMS,
                    due_date=self.estimated_anchor(lead_days=100),
                    priority=Priority.HIGH,
                    source_type=SourceType.PLANNING_WINDOW,
                    generated_reason="No IELTS score recorded while a shortlisted university publishes a minimum requirement.",
                    evidence_note=f"Planning window only: at least one shortlisted university requires a minimum IELTS score of {required}; verify official IELTS or TOEFL test dates separately.",
                )
            else:
                try:
                    if float(student_ielts) < required:
                        self.add(
                            "exam_gap:ielts_improve",
                            title="Plan an English exam retake window",
                            description="Your current IELTS score is below a shortlisted university's published minimum.",
                            category=Category.EXAMS,
                            due_date=self.estimated_anchor(lead_days=100),
                            priority=Priority.HIGH,
                            source_type=SourceType.PLANNING_WINDOW,
                            generated_reason="Your IELTS score is below the verified minimum for a shortlisted university.",
                            evidence_note=f"Planning window only: your IELTS score ({student_ielts}) is below the required minimum ({required}); verify official IELTS or TOEFL test dates separately.",
                        )
                except (TypeError, ValueError):
                    pass

        if preferences.ap_interests:
            self.add(
                "exam_gap:ap_planning",
                title="Plan your AP exams",
                description="Schedule preparation for the AP subjects you noted interest in.",
                category=Category.EXAMS,
                due_date=self.estimated_anchor(lead_days=150),
                priority=Priority.MEDIUM,
                source_type=SourceType.PLANNING_WINDOW,
                generated_reason="Your profile lists AP subject interests with no associated plan yet.",
                evidence_note=f"Planning window only: AP interests on file: {', '.join(preferences.ap_interests[:6])}. Verify official AP exam dates separately.",
            )

        for planned in profile.exam_plans.get("planned", []) if isinstance(profile.exam_plans, dict) else []:
            exam_name = planned.get("name")
            exam_date_str = planned.get("date")
            if not exam_name or not exam_date_str:
                continue
            try:
                exam_date = date.fromisoformat(exam_date_str)
            except ValueError:
                continue
            if exam_date < self.today:
                continue
            self.add(
                f"exam_plan:{exam_name}:{exam_date_str}",
                title=f"Prepare for {exam_name}",
                description=f"You planned to take {exam_name} on {exam_date_str}.",
                category=Category.EXAMS,
                due_date=exam_date,
                priority=_priority_for_due_date(exam_date, self.today),
                source_type=SourceType.EXAM_PLAN,
                generated_reason=f"You have a planned exam date for {exam_name} in your profile.",
                evidence_note=f"Planned exam date from your profile: {exam_date_str}.",
            )

    def _university_deadlines(self, shortlisted):
        for saved in shortlisted:
            university = saved.university
            if university.application_deadline:
                source_url = _verified_source_url(university, "application_deadline")
                deadline = university.application_deadline
                for days_before in DEADLINE_REMINDER_WINDOWS:
                    reminder_date = deadline - timedelta(days=days_before)
                    if reminder_date < self.today:
                        continue
                    self.add(
                        f"university_deadline:{university.id}:{days_before}",
                        title=f"{university.name}: {days_before} days until the deadline",
                        description=f"Review your application for {university.name} before its deadline.",
                        category=Category.DEADLINES,
                        due_date=reminder_date,
                        priority=_priority_for_due_date(reminder_date, self.today),
                        source_type=SourceType.UNIVERSITY_DEADLINE,
                        linked_university=university,
                        source_url=source_url,
                        generated_reason=f"{university.name}'s application deadline is on file.",
                        evidence_note=f"Application deadline: {deadline.isoformat()}.",
                    )
                if deadline >= self.today:
                    self.add(
                        f"university_deadline:{university.id}:final",
                        title=f"Submit your application to {university.name}",
                        description="Final submission day.",
                        category=Category.DEADLINES,
                        due_date=deadline,
                        priority=_priority_for_due_date(deadline, self.today, blocking=True),
                        source_type=SourceType.UNIVERSITY_DEADLINE,
                        linked_university=university,
                        source_url=source_url,
                        generated_reason=f"{university.name}'s application deadline is on file.",
                        evidence_note=f"Application deadline: {deadline.isoformat()}.",
                    )
            else:
                self.add(
                    f"university_deadline_missing:{university.id}",
                    title=f"Verify {university.name}'s application deadline",
                    description="No verified deadline is on file for this university yet.",
                    category=Category.UNIVERSITIES,
                    priority=Priority.MEDIUM,
                    source_type=SourceType.PROFILE_GAP,
                    linked_university=university,
                    source_url=university.admissions_url or university.official_website,
                    generated_reason=f"{university.name} has no verified application deadline on file.",
                    evidence_note="Check the official admissions page for the current deadline.",
                )

    def _scholarships(self, profile, shortlisted):
        if profile.scholarship_need != "yes":
            return
        for saved in shortlisted:
            university = saved.university
            scholarships = list(university.scholarships.all())
            has_aid_signal = bool(
                university.scholarship_available or scholarships or university.financial_aid_url
            )
            if not has_aid_signal:
                continue
            self.add(
                f"scholarship_research:{university.id}",
                title=f"Research financial aid at {university.name}",
                description="You indicated you need financial aid; review what this university offers.",
                category=Category.SCHOLARSHIPS,
                priority=Priority.MEDIUM,
                source_type=SourceType.GENERATED,
                linked_university=university,
                source_url=university.financial_aid_url or university.official_website,
                generated_reason="Your profile indicates scholarship need and this university has financial aid information.",
                evidence_note="Scholarship need: yes.",
            )
            self.add(
                f"scholarship_documents:{university.id}",
                title=f"Prepare financial aid documents for {university.name}",
                description="Gather income, tax, or need-based documentation likely required for aid applications.",
                category=Category.SCHOLARSHIPS,
                priority=Priority.MEDIUM,
                source_type=SourceType.GENERATED,
                linked_university=university,
                source_url=university.financial_aid_url or university.official_website,
                generated_reason="Financial aid applications typically require supporting documents.",
                evidence_note="Scholarship need: yes.",
            )
            for scholarship in scholarships:
                if scholarship.deadline and scholarship.deadline >= self.today:
                    self.add(
                        f"scholarship_deadline:{scholarship.id}",
                        title=f"{scholarship.name} deadline",
                        description=f"Deadline for {scholarship.name} at {university.name}.",
                        category=Category.SCHOLARSHIPS,
                        due_date=scholarship.deadline,
                        priority=_priority_for_due_date(scholarship.deadline, self.today),
                        source_type=SourceType.UNIVERSITY_DEADLINE,
                        linked_university=university,
                        source_url=scholarship.official_url,
                        generated_reason=f"{scholarship.name} has a published deadline.",
                        evidence_note=f"Scholarship deadline: {scholarship.deadline.isoformat()}.",
                    )

    def _fit_analysis(self, profile, shortlisted):
        field_labels = {
            "university_gpa_average": "average GPA",
            "university_sat_average": "average SAT score",
            "university_acceptance_rate": "acceptance rate",
        }
        for saved in shortlisted:
            university = saved.university
            fit = calculate_university_fit(profile, university)

            if fit["category"] == "reach":
                if "gpa_below_average" in fit["risks"]:
                    self.add(
                        f"fit_weak:{university.id}:gpa",
                        title=f"Strengthen your academic profile for {university.name}",
                        description="Your GPA is below this university's verified average.",
                        category=Category.PROFILE,
                        priority=Priority.HIGH,
                        source_type=SourceType.FIT_ANALYSIS,
                        linked_university=university,
                        generated_reason="Fit analysis flagged your GPA as a risk for this reach university.",
                        evidence_note="Your GPA is below this university's verified average.",
                    )
                if "sat_below_average" in fit["risks"]:
                    self.add(
                        f"fit_weak:{university.id}:sat",
                        title=f"Improve your SAT score for {university.name}",
                        description="Your SAT score is below this university's verified average.",
                        category=Category.EXAMS,
                        priority=Priority.HIGH,
                        source_type=SourceType.FIT_ANALYSIS,
                        linked_university=university,
                        generated_reason="Fit analysis flagged your SAT score as a risk for this reach university.",
                        evidence_note="Your SAT score is below this university's verified average.",
                    )

            for missing in fit["missing_fields"]:
                if missing not in field_labels:
                    continue
                self.add(
                    f"fit_missing:{university.id}:{missing}",
                    title=f"Verify {university.name}'s {field_labels[missing]}",
                    description="This statistic is not verified yet, so the fit analysis cannot fully account for it.",
                    category=Category.UNIVERSITIES,
                    priority=Priority.LOW,
                    source_type=SourceType.FIT_ANALYSIS,
                    linked_university=university,
                    source_url=university.admissions_url or university.official_website,
                    generated_reason="Fit analysis is limited by missing verified university data.",
                    evidence_note=f"{university.name}'s {field_labels[missing]} is not verified yet.",
                )

    def _essay_workspace_tasks(self):
        essays = EssayWorkspace.objects.filter(
            user=self.user,
            status__in=(EssayWorkspace.Status.NOT_STARTED, EssayWorkspace.Status.NEEDS_REVISION),
        ).select_related("university")
        if not _is_demo_user(self.user):
            essays = essays.filter(Q(university__isnull=True) | Q(university__is_demo=False))

        for essay in essays:
            due_date = None
            source_url = ""
            if essay.university and essay.university.application_deadline:
                due_date = essay.university.application_deadline
                source_url = _verified_source_url(essay.university, "application_deadline")

            if essay.status == EssayWorkspace.Status.NOT_STARTED:
                title = f"Start your essay: {essay.title}"
                generated_reason = "This essay draft has not been started yet."
            else:
                title = f"Revise your essay: {essay.title}"
                generated_reason = "This essay has open revision tasks from its latest feedback."

            self.add(
                f"essay_workspace:{essay.id}:{essay.status}",
                title=title,
                description=essay.prompt_text[:280]
                or "Open the essay workspace to continue this draft.",
                category=Category.ESSAYS,
                due_date=due_date,
                priority=_priority_for_due_date(
                    due_date,
                    self.today,
                    blocking=essay.status == EssayWorkspace.Status.NEEDS_REVISION,
                ),
                source_type=SourceType.ESSAY_STATUS,
                linked_university=essay.university,
                linked_profile_section=f"essay_workspace:{essay.id}",
                source_url=source_url,
                generated_reason=generated_reason,
                evidence_note=f"Essay status: {essay.status}.",
            )

    def _events(self):
        registrations = (
            EventRegistration.objects.filter(
                user=self.user, status__in=ACTIVE_REGISTRATION_STATUSES
            )
            .select_related("event", "event__source")
            .order_by("event__starts_at")
        )
        for registration in registrations:
            event = registration.event
            if not _is_demo_user(self.user):
                source_title = getattr(getattr(event, "source", None), "source_title", "")
                demo_marker = f"{event.title} {event.short_description} {source_title}".lower()
                if "demo" in demo_marker or "fictional" in demo_marker:
                    continue
            if event.deadline is None:
                continue
            event_deadline_date = event.deadline.date()
            if event_deadline_date < self.today:
                continue
            self.add(
                f"event_reminder:{registration.id}",
                title=f"Prepare for {event.title}",
                description="You are registered for this event.",
                category=Category.EVENTS,
                due_date=event_deadline_date,
                priority=_priority_for_due_date(event_deadline_date, self.today),
                source_type=SourceType.EVENT,
                linked_event=event,
                generated_reason="You are registered for this event and its deadline is approaching.",
                evidence_note=f"Event registration deadline: {event_deadline_date.isoformat()}.",
            )


def generate_roadmap(user) -> tuple[RoadmapPlan, list[str]]:
    """Generate or refresh the user's active roadmap. Returns (plan, warnings)."""
    profile, preferences = ensure_profile_records(user)

    plan, _ = RoadmapPlan.objects.get_or_create(
        user=user,
        active=True,
        defaults={
            "title": "My admissions roadmap",
            "cycle_year": profile.expected_graduation_year,
            "target_country": (profile.target_countries or [""])[0],
        },
    )

    builder = RoadmapBuilder(user, plan)
    warnings = builder.build(profile, preferences)
    if builder.new_tasks:
        RoadmapTask.objects.bulk_create(builder.new_tasks)

    total_tasks = RoadmapTask.objects.filter(plan=plan)
    urgent_count = total_tasks.filter(
        priority=Priority.URGENT, status=RoadmapTask.Status.TODO
    ).count()
    completed_count = total_tasks.filter(status=RoadmapTask.Status.COMPLETED).count()

    plan.cycle_year = profile.expected_graduation_year or plan.cycle_year
    plan.target_country = (profile.target_countries or [plan.target_country])[0]
    plan.summary = (
        f"{len(builder.new_tasks)} new task(s) added. "
        f"{total_tasks.count()} total, {urgent_count} urgent, {completed_count} completed."
    )
    plan.readiness_snapshot = {
        "missing_data_warnings": warnings,
        "shortlisted_count": SavedUniversity.objects.filter(user=user).count(),
        "total_tasks": total_tasks.count(),
        "urgent_tasks": urgent_count,
        "completed_tasks": completed_count,
        "new_tasks_added": len(builder.new_tasks),
    }
    plan.save()

    return plan, warnings
