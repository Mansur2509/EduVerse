from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A single in-app notification for one user.

    Deliberately flat (no generic FK) to keep querying/serialization simple --
    `related_entity_type`/`related_entity_id` are informational hints for the
    frontend, mirroring the same convention `AnalyticsEvent` uses.
    """

    class NotificationType(models.TextChoices):
        DEADLINE_UPCOMING = "deadline_upcoming", "Deadline upcoming"
        EXAM_DATE_UPCOMING = "exam_date_upcoming", "Exam date upcoming"
        ROADMAP_TASK_DUE_SOON = "roadmap_task_due_soon", "Roadmap task due soon"
        RECOMMENDATION_MISSING = "recommendation_missing", "Recommendation missing"
        ESSAY_MISSING = "essay_missing", "Essay missing"
        ESSAY_REVIEW_COMPLETED = "essay_review_completed", "Essay review completed"
        EVENT_REGISTRATION_CONFIRMED = (
            "event_registration_confirmed",
            "Event registration confirmed",
        )
        EVENT_STARTING_SOON = "event_starting_soon", "Event starting soon"
        ORGANIZER_EVENT_APPROVED = "organizer_event_approved", "Organizer event approved"
        ORGANIZER_EVENT_REJECTED = "organizer_event_rejected", "Organizer event rejected"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        UNREAD = "unread", "Unread"
        READ = "read", "Read"
        ARCHIVED = "archived", "Archived"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=32, choices=NotificationType.choices, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.UNREAD, db_index=True
    )
    action_url = models.CharField(max_length=300, blank=True)
    related_entity_type = models.CharField(max_length=40, blank=True)
    related_entity_id = models.PositiveIntegerField(null=True, blank=True)
    # Stable per-user key so the cron-run generator never creates the same
    # notification twice (mirrors `RoadmapTask.dedup_key`).
    dedup_key = models.CharField(max_length=255)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "status")),
            models.Index(fields=("user", "created_at")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "dedup_key"), name="unique_notification_dedup_key_per_user"
            )
        ]

    def __str__(self) -> str:
        return self.title


class NotificationPreference(models.Model):
    """Per-user opt-out toggles, one boolean per notification category."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference"
    )
    deadlines_enabled = models.BooleanField(default=True)
    exams_enabled = models.BooleanField(default=True)
    roadmap_enabled = models.BooleanField(default=True)
    recommendations_essays_enabled = models.BooleanField(default=True)
    essay_reviews_enabled = models.BooleanField(default=True)
    events_enabled = models.BooleanField(default=True)
    organizer_events_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Notification preferences for {self.user_id}"
