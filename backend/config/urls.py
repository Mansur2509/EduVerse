from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from common.health import HealthView
from services.event_service.views import EventViewSet
from services.exam_content_service.views import ExamViewSet, QuestionViewSet
from services.subscription_service.views import SubscriptionViewSet
from services.university_service.views import UniversityViewSet
from services.user_profile_service.views import ProfileViewSet

router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("universities", UniversityViewSet, basename="university")
router.register("exams", ExamViewSet, basename="exam")
router.register("questions", QuestionViewSet, basename="question")
router.register("profiles", ProfileViewSet, basename="profile")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("services.auth_service.urls")),
    path("api/profile/", include("services.user_profile_service.urls")),
    path("api/events/", include("services.event_service.urls")),
    path("api/roadmap/", include("services.roadmap_service.urls")),
    path("api/essays/", include("services.essay_service.urls")),
    path("api/applications/", include("services.application_service.urls")),
    path("api/suggestions/", include("services.suggestions_service.urls")),
    path("api/organizer/", include("services.event_service.organizer_urls")),
    path("api/admin/events/", include("services.event_service.moderation_urls")),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/ai/", include("services.ai_gateway_service.urls")),
    path("api/v1/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
