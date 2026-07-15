from django.db import IntegrityError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services.activity_service.models import AnalyticsEvent
from services.activity_service.services import track_event
from services.essay_service.models import EssayWorkspace
from services.essay_service.serializers import EssayWorkspaceSerializer
from services.university_service.recommendation_cache import invalidate_recommendation_caches
from services.university_service.services import calculate_university_fit
from services.user_profile_service.services import (
    ensure_profile_records,
    get_profile_records_for_read,
)

from .models import (
    ApplicationDocument,
    ApplicationMilestone,
    ApplicationRecommendation,
    ApplicationRequirement,
    ApplicationTrackerItem,
)
from .requirements import generate_default_requirements
from .serializers import (
    ApplicationDocumentSerializer,
    ApplicationMilestoneCreateSerializer,
    ApplicationMilestoneSerializer,
    ApplicationRecommendationSerializer,
    ApplicationRequirementCreateSerializer,
    ApplicationRequirementSerializer,
    ApplicationTrackerItemSerializer,
)
from .timeline import build_application_timeline


class ApplicationTrackerViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationTrackerItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("status", "university", "priority", "target_intake_year")

    def get_queryset(self):
        queryset = ApplicationTrackerItem.objects.filter(user=self.request.user)
        if self.request.query_params.get("include_archived") != "true":
            queryset = queryset.filter(archived_at__isnull=True)
        return (
            queryset
            .select_related("university", "target_program")
            .prefetch_related(
                "milestones",
                "requirements",
                "university__field_verifications",
                "university__data_sources",
            )
        )

    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request, pk=None):
        application = (
            self.get_queryset()
            .prefetch_related(
                "university__field_verifications",
                "university__scholarships",
                "roadmap_tasks",
            )
            .get(pk=self.get_object().pk)
        )
        profile, _ = get_profile_records_for_read(request.user)
        payload = build_application_timeline(
            application, profile, today=timezone.now().date()
        )
        return Response(payload)

    def perform_create(self, serializer):
        university = serializer.validated_data["university"]
        profile, _ = ensure_profile_records(self.request.user)
        fit = calculate_university_fit(profile, university)
        fit_tier = fit.get("category") or ApplicationTrackerItem.FitTier.UNKNOWN
        try:
            application = serializer.save(user=self.request.user, fit_tier=fit_tier)
        except IntegrityError as exc:
            raise ValidationError(
                {"university": "You already have an application tracker item for this university."}
            ) from exc
        track_event(
            user=self.request.user,
            event_type=AnalyticsEvent.EventType.APPLICATION_CREATED,
            entity_type="application",
            entity_id=application.id,
            metadata={
                "source": application.source,
                "fit_tier": application.fit_tier,
                "status": application.status,
            },
        )
        invalidate_recommendation_caches(self.request.user)

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        application = serializer.save()
        if application.status != previous_status:
            track_event(
                user=self.request.user,
                event_type=AnalyticsEvent.EventType.APPLICATION_STATUS_CHANGED,
                entity_type="application",
                entity_id=application.id,
                metadata={"from": previous_status, "to": application.status},
            )

    def perform_destroy(self, instance):
        instance.archived_at = timezone.now()
        instance.save(update_fields=("archived_at", "updated_at"))
        invalidate_recommendation_caches(self.request.user)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        application = (
            ApplicationTrackerItem.objects.filter(user=request.user, pk=pk)
            .select_related("university", "target_program")
            .prefetch_related(
                "milestones",
                "requirements",
                "university__field_verifications",
                "university__data_sources",
            )
            .first()
        )
        if application is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if ApplicationTrackerItem.objects.filter(
            user=request.user,
            university=application.university,
            archived_at__isnull=True,
        ).exclude(pk=application.pk).exists():
            raise ValidationError(
                {"university": "An active target already exists for this university."}
            )
        application.archived_at = None
        application.save(update_fields=("archived_at", "updated_at"))
        invalidate_recommendation_caches(request.user)
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["get", "post"], url_path="milestones")
    def milestones(self, request, pk=None):
        application = self.get_object()

        if request.method == "GET":
            milestones = application.milestones.all()
            return Response(ApplicationMilestoneSerializer(milestones, many=True).data)

        serializer = ApplicationMilestoneCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        milestone = serializer.save(application=application)
        return Response(
            ApplicationMilestoneSerializer(milestone).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get", "post"], url_path="requirements")
    def requirements(self, request, pk=None):
        application = self.get_object()

        if request.method == "GET":
            items = application.requirements.all()
            return Response(ApplicationRequirementSerializer(items, many=True).data)

        serializer = ApplicationRequirementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.validated_data.get("order") or application.requirements.count()
        requirement = serializer.save(
            application=application,
            source=ApplicationRequirement.Source.USER_CREATED,
            order=order,
        )
        return Response(
            ApplicationRequirementSerializer(requirement).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="generate-requirements")
    def generate_requirements_action(self, request, pk=None):
        application = self.get_object()
        requirements = generate_default_requirements(application)
        return Response(ApplicationRequirementSerializer(requirements, many=True).data)

    @action(detail=True, methods=["get", "post"], url_path="recommendations")
    def recommendation_requests(self, request, pk=None):
        application = self.get_object()

        if request.method == "GET":
            items = application.recommendation_requests.select_related("recommender").all()
            return Response(ApplicationRecommendationSerializer(items, many=True).data)

        serializer = ApplicationRecommendationSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        recommendation = serializer.save(application=application)
        return Response(
            ApplicationRecommendationSerializer(recommendation).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get", "post"], url_path="documents")
    def documents(self, request, pk=None):
        application = self.get_object()

        if request.method == "GET":
            items = application.documents.all()
            return Response(ApplicationDocumentSerializer(items, many=True).data)

        serializer = ApplicationDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save(application=application)
        return Response(
            ApplicationDocumentSerializer(document).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get", "post"], url_path="essays")
    def essays(self, request, pk=None):
        application = self.get_object()

        if request.method == "GET":
            items = EssayWorkspace.objects.filter(user=request.user, application=application)
            return Response(EssayWorkspaceSerializer(items, many=True).data)

        data = request.data.copy()
        data["application"] = application.pk
        serializer = EssayWorkspaceSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        essay = serializer.save(user=request.user)
        return Response(EssayWorkspaceSerializer(essay).data, status=status.HTTP_201_CREATED)


class ApplicationMilestoneViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ApplicationMilestoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ApplicationMilestone.objects.filter(application__user=self.request.user)


class ApplicationRequirementViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ApplicationRequirementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ApplicationRequirement.objects.filter(application__user=self.request.user)


class ApplicationRecommendationViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ApplicationRecommendationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ApplicationRecommendation.objects.filter(application__user=self.request.user)


class ApplicationDocumentViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ApplicationDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ApplicationDocument.objects.filter(application__user=self.request.user)
