from django.conf import settings
from django.db import models


class AnalyticsEvent(models.Model):
    """A minimal, sanitized product-analytics event.

    Deliberately thin: only an event type, an optional entity reference, and
    small metadata -- never raw essay text, secrets, or full profile dumps.
    Use `track_event()` in services.py rather than creating rows directly, so
    that sanitization stays in one place.
    """

    class EventType(models.TextChoices):
        USER_REGISTERED = "user_registered", "User registered"
        PROFILE_UPDATED = "profile_updated", "Profile updated"
        PROFILE_ASSESSMENT_REFRESHED = (
            "profile_assessment_refreshed",
            "Profile assessment refreshed",
        )
        UNIVERSITY_VIEWED = "university_viewed", "University viewed"
        UNIVERSITY_SHORTLISTED = "university_shortlisted", "University shortlisted"
        APPLICATION_CREATED = "application_created", "Application created"
        APPLICATION_STATUS_CHANGED = "application_status_changed", "Application status changed"
        ROADMAP_GENERATED = "roadmap_generated", "Roadmap generated"
        ROADMAP_TASK_COMPLETED = "roadmap_task_completed", "Roadmap task completed"
        ESSAY_REVIEW_REQUESTED = "essay_review_requested", "Essay review requested"
        EVENT_REGISTERED = "event_registered", "Event registered"
        ORGANIZER_EVENT_CREATED = "organizer_event_created", "Organizer event created"
        NOTIFICATION_READ = "notification_read", "Notification read"
        NOTIFICATION_ARCHIVED = "notification_archived", "Notification archived"
        ADMIN_MODERATION_ACTION = "admin_moderation_action", "Admin moderation action"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events",
    )
    event_type = models.CharField(max_length=60, choices=EventType.choices, db_index=True)
    entity_type = models.CharField(max_length=40, blank=True)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("event_type", "created_at")),
            models.Index(fields=("user", "created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} #{self.pk}"
