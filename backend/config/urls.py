from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from common.health import HealthView
from services.event_service.views import EventViewSet
from services.exam_content_service.views import (
    ExamViewSet,
    OfficialExamDateViewSet,
    QuestionViewSet,
)
from services.profile_assessment_service.views import (
    LatestProfileAssessmentView,
    ProfileRecommendationsView,
    ProfileStrategyView,
    RunProfileAssessmentView,
)
from services.roadmap_service.views import GenerateRoadmapView, RoadmapPlanView, RoadmapTaskViewSet
from services.subscription_service.views import SubscriptionViewSet
from services.university_service.views import UniversityViewSet
from services.user_profile_service.views import ProfileViewSet

router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("universities", UniversityViewSet, basename="university")
router.register("exams", ExamViewSet, basename="exam")
router.register("exam-dates", OfficialExamDateViewSet, basename="exam-date")
router.register("questions", QuestionViewSet, basename="question")
router.register("profiles", ProfileViewSet, basename="profile")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("roadmaps/tasks", RoadmapTaskViewSet, basename="roadmap-task-v1")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("services.auth_service.urls")),
    path("api/profile/", include("services.user_profile_service.urls")),
    path("api/events/", include("services.event_service.urls")),
    path("api/roadmap/", include("services.roadmap_service.urls")),
    path("api/essays/", include("services.essay_service.urls")),
    path("api/applications/", include("services.application_service.urls")),
    path("api/suggestions/", include("services.suggestions_service.urls")),
    path("api/profile/assessment/", include("services.profile_assessment_service.urls")),
    path("api/organizer/", include("services.event_service.organizer_urls")),
    path("api/admin/events/", include("services.event_service.moderation_urls")),
    path("api/admin/users/", include("services.profile_assessment_service.admin_urls")),
    path("api/admin/university-import/", include("services.university_service.import_urls")),
    path("api/admin/universities/", include("services.university_service.moderation_urls")),
    path("api/admin/organizers/", include("services.event_service.organizer_moderation_urls")),
    path("api/feedback/", include("services.feedback_service.urls")),
    path("api/admin/feedback/", include("services.feedback_service.admin_urls")),
    path("api/reports/", include("services.feedback_service.reports_urls")),
    path("api/admin/reports/", include("services.feedback_service.admin_reports_urls")),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/ai/", include("services.ai_gateway_service.urls")),
    # PROTOCOL-008 PART 7: additive `/api/v1/` paths reusing the same cached-
    # assessment views/service functions as the existing `/api/profile/
    # assessment/latest|run/` routes above -- the old paths are untouched.
    path(
        "api/v1/profile-assessment/me/",
        LatestProfileAssessmentView.as_view(),
        name="profile-assessment-me",
    ),
    path(
        "api/v1/profile-assessment/refresh/",
        RunProfileAssessmentView.as_view(),
        name="profile-assessment-refresh",
    ),
    path("api/v1/recommendations/me/", ProfileRecommendationsView.as_view(), name="recommendations-me"),
    path("api/v1/strategy/me/", ProfileStrategyView.as_view(), name="strategy-me"),
    # Additive `/api/v1/roadmaps/*` paths reusing the same views as the
    # existing `/api/roadmap/` routes above -- the old paths are untouched.
    path("api/v1/roadmaps/me/", RoadmapPlanView.as_view(), name="roadmaps-me"),
    path("api/v1/roadmaps/generate/", GenerateRoadmapView.as_view(), name="roadmaps-generate"),
    path("api/v1/analytics/", include("services.activity_service.urls")),
    path("api/v1/admin/analytics/", include("services.activity_service.admin_urls")),
    path("api/v1/notifications/", include("services.notification_service.urls")),
    path("api/v1/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
