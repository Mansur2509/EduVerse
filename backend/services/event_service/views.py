import csv

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from common.csv_security import neutralize_spreadsheet_formula
from common.permissions import IsAdminOrReadOnly, IsAdminRole, IsOrganizerOrAdmin
from common.throttling import ScopedIPRateThrottle
from services.activity_service.models import AnalyticsEvent
from services.activity_service.services import track_event

from .models import (
    Event,
    EventCategory,
    EventNotification,
    EventRegistration,
    EventTicket,
    OrganizerModeration,
    ParticipationRecord,
)
from .serializers import (
    EventCategorySerializer,
    EventFormFieldSerializer,
    EventModerationLogSerializer,
    EventNotificationSerializer,
    EventRegistrationSerializer,
    EventRejectionSerializer,
    EventSerializer,
    OrganizerEventSerializer,
    OrganizerModerationActionSerializer,
    OrganizerModerationSerializer,
    OrganizerParticipantSerializer,
    ParticipationRecordSerializer,
    PublicEventSerializer,
)
from .services import (
    ACTIVE_REGISTRATION_STATUSES,
    ORGANIZER_EDITABLE_STATUSES,
    approve_event,
    archive_event,
    cancel_event_registration,
    cancel_owned_event,
    check_in_registration,
    event_infrastructure_tables_available,
    public_event_queryset,
    register_for_event,
    reject_event,
    submit_event_for_review,
    validate_event_is_editable,
    validate_form_fields_payload,
)


class PublicEventListView(generics.ListAPIView):
    serializer_class = PublicEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = public_event_queryset().prefetch_related(
            Prefetch(
                "registrations",
                queryset=EventRegistration.objects.filter(
                    user=self.request.user,
                    status__in=ACTIVE_REGISTRATION_STATUSES,
                ).order_by("-updated_at"),
                to_attr="current_user_registrations",
            )
        )
        params = self.request.query_params
        search = params.get("search", "").strip()
        category = params.get("category", "").strip()
        country = params.get("country", "").strip()
        city = params.get("city", "").strip()
        price_type = params.get("price_type", "").strip()
        event_format = params.get("format", "").strip()
        is_online = params.get("is_online", "").strip().lower()

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(short_description__icontains=search)
                | Q(description__icontains=search)
                | Q(organizer_name__icontains=search)
            )
        if category:
            queryset = queryset.filter(category__slug=category)
        if country:
            queryset = queryset.filter(location__country__iexact=country)
        if city:
            queryset = queryset.filter(location__city__iexact=city)
        if price_type:
            queryset = queryset.filter(price_type=price_type)
        if event_format:
            queryset = queryset.filter(format=event_format)
        if is_online in {"true", "false"}:
            queryset = queryset.filter(is_online=is_online == "true")
        return queryset.order_by("starts_at")


class PublicEventDetailView(generics.RetrieveAPIView):
    serializer_class = PublicEventSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"

    def get_queryset(self):
        infrastructure_available = event_infrastructure_tables_available()
        registration_queryset = EventRegistration.objects.filter(
            user=self.request.user,
            status__in=ACTIVE_REGISTRATION_STATUSES,
        ).order_by("-updated_at")
        if infrastructure_available:
            registration_queryset = registration_queryset.select_related("ticket")
        queryset = public_event_queryset().prefetch_related(
            Prefetch(
                "registrations",
                queryset=registration_queryset,
                to_attr="current_user_registrations",
            )
        )
        if infrastructure_available:
            queryset = queryset.prefetch_related("form_fields")
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["include_event_registration_extras"] = True
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        track_event(
            user=request.user,
            event_type=AnalyticsEvent.EventType.EVENT_VIEWED,
            entity_type="event",
            entity_id=instance.id,
        )
        return Response(serializer.data)


