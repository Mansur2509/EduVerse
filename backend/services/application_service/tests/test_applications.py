from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from services.application_service.models import ApplicationTrackerItem
from services.roadmap_service.models import RoadmapPlan, RoadmapTask
from services.university_service.models import University

User = get_user_model()


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


class ApplicationTrackerApiTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="applicant1", email="applicant1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="applicant2", email="applicant2@test.com", password="testpass123"
        )
        self.university = create_university()

    def test_list_requires_authentication(self):
        response = self.client.get("/api/applications/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_application(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["status"], ApplicationTrackerItem.Status.RESEARCHING)
        self.assertEqual(response.data["university_name"], self.university.name)

    def test_duplicate_application_for_same_university_is_rejected(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/applications/", {"university": self.university.id}, format="json")
        response = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_applications_are_self_only(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/applications/", {"university": self.university.id}, format="json")

        self.client.force_authenticate(self.user2)
        response = self.client.get("/api/applications/")
        self.assertEqual(response.data["results"], [])

    def test_cannot_access_another_users_application(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        application_id = created.data["id"]

        self.client.force_authenticate(self.user2)
        response = self.client.get(f"/api/applications/{application_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_status_transition(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        application_id = created.data["id"]

        response = self.client.patch(
            f"/api/applications/{application_id}/", {"status": "preparing"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "preparing")

    def test_creating_application_does_not_force_applying_status(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        self.assertNotEqual(response.data["status"], "applying")

    def test_deadline_missing_is_reported_as_null(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        self.assertIsNone(response.data["deadline"])

    def test_create_and_list_milestones(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        application_id = created.data["id"]

        response = self.client.post(
            f"/api/applications/{application_id}/milestones/",
            {
                "title": "Request recommendation letters",
                "category": "recommendations",
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        list_response = self.client.get(f"/api/applications/{application_id}/milestones/")
        self.assertEqual(len(list_response.data), 1)

    def test_update_milestone_status(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        application_id = created.data["id"]
        milestone = self.client.post(
            f"/api/applications/{application_id}/milestones/",
            {"title": "Submit essays", "category": "essays"},
            format="json",
        )
        milestone_id = milestone.data["id"]

        response = self.client.patch(
            f"/api/applications/milestones/{milestone_id}/",
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "completed")

    def test_cannot_update_another_users_milestone(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        application_id = created.data["id"]
        milestone = self.client.post(
            f"/api/applications/{application_id}/milestones/",
            {"title": "Submit essays", "category": "essays"},
            format="json",
        )
        milestone_id = milestone.data["id"]

        self.client.force_authenticate(self.user2)
        response = self.client.patch(
            f"/api/applications/milestones/{milestone_id}/",
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_milestone_can_link_to_own_roadmap_task(self):
        self.client.force_authenticate(self.user1)
        plan = RoadmapPlan.objects.create(user=self.user1, title="My roadmap")
        task = RoadmapTask.objects.create(
            user=self.user1,
            plan=plan,
            title="Request letters",
            category=RoadmapTask.Category.RECOMMENDATIONS,
            dedup_key="manual:1",
        )
        created = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        application_id = created.data["id"]

        response = self.client.post(
            f"/api/applications/{application_id}/milestones/",
            {
                "title": "Request letters",
                "category": "recommendations",
                "linked_roadmap_task": task.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["linked_roadmap_task"], task.id)

    def test_milestone_cannot_link_to_another_users_roadmap_task(self):
        plan = RoadmapPlan.objects.create(user=self.user2, title="Other roadmap")
        task = RoadmapTask.objects.create(
            user=self.user2,
            plan=plan,
            title="Other task",
            category=RoadmapTask.Category.RECOMMENDATIONS,
            dedup_key="manual:2",
        )

        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        application_id = created.data["id"]

        response = self.client.post(
            f"/api/applications/{application_id}/milestones/",
            {"title": "Borrow", "category": "recommendations", "linked_roadmap_task": task.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_application(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/applications/", {"university": self.university.id}, format="json"
        )
        application_id = created.data["id"]
        response = self.client.delete(f"/api/applications/{application_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ApplicationTrackerItem.objects.filter(id=application_id).exists())
