from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationPreferenceView,
    NotificationStatusUpdateView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("<int:pk>/", NotificationStatusUpdateView.as_view(), name="update-status"),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="mark-all-read"),
    path("preferences/", NotificationPreferenceView.as_view(), name="preferences"),
]