class EventRegistrationView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "event_registration"

    def post(self, request, slug):
        event = get_object_or_404(Event.objects.all(), slug=slug)
        answers = request.data.get("answers") if hasattr(request.data, "get") else None
        registration, created = register_for_event(
            event=event,
            user=request.user,
            answers=answers,
        )
        if created:
            track_event(
                user=request.user,
                event_type=AnalyticsEvent.EventType.EVENT_REGISTERED,
                entity_type="event",
                entity_id=event.id,
            )
        serializer = EventRegistrationSerializer(
            registration,
            context={
                "request": request,
                "include_event_registration_extras": event_infrastructure_tables_available(),
            },
        )
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class EventRegistrationCancelView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "event_registration"

    def post(self, request, slug):
        event = get_object_or_404(Event.objects.all(), slug=slug)
        registration = cancel_event_registration(event=event, user=request.user)
        return Response(
            EventRegistrationSerializer(
                registration,
                context={
                    "request": request,
                    "include_event_registration_extras": event_infrastructure_tables_available(),
                },
            ).data
        )

    def delete(self, request, slug):
        return self.post(request, slug)


class MyEventRegistrationListView(generics.ListAPIView):
    serializer_class = EventRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            EventRegistration.objects.filter(
                user=self.request.user,
                status__in=ACTIVE_REGISTRATION_STATUSES,
            )
            .select_related(
                "event",
                "event__category",
                "event__location",
                "event__source",
                "event__organizer",
            )
            .order_by("event__starts_at")
        )
        if event_infrastructure_tables_available():
            queryset = queryset.select_related("ticket").prefetch_related("answers__field")
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["include_event_registration_extras"] = event_infrastructure_tables_available()
        return context


class MyParticipationRecordListView(generics.ListAPIView):
    serializer_class = ParticipationRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ParticipationRecord.objects.filter(user=self.request.user)
            .select_related("event", "event__organizer")
            .order_by("-verified_at")
        )


class MyEventNotificationListView(generics.ListAPIView):
    """Recent activity for the current user: registration/ticket updates for
    students, moderation/new-registration updates for organizers. A single
    endpoint is safe because `recipient` is always set to the party the
    notification concerns, never a third party.
    """

    serializer_class = EventNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            EventNotification.objects.filter(recipient=self.request.user)
            .select_related("event")
            .order_by("-created_at")
        )


def organizer_event_queryset(user):
    queryset = Event.objects.select_related(
        "category",
        "location",
        "source",
        "organizer",
    ).prefetch_related("moderation_logs")
    if user.is_admin_role:
        return queryset
    return queryset.filter(organizer=user)


class OrganizerCategoryListView(generics.ListAPIView):
    serializer_class = EventCategorySerializer
    permission_classes = [IsOrganizerOrAdmin]
    pagination_class = None
    queryset = EventCategory.objects.order_by("name")


class OrganizerEventListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizerEventSerializer
    permission_classes = [IsOrganizerOrAdmin]
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "event_submission"

    def get_queryset(self):
        return organizer_event_queryset(self.request.user).order_by("-updated_at")

    def perform_create(self, serializer):
        event = serializer.save()
        track_event(
            user=self.request.user,
            event_type=AnalyticsEvent.EventType.ORGANIZER_EVENT_CREATED,
            entity_type="event",
            entity_id=event.id,
        )


class OrganizerEventDetailView(generics.GenericAPIView):
    serializer_class = OrganizerEventSerializer
    permission_classes = [IsOrganizerOrAdmin]
    lookup_field = "slug"
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "event_submission"

    def get_queryset(self):
        return organizer_event_queryset(self.request.user)

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object()).data)

    def patch(self, request, *args, **kwargs):
        event = self.get_object()
        validate_event_is_editable(event)
        serializer = self.get_serializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OrganizerEventSubmitView(generics.GenericAPIView):
    serializer_class = OrganizerEventSerializer
    permission_classes = [IsOrganizerOrAdmin]
    lookup_field = "slug"
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "event_submission"

    def get_queryset(self):
        return organizer_event_queryset(self.request.user)

    def post(self, request, *args, **kwargs):
        event = submit_event_for_review(
            event=self.get_object(),
            actor=request.user,
        )
        return Response(self.get_serializer(event).data)


class OrganizerEventRegistrationListView(generics.ListAPIView):
    serializer_class = OrganizerParticipantSerializer
    permission_classes = [IsOrganizerOrAdmin]

    def get_event(self):
        event = get_object_or_404(
            organizer_event_queryset(self.request.user),
            slug=self.kwargs["slug"],
        )
        if event.moderation_status != Event.Status.PUBLISHED:
            raise ValidationError(
                {"status": "Participants are available only for published events."}
            )
        return event

    def get_queryset(self):
        return (
            EventRegistration.objects.filter(
                event=self.get_event(),
            )
            .select_related("ticket", "participation_record")
            .prefetch_related("answers__field")
            .order_by("-created_at")
        )


