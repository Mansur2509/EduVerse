from django.conf import settings
from django.db import models


class FeedbackReport(models.Model):
    class FeedbackType(models.TextChoices):
        ISSUE = "issue", "Issue"
        IDEA = "idea", "Idea"
        CONFUSING = "confusing", "Confusing"
        DATA = "data", "Data"

    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWED = "reviewed", "Reviewed"
        RESOLVED = "resolved", "Resolved"
        ARCHIVED = "archived", "Archived"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback_reports",
    )
    contact = models.CharField(max_length=180, blank=True)
    feedback_type = models.CharField(
        max_length=20, choices=FeedbackType.choices, default=FeedbackType.ISSUE
    )
    page_module = models.CharField(max_length=160, blank=True)
    message = models.TextField(max_length=1500)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NORMAL, db_index=True
    )
    user_agent = models.CharField(max_length=300, blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.feedback_type} feedback #{self.pk} ({self.status})"
