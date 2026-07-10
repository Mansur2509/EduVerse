import logging
from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.utils import timezone

from services.application_service.models import ApplicationRecommendation, ApplicationTrackerItem
from services.essay_service.models import EssayWorkspace
from services.event_service.models import EventRegistration
from services.roadmap_service.models import RoadmapTask
from services.user_profile_service.models import StudentProfile

from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)
User = get_user_model()

# Same threshold set for every deadline-shaped trigger (application/financial
# aid/scholarship deadlines, roadmap tasks, exam dates, essay/recommendation
# due dates) so a user gets one heads-up notification at 30, 7, and 1 day(s)
# out, then nothing further once the date passes.
THRESHOLD_DAYS = (30, 7, 1)

PREFERENCE_FIELD_BY_TYPE = {
    Notification.NotificationType.DEADLINE_UPCOMING: "deadlines_enabled",
    Notification.NotificationType.EXAM_DATE_UPCOMING: "exams_enabled",
    Notification.NotificationType.ROADMAP_TASK_DUE_SOON: "roadmap_enabled",
    Notification.NotificationType.RECOMMENDATION_MISSING: "recommendations_essays_enabled",
    Notification.NotificationType.ESSAY_MISSING: "recommendations_essays_enabled",
    Notification.NotificationType.ESSAY_REVIEW_COMPLETED: "essay_reviews_enabled",
    Notification.NotificationType.EVENT_REGISTRATION_CONFIRMED: "events_enabled",
    Notification.NotificationType.EVENT_STARTING_SOON: "events_enabled",
    Notification.NotificationType.ORGANIZER_EVENT_APPROVED: "organizer_events_enabled",
    Notification.NotificationType.ORGANIZER_EVENT_REJECTED: "organizer_events_enabled",
}


def ensure_notification_preference(user) -> NotificationPreference:
    preference, _ = NotificationPreference.objects.get_or_create(user=user)
    return preference


def _preference_allows(user, notification_type: str) -> bool:
    field = PREFERENCE_FIELD_BY_TYPE.get(notification_type)
    if not field:
        return True
    return getattr(ensure_notification_preference(user), field)


def _priority_for_days_remaining(days_remaining: int) -> str:
    if days_remaining <= 1:
        return Notification.Priority.URGENT
    if days_remaining <= 7:
        return Notification.Priority.HIGH
    return Notification.Priority.NORMAL


def create_notification(
    *,
    user,
    notification_type: str,
    title: str,
    dedup_key: str,
    message: str = "",
    priority: str = Notification.Priority.NORMAL,
    action_url: str = "",
    related_entity_type: str = "",
    related_entity_id: int | None = None,
    scheduled_for=None,
) -> Notification | None:
    """Create a notification unless the user opted out or it already exists.

    `dedup_key` must be a caller-chosen string that is stable and unique for
    "this exact notification for this exact user" (e.g. including the
    threshold day-count for cron-generated ones) so re-running the generator
    -- or a duplicate synchronous call -- never creates a second row.
    """
    if not _preference_allows(user, notification_type):
        return None
    try:
        notification, created = Notification.objects.get_or_create(
            user=user,
            dedup_key=dedup_key,
            defaults={
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "priority": priority,
                "action_url": action_url,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
                "scheduled_for": scheduled_for,
                "sent_at": timezone.now(),
            },
        )
    except Exception:
        logger.warning("Failed to create notification %s for user %s", notification_type, user.id, exc_info=True)
        return None
    return notification if created else None


def generate_deadline_notifications() -> int:
    created = 0
    today = timezone.now().date()
    deadline_fields = (
        ("deadline", "application"),
        ("financial_aid_deadline", "financial aid"),
        ("scholarship_deadline", "scholarship"),
    )
    open_statuses = ApplicationTrackerItem.Status
    items = ApplicationTrackerItem.objects.exclude(
        status__in=(open_statuses.ACCEPTED, open_statuses.REJECTED, open_statuses.WITHDRAWN)
    ).select_related("university", "user")
    for item in items:
        for field_name, label in deadline_fields:
            deadline_value: date | None = getattr(item, field_name)
            if not deadline_value:
                continue
            days_remaining = (deadline_value - today).days
            if days_remaining not in THRESHOLD_DAYS:
                continue
            notification = create_notification(
                user=item.user,
                notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
                title=f"{item.university.name} {label} deadline in {days_remaining} day(s)",
                message=f"The {label} deadline for {item.university.name} is {deadline_value.isoformat()}.",
                priority=_priority_for_days_remaining(days_remaining),
                action_url="/applications",
                related_entity_type="application",
                related_entity_id=item.id,
                dedup_key=f"deadline:{field_name}:{item.id}:{days_remaining}",
            )
            if notification:
                created += 1
    return created


