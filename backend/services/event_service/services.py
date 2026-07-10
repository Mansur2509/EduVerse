import re
import secrets
import uuid
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from django.db import OperationalError, ProgrammingError, connection, transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from rest_framework import serializers

from services.notification_service.models import Notification
from services.notification_service.services import create_notification
from services.user_profile_service.services import ensure_profile_records

from .models import (
    Event,
    EventFormField,
    EventModerationLog,
    EventNotification,
    EventRegistration,
    EventRegistrationAnswer,
    EventSubmission,
    EventTicket,
    ParticipationRecord,
)

ACTIVE_REGISTRATION_STATUSES = (
    EventRegistration.Status.REGISTERED,
    EventRegistration.Status.WAITLISTED,
    EventRegistration.Status.ATTENDED,
)

ORGANIZER_EDITABLE_STATUSES = (
    Event.Status.DRAFT,
    Event.Status.PENDING_REVIEW,
    Event.Status.REJECTED,
)

MAX_FORM_FIELDS_PER_EVENT = 20
MAX_SHORT_ANSWER_LENGTH = 240
MAX_LONG_ANSWER_LENGTH = 4000
MAX_CHOICE_COUNT = 20
MAX_CHOICE_LENGTH = 120

TELEGRAM_USERNAME_RE = re.compile(r"^@?[A-Za-z0-9_]{5,32}$")


@lru_cache(maxsize=1)
def event_infrastructure_tables_available() -> bool:
    """Return whether optional event form/ticket tables are present.

    Core catalog and my-registration endpoints must stay readable during a
    deploy window where code has shipped but the new optional tables have not
    been migrated yet. Detail/register/organizer flows still require the
    migration for the full infrastructure feature set.
    """

    try:
        table_names = set(connection.introspection.table_names())
    except (OperationalError, ProgrammingError):
        return False
    required_tables = {
        EventFormField._meta.db_table,
        EventRegistrationAnswer._meta.db_table,
        EventTicket._meta.db_table,
    }
    return required_tables.issubset(table_names)


def generate_unique_event_slug(title: str) -> str:
    base_slug = slugify(title)[:240] or "event"
    slug = base_slug
    suffix = 2
    while Event.objects.filter(slug=slug).exists():
        slug = f"{base_slug[:240 - len(str(suffix)) - 1]}-{suffix}"
        suffix += 1
    return slug


def validate_event_is_editable(event: Event) -> None:
    if event.moderation_status not in ORGANIZER_EDITABLE_STATUSES:
        raise serializers.ValidationError(
            {"status": "Only draft, pending, or rejected events can be edited."}
        )