class OrganizerEventFormView(generics.GenericAPIView):
    permission_classes = [IsOrganizerOrAdmin]
    lookup_field = "slug"

    def get_queryset(self):
        return organizer_event_queryset(self.request.user).prefetch_related("form_fields")

    def get(self, request, *args, **kwargs):
        event = self.get_object()
        return Response(
            {
                "event": event.slug,
                "can_edit": event.moderation_status in ORGANIZER_EDITABLE_STATUSES,
                "fields": EventFormFieldSerializer(
                    event.form_fields.all().order_by("order", "id"),
                    many=True,
                ).data,
            }
        )

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        event = self.get_object()
        validate_event_is_editable(event)
        fields_payload = request.data.get("fields", [])
        if not isinstance(fields_payload, list):
            raise ValidationError({"fields": "Fields must be a list."})
        normalized_fields = validate_form_fields_payload(fields_payload)
        event.form_fields.all().delete()
        for field in normalized_fields:
            event.form_fields.create(**field)
        return Response(
            {
                "event": event.slug,
                "can_edit": True,
                "fields": EventFormFieldSerializer(
                    event.form_fields.all().order_by("order", "id"),
                    many=True,
                ).data,
            }
        )


class OrganizerEventCheckInView(generics.GenericAPIView):
    serializer_class = OrganizerParticipantSerializer
    permission_classes = [IsOrganizerOrAdmin]

    def get_event(self):
        event = get_object_or_404(
            organizer_event_queryset(self.request.user),
            slug=self.kwargs["slug"],
        )
        if event.moderation_status != Event.Status.PUBLISHED:
            raise ValidationError(
                {"status": "Check-in is available only for published events."}
            )
        return event

    def post(self, request, *args, **kwargs):
        registration = check_in_registration(
            event=self.get_event(),
            registration_id=self.kwargs["registration_id"],
            actor=request.user,
        )
        registration = (
            EventRegistration.objects.select_related("ticket", "participation_record")
            .prefetch_related("answers__field")
            .get(pk=registration.pk)
        )
        return Response(self.get_serializer(registration).data)


class OrganizerEventTicketVerifyView(generics.GenericAPIView):
    serializer_class = OrganizerParticipantSerializer
    permission_classes = [IsOrganizerOrAdmin]

    def post(self, request, *args, **kwargs):
        event = get_object_or_404(
            organizer_event_queryset(request.user),
            slug=kwargs["slug"],
        )
        code = str(request.data.get("code", "")).strip()
        if not code:
            raise ValidationError({"code": "Ticket code is required."})
        ticket = (
            EventTicket.objects.select_related("registration", "registration__user")
            .filter(event=event, code=code)
            .first()
        )
        if not ticket:
            raise ValidationError({"code": "Ticket was not found for this event."})
        registration = (
            EventRegistration.objects.select_related("ticket", "participation_record")
            .prefetch_related("answers__field")
            .get(pk=ticket.registration_id)
        )
        return Response(self.get_serializer(registration).data)


