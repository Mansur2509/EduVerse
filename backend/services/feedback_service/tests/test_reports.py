from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from services.essay_service.models import AIEssayScoreReport, EssayWorkspace
from services.event_service.models import Event, EventCategory
from services.feedback_service.models import UserReport
from services.university_service.models import University

User = get_user_model()

CREATE_URL = "/api/reports/"
LIST_URL = "/api/admin/reports/"


def detail_url(pk: int) -> str:
    return f"/api/admin/reports/{pk}/"


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


def create_published_event(slug="test-event", **overrides):
    category = EventCategory.objects.create(name=f"Category {slug}", slug=f"category-{slug}")
    defaults = {
        "category": category,
        "title": "Test Event",
        "description": "A test event.",
        "organizer_name": "Test Organizer",
        "format": Event.Format.ONLINE,
        "starts_at": timezone.now() + timezone.timedelta(days=30),
        "visibility": Event.Visibility.PUBLIC,
        "moderation_status": Event.Status.PUBLISHED,
    }
    defaults.update(overrides)
    return Event.objects.create(slug=slug, **defaults)


class UserReportSubmissionTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(
            username="reporter@example.com",
            email="reporter@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.STUDENT,
        )

    def test_anonymous_user_cannot_submit_report(self):
        response = self.client.post(
            CREATE_URL,
            {"target_type": "university", "target_id": 1, "reason": "Wrong deadline listed."},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_submit_report(self):
        university = create_university()
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {
                "target_type": "university",
                "target_id": university.id,
                "reason": "Wrong deadline listed.",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        report = UserReport.objects.get()
        self.assertEqual(report.reporter, self.student)
        self.assertEqual(report.status, UserReport.Status.OPEN)
        self.assertEqual(report.target_id, university.id)

    def test_submit_report_query_count_is_bounded(self):
        # Guards validate()'s target-existence + dedup checks (each a single
        # .exists() call), the insert, and the analytics event write (POST-V1-021)
        # against a future change adding a per-request N+1.
        university = create_university()
        self.client.force_authenticate(self.student)
        with self.assertNumQueries(4):
            response = self.client.post(
                CREATE_URL,
                {
                    "target_type": "university",
                    "target_id": university.id,
                    "reason": "Wrong deadline listed.",
                },
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_blank_reason_is_rejected(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL, {"target_type": "event", "target_id": 1, "reason": "   "}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserReport.objects.exists())

    def test_client_cannot_set_status_on_create(self):
        organizer = User.objects.create_user(
            username="organizer@example.com",
            email="organizer@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.ORGANIZER,
        )
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {
                "target_type": "organizer",
                "target_id": organizer.id,
                "reason": "Suspicious event listings.",
                "status": "resolved",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        report = UserReport.objects.get()
        self.assertEqual(report.status, UserReport.Status.OPEN)

    def test_user_report_submission_is_rate_limited(self):
        events = [create_published_event(slug=f"rate-limit-event-{i}") for i in range(3)]
        self.client.force_authenticate(self.student)
        with patch.object(
            ScopedRateThrottle,
            "THROTTLE_RATES",
            {"report_submit": "2/minute"},
        ):
            first = self.client.post(
                CREATE_URL,
                {"target_type": "event", "target_id": events[0].id, "reason": "First report"},
            )
            second = self.client.post(
                CREATE_URL,
                {"target_type": "event", "target_id": events[1].id, "reason": "Second report"},
            )
            third = self.client.post(
                CREATE_URL,
                {"target_type": "event", "target_id": events[2].id, "reason": "Third report"},
            )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(third.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_nonexistent_university_target_is_rejected(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {"target_type": "university", "target_id": 999999, "reason": "Made up target."},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserReport.objects.exists())

    def test_unpublished_university_target_is_rejected(self):
        university = create_university(slug="draft-university", is_published=False)
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {"target_type": "university", "target_id": university.id, "reason": "Not visible yet."},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unpublished_event_target_is_rejected(self):
        # create_published_event's defaults are overridden here to a
        # not-yet-visible state (moderation defaults to pending_review).
        event = create_published_event(
            slug="draft-event", moderation_status=Event.Status.PENDING_REVIEW
        )
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {"target_type": "event", "target_id": event.id, "reason": "Not visible yet."},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_role_target_is_rejected_as_organizer(self):
        other_student = User.objects.create_user(
            username="other-student@example.com",
            email="other-student@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {
                "target_type": "organizer",
                "target_id": other_student.id,
                "reason": "Not actually an organizer.",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_essay_review_target_must_belong_to_reporter(self):
        other_student = User.objects.create_user(
            username="essay-owner@example.com",
            email="essay-owner@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.STUDENT,
        )
        essay = EssayWorkspace.objects.create(user=other_student, title="Not yours")
        report_obj = AIEssayScoreReport.objects.create(
            user=other_student,
            essay=essay,
            essay_text_hash="hash-1",
            context_hash="context-1",
            model_name="test-model",
            raw_output_json={},
            overall_essay_readiness=70,
            prompt_fit=20,
            structure=15,
            specificity_evidence=15,
            authenticity=10,
            language_clarity=8,
            confidence=AIEssayScoreReport.Confidence.MEDIUM,
            word_count=100,
            word_limit_status=AIEssayScoreReport.WordLimitStatus.WITHIN,
            ai_paraphrase_style_signal=AIEssayScoreReport.StyleSignal.LOW,
            generic_language_signal="low",
            unsupported_claims_signal=AIEssayScoreReport.ClaimsSignal.LOW,
        )
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {
                "target_type": "essay_review",
                "target_id": report_obj.id,
                "reason": "Not my review.",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserReport.objects.exists())

    def test_other_target_type_has_no_existence_check(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {"target_type": "other", "target_id": 0, "reason": "General site issue."},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_duplicate_open_report_for_same_target_is_rejected(self):
        university = create_university()
        self.client.force_authenticate(self.student)
        first = self.client.post(
            CREATE_URL,
            {"target_type": "university", "target_id": university.id, "reason": "First report."},
        )
        second = self.client.post(
            CREATE_URL,
            {"target_type": "university", "target_id": university.id, "reason": "Same thing again."},
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserReport.objects.count(), 1)

    def test_new_report_allowed_after_earlier_one_is_resolved(self):
        university = create_university()
        UserReport.objects.create(
            reporter=self.student,
            target_type=UserReport.TargetType.UNIVERSITY,
            target_id=university.id,
            reason="Old, already-handled issue.",
            status=UserReport.Status.RESOLVED,
        )
        self.client.force_authenticate(self.student)
        response = self.client.post(
            CREATE_URL,
            {
                "target_type": "university",
                "target_id": university.id,
                "reason": "A new, separate issue.",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(UserReport.objects.count(), 2)


class UserReportAdminPermissionTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.STUDENT,
        )
        self.admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.ADMIN,
        )
        self.report = UserReport.objects.create(
            reporter=self.student,
            target_type=UserReport.TargetType.UNIVERSITY,
            target_id=1,
            reason="Outdated tuition figures.",
        )

    def test_anonymous_cannot_list(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_list(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)

    def test_admin_can_filter_by_target_type(self):
        UserReport.objects.create(
            reporter=self.student,
            target_type=UserReport.TargetType.EVENT,
            target_id=2,
            reason="Duplicate listing.",
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get(LIST_URL, {"target_type": "event"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["target_type"], "event")

    def test_student_cannot_update(self):
        self.client.force_authenticate(self.student)
        response = self.client.patch(detail_url(self.report.id), {"status": "resolved"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_resolving_sets_resolved_at(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(detail_url(self.report.id), {"status": "resolved"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, UserReport.Status.RESOLVED)
        self.assertIsNotNone(self.report.resolved_at)

    def test_admin_moving_to_reviewing_does_not_set_resolved_at(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(detail_url(self.report.id), {"status": "reviewing"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, UserReport.Status.REVIEWING)
        self.assertIsNone(self.report.resolved_at)

    def test_admin_cannot_edit_reason_via_update(self):
        self.client.force_authenticate(self.admin)
        original_reason = self.report.reason
        response = self.client.patch(detail_url(self.report.id), {"reason": "Rewritten"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.report.refresh_from_db()
        self.assertEqual(self.report.reason, original_reason)