def _is_blank_answer(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and not value:
        return True
    return False


def normalize_form_choices(raw_choices) -> list[str]:
    if raw_choices in (None, ""):
        return []
    if not isinstance(raw_choices, list):
        raise serializers.ValidationError({"choices": "Choices must be a list."})
    normalized: list[str] = []
    seen: set[str] = set()
    for choice in raw_choices:
        if not isinstance(choice, str):
            raise serializers.ValidationError({"choices": "Each choice must be text."})
        value = choice.strip()
        if not value:
            continue
        if len(value) > MAX_CHOICE_LENGTH:
            raise serializers.ValidationError(
                {"choices": f"Choices must be {MAX_CHOICE_LENGTH} characters or fewer."}
            )
        lowered = value.casefold()
        if lowered not in seen:
            normalized.append(value)
            seen.add(lowered)
    if len(normalized) > MAX_CHOICE_COUNT:
        raise serializers.ValidationError(
            {"choices": f"No more than {MAX_CHOICE_COUNT} choices are allowed."}
        )
    return normalized


def validate_form_fields_payload(fields: list[dict]) -> list[dict]:
    if len(fields) > MAX_FORM_FIELDS_PER_EVENT:
        raise serializers.ValidationError(
            {"fields": f"No more than {MAX_FORM_FIELDS_PER_EVENT} form fields are allowed."}
        )
    normalized_fields = []
    for index, field in enumerate(fields):
        field_type = field.get("field_type")
        if field_type not in EventFormField.FieldType.values:
            raise serializers.ValidationError({"field_type": "Unsupported form field type."})
        label = str(field.get("label", "")).strip()
        if not label:
            raise serializers.ValidationError({"label": "A field label is required."})
        if len(label) > 160:
            raise serializers.ValidationError({"label": "Field labels must be 160 characters or fewer."})
        help_text = str(field.get("help_text", "")).strip()
        if len(help_text) > 500:
            raise serializers.ValidationError({"help_text": "Help text must be 500 characters or fewer."})
        choices = normalize_form_choices(field.get("choices", []))
        if field_type in (
            EventFormField.FieldType.SINGLE_CHOICE,
            EventFormField.FieldType.MULTIPLE_CHOICE,
        ) and not choices:
            raise serializers.ValidationError({"choices": "Choice fields need at least one option."})
        if field_type not in (
            EventFormField.FieldType.SINGLE_CHOICE,
            EventFormField.FieldType.MULTIPLE_CHOICE,
        ):
            choices = []
        validation = field.get("validation") if isinstance(field.get("validation"), dict) else {}
        normalized_fields.append(
            {
                "field_type": field_type,
                "label": label,
                "help_text": help_text,
                "is_required": bool(field.get("is_required", False)),
                "order": index,
                "choices": choices,
                "validation": validation,
            }
        )
    return normalized_fields


def _field_input_key(field: EventFormField) -> str:
    return str(field.id)


def normalize_answer_value(field: EventFormField, raw_value):
    if _is_blank_answer(raw_value):
        if field.is_required:
            raise serializers.ValidationError(
                {str(field.id): f"{field.label} is required."}
            )
        return None

    if field.field_type == EventFormField.FieldType.SHORT_TEXT:
        value = str(raw_value).strip()
        if len(value) > MAX_SHORT_ANSWER_LENGTH:
            raise serializers.ValidationError(
                {str(field.id): f"{field.label} must be {MAX_SHORT_ANSWER_LENGTH} characters or fewer."}
            )
        return value

    if field.field_type == EventFormField.FieldType.LONG_TEXT:
        value = str(raw_value).strip()
        if len(value) > MAX_LONG_ANSWER_LENGTH:
            raise serializers.ValidationError(
                {str(field.id): f"{field.label} must be {MAX_LONG_ANSWER_LENGTH} characters or fewer."}
            )
        return value

    if field.field_type == EventFormField.FieldType.SINGLE_CHOICE:
        value = str(raw_value).strip()
        if value not in field.choices:
            raise serializers.ValidationError({str(field.id): "Choose one of the allowed options."})
        return value

    if field.field_type == EventFormField.FieldType.MULTIPLE_CHOICE:
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        normalized = []
        for item in values:
            value = str(item).strip()
            if value not in field.choices:
                raise serializers.ValidationError({str(field.id): "Choose only allowed options."})
            if value not in normalized:
                normalized.append(value)
        return normalized

    if field.field_type == EventFormField.FieldType.NUMBER:
        try:
            decimal_value = Decimal(str(raw_value).strip())
        except (InvalidOperation, ValueError):
            raise serializers.ValidationError({str(field.id): "Enter a valid number."}) from None
        return str(decimal_value.normalize())

    if field.field_type == EventFormField.FieldType.DATE:
        value = str(raw_value).strip()
        if not parse_date(value):
            raise serializers.ValidationError({str(field.id): "Enter a valid date."})
        return value

    if field.field_type == EventFormField.FieldType.EMAIL:
        value = str(raw_value).strip()
        try:
            EmailValidator()(value)
        except DjangoValidationError:
            raise serializers.ValidationError({str(field.id): "Enter a valid email address."}) from None
        return value

    if field.field_type == EventFormField.FieldType.PHONE:
        value = str(raw_value).strip()
        if len(value) > 40:
            raise serializers.ValidationError({str(field.id): "Enter a shorter phone number."})
        return value

    if field.field_type == EventFormField.FieldType.TELEGRAM:
        value = str(raw_value).strip()
        if not TELEGRAM_USERNAME_RE.match(value):
            raise serializers.ValidationError({str(field.id): "Enter a valid Telegram username."})
        return value if value.startswith("@") else f"@{value}"

    if field.field_type == EventFormField.FieldType.URL:
        value = str(raw_value).strip()
        if len(value) > 500 or not value.startswith(("http://", "https://")):
            raise serializers.ValidationError({str(field.id): "Enter a safe http(s) link."})
        return value

    raise serializers.ValidationError({str(field.id): "Unsupported form field."})


def normalize_registration_answers(event: Event, answers) -> list[tuple[EventFormField, object]]:
    fields = list(event.form_fields.order_by("order", "id"))
    if not fields:
        return []
    if answers is None:
        answers = {}
    if not isinstance(answers, dict):
        raise serializers.ValidationError({"answers": "Answers must be an object keyed by form field id."})

    known_keys = {_field_input_key(field) for field in fields}
    unknown_keys = [key for key in answers.keys() if str(key) not in known_keys]
    if unknown_keys:
        raise serializers.ValidationError({"answers": "Unknown registration form field."})

    normalized_answers = []
    for field in fields:
        raw_value = answers.get(_field_input_key(field))
        normalized_value = normalize_answer_value(field, raw_value)
        if normalized_value is not None:
            normalized_answers.append((field, normalized_value))
    return normalized_answers


def _generate_ticket_code() -> str:
    return f"evt_{secrets.token_urlsafe(24)}"


def _generate_public_verification_code() -> str:
    return f"part_{secrets.token_urlsafe(18)}"


def ensure_ticket_for_registration(
    registration: EventRegistration,
    *,
    reactivate_cancelled: bool = True,
) -> EventTicket:
    ticket, created = EventTicket.objects.get_or_create(
        registration=registration,
        defaults={
            "event": registration.event,
            "user": registration.user,
            "code": _generate_ticket_code(),
            "status": EventTicket.Status.ACTIVE,
        },
    )
    if (
        not created
        and reactivate_cancelled
        and ticket.status in (EventTicket.Status.CANCELLED, EventTicket.Status.EXPIRED)
    ):
        ticket.status = EventTicket.Status.ACTIVE
        ticket.code = _generate_ticket_code()
        ticket.checked_in_at = None
        ticket.event = registration.event
        ticket.user = registration.user
        ticket.save(update_fields=["status", "code", "checked_in_at", "event", "user"])
    return ticket


def replace_registration_answers(
    *,
    registration: EventRegistration,
    normalized_answers: list[tuple[EventFormField, object]],
) -> None:
    registration.answers.all().delete()
    EventRegistrationAnswer.objects.bulk_create(
        [
            EventRegistrationAnswer(
                registration=registration,
                field=field,
                value=value,
            )
            for field, value in normalized_answers
        ]
    )


def create_event_notification(
    *,
    event: Event,
    notification_type: str,
    recipient=None,
    actor=None,
    registration: EventRegistration | None = None,
    channel: str = EventNotification.Channel.INTERNAL,
    payload: dict | None = None,
    status: str = EventNotification.DeliveryStatus.PENDING,
) -> EventNotification | None:
    if not event_infrastructure_tables_available():
        return None
    return EventNotification.objects.create(
        event=event,
        registration=registration,
        actor=actor,
        recipient=recipient,
        notification_type=notification_type,
        channel=channel,
        status=status,
        payload=payload or {},
    )


def _log_transition(
    *,
    event: Event,
    actor,
    previous_status: str,
    new_status: str,
    note: str = "",
) -> None:
    EventModerationLog.objects.create(
        event=event,
        moderator=actor,
        previous_status=previous_status,
        new_status=new_status,
        note=note,
    )


@transaction.atomic
def submit_event_for_review(*, event: Event, actor) -> Event:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if locked_event.moderation_status not in (
        Event.Status.DRAFT,
        Event.Status.REJECTED,
    ):
        raise serializers.ValidationError(
            {"status": "Only draft or rejected events can be submitted."}
        )

    previous_status = locked_event.moderation_status
    locked_event.moderation_status = Event.Status.PENDING_REVIEW
    locked_event.save(update_fields=["moderation_status", "updated_at"])
    submission, created = EventSubmission.objects.get_or_create(
        event=locked_event,
        defaults={"submitted_by": actor},
    )
    if not created:
        submission.submitted_by = actor
        submission.submitted_at = timezone.now()
        submission.save(update_fields=["submitted_by", "submitted_at"])
    _log_transition(
        event=locked_event,
        actor=actor,
        previous_status=previous_status,
        new_status=Event.Status.PENDING_REVIEW,
        note="Submitted for moderation.",
    )
    return locked_event


@transaction.atomic
def approve_event(*, event: Event, actor) -> Event:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if locked_event.organizer_id == actor.id:
        raise serializers.ValidationError(
            {"event": "Moderators cannot approve their own event."}
        )
    if locked_event.moderation_status != Event.Status.PENDING_REVIEW:
        raise serializers.ValidationError(
            {"status": "Only pending events can be approved."}
        )

    locked_event.moderation_status = Event.Status.PUBLISHED
    locked_event.save(update_fields=["moderation_status", "updated_at"])
    _log_transition(
        event=locked_event,
        actor=actor,
        previous_status=Event.Status.PENDING_REVIEW,
        new_status=Event.Status.PUBLISHED,
        note="Approved for publication.",
    )
    create_event_notification(
        event=locked_event,
        recipient=locked_event.organizer,
        actor=actor,
        notification_type=EventNotification.NotificationType.EVENT_APPROVED,
    )
    if locked_event.organizer_id:
        create_notification(
            user=locked_event.organizer,
            notification_type=Notification.NotificationType.ORGANIZER_EVENT_APPROVED,
            title=f'"{locked_event.title}" was approved',
            message=f'"{locked_event.title}" is now published and open for registration.',
            action_url=f"/organizer/events/{locked_event.slug}",
            related_entity_type="event",
            related_entity_id=locked_event.id,
            dedup_key=f"organizer_event_approved:{locked_event.id}",
        )
    return locked_event


@transaction.atomic
def reject_event(*, event: Event, actor, reason: str) -> Event:
    reason = reason.strip()
    if not reason:
        raise serializers.ValidationError({"reason": "A rejection reason is required."})

    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if locked_event.organizer_id == actor.id:
        raise serializers.ValidationError(
            {"event": "Moderators cannot reject their own event."}
        )
    if locked_event.moderation_status != Event.Status.PENDING_REVIEW:
        raise serializers.ValidationError(
            {"status": "Only pending events can be rejected."}
        )

    locked_event.moderation_status = Event.Status.REJECTED
    locked_event.save(update_fields=["moderation_status", "updated_at"])
    _log_transition(
        event=locked_event,
        actor=actor,
        previous_status=Event.Status.PENDING_REVIEW,
        new_status=Event.Status.REJECTED,
        note=reason,
    )
    create_event_notification(
        event=locked_event,
        recipient=locked_event.organizer,
        actor=actor,
        notification_type=EventNotification.NotificationType.EVENT_REJECTED,
        payload={"reason": reason},
    )
    if locked_event.organizer_id:
        create_notification(
            user=locked_event.organizer,
            notification_type=Notification.NotificationType.ORGANIZER_EVENT_REJECTED,
            title=f'"{locked_event.title}" was rejected',
            message=reason,
            action_url=f"/organizer/events/{locked_event.slug}",
            related_entity_type="event",
            related_entity_id=locked_event.id,
            dedup_key=f"organizer_event_rejected:{locked_event.id}:{timezone.now().isoformat()}",
        )
    return locked_event


@transaction.atomic
def archive_event(*, event: Event, actor, is_admin: bool = False) -> Event:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    allowed_statuses = (
        tuple(Event.Status.values)
        if is_admin
        else (
            Event.Status.DRAFT,
            Event.Status.PENDING_REVIEW,
            Event.Status.REJECTED,
        )
    )
    if locked_event.moderation_status not in allowed_statuses:
        raise serializers.ValidationError(
            {"status": "This event cannot be archived in its current status."}
        )
    if locked_event.moderation_status == Event.Status.ARCHIVED:
        raise serializers.ValidationError({"status": "This event is already archived."})

    previous_status = locked_event.moderation_status
    locked_event.moderation_status = Event.Status.ARCHIVED
    locked_event.save(update_fields=["moderation_status", "updated_at"])
    _log_transition(
        event=locked_event,
        actor=actor,
        previous_status=previous_status,
        new_status=Event.Status.ARCHIVED,
        note="Event archived.",
    )
    return locked_event


@transaction.atomic
def cancel_owned_event(*, event: Event, actor) -> Event:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if locked_event.moderation_status != Event.Status.PUBLISHED:
        raise serializers.ValidationError(
            {"status": "Only published events can be cancelled."}
        )

    locked_event.moderation_status = Event.Status.CANCELLED
    locked_event.save(update_fields=["moderation_status", "updated_at"])
    _log_transition(
        event=locked_event,
        actor=actor,
        previous_status=Event.Status.PUBLISHED,
        new_status=Event.Status.CANCELLED,
        note="Event cancelled by its organizer.",
    )
    return locked_event


def build_registration_snapshots(user) -> tuple[dict, dict]:
    profile, preferences = ensure_profile_records(user)
    registration_data = {
        "full_name": profile.full_name,
        "country": profile.country,
        "city": profile.city,
        "school_or_university": profile.school_or_university,
        "grade": profile.grade,
        "education_status": profile.education_status,
        "intended_degree": profile.intended_degree,
        "intended_majors": profile.intended_majors,
        "interests": preferences.interests,
        "languages": profile.languages,
    }
    contact_snapshot = {
        "email": user.email,
        "telegram_username": profile.telegram_username,
        "phone": profile.phone,
    }
    return registration_data, contact_snapshot


def payment_status_for_event(event: Event) -> str:
    if event.price_type == Event.PriceType.FREE:
        return EventRegistration.PaymentStatus.NOT_REQUIRED
    return EventRegistration.PaymentStatus.PENDING


@transaction.atomic
def register_for_event(*, event: Event, user, answers=None) -> tuple[EventRegistration, bool]:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    now = timezone.now()

    if locked_event.moderation_status != Event.Status.PUBLISHED:
        raise serializers.ValidationError({"event": "This event is not open for registration."})
    if locked_event.visibility != Event.Visibility.PUBLIC:
        raise serializers.ValidationError({"event": "This event is not publicly registerable."})
    if locked_event.deadline and locked_event.deadline < now:
        raise serializers.ValidationError({"event": "The registration deadline has passed."})
    if locked_event.starts_at <= now:
        raise serializers.ValidationError({"event": "Registration is closed because the event has started."})

    active_registration = EventRegistration.objects.filter(
        user=user,
        event=locked_event,
        status__in=ACTIVE_REGISTRATION_STATUSES,
    ).first()
    if active_registration:
        raise serializers.ValidationError({"event": "You are already registered for this event."})

    active_count = EventRegistration.objects.filter(
        event=locked_event,
        status__in=(
            EventRegistration.Status.REGISTERED,
            EventRegistration.Status.ATTENDED,
        ),
    ).count()
    if locked_event.capacity is not None and active_count >= locked_event.capacity:
        raise serializers.ValidationError({"event": "This event has reached capacity."})

    infrastructure_available = event_infrastructure_tables_available()
    normalized_answers = (
        normalize_registration_answers(locked_event, answers)
        if infrastructure_available
        else []
    )
    registration_data, contact_snapshot = build_registration_snapshots(user)
    cancelled_registration = (
        EventRegistration.objects.select_for_update()
        .filter(
            user=user,
            event=locked_event,
            status=EventRegistration.Status.CANCELLED,
        )
        .order_by("-updated_at")
        .first()
    )
    defaults = {
        "status": EventRegistration.Status.REGISTERED,
        "registration_data": registration_data,
        "contact_snapshot": contact_snapshot,
        "payment_status": payment_status_for_event(locked_event),
    }
    if cancelled_registration:
        for field, value in defaults.items():
            setattr(cancelled_registration, field, value)
        cancelled_registration.save()
        if infrastructure_available:
            replace_registration_answers(
                registration=cancelled_registration,
                normalized_answers=normalized_answers,
            )
            ensure_ticket_for_registration(cancelled_registration)
        create_event_notification(
            event=locked_event,
            recipient=user,
            registration=cancelled_registration,
            notification_type=EventNotification.NotificationType.REGISTRATION_CONFIRMED,
        )
        create_notification(
            user=user,
            notification_type=Notification.NotificationType.EVENT_REGISTRATION_CONFIRMED,
            title=f'Registration confirmed for "{locked_event.title}"',
            message=f"You're registered for {locked_event.title} on {locked_event.starts_at:%B %d, %Y}.",
            action_url=f"/events/{locked_event.slug}",
            related_entity_type="event",
            related_entity_id=locked_event.id,
            dedup_key=f"event_registration_confirmed:{cancelled_registration.id}",
        )
        return cancelled_registration, False

    registration = EventRegistration.objects.create(
        user=user,
        event=locked_event,
        **defaults,
    )
    if infrastructure_available:
        replace_registration_answers(
            registration=registration,
            normalized_answers=normalized_answers,
        )
        ensure_ticket_for_registration(registration)
    create_event_notification(
        event=locked_event,
        recipient=user,
        registration=registration,
        notification_type=EventNotification.NotificationType.REGISTRATION_CONFIRMED,
    )
    create_notification(
        user=user,
        notification_type=Notification.NotificationType.EVENT_REGISTRATION_CONFIRMED,
        title=f'Registration confirmed for "{locked_event.title}"',
        message=f"You're registered for {locked_event.title} on {locked_event.starts_at.isoformat()}.",
        action_url=f"/events/{locked_event.slug}",
        related_entity_type="event",
        related_entity_id=locked_event.id,
        dedup_key=f"event_registration_confirmed:{registration.id}",
    )
    if locked_event.organizer_id:
        create_event_notification(
            event=locked_event,
            recipient=locked_event.organizer,
            registration=registration,
            notification_type=EventNotification.NotificationType.ORGANIZER_NEW_REGISTRATION,
        )
    return registration, True


@transaction.atomic
def cancel_event_registration(*, event: Event, user) -> EventRegistration:
    registration = (
        EventRegistration.objects.select_for_update()
        .filter(
            user=user,
            event=event,
            status__in=(
                EventRegistration.Status.REGISTERED,
                EventRegistration.Status.WAITLISTED,
            ),
        )
        .first()
    )
    if not registration:
        raise serializers.ValidationError({"event": "No active registration was found."})

    registration.status = EventRegistration.Status.CANCELLED
    registration.save(update_fields=["status", "updated_at"])
    if event_infrastructure_tables_available() and hasattr(registration, "ticket"):
        registration.ticket.status = EventTicket.Status.CANCELLED
        registration.ticket.save(update_fields=["status"])
    create_event_notification(
        event=event,
        recipient=user,
        registration=registration,
        notification_type=EventNotification.NotificationType.REGISTRATION_CANCELLED,
    )
    return registration


@transaction.atomic
def check_in_registration(
    *,
    event: Event,
    registration_id: int,
    actor,
) -> EventRegistration:
    registration = (
        EventRegistration.objects.select_for_update()
        .select_related("event", "user", "event__organizer")
        .filter(event=event, id=registration_id)
        .first()
    )
    if not registration:
        raise serializers.ValidationError({"registration": "Registration not found."})
    if registration.status == EventRegistration.Status.CANCELLED:
        raise serializers.ValidationError({"registration": "Cancelled registrations cannot be checked in."})
    if registration.status not in (
        EventRegistration.Status.REGISTERED,
        EventRegistration.Status.WAITLISTED,
        EventRegistration.Status.ATTENDED,
    ):
        raise serializers.ValidationError({"registration": "This registration cannot be checked in."})

    now = timezone.now()
    ticket = ensure_ticket_for_registration(registration, reactivate_cancelled=False)
    if ticket.status == EventTicket.Status.CANCELLED:
        raise serializers.ValidationError({"ticket": "Cancelled tickets cannot be checked in."})

    if registration.status != EventRegistration.Status.ATTENDED:
        registration.status = EventRegistration.Status.ATTENDED
        registration.save(update_fields=["status", "updated_at"])
    if ticket.status != EventTicket.Status.CHECKED_IN:
        ticket.status = EventTicket.Status.CHECKED_IN
        ticket.checked_in_at = now
        ticket.save(update_fields=["status", "checked_in_at"])

    record, created = ParticipationRecord.objects.get_or_create(
        registration=registration,
        defaults={
            "event": event,
            "user": registration.user,
            "organizer": event.organizer,
            "attendance_status": ParticipationRecord.AttendanceStatus.CHECKED_IN,
            "participation_type": ParticipationRecord.ParticipationType.ATTENDEE,
            "verification_status": ParticipationRecord.VerificationStatus.VERIFIED,
            "verified_at": now,
            "record_id": uuid.uuid4(),
            "public_verification_code": _generate_public_verification_code(),
        },
    )
    if not created:
        record.attendance_status = ParticipationRecord.AttendanceStatus.CHECKED_IN
        record.verification_status = ParticipationRecord.VerificationStatus.VERIFIED
        record.verified_at = record.verified_at or now
        record.organizer = event.organizer
        record.save(
            update_fields=[
                "attendance_status",
                "verification_status",
                "verified_at",
                "organizer",
                "updated_at",
            ]
        )

    create_event_notification(
        event=event,
        recipient=registration.user,
        actor=actor,
        registration=registration,
        notification_type=EventNotification.NotificationType.CHECK_IN_CONFIRMED,
    )
    create_event_notification(
        event=event,
        recipient=registration.user,
        actor=actor,
        registration=registration,
        notification_type=EventNotification.NotificationType.PARTICIPATION_VERIFIED,
    )
    return registration


def public_event_queryset():
    return (
        Event.objects.filter(
            moderation_status=Event.Status.PUBLISHED,
            visibility=Event.Visibility.PUBLIC,
        )
        .select_related("category", "location", "source", "organizer")
        .annotate(
            active_registration_count=Count(
                "registrations",
                filter=Q(
                    registrations__status__in=(
                        EventRegistration.Status.REGISTERED,
                        EventRegistration.Status.ATTENDED,
                    )
                ),
            )
        )
    )
