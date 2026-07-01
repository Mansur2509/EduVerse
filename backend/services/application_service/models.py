from django.conf import settings
from django.db import models

from common.validators import validate_http_url


class ApplicationTrackerItem(models.Model):
    class ApplicationRound(models.TextChoices):
        EARLY_DECISION = "early_decision", "Early decision"
        EARLY_ACTION = "early_action", "Early action"
        RESTRICTIVE_EARLY_ACTION = "restrictive_early_action", "Restrictive early action"
        REGULAR_DECISION = "regular_decision", "Regular decision"
        ROLLING = "rolling", "Rolling"
        SCHOLARSHIP = "scholarship", "Scholarship"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        RESEARCHING = "researching", "Researching"
        SHORTLISTED = "shortlisted", "Shortlisted"
        PREPARING = "preparing", "Preparing"
        APPLYING = "applying", "Applying"
        SUBMITTED = "submitted", "Submitted"
        AWAITING_DECISION = "awaiting_decision", "Awaiting decision"
        ACCEPTED = "accepted", "Accepted"
        WAITLISTED = "waitlisted", "Waitlisted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        DREAM = "dream", "Dream"

    class TaskStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        DRAFTING = "drafting", "Drafting"
        NEEDS_REVISION = "needs_revision", "Needs revision"
        READY = "ready", "Ready"
        SUBMITTED = "submitted", "Submitted"

    class RecommendationsStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        REQUESTED = "requested", "Requested"
        RECEIVED = "received", "Received"
        SUBMITTED = "submitted", "Submitted"

    class TestScoresStatus(models.TextChoices):
        NOT_REQUIRED = "not_required", "Not required"
        PLANNED = "planned", "Planned"
        READY = "ready", "Ready"
        SENT = "sent", "Sent"

    class DocumentsStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        COLLECTING = "collecting", "Collecting"
        READY = "ready", "Ready"
        SUBMITTED = "submitted", "Submitted"

    class FinancialAidStatus(models.TextChoices):
        NOT_APPLYING = "not_applying", "Not applying"
        RESEARCHING = "researching", "Researching"
        PREPARING = "preparing", "Preparing"
        SUBMITTED = "submitted", "Submitted"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="application_items"
    )
    university = models.ForeignKey(
        "university_service.University", on_delete=models.CASCADE, related_name="application_items"
    )
    target_program = models.ForeignKey(
        "university_service.UniversityProgram",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_items",
    )
    application_round = models.CharField(
        max_length=30, choices=ApplicationRound.choices, default=ApplicationRound.REGULAR_DECISION
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESEARCHING, db_index=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    deadline = models.DateField(null=True, blank=True)
    financial_aid_deadline = models.DateField(null=True, blank=True)
    scholarship_deadline = models.DateField(null=True, blank=True)
    essays_status = models.CharField(
        max_length=20, choices=TaskStatus.choices, default=TaskStatus.NOT_STARTED
    )
    recommendations_status = models.CharField(
        max_length=20, choices=RecommendationsStatus.choices, default=RecommendationsStatus.NOT_STARTED
    )
    test_scores_status = models.CharField(
        max_length=20, choices=TestScoresStatus.choices, default=TestScoresStatus.NOT_REQUIRED
    )
    documents_status = models.CharField(
        max_length=20, choices=DocumentsStatus.choices, default=DocumentsStatus.NOT_STARTED
    )
    financial_aid_status = models.CharField(
        max_length=20, choices=FinancialAidStatus.choices, default=FinancialAidStatus.NOT_APPLYING
    )
    notes = models.TextField(max_length=3000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("deadline", "-priority", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "university"), name="unique_application_per_university"
            )
        ]
        indexes = [models.Index(fields=("user", "status"))]

    def __str__(self) -> str:
        return f"{self.university_id} application for {self.user_id}"


class ApplicationMilestone(models.Model):
    class Category(models.TextChoices):
        ESSAYS = "essays", "Essays"
        RECOMMENDATIONS = "recommendations", "Recommendations"
        TESTS = "tests", "Tests"
        FINANCIAL_AID = "financial_aid", "Financial aid"
        DOCUMENTS = "documents", "Documents"
        SUBMISSION = "submission", "Submission"
        INTERVIEW = "interview", "Interview"
        DECISION = "decision", "Decision"

    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    application = models.ForeignKey(
        ApplicationTrackerItem, on_delete=models.CASCADE, related_name="milestones"
    )
    title = models.CharField(max_length=240)
    category = models.CharField(max_length=20, choices=Category.choices)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    notes = models.TextField(max_length=1000, blank=True)
    linked_roadmap_task = models.ForeignKey(
        "roadmap_service.RoadmapTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_milestones",
    )
    source_url = models.URLField(blank=True, validators=[validate_http_url])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("due_date", "-created_at")
        indexes = [models.Index(fields=("application", "status"))]

    def __str__(self) -> str:
        return self.title
