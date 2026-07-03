from django.urls import path

from .views import FeedbackReportCreateView

app_name = "feedback"

urlpatterns = [
    path("", FeedbackReportCreateView.as_view(), name="create"),
]
