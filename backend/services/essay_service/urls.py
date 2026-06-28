from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EssayRevisionTaskViewSet, EssayWorkspaceViewSet

app_name = "essays"

router = DefaultRouter()
router.register("revision-tasks", EssayRevisionTaskViewSet, basename="essay-revision-task")
router.register("", EssayWorkspaceViewSet, basename="essay-workspace")

urlpatterns = [
    path("", include(router.urls)),
]
