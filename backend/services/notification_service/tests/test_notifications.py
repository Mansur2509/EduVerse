from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from services.application_service.models import ApplicationRecommendation, ApplicationTrackerItem
from services.essay_service.models import AIEssayScoreReport, EssayWorkspace
from services.event_service.models import Event, EventCategory, EventRegistration
from services.event_service.services import approve_event, register_for_event, reject_event
from services.notification_service.models import Notification, NotificationPreference
from services.notification_service.services import (
    create_notification,
    generate_deadline_notifications,
    generate_essay_missing_notifications,
    generate_event_starting_soon_notifications,
    generate_exam_date_notifications,
    generate_recommendation_missing_notifications,
    generate_roadmap_task_notifications,
)
from services.roadmap_service.models import RoadmapPlan, RoadmapTask
from services.university_service.models import University
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()

STRONG_PASSWORD = "Strong-Development-Password-842!"


def create_university(slug="test-university", **overrides):
    defaults = {
        "name": "Test University",
        "country": "Demoland",
        "city": "Sample City",
        "official_website": f"https://example.com/{slug}",
        "is_published": True,
    }
    defaults.update(overrides)
    return University.objects.create(slug=slug, **defaults)


def create_user(email="student@example.com", **overrides):
    defaults = {"username": email, "email": email, "password": STRONG_PASSWORD}
    defaults.update(overrides)
    password = defaults.pop("password")
    user = User.objects.create_user(**defaults, password=password)
    return user


class CreateNotificationTests(APITestCase):
    def setUp(self):
        self.user = create_user()

    def test_dedup_key_prevents_duplicate_creation(self):
        first = create_notification(
            user=self.user,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Test",
            dedup_key="dedup:1",
        )
        second = create_notification(
            user=self.user,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Test again",
            dedup_key="dedup:1",
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_opted_out_preference_blocks_creation(self):
        preference = NotificationPreference.objects.create(user=self.user, deadlines_enabled=False)
        notification = create_notification(
            user=self.user,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Should not be created",
            dedup_key="dedup:opted-out",
        )
        self.assertIsNone(notification)
        self.assertEqual(Notification.objects.count(), 0)
        preference.refresh_from_db()
        self.assertFalse(preference.deadlines_enabled)


class GenerateDeadlineNotificationsTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.university = create_university()

    def _application(self, **overrides):
        defaults = {"user": self.user, "university": self.university}
        defaults.update(overrides)
        return ApplicationTrackerItem.objects.create(**defaults)

    def test_creates_notification_at_seven_day_threshold(self):
        deadline = timezone.now().date() + timedelta(days=7)
        application = self._application(deadline=deadline)
        created = generate_deadline_notifications()
        self.assertEqual(created, 1)
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.notification_type, Notification.NotificationType.DEADLINE_UPCOMING)
        self.assertEqual(notification.related_entity_id, application.id)
        self.assertEqual(notification.priority, Notification.Priority.HIGH)

    def test_no_notification_outside_threshold_days(self):
        self._application(deadline=timezone.now().date() + timedelta(days=8))
        created = generate_deadline_notifications()
        self.assertEqual(created, 0)

    def test_skips_closed_applications(self):
        self._application(
            deadline=timezone.now().date() + timedelta(days=1),
            status=ApplicationTrackerItem.Status.ACCEPTED,
        )
        created = generate_deadline_notifications()
        self.assertEqual(created, 0)

    def test_rerunning_generator_does_not_duplicate(self):
        self._application(deadline=timezone.now().date() + timedelta(days=1))
        generate_deadline_notifications()
        second_run_created = generate_deadline_notifications()
        self.assertEqual(second_run_created, 0)
        self.assertEqual(Notification.objects.count(), 1)


class GenerateRoadmapTaskNotificationsTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.plan = RoadmapPlan.objects.create(user=self.user, title="My roadmap")

    def test_creates_notification_for_task_due_soon(self):
        RoadmapTask.objects.create(
            user=self.user,
            plan=self.plan,
            title="Request letters",
            category=RoadmapTask.Category.RECOMMENDATIONS,
            due_date=timezone.now().date() + timedelta(days=1),
            dedup_key="manual:1",
        )
        created = generate_roadmap_task_notifications()
        self.assertEqual(created, 1)
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.notification_type, Notification.NotificationType.ROADMAP_TASK_DUE_SOON)

    def test_completed_task_is_excluded(self):
        RoadmapTask.objects.create(
            user=self.user,
            plan=self.plan,
            title="Request letters",
            category=RoadmapTask.Category.RECOMMENDATIONS,
            due_date=timezone.now().date() + timedelta(days=1),
            status=RoadmapTask.Status.COMPLETED,
            dedup_key="manual:2",
        )
        created = generate_roadmap_task_notifications()
        self.assertEqual(created, 0)


class GenerateEssayMissingNotificationsTests(APITestCase):
    def setUp(self):
        self.user = create_user()

    def _essay(self, **overrides):
        defaults = {
            "user": self.user,
            "title": "Common App essay",
            "due_date": timezone.now().date() + timedelta(days=7),
        }
        defaults.update(overrides)
        return EssayWorkspace.objects.create(**defaults)

    def test_creates_notification_for_unfinished_essay(self):
        essay = self._essay(status=EssayWorkspace.Status.DRAFTING)
        created = generate_essay_missing_notifications()
        self.assertEqual(created, 1)
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.related_entity_id, essay.id)

    def test_submitted_essay_is_excluded(self):
        self._essay(status=EssayWorkspace.Status.SUBMITTED)
        created = generate_essay_missing_notifications()
        self.assertEqual(created, 0)


class GenerateRecommendationMissingNotificationsTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.university = create_university()
        self.application = ApplicationTrackerItem.objects.create(user=self.user, university=self.university)

    def test_creates_notification_for_unsubmitted_recommendation(self):
        recommendation = ApplicationRecommendation.objects.create(
            application=self.application,
            recommender_name="Ms. Rivera",
            status=ApplicationRecommendation.Status.REQUESTED,
            due_date=timezone.now().date() + timedelta(days=1),
        )
        created = generate_recommendation_missing_notifications()
        self.assertEqual(created, 1)
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.related_entity_id, recommendation.id)

    def test_submitted_recommendation_is_excluded(self):
        ApplicationRecommendation.objects.create(
            application=self.application,
            recommender_name="Ms. Rivera",
            status=ApplicationRecommendation.Status.SUBMITTED,
            due_date=timezone.now().date() + timedelta(days=1),
        )
        created = generate_recommendation_missing_notifications()
        self.assertEqual(created, 0)


class GenerateExamDateNotificationsTests(APITestCase):
    def setUp(self):
        self.user = create_user()

    def test_creates_notification_for_planned_exam_at_threshold(self):
        profile, _ = ensure_profile_records(self.user)
        exam_date = (timezone.now().date() + timedelta(days=30)).isoformat()
        profile.exam_plans = {"planned": [{"name": "SAT", "date": exam_date, "target_score": "1500"}]}
        profile.save(update_fields=["exam_plans"])

        created = generate_exam_date_notifications()
        self.assertEqual(created, 1)
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.notification_type, Notification.NotificationType.EXAM_DATE_UPCOMING)

    def test_malformed_exam_entry_is_skipped_without_error(self):
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {"planned": [{"name": "SAT"}]}
        profile.save(update_fields=["exam_plans"])

        created = generate_exam_date_notifications()
        self.assertEqual(created, 0)


class GenerateEventStartingSoonNotificationsTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.category = EventCategory.objects.create(name="Workshop", slug="workshop")

    def _event(self, **overrides):
        defaults = {
            "category": self.category,
            "title": "Sample Workshop",
            "slug": "sample-workshop",
            "description": "A workshop.",
            "organizer_name": "Test Organizer",
            "format": Event.Format.OFFLINE,
            "starts_at": timezone.now() + timedelta(days=1),
            "moderation_status": Event.Status.PUBLISHED,
        }
        defaults.update(overrides)
        return Event.objects.create(**defaults)

    def test_creates_notification_for_registered_user(self):
        event = self._event()
        registration = EventRegistration.objects.create(
            user=self.user, event=event, status=EventRegistration.Status.REGISTERED
        )
        created = generate_event_starting_soon_notifications()
        self.assertEqual(created, 1)
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.related_entity_id, event.id)
        self.assertIn(event.slug, notification.action_url)
        self.assertTrue(EventRegistration.objects.filter(id=registration.id).exists())

    def test_cancelled_registration_is_excluded(self):
        event = self._event()
        EventRegistration.objects.create(
            user=self.user, event=event, status=EventRegistration.Status.CANCELLED
        )
        created = generate_event_starting_soon_notifications()
        self.assertEqual(created, 0)


class EventServiceSynchronousTriggerTests(APITestCase):
    def setUp(self):
        self.organizer = create_user(email="organizer@example.com", role=User.Role.ORGANIZER)
        self.admin = create_user(email="admin@example.com", role=User.Role.ADMIN)
        self.student = create_user(email="student@example.com")
        self.category = EventCategory.objects.create(name="Workshop", slug="workshop")

    def _event(self, **overrides):
        defaults = {
            "organizer": self.organizer,
            "category": self.category,
            "title": "Sample Workshop",
            "slug": "sample-workshop",
            "description": "A workshop.",
            "organizer_name": "Test Organizer",
            "format": Event.Format.OFFLINE,
            "starts_at": timezone.now() + timedelta(days=30),
            "moderation_status": Event.Status.PENDING_REVIEW,
        }
        defaults.update(overrides)
        return Event.objects.create(**defaults)

    def test_approve_event_notifies_organizer(self):
        event = self._event()
        approve_event(event=event, actor=self.admin)
        notification = Notification.objects.get(
            user=self.organizer, notification_type=Notification.NotificationType.ORGANIZER_EVENT_APPROVED
        )
        self.assertIn(event.slug, notification.action_url)

    def test_reject_event_notifies_organizer_with_reason(self):
        event = self._event()
        reject_event(event=event, actor=self.admin, reason="Missing verifiable source.")
        notification = Notification.objects.get(
            user=self.organizer, notification_type=Notification.NotificationType.ORGANIZER_EVENT_REJECTED
        )
        self.assertEqual(notification.message, "Missing verifiable source.")

    def test_register_for_event_notifies_student(self):
        event = self._event(moderation_status=Event.Status.PUBLISHED)
        register_for_event(event=event, user=self.student)
        notification = Notification.objects.get(
            user=self.student,
            notification_type=Notification.NotificationType.EVENT_REGISTRATION_CONFIRMED,
        )
        self.assertEqual(notification.related_entity_id, event.id)


