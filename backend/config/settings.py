import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

from config.database_guard import validate_production_database

BASE_DIR = Path(__file__).resolve().parent.parent


def csv_env(name: str, default: str = "") -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key-change-before-deploy")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = csv_env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "common",
    "services.auth_service",
    "services.user_profile_service",
    "services.university_service",
    "services.event_service",
    "services.roadmap_service",
    "services.essay_service",
    "services.application_service",
    "services.suggestions_service",
    "services.profile_assessment_service",
    "services.ai_gateway_service",
    "services.exam_content_service",
    "services.finance_literacy_service",
    "services.subscription_service",
    "services.notification_service",
    "services.research_service",
    "services.activity_service",
    "services.feedback_service",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default="postgresql://uniway:change-me-for-local-development@localhost:5432/uniway",
        conn_max_age=60,
        conn_health_checks=True,
    )
}

# Fail loudly (ImproperlyConfigured) if production would start against a
# fallback/local database -- see config/database_guard.py for the rationale.
validate_production_database(
    debug=DEBUG,
    database_url=os.getenv("DATABASE_URL", ""),
    engine=DATABASES["default"]["ENGINE"],
)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "auth_service.User"

CORS_ALLOWED_ORIGINS = csv_env("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CSRF_TRUSTED_ORIGINS = csv_env("CSRF_TRUSTED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = True

SECURE_COOKIES = os.getenv("DJANGO_SECURE_COOKIES", "false").lower() == "true"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/hour",
        "user": "500/hour",
        "ai": "20/day",
        "ai_essay_score": "30/hour",
        "auth_login": "10/hour",
        "auth_register": "5/hour",
        "event_registration": "30/hour",
        "event_submission": "60/hour",
        "event_moderation": "120/hour",
        "university_import": "20/hour",
    },
}

# Beta-only fallback while no real background queue exists. Production should
# leave this false so admin uploads return immediately and process in a daemon
# thread instead of blocking gunicorn startup or the request path.
UNIVERSITY_IMPORT_RUN_INLINE = (
    os.getenv("UNIVERSITY_IMPORT_RUN_INLINE", "false").lower() == "true"
)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_PROFILE_ASSESSMENT_MODEL = os.getenv(
    "AI_PROFILE_ASSESSMENT_MODEL",
    "gemini-1.5-flash",
)
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "20"))
AI_MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "1200"))
AI_PROFILE_ASSESSMENT_ENABLED = (
    os.getenv("AI_PROFILE_ASSESSMENT_ENABLED", "false").lower() == "true"
)
AI_PROFILE_ASSESSMENT_DAILY_LIMIT = int(
    os.getenv("AI_PROFILE_ASSESSMENT_DAILY_LIMIT", "1")
)

# Essay scoring reuses GEMINI_API_KEY above; everything else is scoped to its
# own env vars so quota/model/timeout tuning never collides with profile
# assessment.
AI_ESSAY_SCORING_ENABLED = os.getenv("AI_ESSAY_SCORING_ENABLED", "false").lower() == "true"
AI_ESSAY_MODEL = os.getenv("AI_ESSAY_MODEL", "gemini-flash-latest")
AI_ESSAY_TIMEOUT_SECONDS = int(os.getenv("AI_ESSAY_TIMEOUT_SECONDS", "30"))
AI_ESSAY_MAX_OUTPUT_TOKENS = int(os.getenv("AI_ESSAY_MAX_OUTPUT_TOKENS", "2500"))
AI_ESSAY_TEMPERATURE = float(os.getenv("AI_ESSAY_TEMPERATURE", "0"))
AI_ESSAY_DAILY_FREE_LIMIT = int(os.getenv("AI_ESSAY_DAILY_FREE_LIMIT", "1"))
AI_ESSAY_BASIC_MONTHLY_LIMIT = int(os.getenv("AI_ESSAY_BASIC_MONTHLY_LIMIT", "10"))
AI_ESSAY_PREMIUM_MONTHLY_LIMIT = int(os.getenv("AI_ESSAY_PREMIUM_MONTHLY_LIMIT", "30"))
AI_ESSAY_PRO_MONTHLY_LIMIT = int(os.getenv("AI_ESSAY_PRO_MONTHLY_LIMIT", "100"))
