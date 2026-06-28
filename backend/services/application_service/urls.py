from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ApplicationMilestoneViewSet, ApplicationTrackerViewSet

app_name = "applications"

router = DefaultRouter()
router.register("milestones", ApplicationMilestoneViewSet, basename="application-milestone")
router.register("", ApplicationTrackerViewSet, basename="application")

urlpatterns = [
    path("", include(router.urls)),
]
