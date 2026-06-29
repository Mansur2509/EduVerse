from django.conf import settings
from django.db import models

from common.validators import validate_http_url


class SuggestedItem(models.Model):
    class SuggestionType(models.TextChoices):
        EXAM_DATE = "exam_date", "Exam date"
        EXAM_PLAN = "exam_plan", "Exam plan"
        ESSAY_DEADLINE = "essay_deadline", "Essay deadline"
        ESSAY_WORD_LIMIT = "essay_word_limit", "Essay word limit"
        APPLICATION_DEADLINE = "application_deadline", "Application deadline"
        SCHOLARSHIP_DEADLINE = "scholarship_deadline", "Scholarship deadline"
        SCHOLARSHIP_TYPE = "scholarship_type", "Scholarship type"
        COURSE_RECOMMENDATION = "course_recommendation", "Course recommendation"
        AP_RECOMMENDATION = "ap_recommendation", "AP recommendation"
        DOCUMENT_DEADLINE = "document_deadline", "Document deadline"
        PROFILE_GAP = "profile_gap", "Profile gap"
        ROADMAP_INSTRUCTION = "roadmap_instruction", "Roadmap instruction"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class SourceType(models.TextChoices):
        OFFICIAL = "official", "Official"
        VERIFIED_UNIVERSITY_DATA = "verified_university_data", "Verified university data"
        PLANNING_WINDOW = "planning_window", "Planning window"
        PROFILE_BASED = "profile_based", "Profile based"
        ROADMAP_BASED = "roadmap_based", "Roadmap based"
        MISSING_DATA_WARNING = "missing_data_warning", "Missing data warning"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISMISSED = "dismissed", "Dismissed"
        ADDED_TO_ROADMAP = "added_to_roadmap", "Added to roadmap"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="suggested_items",
    )
    suggestion_type = models.CharField(
        max_length=40,
        choices=SuggestionType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )
    source_type = models.CharField(
        max_length=40,
        choices=SourceType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    linked_university = models.ForeignKey(
        "university_service.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_items",
    )
    linked_application = models.ForeignKey(
        "application_service.ApplicationTrackerItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_items",
    )
    linked_essay = models.ForeignKey(
        "essay_service.EssayWorkspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_items",
    )
    linked_roadmap_task = models.ForeignKey(
        "roadmap_service.RoadmapTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_items",
    )

    recommended_start_date = models.DateField(null=True, blank=True)
    recommended_end_date = models.DateField(null=True, blank=True)
    official_deadline = models.DateField(null=True, blank=True)
    word_limit = models.PositiveSmallIntegerField(null=True, blank=True)
    source_url = models.URLField(blank=True, validators=[validate_http_url])
    evidence_note = models.TextField(blank=True)

    dedup_key = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    added_to_roadmap_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = (
            "status",
            "recommended_end_date",
            "official_deadline",
            "-priority",
            "created_at",
        )
        constraints = [
            models.UniqueConstraint(
                fields=("user", "dedup_key"),
                name="unique_suggestion_per_user_key",
            )
        ]
        indexes = [
            models.Index(fields=("user", "status")),
            models.Index(fields=("user", "suggestion_type")),
        ]

    def __str__(self) -> str:
        return self.title