def generate_exam_date_notifications() -> int:
    created = 0
    today = timezone.now().date()
    profiles = StudentProfile.objects.exclude(exam_plans={}).select_related("user")
    for profile in profiles:
        planned = profile.exam_plans.get("planned") if isinstance(profile.exam_plans, dict) else None
        if not planned:
            continue
        for exam in planned:
            name = exam.get("name") if isinstance(exam, dict) else None
            date_str = exam.get("date") if isinstance(exam, dict) else None
            if not name or not date_str:
                continue
            try:
                exam_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            days_remaining = (exam_date - today).days
            if days_remaining not in THRESHOLD_DAYS:
                continue
            notification = create_notification(
                user=profile.user,
                notification_type=Notification.NotificationType.EXAM_DATE_UPCOMING,
                title=f"{name} in {days_remaining} day(s)",
                message=f"Your planned {name} date is {date_str}.",
                priority=_priority_for_days_remaining(days_remaining),
                action_url="/profile",
                related_entity_type="exam_plan",
                dedup_key=f"exam_date:{profile.user_id}:{name}:{date_str}",
            )
            if notification:
                created += 1
    return created


def generate_roadmap_task_notifications() -> int:
    created = 0
    today = timezone.now().date()
    tasks = RoadmapTask.objects.exclude(
        status__in=(RoadmapTask.Status.COMPLETED, RoadmapTask.Status.SKIPPED)
    ).exclude(due_date__isnull=True).select_related("user")
    for task in tasks:
        days_remaining = (task.due_date - today).days
        if days_remaining not in THRESHOLD_DAYS:
            continue
        notification = create_notification(
            user=task.user,
            notification_type=Notification.NotificationType.ROADMAP_TASK_DUE_SOON,
            title=f'Roadmap task "{task.title}" due in {days_remaining} day(s)',
            message=task.title,
            priority=_priority_for_days_remaining(days_remaining),
            action_url="/roadmap",
            related_entity_type="roadmap_task",
            related_entity_id=task.id,
            dedup_key=f"roadmap_task_due_soon:{task.id}:{days_remaining}",
        )
        if notification:
            created += 1
    return created


def generate_recommendation_missing_notifications() -> int:
    created = 0
    today = timezone.now().date()
    requests = ApplicationRecommendation.objects.exclude(
        status=ApplicationRecommendation.Status.SUBMITTED
    ).exclude(due_date__isnull=True).select_related("application__user", "application__university")
    for recommendation in requests:
        days_remaining = (recommendation.due_date - today).days
        if days_remaining not in THRESHOLD_DAYS:
            continue
        application = recommendation.application
        display_name = recommendation.recommender_name or "Your recommender"
        notification = create_notification(
            user=application.user,
            notification_type=Notification.NotificationType.RECOMMENDATION_MISSING,
            title=f"Recommendation from {display_name} due in {days_remaining} day(s)",
            message=f"{display_name}'s recommendation for {application.university.name} is still not submitted.",
            priority=_priority_for_days_remaining(days_remaining),
            action_url="/applications",
            related_entity_type="recommendation",
            related_entity_id=recommendation.id,
            dedup_key=f"recommendation_missing:{recommendation.id}:{days_remaining}",
        )
        if notification:
            created += 1
    return created


def generate_essay_missing_notifications() -> int:
    created = 0
    today = timezone.now().date()
    terminal_statuses = (
        EssayWorkspace.Status.SUBMITTED,
        EssayWorkspace.Status.READY,
        EssayWorkspace.Status.SKIPPED,
    )
    essays = EssayWorkspace.objects.exclude(status__in=terminal_statuses).exclude(
        due_date__isnull=True
    ).select_related("user")
    for essay in essays:
        days_remaining = (essay.due_date - today).days
        if days_remaining not in THRESHOLD_DAYS:
            continue
        notification = create_notification(
            user=essay.user,
            notification_type=Notification.NotificationType.ESSAY_MISSING,
            title=f'Essay "{essay.title}" due in {days_remaining} day(s)',
            message=f'"{essay.title}" is due {essay.due_date.isoformat()} and is not finished yet.',
            priority=_priority_for_days_remaining(days_remaining),
            action_url="/essays",
            related_entity_type="essay",
            related_entity_id=essay.id,
            dedup_key=f"essay_missing:{essay.id}:{days_remaining}",
        )
        if notification:
            created += 1
    return created


def generate_event_starting_soon_notifications() -> int:
    created = 0
    today = timezone.now().date()
    registrations = EventRegistration.objects.filter(
        status__in=(EventRegistration.Status.REGISTERED, EventRegistration.Status.ATTENDED)
    ).select_related("event", "user")
    for registration in registrations:
        event = registration.event
        days_remaining = (event.starts_at.date() - today).days
        if days_remaining not in THRESHOLD_DAYS:
            continue
        notification = create_notification(
            user=registration.user,
            notification_type=Notification.NotificationType.EVENT_STARTING_SOON,
            title=f'"{event.title}" starts in {days_remaining} day(s)',
            message=f"{event.title} starts {event.starts_at:%B %d, %Y}.",
            priority=_priority_for_days_remaining(days_remaining),
            action_url=f"/events/{event.slug}",
            related_entity_type="event",
            related_entity_id=event.id,
            dedup_key=f"event_starting_soon:{registration.id}:{days_remaining}",
        )
        if notification:
            created += 1
    return created


def generate_all_notifications() -> dict:
    return {
        "deadlines": generate_deadline_notifications(),
        "exam_dates": generate_exam_date_notifications(),
        "roadmap_tasks": generate_roadmap_task_notifications(),
        "recommendations_missing": generate_recommendation_missing_notifications(),
        "essays_missing": generate_essay_missing_notifications(),
        "events_starting_soon": generate_event_starting_soon_notifications(),
    }
