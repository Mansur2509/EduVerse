from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from services.activity_service.models import AnalyticsEvent
from services.activity_service.services import track_event

from .models import (
    Activity,
    EssayDraft,
    Honor,
    Olympiad,
    PortfolioProject,
    Recommender,
    ResearchProject,
    Sport,
    StudentProfile,
    Volunteer,
)
from .serializers import (
    ActivitySerializer,
    ApplicationReadinessSerializer,
    EssayDraftSerializer,
    HonorSerializer,
    OlympiadSerializer,
    PortfolioProjectSerializer,
    ProfileCompletionSerializer,
    ProfileSerializer,
    RecommenderSerializer,
    ResearchProjectSerializer,
    SportSerializer,
    VolunteerSerializer,
)
from .services import (
    calculate_profile_completion,
    ensure_profile_records,
    get_profile_records_for_read,
)


class CurrentProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get_profile(self, request, *, for_update=False):
        records = ensure_profile_records if for_update else get_profile_records_for_read
        profile, _ = records(request.user)
        return profile

    def get(self, request):
        return Response(ProfileSerializer(self.get_profile(request)).data)

    def patch(self, request):
        profile = self.get_profile(request, for_update=True)
        is_still_onboarding = profile.onboarding_completed_at is None
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        track_event(user=request.user, event_type=AnalyticsEvent.EventType.PROFILE_UPDATED)
        if is_still_onboarding and not AnalyticsEvent.objects.filter(
            user=request.user, event_type=AnalyticsEvent.EventType.ONBOARDING_STARTED
        ).exists():
            track_event(user=request.user, event_type=AnalyticsEvent.EventType.ONBOARDING_STARTED)
        return Response(ProfileSerializer(profile).data)


class ProfileCompletionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = get_profile_records_for_read(request.user)
        return Response(ProfileCompletionSerializer.for_profile(profile).data)


class CompleteOnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, preferences = ensure_profile_records(request.user)
        completion = calculate_profile_completion(profile, preferences)
        if not completion.can_complete:
            return Response(
                {
                    "detail": "Complete all required onboarding fields and sections.",
                    "missing_fields": completion.missing_fields,
                    "missing_sections": completion.missing_sections,
                },
                status=400,
            )

        if profile.onboarding_completed_at is None:
            profile.onboarding_completed_at = timezone.now()
            profile.save(update_fields=["onboarding_completed_at", "updated_at"])
            track_event(user=request.user, event_type=AnalyticsEvent.EventType.ONBOARDING_COMPLETED)
        return Response(ProfileCompletionSerializer.for_profile(profile).data)


class ApplicationReadinessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = get_profile_records_for_read(request.user)
        return Response(ApplicationReadinessSerializer.for_profile(profile).data)


class ProfileViewSet(
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = StudentProfile.objects.select_related("user")

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        if request.method == "PATCH":
            profile, _ = ensure_profile_records(request.user)
        else:
            profile, _ = get_profile_records_for_read(request.user)
        if request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            profile = serializer.save()
            track_event(user=request.user, event_type=AnalyticsEvent.EventType.PROFILE_UPDATED)
        return Response(self.get_serializer(profile).data)


# Base class for profile item viewsets (self-only access)
class ProfileItemViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ActivityViewSet(ProfileItemViewSet):
    serializer_class = ActivitySerializer
    queryset = Activity.objects.all()


class HonorViewSet(ProfileItemViewSet):
    serializer_class = HonorSerializer
    queryset = Honor.objects.all()


class OlympiadViewSet(ProfileItemViewSet):
    serializer_class = OlympiadSerializer
    queryset = Olympiad.objects.all()


class SportViewSet(ProfileItemViewSet):
    serializer_class = SportSerializer
    queryset = Sport.objects.all()


class ResearchProjectViewSet(ProfileItemViewSet):
    serializer_class = ResearchProjectSerializer
    queryset = ResearchProject.objects.all()


class EssayDraftViewSet(ProfileItemViewSet):
    serializer_class = EssayDraftSerializer
    queryset = EssayDraft.objects.all()


class PortfolioProjectViewSet(ProfileItemViewSet):
    serializer_class = PortfolioProjectSerializer
    queryset = PortfolioProject.objects.all()


class VolunteerViewSet(ProfileItemViewSet):
    serializer_class = VolunteerSerializer
    queryset = Volunteer.objects.all()


class RecommenderViewSet(ProfileItemViewSet):
    serializer_class = RecommenderSerializer
    queryset = Recommender.objects.all()
