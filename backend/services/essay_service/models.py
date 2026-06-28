from django.conf import settings
from django.db import models

from common.validators import validate_http_url


class EssayWorkspace(models.Model):
    class EssayType(models.TextChoices):
        COMMON_APP = "common_app", "Common App personal statement"
        SUPPLEMENT = "supplement", "Supplement"
        SCHOLARSHIP = "scholarship", "Scholarship"
        ACTIVITY = "activity", "Activity description"
        INTELLECTUAL_INTEREST = "intellectual_interest", "Intellectual interest"
        WHY_MAJOR = "why_major", "Why this major"
        WHY_SCHOOL = "why_school", "Why this school"
        ADDITIONAL_INFORMATION = "additional_information", "Additional information"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        DRAFTING = "drafting", "Drafting"
        NEEDS_REVISION = "needs_revision", "Needs revision"
        REVIEWED = "reviewed", "Reviewed"
        READY = "ready", "Ready"
        SUBMITTED = "submitted", "Submitted"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="essay_workspaces"
    )
    university = models.ForeignKey(
        "university_service.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="essay_workspaces",
    )
    title = models.CharField(max_length=240)
    essay_type = models.CharField(max_length=30, choices=EssayType.choices, default=EssayType.OTHER)
    prompt_text = models.TextField(blank=True)
    word_limit = models.PositiveSmallIntegerField(null=True, blank=True)
    draft_text = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    source_url = models.URLField(blank=True, validators=[validate_http_url])
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [models.Index(fields=("user", "status"))]

    def __str__(self) -> str:
        return self.title


class EssayFeedback(models.Model):
    class OverallLabel(models.TextChoices):
        WEAK = "weak", "Weak"
        DEVELOPING = "developing", "Developing"
        SOLID = "solid", "Solid"
        STRONG = "strong", "Strong"
        EXCELLENT = "excellent", "Excellent"

    class WordLimitStatus(models.TextChoices):
        TOO_SHORT = "too_short", "Too short"
        WITHIN_LIMIT = "within_limit", "Within limit"
        TOO_LONG = "too_long", "Too long"

    essay = models.ForeignKey(
        EssayWorkspace, on_delete=models.CASCADE, related_name="feedback_entries"
    )
    overall_label = models.CharField(max_length=20, choices=OverallLabel.choices)
    structure_score = models.PositiveSmallIntegerField(null=True, blank=True)
    clarity_score = models.PositiveSmallIntegerField(null=True, blank=True)
    authenticity_score = models.PositiveSmallIntegerField(null=True, blank=True)
    specificity_score = models.PositiveSmallIntegerField(null=True, blank=True)
    grammar_score = models.PositiveSmallIntegerField(null=True, blank=True)
    prompt_fit_score = models.PositiveSmallIntegerField(null=True, blank=True)
    word_count = models.PositiveIntegerField(default=0)
    word_limit_status = models.CharField(max_length=20, choices=WordLimitStatus.choices)
    summary = models.TextField(blank=True)
    strengths = models.JSONField(default=list, blank=True)
    issues = models.JSONField(default=list, blank=True)
    revision_tasks = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Feedback for {self.essay_id} ({self.overall_label})"


class EssayRevisionTask(models.Model):
    class Category(models.TextChoices):
        STRUCTURE = "structure", "Structure"
        CLARITY = "clarity", "Clarity"
        SPECIFICITY = "specificity", "Specificity"
        AUTHENTICITY = "authenticity", "Authenticity"
        GRAMMAR = "grammar", "Grammar"
        WORD_COUNT = "word_count", "Word count"
        PROMPT_FIT = "prompt_fit", "Prompt fit"

    class Status(models.TextChoices):
        TODO = "todo", "To do"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    essay = models.ForeignKey(
        EssayWorkspace, on_delete=models.CASCADE, related_name="revision_tasks"
    )
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("status", "-created_at")
        indexes = [models.Index(fields=("essay", "category"))]

    def __str__(self) -> str:
        return self.title
