from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from common.permissions import IsAdminRole
from common.throttling import ScopedIPRateThrottle
from services.activity_service.models import AnalyticsEvent
from services.activity_service.services import track_event

from .models import FeedbackReport, UserReport
from .serializers import (
    FeedbackReportAdminSerializer,
    FeedbackReportCreateSerializer,
    UserReportAdminSerializer,
    UserReportCreateSerializer,
)


class FeedbackReportCreateView(generics.CreateAPIView):
    """Public, write-only submission endpoint. Anonymous callers are allowed
    since the feedback modal is also reachable from the pre-auth login page.
    """

    serializer_class = FeedbackReportCreateSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "feedback_submit"

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(
            user=user,
            user_agent=self.request.META.get("HTTP_USER_AGENT", "")[:300],
        )


class AdminFeedbackReportListView(generics.ListAPIView):
    serializer_class = FeedbackReportAdminSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = {
        "status": ["exact"],
        "feedback_type": ["exact"],
        "priority": ["exact"],
        "page_module": ["exact"],
    }
    ordering_fields = ("created_at", "priority", "status")
    ordering = ("-created_at",)
    queryset = FeedbackReport.objects.select_related("user").all()


class AdminFeedbackReportDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = FeedbackReportAdminSerializer
    permission_classes = [IsAdminRole]
    queryset = FeedbackReport.objects.select_related("user").all()


class UserReportCreateView(generics.CreateAPIView):
    serializer_class = UserReportCreateSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle, ScopedIPRateThrottle]
    throttle_scope = "report_submit"

    def perform_create(self, serializer):
        report = serializer.save(reporter=self.request.user)
        track_event(
            user=self.request.user,
            event_type=AnalyticsEvent.EventType.REPORT_SUBMITTED,
            entity_type=report.target_type,
            entity_id=report.target_id,
        )


class AdminUserReportListView(generics.ListAPIView):
    serializer_class = UserReportAdminSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = {"status": ["exact"], "target_type": ["exact"]}
    ordering_fields = ("created_at", "status")
    ordering = ("-created_at",)
    queryset = UserReport.objects.select_related("reporter").all()


class AdminUserReportDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserReportAdminSerializer
    permission_classes = [IsAdminRole]
    queryset = UserReport.objects.select_related("reporter").all()

    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        terminal_statuses = {UserReport.Status.RESOLVED, UserReport.Status.DISMISSED}
        if new_status in terminal_statuses and self.get_object().status not in terminal_statuses:
            report = serializer.save(resolved_at=timezone.now())
        else:
            report = serializer.save()
        track_event(
            user=self.request.user,
            event_type=AnalyticsEvent.EventType.ADMIN_MODERATION_ACTION,
            entity_type="report",
            entity_id=report.id,
            metadata={"status": report.status},
        )
