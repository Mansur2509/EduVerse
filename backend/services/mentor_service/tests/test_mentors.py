from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from services.feedback_service.models import UserReport
from services.mentor_service.models import MentorBlock, MentorProfile, MentorshipSession

User = get_user_model()
STRONG_PASSWORD = "Strong-Development-Password-842!"


def _verified_mentor(email="mentor@example.com", accepting=True):
    user = User.objects.create_user(username=email, email=email, password=STRONG_PASSWORD)
    return MentorProfile.objects.create(
        user=user, is_verified=True, is_accepting_requests=accepting, bio="Experienced mentor"
    )


def _unverified_mentor(email="unverified@example.com"):
    user = User.objects.create_user(username=email, email=email, password=STRONG_PASSWORD)
    return MentorProfile.objects.create(user=user, is_verified=False)


class MentorVisibilityTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student@example.com", email="student@example.com", password=STRONG_PASSWORD
        )
        self.client.force_authenticate(self.student)

    def test_unverified_mentor_never_appears_in_browse(self):
        _unverified_mentor()
        verified = _verified_mentor()

        response = self.client.get("/api/v1/mentors/")

        mentor_ids = [m["id"] for m in response.data["results"]]
        self.assertEqual(mentor_ids, [verified.id])

    def test_mentor_not_accepting_requests_never_appears_in_browse(self):
        _verified_mentor(email="notaccepting@example.com", accepting=False)

        response = self.client.get("/api/v1/mentors/")

        self.assertEqual(response.data["results"], [])

    def test_mentor_serializer_never_exposes_email(self):
        _verified_mentor()

        response = self.client.get("/api/v1/mentors/")

        self.assertNotIn("mentor@example.com", str(response.data))
        self.assertNotIn("email", response.data["results"][0])

    def test_cannot_request_a_session_with_an_unverified_mentor(self):
        mentor = _unverified_mentor()

        response = self.client.post(
            "/api/v1/mentors/sessions/", {"mentor_id": mentor.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SessionRequestFlowTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student2@example.com", email="student2@example.com", password=STRONG_PASSWORD
        )
        self.mentor_profile = _verified_mentor(email="mentor2@example.com")
        self.client.force_authenticate(self.student)

    def test_requesting_a_session_creates_it_in_requested_status(self):
        response = self.client.post(
            "/api/v1/mentors/sessions/",
            {"mentor_id": self.mentor_profile.id, "topic": "College essay advice"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["status"], "requested")

    def test_mentor_can_accept_a_requested_session(self):
        session = MentorshipSession.objects.create(mentor=self.mentor_profile, student=self.student)
        self.client.force_authenticate(self.mentor_profile.user)

        response = self.client.patch(
            f"/api/v1/mentors/sessions/{session.id}/status/", {"status": "accepted"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        session.refresh_from_db()
        self.assertEqual(session.status, MentorshipSession.Status.ACCEPTED)
        self.assertIsNotNone(session.responded_at)

    def test_a_third_party_cannot_change_session_status(self):
        session = MentorshipSession.objects.create(mentor=self.mentor_profile, student=self.student)
        outsider = User.objects.create_user(
            username="outsider@example.com", email="outsider@example.com", password=STRONG_PASSWORD
        )
        self.client.force_authenticate(outsider)

        response = self.client.patch(
            f"/api/v1/mentors/sessions/{session.id}/status/", {"status": "accepted"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_declined_session_can_never_become_accepted(self):
        session = MentorshipSession.objects.create(
            mentor=self.mentor_profile, student=self.student, status=MentorshipSession.Status.DECLINED
        )
        self.client.force_authenticate(self.mentor_profile.user)

        response = self.client.patch(
            f"/api/v1/mentors/sessions/{session.id}/status/", {"status": "accepted"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_completed_session_can_never_change_again(self):
        session = MentorshipSession.objects.create(
            mentor=self.mentor_profile, student=self.student, status=MentorshipSession.Status.COMPLETED
        )
        self.client.force_authenticate(self.student)

        response = self.client.patch(
            f"/api/v1/mentors/sessions/{session.id}/status/", {"status": "cancelled"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_no_serializer_in_this_app_ever_returns_email(self):
        session = MentorshipSession.objects.create(mentor=self.mentor_profile, student=self.student)

        response = self.client.get("/api/v1/mentors/sessions/")

        self.assertNotIn("mentor2@example.com", str(response.data))
        self.assertNotIn("student2@example.com", str(response.data))
        self.assertEqual(response.data["results"][0]["id"], session.id)


class BlockingTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="blocker@example.com", email="blocker@example.com", password=STRONG_PASSWORD
        )
        self.mentor_profile = _verified_mentor(email="blockedmentor@example.com")
        self.client.force_authenticate(self.student)

    def test_blocking_a_mentor_prevents_a_new_session_request(self):
        self.client.post(
            "/api/v1/mentors/block/", {"user_id": self.mentor_profile.user_id}, format="json"
        )

        response = self.client.post(
            "/api/v1/mentors/sessions/", {"mentor_id": self.mentor_profile.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_block_is_effective_in_the_reverse_direction_too(self):
        MentorBlock.objects.create(blocker=self.mentor_profile.user, blocked=self.student)

        response = self.client.post(
            "/api/v1/mentors/sessions/", {"mentor_id": self.mentor_profile.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MentorshipReportRoutingTests(APITestCase):
    def test_reporting_a_session_reaches_the_shared_admin_inbox_with_correct_target_type(self):
        student = User.objects.create_user(
            username="reporter2@example.com", email="reporter2@example.com", password=STRONG_PASSWORD
        )
        mentor_profile = _verified_mentor(email="reportedmentor@example.com")
        session = MentorshipSession.objects.create(mentor=mentor_profile, student=student)
        self.client.force_authenticate(student)

        response = self.client.post(
            "/api/reports/",
            {
                "target_type": UserReport.TargetType.MENTORSHIP_SESSION,
                "target_id": session.id,
                "reason": "Inappropriate conduct during the session.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            UserReport.objects.filter(
                reporter=student,
                target_type=UserReport.TargetType.MENTORSHIP_SESSION,
                target_id=session.id,
            ).exists()
        )

    def test_cannot_report_a_session_that_is_not_your_own(self):
        student = User.objects.create_user(
            username="notinvolved@example.com", email="notinvolved@example.com", password=STRONG_PASSWORD
        )
        other_student = User.objects.create_user(
            username="realstudent@example.com", email="realstudent@example.com", password=STRONG_PASSWORD
        )
        mentor_profile = _verified_mentor(email="uninvolvedmentor@example.com")
        session = MentorshipSession.objects.create(mentor=mentor_profile, student=other_student)
        self.client.force_authenticate(student)

        response = self.client.post(
            "/api/reports/",
            {
                "target_type": UserReport.TargetType.MENTORSHIP_SESSION,
                "target_id": session.id,
                "reason": "Not my session.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PerformanceRegressionTests(APITestCase):
    """POST-V1-021 Phase 11: guards against the N+1/extra-query patterns
    already fixed once in this app -- see mentor_service/views.py."""

    def test_browse_query_count_does_not_grow_with_mentor_count(self):
        student = User.objects.create_user(
            username="browsestudent@example.com", email="browsestudent@example.com", password=STRONG_PASSWORD
        )
        self.client.force_authenticate(student)

        _verified_mentor(email="browse1@example.com")
        _verified_mentor(email="browse2@example.com")
        with self.assertNumQueries(1):
            small_response = self.client.get("/api/v1/mentors/")
        self.assertEqual(len(small_response.data["results"]), 2)

        _verified_mentor(email="browse3@example.com")
        _verified_mentor(email="browse4@example.com")
        _verified_mentor(email="browse5@example.com")
        with self.assertNumQueries(1):
            large_response = self.client.get("/api/v1/mentors/")
        self.assertEqual(len(large_response.data["results"]), 5)

    def test_accepting_a_session_does_not_incur_an_extra_mentor_lookup_query(self):
        mentor_profile = _verified_mentor(email="acceptmentor@example.com")
        student = User.objects.create_user(
            username="acceptstudent@example.com", email="acceptstudent@example.com", password=STRONG_PASSWORD
        )
        session = MentorshipSession.objects.create(mentor=mentor_profile, student=student)
        self.client.force_authenticate(mentor_profile.user)

        with self.assertNumQueries(2):
            response = self.client.patch(
                f"/api/v1/mentors/sessions/{session.id}/status/", {"status": "accepted"}, format="json"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
