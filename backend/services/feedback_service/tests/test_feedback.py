from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from services.feedback_service.models import FeedbackReport

User = get_user_model()

CREATE_URL = "/api/feedback/"
LIST_URL = "/api/admin/feedback/"


def detail_url(pk: int) -> str:
    return f"/api/admin/feedback/{pk}/"


class FeedbackSubmissionTests(APITestCase):
    def test_authenticated_user_can_submit_feedback(self):
        user = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            CREATE_URL,
            {
                "feedback_type": "issue",
                "page_module": "/roadmap",
                "message": "The filter row overlaps on a narrow screen.",
                "contact": "student@example.com",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        report = FeedbackReport.objects.get()
        self.assertEqual(report.user, user)
        self.assertEqual(report.status, FeedbackReport.Status.NEW)

    def test_anonymous_user_can_submit_feedback(self):
        response = self.client.post(
            CREATE_URL,
            {
                "feedback_type": "idea",
                "page_module": "/login",
                "message": "Add a dark mode toggle.",
            },
            HTTP_USER_AGENT="TestAgent/1.0",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        report = FeedbackReport.objects.get()
        self.assertIsNone(report.user)
        self.assertEqual(report.user_agent, "TestAgent/1.0")

    def test_blank_message_is_rejected(self):
        response = self.client.post(
            CREATE_URL,
            {"feedback_type": "issue", "page_module": "/roadmap", "message": "   "},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(FeedbackReport.objects.exists())

    def test_client_cannot_set_status_or_user_on_create(self):
        other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.STUDENT,
        )
        response = self.client.post(
            CREATE_URL,
            {
                "feedback_type": "issue",
                "page_module": "/roadmap",
                "message": "Trying to spoof fields.",
                "status": "resolved",
                "user": other_user.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        report = FeedbackReport.objects.get()
        self.assertEqual(report.status, FeedbackReport.Status.NEW)
        self.assertIsNone(report.user)


class FeedbackAdminPermissionTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.STUDENT,
        )
        self.organizer = User.objects.create_user(
            username="organizer@example.com",
            email="organizer@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.ORGANIZER,
        )
        self.admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.ADMIN,
        )
        self.report = FeedbackReport.objects.create(
            feedback_type=FeedbackReport.FeedbackType.ISSUE,
            page_module="/roadmap",
            message="Filters overlap on mobile.",
        )

    def test_anonymous_cannot_list(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_list(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_cannot_list_unless_admin(self):
        self.client.force_authenticate(self.organizer)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)

    def test_admin_can_filter_by_status(self):
        FeedbackReport.objects.create(
            feedback_type=FeedbackReport.FeedbackType.IDEA,
            page_module="/essays",
            message="Add a dark mode toggle.",
            status=FeedbackReport.Status.RESOLVED,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get(LIST_URL, {"status": "resolved"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "resolved")

    def test_student_cannot_update(self):
        self.client.force_authenticate(self.student)
        response = self.client.patch(detail_url(self.report.id), {"status": "reviewed"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, FeedbackReport.Status.NEW)

    def test_admin_can_update_status_and_notes(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            detail_url(self.report.id),
            {"status": "reviewed", "priority": "high", "admin_notes": "Looking into it."},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, FeedbackReport.Status.REVIEWED)
        self.assertEqual(self.report.priority, FeedbackReport.Priority.HIGH)
        self.assertEqual(self.report.admin_notes, "Looking into it.")

    def test_admin_cannot_edit_message_via_update(self):
        self.client.force_authenticate(self.admin)
        original_message = self.report.message
        response = self.client.patch(
            detail_url(self.report.id), {"message": "Rewritten by admin"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.report.refresh_from_db()
        self.assertEqual(self.report.message, original_message)
