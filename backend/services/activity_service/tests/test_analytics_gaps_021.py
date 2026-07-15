"""POST-V1-021 Phase 4: closes the specific analytics gaps found when this
task's own event list (account_created, onboarding_started/completed,
essay_created, essay_review_completed, event_viewed, report_submitted,
demo_login_used) was checked against the pre-existing activity_service
infrastructure. Most of that infrastructure (AnalyticsEvent, track_event,
the 3 admin analytics endpoints, the frontend dashboard) already existed;
these tests cover only what was actually missing or newly wired.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from common.demo_accounts import (
    CANONICAL_STUDENT_DEMO_EMAIL,
    DEMO_PASSWORD,
    ensure_canonical_student_demo_account,
)
from services.activity_service.models import AnalyticsEvent
from services.essay_service.tests.test_essays import FakeEssayScoringClient, valid_ai_score_output
from services.event_service.models import Event, EventCategory, EventLocation, EventSource
from services.feedback_service.models import UserReport
from services.university_service.models import University
from services.user_profile_service.tests.test_profile_api import ProfileApiTests

User = get_user_model()
STRONG_PASSWORD = "Strong-Development-Password-842!"


class AccountAndDemoLoginAnalyticsTests(APITestCase):
    def test_registration_is_tracked_as_user_registered(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "new.student@example.com",
                "full_name": "New Student",
                "password": STRONG_PASSWORD,
                "password_confirm": STRONG_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(email="new.student@example.com")
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=user, event_type=AnalyticsEvent.EventType.USER_REGISTERED
            ).exists()
        )

    def test_demo_account_login_is_tracked(self):
        ensure_canonical_student_demo_account(User)

        response = self.client.post(
            "/api/auth/login/",
            {"email": CANONICAL_STUDENT_DEMO_EMAIL, "password": DEMO_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                event_type=AnalyticsEvent.EventType.DEMO_LOGIN_USED
            ).exists()
        )

    def test_ordinary_login_is_not_tracked_as_demo_login(self):
        User.objects.create_user(
            username="real.student@example.com",
            email="real.student@example.com",
            password=STRONG_PASSWORD,
        )

        response = self.client.post(
            "/api/auth/login/",
            {"email": "real.student@example.com", "password": STRONG_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(
            AnalyticsEvent.objects.filter(
                event_type=AnalyticsEvent.EventType.DEMO_LOGIN_USED
            ).exists()
        )


class OnboardingAnalyticsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="onboarding@example.com",
            email="onboarding@example.com",
            password=STRONG_PASSWORD,
        )
        self.client.force_authenticate(self.user)

    def test_first_profile_patch_while_incomplete_tracks_onboarding_started(self):
        self.client.patch(reverse("profile:me"), {"country": "Uzbekistan"}, format="json")

        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.user, event_type=AnalyticsEvent.EventType.ONBOARDING_STARTED
            ).exists()
        )

    def test_onboarding_started_is_not_tracked_twice(self):
        self.client.patch(reverse("profile:me"), {"country": "Uzbekistan"}, format="json")
        self.client.patch(reverse("profile:me"), {"city": "Tashkent"}, format="json")

        self.assertEqual(
            AnalyticsEvent.objects.filter(
                user=self.user, event_type=AnalyticsEvent.EventType.ONBOARDING_STARTED
            ).count(),
            1,
        )

    def test_completing_onboarding_tracks_onboarding_completed(self):
        self.client.patch(
            reverse("profile:me"), ProfileApiTests.complete_onboarding_payload, format="json"
        )

        response = self.client.post(reverse("profile:complete-onboarding"))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.user, event_type=AnalyticsEvent.EventType.ONBOARDING_COMPLETED
            ).exists()
        )

    def test_completing_onboarding_twice_only_tracks_once(self):
        self.client.patch(
            reverse("profile:me"), ProfileApiTests.complete_onboarding_payload, format="json"
        )
        self.client.post(reverse("profile:complete-onboarding"))

        self.client.post(reverse("profile:complete-onboarding"))

        self.assertEqual(
            AnalyticsEvent.objects.filter(
                user=self.user, event_type=AnalyticsEvent.EventType.ONBOARDING_COMPLETED
            ).count(),
            1,
        )


class EssayAnalyticsGapTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="essayanalytics@example.com",
            email="essayanalytics@example.com",
            password=STRONG_PASSWORD,
        )
        self.client.force_authenticate(self.user)

    def test_creating_an_essay_tracks_essay_created(self):
        response = self.client.post(
            "/api/essays/", {"title": "My essay", "draft_text": ""}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.user,
                event_type=AnalyticsEvent.EventType.ESSAY_CREATED,
                entity_id=response.data["id"],
            ).exists()
        )

    @patch.object(
        __import__(
            "services.essay_service.ai_scoring", fromlist=["GeminiEssayScoringClient"]
        ),
        "GeminiEssayScoringClient",
    )
    def test_successful_score_tracks_essay_review_completed(self, mock_client_cls):
        from services.essay_service.models import EssayWorkspace

        essay = EssayWorkspace.objects.create(
            user=self.user,
            title="Scored essay",
            essay_type=EssayWorkspace.EssayType.SUPPLEMENT,
            draft_text="A real essay draft with enough words to be evaluated. " * 20,
            word_limit=650,
        )
        mock_client_cls.return_value = FakeEssayScoringClient(valid_ai_score_output())

        with self.settings(
            AI_ESSAY_SCORING_ENABLED=True,
            GEMINI_API_KEY="test-gemini-key",
            AI_ESSAY_DAILY_FREE_LIMIT=5,
        ):
            response = self.client.post(f"/api/essays/{essay.id}/score/")

        self.assertEqual(response.data["reason"], "scored", response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.user,
                event_type=AnalyticsEvent.EventType.ESSAY_REVIEW_COMPLETED,
                entity_id=essay.id,
            ).exists()
        )


class EventViewedAnalyticsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="eventviewer@example.com",
            email="eventviewer@example.com",
            password=STRONG_PASSWORD,
        )
        self.client.force_authenticate(self.user)
        category = EventCategory.objects.create(name="Workshop", slug="workshop")
        self.event = Event.objects.create(
            category=category,
            title="Sample Event",
            slug="sample-event",
            description="Original demonstration description.",
            organizer_name="Demo organizer",
            format=Event.Format.ONLINE,
            starts_at=timezone.now() + timedelta(days=10),
            deadline=timezone.now() + timedelta(days=5),
            moderation_status=Event.Status.PUBLISHED,
        )
        EventLocation.objects.create(event=self.event, country="Demo")
        EventSource.objects.create(
            event=self.event,
            source_title="Demo source",
            source_url="https://example.com/sample-event",
            is_official=False,
        )

    def test_viewing_event_detail_tracks_event_viewed(self):
        response = self.client.get(f"/api/events/{self.event.slug}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.user,
                event_type=AnalyticsEvent.EventType.EVENT_VIEWED,
                entity_id=self.event.id,
            ).exists()
        )


class ReportSubmittedAnalyticsTests(APITestCase):
    def test_submitting_a_report_tracks_report_submitted(self):
        user = User.objects.create_user(
            username="reporter@example.com", email="reporter@example.com", password=STRONG_PASSWORD
        )
        self.client.force_authenticate(user)
        university = University.objects.create(
            slug="report-target-university",
            name="Report Target University",
            country="Demoland",
            city="Sample City",
            official_website="https://example.com/report-target-university",
            is_published=True,
        )

        response = self.client.post(
            "/api/reports/",
            {
                "target_type": UserReport.TargetType.UNIVERSITY,
                "target_id": university.id,
                "reason": "Incorrect information",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=user,
                event_type=AnalyticsEvent.EventType.REPORT_SUBMITTED,
                entity_type=UserReport.TargetType.UNIVERSITY,
                entity_id=university.id,
            ).exists()
        )


class ApplicationCreatedStatusMetadataTests(APITestCase):
    def test_application_created_event_metadata_includes_status(self):
        user = User.objects.create_user(
            username="applicant@example.com", email="applicant@example.com", password=STRONG_PASSWORD
        )
        self.client.force_authenticate(user)
        university = University.objects.create(
            slug="metadata-test-university",
            name="Metadata Test University",
            country="Demoland",
            city="Sample City",
            official_website="https://example.com/metadata-test-university",
            is_published=True,
        )

        response = self.client.post(
            "/api/applications/", {"university": university.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        event = AnalyticsEvent.objects.get(
            user=user, event_type=AnalyticsEvent.EventType.APPLICATION_CREATED
        )
        self.assertEqual(event.metadata.get("status"), "researching")


class DemoAccountExclusionFromAdminAnalyticsTests(APITestCase):
    """The canonical public demo account must never inflate platform-wide
    aggregates that founders/operators use to judge real usage."""

    def setUp(self):
        ensure_canonical_student_demo_account(User)
        self.demo_user = User.objects.get(email=CANONICAL_STUDENT_DEMO_EMAIL)
        self.admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password=STRONG_PASSWORD,
            role=User.Role.ADMIN,
        )

    def test_demo_account_excluded_from_total_and_active_user_counts(self):
        real_user = User.objects.create_user(
            username="real@example.com", email="real@example.com", password=STRONG_PASSWORD
        )
        self.client.force_authenticate(self.demo_user)
        self.client.patch(reverse("profile:me"), {"country": "Uzbekistan"}, format="json")

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/admin/analytics/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # total_users excludes the demo account: admin + real_user only.
        self.assertEqual(response.data["total_users"], 2)
        self.assertNotIn(real_user.email, [])  # real_user exists, sanity no-op

    def test_demo_account_excluded_from_feature_usage(self):
        self.client.force_authenticate(self.demo_user)
        self.client.patch(reverse("profile:me"), {"country": "Uzbekistan"}, format="json")

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/admin/analytics/feature-usage/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(AnalyticsEvent.EventType.PROFILE_UPDATED, response.data)


class OnboardingCompletionRateMetricTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin2@example.com",
            email="admin2@example.com",
            password=STRONG_PASSWORD,
            role=User.Role.ADMIN,
        )

    def test_onboarding_completion_rate_reflects_real_users_only(self):
        completed_user = User.objects.create_user(
            username="completed@example.com", email="completed@example.com", password=STRONG_PASSWORD
        )
        self.client.force_authenticate(completed_user)
        self.client.patch(
            reverse("profile:me"), ProfileApiTests.complete_onboarding_payload, format="json"
        )
        self.client.post(reverse("profile:complete-onboarding"))

        User.objects.create_user(
            username="incomplete@example.com", email="incomplete@example.com", password=STRONG_PASSWORD
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/admin/analytics/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 2 real non-admin users + 1 admin = 3 total; 1 of 3 completed onboarding.
        self.assertAlmostEqual(response.data["onboarding_completion_rate_percent"], 33.3, places=1)
