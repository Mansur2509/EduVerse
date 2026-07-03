from django.urls import path

from .views import AdminFeedbackReportDetailView, AdminFeedbackReportListView

app_name = "admin-feedback"

urlpatterns = [
    path("", AdminFeedbackReportListView.as_view(), name="list"),
    path("<int:pk>/", AdminFeedbackReportDetailView.as_view(), name="detail"),
]
