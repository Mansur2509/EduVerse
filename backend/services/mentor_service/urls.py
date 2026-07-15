from django.urls import path

from .views import (
    BlockMentorUserView,
    MentorBrowseView,
    MentorshipSessionListCreateView,
    MentorshipSessionStatusView,
)

app_name = "mentors"

urlpatterns = [
    path("", MentorBrowseView.as_view(), name="browse"),
    path("sessions/", MentorshipSessionListCreateView.as_view(), name="sessions"),
    path("sessions/<int:pk>/status/", MentorshipSessionStatusView.as_view(), name="session-status"),
    path("block/", BlockMentorUserView.as_view(), name="block"),
]
