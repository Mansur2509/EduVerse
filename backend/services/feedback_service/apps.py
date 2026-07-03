from django.apps import AppConfig


class FeedbackServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services.feedback_service"
    label = "feedback_service"
    verbose_name = "Feedback"
