from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from services.activity_service.models import AnalyticsEvent
from services.feedback_service.models import UserReport
from services.notification_service.services import create_notification
from services.university_service.models import University

User = get_user_model()

STRONG_PASSWORD = "Strong-Development-Password-842!"


class ModerationAnalyticsIntegrationTests(APITestCase):
    """Phase 5: admin moderation actions (university/report/organizer) must
    each show up as an `admin_moderation_action` analytics event, and the
    admin feature-usage endpoint must surface them."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password=STRONG_PASSWORD,
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(self.admin)

    def test_admin_university_moderation_action_tracked_in_analytics(self):
        university = University.objects.create(
            slug="test-university",
            name="Test University",
            country="Demoland",
            city="Sample City",
            official_website="https://example.com/test-university",
            is_published=True,
        )
        response = self.client.patch(
            f"/api/admin/universities/{university.id}/moderation/",
            {"status": "verified", "issue_type": "admin_note"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.admin,
                event_type=AnalyticsEvent.EventType.ADMIN_MODERATION_ACTION,
                entity_type="university",
                entity_id=university.id,
            ).exists()
        )

    def test_admin_report_resolution_tracked_in_analytics(self):
        reporter = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password=STRONG_PASSWORD,
        )
        report = UserReport.objects.create(
            reporter=reporter,
            target_type=UserReport.TargetType.OTHER,
            target_id=1,
            reason="Inappropriate content",
        )
        response = self.client.patch(
            f"/api/admin/reports/{report.id}/", {"status": "resolved"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.admin,
                event_type=AnalyticsEvent.EventType.ADMIN_MODERATION_ACTION,
                entity_type="report",
                entity_id=report.id,
            ).exists()
        )

    def test_admin_organizer_moderation_tracked_in_analytics(self):
        organizer = User.objects.create_user(
            username="organizer@example.com",
            email="organizer@example.com",
            password=STRONG_PASSWORD,
            role=User.Role.ORGANIZER,
        )
        response = self.client.patch(
            f"/api/admin/organizers/{organizer.id}/moderation/",
            {"status": "approved"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.admin,
                event_type=AnalyticsEvent.EventType.ADMIN_MODERATION_ACTION,
                entity_type="organizer",
                entity_id=organizer.id,
            ).exists()
        )

    def test_admin_analytics_feature_usage_includes_moderation_events(self):
        university = University.objects.create(
            slug="test-university",
            name="Test University",
            country="Demoland",
            city="Sample City",
            official_website="https://example.com/test-university",
            is_published=True,
        )
        self.client.patch(
            f"/api/admin/universities/{university.id}/moderation/",
            {"status": "verified", "issue_type": "admin_note"},
            format="json",
        )
        response = self.client.get("/api/v1/admin/analytics/feature-usage/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("admin_moderation_action"), 1)


class NotificationAnalyticsIntegrationTests(APITestCase):
    """Phase 5: reading/archiving a notification must be tracked in analytics."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password=STRONG_PASSWORD,
        )
        self.client.force_authenticate(self.user)

    def test_marking_notification_read_tracked_in_analytics(self):
        notification = create_notification(
            user=self.user,
            notification_type="deadline_upcoming",
            title="Test notification",
            dedup_key="integration-test:1",
        )
        response = self.client.patch(
            f"/api/v1/notifications/{notification.id}/", {"status": "read"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.user,
                event_type=AnalyticsEvent.EventType.NOTIFICATION_READ,
                entity_id=notification.id,
            ).exists()
        )

    def test_archiving_notification_tracked_in_analytics(self):
        notification = create_notification(
            user=self.user,
            notification_type="deadline_upcoming",
            title="Test notification",
            dedup_key="integration-test:2",
        )
        response = self.client.patch(
            f"/api/v1/notifications/{notification.id}/", {"status": "archived"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=self.user,
                event_type=AnalyticsEvent.EventType.NOTIFICATION_ARCHIVED,
                entity_id=notification.id,
            ).exists()
        )
