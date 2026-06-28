from django.apps import AppConfig


class ApplicationServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services.application_service"
    label = "application_service"
    verbose_name = "Application tracker"
