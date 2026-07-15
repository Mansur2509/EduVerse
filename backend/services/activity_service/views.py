from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.demo_accounts import CANONICAL_STUDENT_DEMO_EMAIL
from common.permissions import IsAdminRole
from services.application_service.models import ApplicationTrackerItem
from services.essay_service.models import AIEssayScoreReport
from services.roadmap_service.models import RoadmapTask
from services.user_profile_service.models import StudentProfile
from services.user_profile_service.services import (
    calculate_profile_completion,
    get_profile_records_for_read,
)

from .models import AnalyticsEvent
from .serializers import AdminAnalyticsSummarySerializer, UserAnalyticsSerializer

User = get_user_model()

# Admin analytics are platform-wide aggregates, not tied to any one user's
# recent actions -- a short staleness window here is invisible to admins and
# meaningfully cuts down on ~10 COUNT queries recomputed from scratch on
# every dashboard load (PERFORMANCE-011 PART 7). No user_id in the key: this
# is intentionally global, shared-across-admins data.
ADMIN_ANALYTICS_CACHE_SECONDS = 90
ADMIN_ANALYTICS_SUMMARY_CACHE_KEY = "admin-analytics:summary"
ADMIN_ANALYTICS_FEATURE_USAGE_CACHE_KEY = "admin-analytics:feature-usage"
ADMIN_ANALYTICS_ACTIVITY_CACHE_KEY = "admin-analytics:activity"


class MyAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, preferences = get_profile_records_for_read(user)
        completion = calculate_profile_completion(profile, preferences)

        roadmap_tasks = RoadmapTask.objects.filter(user=user)
        applications = ApplicationTrackerItem.objects.filter(user=user)
        applications_by_status = dict(
            applications.values("status").annotate(count=Count("id")).values_list(
                "status", "count"
            )
        )
        upcoming_cutoff = timezone.now().date() + timedelta(days=30)
        upcoming_deadlines_count = applications.filter(
            deadline__isnull=False,
            deadline__gte=timezone.now().date(),
            deadline__lte=upcoming_cutoff,
        ).count()

        activity_by_type = dict(
            AnalyticsEvent.objects.filter(user=user)
            .values("event_type")
            .annotate(count=Count("id"))
            .values_list("event_type", "count")
        )

        data = {
            "profile_completion_percent": completion.percentage,
            "roadmap_tasks_completed": roadmap_tasks.filter(
                status=RoadmapTask.Status.COMPLETED
            ).count(),
            "roadmap_tasks_total": roadmap_tasks.count(),
            "applications_by_status": applications_by_status,
            "essay_reviews_count": AIEssayScoreReport.objects.filter(user=user).count(),
            "upcoming_deadlines_count": upcoming_deadlines_count,
            "activity_by_type": activity_by_type,
        }
        return Response(UserAnalyticsSerializer(data).data)


class AdminAnalyticsSummaryView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        payload = cache.get_or_set(
            ADMIN_ANALYTICS_SUMMARY_CACHE_KEY, self._compute, ADMIN_ANALYTICS_CACHE_SECONDS
        )
        return Response(payload)

    def _compute(self):
        now = timezone.now()
        since_7d = now - timedelta(days=7)
        since_30d = now - timedelta(days=30)

        # Platform-wide aggregates must reflect real usage, not this
        # project's own demo/QA traffic against the public canonical demo
        # account -- exclude it everywhere a user is counted or attributed.
        real_users = User.objects.exclude(email__iexact=CANONICAL_STUDENT_DEMO_EMAIL)
        real_events = AnalyticsEvent.objects.exclude(
            user__email__iexact=CANONICAL_STUDENT_DEMO_EMAIL
        )

        active_7d = (
            real_events.filter(created_at__gte=since_7d, user__isnull=False)
            .values("user_id")
            .distinct()
            .count()
        )
        active_30d = (
            real_events.filter(created_at__gte=since_30d, user__isnull=False)
            .values("user_id")
            .distinct()
            .count()
        )
        retained = (
            real_events.filter(user__isnull=False)
            .values("user_id")
            .annotate(count=Count("id"))
            .filter(count__gte=2)
            .count()
        )
        completed_onboarding = StudentProfile.objects.exclude(
            user__email__iexact=CANONICAL_STUDENT_DEMO_EMAIL
        ).filter(onboarding_completed_at__isnull=False).count()
        total_real_users = real_users.count()
        onboarding_completion_rate_percent = (
            round(completed_onboarding / total_real_users * 100, 1) if total_real_users else 0.0
        )

        data = {
            "total_users": total_real_users,
            "new_users_7d": real_users.filter(date_joined__gte=since_7d).count(),
            "new_users_30d": real_users.filter(date_joined__gte=since_30d).count(),
            "active_users_7d": active_7d,
            "active_users_30d": active_30d,
            "onboarding_completion_rate_percent": onboarding_completion_rate_percent,
            "applications_created_total": real_events.filter(
                event_type=AnalyticsEvent.EventType.APPLICATION_CREATED
            ).count(),
            "universities_shortlisted_total": real_events.filter(
                event_type=AnalyticsEvent.EventType.UNIVERSITY_SHORTLISTED
            ).count(),
            "essay_reviews_requested_total": real_events.filter(
                event_type=AnalyticsEvent.EventType.ESSAY_REVIEW_REQUESTED
            ).count(),
            "roadmap_generations_total": real_events.filter(
                event_type=AnalyticsEvent.EventType.ROADMAP_GENERATED
            ).count(),
            "event_registrations_total": real_events.filter(
                event_type=AnalyticsEvent.EventType.EVENT_REGISTERED
            ).count(),
            "organizer_events_created_total": real_events.filter(
                event_type=AnalyticsEvent.EventType.ORGANIZER_EVENT_CREATED
            ).count(),
            "retained_users_2plus_actions": retained,
        }
        return AdminAnalyticsSummarySerializer(data).data


class AdminAnalyticsFeatureUsageView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        payload = cache.get_or_set(
            ADMIN_ANALYTICS_FEATURE_USAGE_CACHE_KEY, self._compute, ADMIN_ANALYTICS_CACHE_SECONDS
        )
        return Response(payload)

    def _compute(self):
        counts = (
            AnalyticsEvent.objects.exclude(user__email__iexact=CANONICAL_STUDENT_DEMO_EMAIL)
            .values("event_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return {row["event_type"]: row["count"] for row in counts}


class AdminAnalyticsActivityView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        payload = cache.get_or_set(
            ADMIN_ANALYTICS_ACTIVITY_CACHE_KEY, self._compute, ADMIN_ANALYTICS_CACHE_SECONDS
        )
        return Response(payload)

    def _compute(self):
        since = timezone.now() - timedelta(days=30)
        rows = (
            AnalyticsEvent.objects.filter(created_at__gte=since)
            .exclude(user__email__iexact=CANONICAL_STUDENT_DEMO_EMAIL)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        daily_counts = {row["day"].isoformat(): row["count"] for row in rows}
        return {"daily_event_counts": daily_counts}
