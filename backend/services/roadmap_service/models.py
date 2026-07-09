from django.conf import settings
from django.db import models

from common.validators import validate_http_url


class RoadmapPlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roadmap_plans"
    )
    title = models.CharField(max_length=240, blank=True)
    cycle_year = models.PositiveSmallIntegerField(null=True, blank=True)
    target_country = models.CharField(max_length=100, blank=True)
    primary_goal = models.CharField(max_length=240, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    last_refreshed_at = models.DateTimeField(auto_now=True)
    summary = models.TextField(blank=True)
    readiness_snapshot = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-generated_at",)

    def __str__(self) -> str:
        return self.title or f"Roadmap for {self.user_id}"


class RoadmapTask(models.Model):
    TIMELINE_MARKER_DAYS = {"60", "30", "15", "14", "7"}

    class Category(models.TextChoices):
        PROFILE = "profile", "Profile"
        EXAMS = "exams", "Exams"
        ESSAYS = "essays", "Essays"
        UNIVERSITIES = "universities", "Universities"
        SCHOLARSHIPS = "scholarships", "Scholarships"
        ACTIVITIES = "activities", "Activities"
        RESEARCH = "research", "Research"
        PORTFOLIO = "portfolio", "Portfolio"
        DEADLINES = "deadlines", "Deadlines"
        EVENTS = "events", "Events"
        RECOMMENDATIONS = "recommendations", "Recommendations"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    class SourceType(models.TextChoices):
        GENERATED = "generated", "Generated"
        MANUAL = "manual", "Manual"
        UNIVERSITY_DEADLINE = "university_deadline", "University deadline"
        PROFILE_GAP = "profile_gap", "Profile gap"
        FIT_ANALYSIS = "fit_analysis", "Fit analysis"
        ESSAY_STATUS = "essay_status", "Essay status"
        EXAM_PLAN = "exam_plan", "Exam plan"
        PLANNING_WINDOW = "planning_window", "Planning window"
        EVENT = "event", "Event"
        CACHED_ASSESSMENT = "cached_assessment", "Cached profile assessment"

    class EstimatedEffort(models.TextChoices):
        SHORT = "short", "Short"
        MEDIUM = "medium", "Medium"
        LONG = "long", "Long"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roadmap_tasks"
    )
    plan = models.ForeignKey(RoadmapPlan, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO, db_index=True
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.GENERATED
    )

    linked_university = models.ForeignKey(
        "university_service.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roadmap_tasks",
    )
    linked_program = models.ForeignKey(
        "university_service.UniversityProgram",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roadmap_tasks",
    )
    linked_application = models.ForeignKey(
        "application_service.ApplicationTrackerItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roadmap_tasks",
    )
    linked_event = models.ForeignKey(
        "event_service.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roadmap_tasks",
    )
    linked_profile_section = models.CharField(max_length=60, blank=True)
    # One of the 12 profile_assessment_service signal names (activities,
    # research_experience, portfolio, ...) when this task traces back to a
    # specific benchmark-gap dimension from the cached AIProfileAssessment.
    # Blank for tasks generated from other sources (deadlines, exam plans).
    linked_score_dimension = models.CharField(max_length=40, blank=True)
    estimated_effort = models.CharField(
        max_length=10, choices=EstimatedEffort.choices, default=EstimatedEffort.MEDIUM
    )

    generated_reason = models.TextField(blank=True)
    evidence_note = models.TextField(blank=True)
    source_url = models.URLField(blank=True, validators=[validate_http_url])

    # Stable key used by the generator to avoid creating duplicate tasks on
    # repeated regeneration. Not exposed for write through the API.
    dedup_key = models.CharField(max_length=255, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("due_date", "-priority", "created_at")
        indexes = [
            models.Index(fields=("user", "status")),
            models.Index(fields=("plan", "dedup_key")),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def task_kind(self) -> str:
        return "manual" if self.source_type == self.SourceType.MANUAL else "generated"

    @property
    def is_timeline_marker(self) -> bool:
        if self.source_type != self.SourceType.UNIVERSITY_DEADLINE:
            return False
        if not self.dedup_key.startswith("university_deadline:"):
            return False
        marker = self.dedup_key.rsplit(":", 1)[-1]
        return marker in self.TIMELINE_MARKER_DAYS


class RoadmapTaskDependency(models.Model):
    task = models.ForeignKey(
        RoadmapTask, on_delete=models.CASCADE, related_name="dependencies"
    )
    depends_on_task = models.ForeignKey(
        RoadmapTask, on_delete=models.CASCADE, related_name="blocking_for"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("task", "depends_on_task"), name="unique_roadmap_task_dependency"
            )
        ]
