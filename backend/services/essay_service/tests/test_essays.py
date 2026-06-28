from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from services.essay_service.feedback_engine import generate_feedback
from services.essay_service.models import EssayFeedback, EssayRevisionTask, EssayWorkspace
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


class EssayFeedbackEngineTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="writer1", email="writer1@test.com", password="testpass123"
        )

    def test_empty_draft_flagged_and_scored_zero(self):
        essay = EssayWorkspace.objects.create(user=self.user, title="My essay", draft_text="")
        result = generate_feedback(essay)
        self.assertIn("empty_draft", result["issues"])
        self.assertEqual(result["structure_score"], 0)
        self.assertEqual(result["overall_label"], EssayFeedback.OverallLabel.WEAK)

    def test_word_limit_too_short(self):
        essay = EssayWorkspace.objects.create(
            user=self.user, title="Short", draft_text="A short draft. " * 5, word_limit=650
        )
        result = generate_feedback(essay)
        self.assertEqual(result["word_limit_status"], EssayFeedback.WordLimitStatus.TOO_SHORT)

    def test_word_limit_too_long(self):
        essay = EssayWorkspace.objects.create(
            user=self.user, title="Long", draft_text="word " * 800, word_limit=650
        )
        result = generate_feedback(essay)
        self.assertEqual(result["word_limit_status"], EssayFeedback.WordLimitStatus.TOO_LONG)

    def test_generic_language_detected(self):
        draft = (
            "Ever since I was young, I have always loved helping people. "
            * 6
        )
        essay = EssayWorkspace.objects.create(user=self.user, title="Generic", draft_text=draft)
        result = generate_feedback(essay)
        self.assertIn("generic_language", result["issues"])

    def test_missing_quantified_impact_detected(self):
        draft = (
            "I worked hard on my community project and met many wonderful people "
            "who taught me valuable lessons about resilience and teamwork. " * 4
        )
        essay = EssayWorkspace.objects.create(user=self.user, title="Vague", draft_text=draft)
        result = generate_feedback(essay)
        self.assertIn("missing_quantified_impact", result["issues"])

    def test_why_school_essay_without_university_name_flagged(self):
        university = create_university()
        draft = (
            "I want to study here because of the strong programs and the community. " * 5
        )
        essay = EssayWorkspace.objects.create(
            user=self.user,
            title="Why school",
            essay_type=EssayWorkspace.EssayType.WHY_SCHOOL,
            university=university,
            draft_text=draft,
        )
        result = generate_feedback(essay)
        self.assertIn("missing_why_this_school", result["issues"])

    def test_why_school_essay_with_university_name_not_flagged(self):
        university = create_university(name="Demo State University")
        draft = (
            "I want to study at Demo State University because of its strong programs "
            "and supportive faculty in my intended field. " * 4
        )
        essay = EssayWorkspace.objects.create(
            user=self.user,
            title="Why school",
            essay_type=EssayWorkspace.EssayType.WHY_SCHOOL,
            university=university,
            draft_text=draft,
        )
        result = generate_feedback(essay)
        self.assertNotIn("missing_why_this_school", result["issues"])

    def test_no_paragraph_breaks_detected_for_long_single_block(self):
        draft = "word " * 200
        essay = EssayWorkspace.objects.create(user=self.user, title="Block", draft_text=draft)
        result = generate_feedback(essay)
        self.assertIn("no_paragraph_breaks", result["issues"])

    def test_feedback_never_includes_a_generated_full_essay(self):
        essay = EssayWorkspace.objects.create(
            user=self.user, title="Check", draft_text="Some draft text without much detail. " * 5
        )
        result = generate_feedback(essay)
        self.assertNotIn("generated_essay", result)
        self.assertNotIn("rewritten_text", result)


class EssayWorkspaceApiTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="writer1", email="writer1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="writer2", email="writer2@test.com", password="testpass123"
        )

    def test_list_requires_authentication(self):
        response = self.client.get("/api/essays/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_and_list_essay(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(
            "/api/essays/",
            {"title": "My Common App essay", "essay_type": "common_app", "draft_text": "Hello"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        essay_id = response.data["id"]

        list_response = self.client.get("/api/essays/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["results"]), 1)
        self.assertEqual(list_response.data["results"][0]["id"], essay_id)

    def test_essays_are_self_only(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/essays/", {"title": "Mine", "draft_text": ""}, format="json")

        self.client.force_authenticate(self.user2)
        response = self.client.get("/api/essays/")
        self.assertEqual(response.data["results"], [])

    def test_cannot_access_another_users_essay(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Mine", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]

        self.client.force_authenticate(self.user2)
        response = self.client.get(f"/api/essays/{essay_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_title_is_required(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/essays/", {"title": "  "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_feedback_creates_feedback_and_revision_tasks(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]

        response = self.client.post(f"/api/essays/{essay_id}/feedback/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNotNone(response.data["feedback"])
        self.assertTrue(EssayFeedback.objects.filter(essay_id=essay_id).exists())
        self.assertTrue(EssayRevisionTask.objects.filter(essay_id=essay_id).exists())

        essay = EssayWorkspace.objects.get(id=essay_id)
        self.assertEqual(essay.status, EssayWorkspace.Status.NEEDS_REVISION)

    def test_regenerating_feedback_does_not_duplicate_todo_revision_tasks(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]

        self.client.post(f"/api/essays/{essay_id}/feedback/")
        count_after_first = EssayRevisionTask.objects.filter(essay_id=essay_id).count()
        self.client.post(f"/api/essays/{essay_id}/feedback/")
        count_after_second = EssayRevisionTask.objects.filter(essay_id=essay_id).count()
        self.assertEqual(count_after_first, count_after_second)

    def test_manual_revision_task_creation(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": "Some content here."}, format="json"
        )
        essay_id = created.data["id"]

        response = self.client.post(
            f"/api/essays/{essay_id}/revision-tasks/",
            {"title": "Re-read introduction", "description": "", "category": "clarity"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_update_revision_task_status(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]
        task_response = self.client.post(
            f"/api/essays/{essay_id}/revision-tasks/",
            {"title": "Fix something", "category": "clarity"},
            format="json",
        )
        task_id = task_response.data["id"]

        response = self.client.patch(
            f"/api/essays/revision-tasks/{task_id}/", {"status": "completed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "completed")

    def test_cannot_update_another_users_revision_task(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]
        task_response = self.client.post(
            f"/api/essays/{essay_id}/revision-tasks/",
            {"title": "Fix something", "category": "clarity"},
            format="json",
        )
        task_id = task_response.data["id"]

        self.client.force_authenticate(self.user2)
        response = self.client.patch(
            f"/api/essays/revision-tasks/{task_id}/", {"status": "completed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_essay(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]
        response = self.client.delete(f"/api/essays/{essay_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EssayWorkspace.objects.filter(id=essay_id).exists())

    def test_no_ghostwriting_endpoint_exists(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]
        for path in (
            f"/api/essays/{essay_id}/write/",
            f"/api/essays/{essay_id}/generate/",
        ):
            response = self.client.post(path)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