class OrganizerEventParticipantsExportView(generics.GenericAPIView):
    permission_classes = [IsOrganizerOrAdmin]

    def get_event(self):
        event = get_object_or_404(
            organizer_event_queryset(self.request.user).prefetch_related("form_fields"),
            slug=self.kwargs["slug"],
        )
        if event.moderation_status != Event.Status.PUBLISHED:
            raise ValidationError(
                {"status": "Exports are available only for published events."}
            )
        return event

    def get(self, request, *args, **kwargs):
        event = self.get_event()
        fields = list(event.form_fields.all().order_by("order", "id"))
        registrations = (
            EventRegistration.objects.filter(event=event)
            .select_related("ticket")
            .prefetch_related("answers__field")
            .order_by("-created_at")
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{event.slug}-participants.csv"'
        )
        writer = csv.writer(response)
        header = [
            "participant_name",
            "email",
            "telegram_username",
            "registration_status",
            "payment_status",
            "ticket_status",
            "checked_in_at",
            "registered_at",
        ] + [field.label for field in fields]
        writer.writerow([neutralize_spreadsheet_formula(value) for value in header])
        for registration in registrations:
            answers_by_field = {
                answer.field_id: answer.value for answer in registration.answers.all()
            }
            ticket = getattr(registration, "ticket", None)
            writer.writerow(
                [
                    neutralize_spreadsheet_formula(value)
                    for value in [
                        registration.registration_data.get("full_name", ""),
                        registration.contact_snapshot.get("email", ""),
                        registration.contact_snapshot.get("telegram_username", ""),
                        registration.status,
                        registration.payment_status,
                        ticket.status if ticket else "",
                        ticket.checked_in_at.isoformat()
                        if ticket and ticket.checked_in_at
                        else "",
                        registration.created_at.isoformat(),
                        *[answers_by_field.get(field.id, "") for field in fields],
                    ]
                ]
            )
        return response


class OrganizerEventAnalyticsView(APIView):
    permission_classes = [IsOrganizerOrAdmin]

    def get(self, request):
        events = organizer_event_queryset(request.user)
        registrations = EventRegistration.objects.filter(event__in=events)
        total_registrations = registrations.count()
        checked_in_count = registrations.filter(status=EventRegistration.Status.ATTENDED).count()
        total_capacity = 0
        published_with_capacity = 0
        for event in events:
            if event.capacity:
                total_capacity += event.capacity
                published_with_capacity += event.registrations.filter(
                    status__in=ACTIVE_REGISTRATION_STATUSES
                ).count()
        by_event = (
            events.annotate(
                registration_count=Count(
                    "registrations",
                    filter=Q(registrations__status__in=ACTIVE_REGISTRATION_STATUSES),
                ),
                checked_in_count=Count(
                    "registrations",
                    filter=Q(registrations__status=EventRegistration.Status.ATTENDED),
                ),
            )
            .order_by("-starts_at")
            .values("slug", "title", "registration_count", "checked_in_count")[:10]
        )
        return Response(
            {
                "total_events": events.count(),
                "draft_count": events.filter(moderation_status=Event.Status.DRAFT).count(),
                "pending_count": events.filter(
                    moderation_status=Event.Status.PENDING_REVIEW
                ).count(),
                "published_count": events.filter(
                    moderation_status=Event.Status.PUBLISHED
                ).count(),
                "rejected_count": events.filter(moderation_status=Event.Status.REJECTED).count(),
                "cancelled_count": events.filter(moderation_status=Event.Status.CANCELLED).count(),
                "archived_count": events.filter(moderation_status=Event.Status.ARCHIVED).count(),
                "total_registrations": total_registrations,
                "checked_in_count": checked_in_count,
                "attendance_rate": (
                    round((checked_in_count / total_registrations) * 100, 1)
                    if total_registrations
                    else None
                ),
                "capacity_fill_percentage": (
                    round((published_with_capacity / total_capacity) * 100, 1)
                    if total_capacity
                    else None
                ),
                "registrations_by_event": list(by_event),
            }
        )


class OrganizerEventArchiveView(generics.GenericAPIView):
    serializer_class = OrganizerEventSerializer
    permission_classes = [IsOrganizerOrAdmin]
    lookup_field = "slug"
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "event_submission"

    def get_queryset(self):
        return organizer_event_queryset(self.request.user)

    def post(self, request, *args, **kwargs):
        event = archive_event(
            event=self.get_object(),
            actor=request.user,
            is_admin=False,
        )
        return Response(self.get_serializer(event).data)


class OrganizerEventCancelView(generics.GenericAPIView):
    serializer_class = OrganizerEventSerializer
    permission_classes = [IsOrganizerOrAdmin]
    lookup_field = "slug"
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "event_submission"

    def get_queryset(self):
        return organizer_event_queryset(self.request.user)

    def post(self, request, *args, **kwargs):
        event = cancel_owned_event(
            event=self.get_object(),
            actor=request.user,
        )
        return Response(self.get_serializer(event).data)


