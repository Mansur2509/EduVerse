from rest_framework import generics
from rest_framework.permissions import AllowAny

from common.permissions import IsAdminRole

from .models import FeedbackReport
from .serializers import FeedbackReportAdminSerializer, FeedbackReportCreateSerializer


class FeedbackReportCreateView(generics.CreateAPIView):
    """Public, write-only submission endpoint. Anonymous callers are allowed
    since the feedback modal is also reachable from the pre-auth login page.
    """

    serializer_class = FeedbackReportCreateSerializer
    permission_classes = [AllowAny]

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
