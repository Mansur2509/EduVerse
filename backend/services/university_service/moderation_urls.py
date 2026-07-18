from django.urls import path

from .views import (
    AdminRecommendationDiagnosticsView,
    AdminUniversityModerationActionView,
    AdminUniversityReviewQueueView,
)

app_name = "university-moderation"

urlpatterns = [
    path("review-queue/", AdminUniversityReviewQueueView.as_view(), name="review-queue"),
    path(
        "<int:pk>/moderation/",
        AdminUniversityModerationActionView.as_view(),
        name="moderation-action",
    ),
    path(
        "<int:user_id>/recommendation-diagnostics/",
        AdminRecommendationDiagnosticsView.as_view(),
        name="recommendation-diagnostics",
    ),
]