class PendingEventModerationListView(generics.ListAPIView):
    serializer_class = OrganizerEventSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return (
            Event.objects.filter(moderation_status=Event.Status.PENDING_REVIEW)
            .select_related("category", "location", "source", "organizer")
            .prefetch_related("moderation_logs")
            .order_by("updated_at")
        )


class AdminEventActionView(generics.GenericAPIView):
    serializer_class = OrganizerEventSerializer
    permission_classes = [IsAdminRole]
    lookup_field = "slug"
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "event_moderation"
    queryset = Event.objects.select_related(
        "category",
        "location",
        "source",
        "organizer",
    ).prefetch_related("moderation_logs")


class AdminEventApproveView(AdminEventActionView):
    def post(self, request, *args, **kwargs):
        event = approve_event(event=self.get_object(), actor=request.user)
        return Response(self.get_serializer(event).data)


class AdminEventRejectView(AdminEventActionView):
    def post(self, request, *args, **kwargs):
        rejection = EventRejectionSerializer(data=request.data)
        rejection.is_valid(raise_exception=True)
        event = reject_event(
            event=self.get_object(),
            actor=request.user,
            reason=rejection.validated_data["reason"],
        )
        return Response(self.get_serializer(event).data)


class AdminEventArchiveView(AdminEventActionView):
    def post(self, request, *args, **kwargs):
        event = archive_event(
            event=self.get_object(),
            actor=request.user,
            is_admin=True,
        )
        return Response(self.get_serializer(event).data)


class AdminEventModerationLogListView(generics.ListAPIView):
    serializer_class = EventModerationLogSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None

    def get_queryset(self):
        event = get_object_or_404(Event, slug=self.kwargs["slug"])
        return event.moderation_logs.select_related("moderator").order_by("-created_at")


class EventViewSet(ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    search_fields = ("title", "description", "organizer_name", "location__city")
    filterset_fields = (
        "category__slug",
        "format",
        "is_free",
        "price_type",
        "scholarship_available",
        "language",
        "location__country",
        "location__city",
    )
    ordering_fields = ("starts_at", "deadline", "created_at")

    def get_queryset(self):
        queryset = Event.objects.select_related("category", "location", "source", "organizer")
        user = self.request.user
        if user.is_authenticated and user.is_admin_role:
            return queryset
        if user.is_authenticated and user.is_organizer and self.action not in {"list", "retrieve"}:
            return queryset.filter(organizer=user)

        queryset = queryset.filter(
            moderation_status=Event.Status.PUBLISHED,
            visibility=Event.Visibility.PUBLIC,
        )
        deadline_before = parse_datetime(self.request.query_params.get("deadline_before", ""))
        deadline_after = parse_datetime(self.request.query_params.get("deadline_after", ""))
        if deadline_before:
            queryset = queryset.filter(deadline__lte=deadline_before)
        if deadline_after:
            queryset = queryset.filter(deadline__gte=deadline_after)
        return queryset

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        if self.action == "create":
            return [IsOrganizerOrAdmin()]
        return [IsAdminOrReadOnly()]


User = get_user_model()


class AdminOrganizerListView(generics.ListAPIView):
    serializer_class = OrganizerModerationSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return (
            User.objects.filter(role=User.Role.ORGANIZER)
            .select_related("organizer_moderation")
            .annotate(event_count=Count("organized_events"))
            .order_by("email")
        )


class AdminOrganizerModerationActionView(generics.GenericAPIView):
    serializer_class = OrganizerModerationActionSerializer
    permission_classes = [IsAdminRole]

    def patch(self, request, *args, **kwargs):
        organizer = get_object_or_404(User, pk=kwargs["pk"], role=User.Role.ORGANIZER)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        record, _created = OrganizerModeration.objects.update_or_create(
            organizer=organizer,
            defaults={
                "status": data["status"],
                "reason": data.get("reason", ""),
                "reviewed_by": request.user,
                "reviewed_at": timezone.now(),
            },
        )
        track_event(
            user=request.user,
            event_type=AnalyticsEvent.EventType.ADMIN_MODERATION_ACTION,
            entity_type="organizer",
            entity_id=organizer.id,
            metadata={"status": data["status"]},
        )
        return Response(OrganizerModerationSerializer(organizer).data)