@override_settings(
    AI_ESSAY_SCORING_ENABLED=True,
    GEMINI_API_KEY="test-gemini-key",
    AI_ESSAY_DAILY_FREE_LIMIT=2,
)
class EssayReviewCompletedTriggerTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = create_user()
        self.essay = EssayWorkspace.objects.create(
            user=self.user,
            title="Leadership essay",
            draft_text="I built a student library project serving 120 students. " * 20,
            word_limit=650,
        )

    def _valid_ai_output(self):
        return {
            "overall_essay_readiness": 78,
            "confidence": "medium",
            "subscores": {
                "prompt_fit": 20,
                "structure": 16,
                "specificity_evidence": 15,
                "authenticity": 12,
                "language_clarity": 8,
                "word_limit_discipline": 4,
                "school_program_alignment": 4,
            },
            "ai_paraphrase_style_signal": "low",
            "generic_language_signal": "medium",
            "unsupported_claims_signal": "low",
            "strength_flags": ["clear motivation"],
            "risk_flags": ["needs more evidence"],
            "approximate_suggestions": ["Add one specific example of impact."],
            "source_warnings": [],
            "biggest_strength": "A clear, consistent motivation runs through the essay.",
            "biggest_weakness": "The middle section lacks a specific, concrete example.",
            "reflective_questions": ["What single moment best shows this motivation in action?"],
            "action_plan": "Add one concrete example, then tighten the closing paragraph.",
        }

    def test_scoring_an_essay_creates_a_completed_notification(self):
        class FakeClient:
            def score_essay(self, *, system_prompt, user_prompt, response_schema=None):
                return self._output

        client = FakeClient()
        client._output = self._valid_ai_output()
        self.client.force_authenticate(self.user)
        with patch("services.essay_service.ai_scoring.GeminiEssayScoringClient", return_value=client):
            response = self.client.post(f"/api/essays/{self.essay.id}/score/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        report = AIEssayScoreReport.objects.get(essay=self.essay)
        notification = Notification.objects.get(
            user=self.user, notification_type=Notification.NotificationType.ESSAY_REVIEW_COMPLETED
        )
        self.assertEqual(notification.dedup_key, f"essay_review_completed:{report.id}")

    def test_cached_score_does_not_create_a_second_notification(self):
        class FakeClient:
            def score_essay(self, *, system_prompt, user_prompt, response_schema=None):
                return self._output

        client = FakeClient()
        client._output = self._valid_ai_output()
        self.client.force_authenticate(self.user)
        with patch("services.essay_service.ai_scoring.GeminiEssayScoringClient", return_value=client):
            self.client.post(f"/api/essays/{self.essay.id}/score/")
            second = self.client.post(f"/api/essays/{self.essay.id}/score/")
        self.assertEqual(second.data["reason"], "cached")
        self.assertEqual(
            Notification.objects.filter(
                user=self.user, notification_type=Notification.NotificationType.ESSAY_REVIEW_COMPLETED
            ).count(),
            1,
        )


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user1 = create_user(email="user1@example.com")
        self.user2 = create_user(email="user2@example.com")

    def test_anonymous_cannot_list_notifications(self):
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_own_notifications(self):
        create_notification(
            user=self.user1,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Mine",
            dedup_key="a",
        )
        create_notification(
            user=self.user2,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Not mine",
            dedup_key="b",
        )
        self.client.force_authenticate(self.user1)
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Mine")

    def test_mark_notification_read(self):
        notification = create_notification(
            user=self.user1,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Mine",
            dedup_key="a",
        )
        self.client.force_authenticate(self.user1)
        response = self.client.patch(
            f"/api/v1/notifications/{notification.id}/", {"status": "read"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.READ)

    def test_cannot_update_another_users_notification(self):
        notification = create_notification(
            user=self.user1,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Mine",
            dedup_key="a",
        )
        self.client.force_authenticate(self.user2)
        response = self.client.patch(
            f"/api/v1/notifications/{notification.id}/", {"status": "read"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_all_read_only_affects_own_unread(self):
        n1 = create_notification(
            user=self.user1,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Mine 1",
            dedup_key="a",
        )
        create_notification(
            user=self.user2,
            notification_type=Notification.NotificationType.DEADLINE_UPCOMING,
            title="Not mine",
            dedup_key="b",
        )
        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/v1/notifications/mark-all-read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"], 1)
        n1.refresh_from_db()
        self.assertEqual(n1.status, Notification.Status.READ)
        self.assertEqual(
            Notification.objects.get(user=self.user2).status, Notification.Status.UNREAD
        )


class NotificationPreferenceApiTests(APITestCase):
    def setUp(self):
        self.user = create_user()

    def test_get_preferences_defaults_to_all_enabled(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/notifications/preferences/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["deadlines_enabled"])
        self.assertTrue(response.data["essay_reviews_enabled"])

    def test_patch_preferences_updates_a_field(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            "/api/v1/notifications/preferences/", {"events_enabled": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data["events_enabled"])
        self.assertEqual(
            NotificationPreference.objects.get(user=self.user).events_enabled, False
        )
