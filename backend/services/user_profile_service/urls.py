from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityViewSet,
    ApplicationReadinessView,
    CompleteOnboardingView,
    CurrentProfileView,
    EssayDraftViewSet,
    HonorViewSet,
    OlympiadViewSet,
    PortfolioProjectViewSet,
    ProfileCompletionView,
    RecommenderViewSet,
    ResearchProjectViewSet,
    SportViewSet,
    VolunteerViewSet,
)

app_name = "profile"

router = DefaultRouter()
router.register(r"activities", ActivityViewSet, basename="activity")
router.register(r"honors", HonorViewSet, basename="honor")
router.register(r"olympiads", OlympiadViewSet, basename="olympiad")
router.register(r"sports", SportViewSet, basename="sport")
router.register(r"research-projects", ResearchProjectViewSet, basename="research-project")
router.register(r"essays", EssayDraftViewSet, basename="essay")
router.register(r"portfolio-projects", PortfolioProjectViewSet, basename="portfolio-project")
router.register(r"volunteering", VolunteerViewSet, basename="volunteer")
router.register(r"recommenders", RecommenderViewSet, basename="recommender")

urlpatterns = [
    path("me/", CurrentProfileView.as_view(), name="me"),
    path("completion/", ProfileCompletionView.as_view(), name="completion"),
    path("complete-onboarding/", CompleteOnboardingView.as_view(), name="complete-onboarding"),
    path("readiness/", ApplicationReadinessView.as_view(), name="readiness"),
    path("", include(router.urls)),
]
