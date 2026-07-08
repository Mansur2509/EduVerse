from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from services.application_service.models import ApplicationTrackerItem
from services.roadmap_service.models import RoadmapTask
from services.suggestions_service.models import SuggestedItem
from services.university_service.models import (
    SavedUniversity,
    University,
    UniversityFieldVerification,
)
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


def create_university(slug="suggestion-university", **overrides):
    defaults = {
        "name": slug.replace("-", " ").title(),
        "country": "Demoland",
        "city": "Sample City",
        "official_website": f"https://example.com/{slug}",
        "admissions_url": f"https://example.com/{slug}/admissions",
        "financial_aid_url": f"https://example.com/{slug}/aid",
        "is_published": True,
    }
    defaults.update(overrides)
    return University.objects.create(slug=slug, **defaults)


def graduation_year_for_cycle_date(value: date) -> int:
    return value.year + 1 if value.month >= 8 else value.year


class SuggestionsApiTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="suggestion1",
            email="suggestion1@test.com",
            password="testpass123",
        )
        self.user2 = User.objects.create_user(
            username="suggestion2",
            email="suggestion2@test.com",
            password="testpass123",
        )
        self.today = timezone.now().date()

    def test_list_requires_authentication(self):
        response = self.client.get("/api/suggestions/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_page_size_is_capped_below_global_default(self):
        for index in range(60):
            SuggestedItem.objects.create(
                user=self.user1,
                suggestion_type=SuggestedItem.SuggestionType.PROFILE_GAP,
                title=f"Suggestion {index}",
                description="Check the official admissions source before planning.",
                priority=SuggestedItem.Priority.LOW,
                source_type=SuggestedItem.SourceType.MISSING_DATA_WARNING,
                dedup_key=f"cap-test:{index}",
            )
        self.client.force_authenticate(self.user1)

        response = self.client.get("/api/suggestions/?page_size=1000")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 50)
        self.assertEqual(response.data["count"], 60)

    def test_generate_creates_profile_course_and_roadmap_suggestions(self):
        profile, preferences = ensure_profile_records(self.user1)
        profile.intended_majors = ["Computer Science"]
        profile.exam_plans = {
            "planned": [
                {
                    "exam_type": "SAT",
                    "planned_retake": True,
                    "planned_retake_month": f"{self.today.year + 1}-03",
                    "test_status": "retaking",
                }
            ]
        }
        profile.save()
        preferences.ap_interests = ["Computer Science"]
        preferences.save()

        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/suggestions/generate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        suggestion_types = {item["suggestion_type"] for item in response.data["suggestions"]}
        self.assertIn(SuggestedItem.SuggestionType.EXAM_PLAN, suggestion_types)
        self.assertIn(SuggestedItem.SuggestionType.AP_RECOMMENDATION, suggestion_types)
        self.assertIn(SuggestedItem.SuggestionType.PROFILE_GAP, suggestion_types)
        self.assertIn(SuggestedItem.SuggestionType.ROADMAP_INSTRUCTION, suggestion_types)

    def test_missing_deadline_creates_warning_without_official_deadline(self):
        university = create_university("missing-deadline", application_deadline=None)
        SavedUniversity.objects.create(user=self.user1, university=university)

        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/suggestions/generate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        deadline_item = SuggestedItem.objects.get(
            user=self.user1,
            dedup_key=f"application_deadline_missing:{university.id}",
        )
        self.assertEqual(deadline_item.source_type, SuggestedItem.SourceType.MISSING_DATA_WARNING)
        self.assertIsNone(deadline_item.official_deadline)
        self.assertIsNone(deadline_item.recommended_end_date)

    def test_verified_application_deadline_includes_four_reminders_and_final(self):
        deadline = self.today + timedelta(days=100)
        profile, _ = ensure_profile_records(self.user1)
        profile.expected_graduation_year = graduation_year_for_cycle_date(deadline)
        profile.save(update_fields=["expected_graduation_year"])
        university = create_university("verified-deadline", application_deadline=deadline)
        UniversityFieldVerification.objects.create(
            university=university,
            field_name="application_deadline",
            status="verified",
            source_url="https://example.com/verified-deadline/source",
            last_verified_date=self.today,
        )
        SavedUniversity.objects.create(user=self.user1, university=university)

        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/suggestions/generate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        deadline_items = SuggestedItem.objects.filter(
            user=self.user1,
            suggestion_type=SuggestedItem.SuggestionType.APPLICATION_DEADLINE,
            linked_university=university,
            source_type=SuggestedItem.SourceType.VERIFIED_UNIVERSITY_DATA,
        )
        self.assertEqual(deadline_items.count(), 5)
        self.assertTrue(deadline_items.filter(dedup_key=f"application_deadline:{university.id}:14").exists())
        self.assertTrue(
            deadline_items.filter(
                dedup_key=f"application_deadline:{university.id}:0",
                official_deadline=deadline,
            ).exists()
        )

    def test_demo_university_is_ignored_for_normal_user_suggestions(self):
        demo_university = create_university(
            "uniway-demo-university",
            name="UniWay Demo University",
            is_demo=True,
            application_deadline=self.today + timedelta(days=90),
        )
        SavedUniversity.objects.create(user=self.user1, university=demo_university)

        self.client.force_authenticate(self.user1)
        self.client.post("/api/suggestions/generate/")

        self.assertFalse(
            SuggestedItem.objects.filter(user=self.user1, linked_university=demo_university).exists()
        )

    def test_add_suggestion_to_roadmap_creates_self_owned_task(self):
        deadline = self.today + timedelta(days=80)
        profile, _ = ensure_profile_records(self.user1)
        profile.expected_graduation_year = graduation_year_for_cycle_date(deadline)
        profile.save(update_fields=["expected_graduation_year"])
        university = create_university("tracked-documents", application_deadline=deadline)
        application = ApplicationTrackerItem.objects.create(user=self.user1, university=university)

        self.client.force_authenticate(self.user1)
        self.client.post("/api/suggestions/generate/")
        suggestion = SuggestedItem.objects.get(
            user=self.user1,
            linked_application=application,
            suggestion_type=SuggestedItem.SuggestionType.DOCUMENT_DEADLINE,
        )

        response = self.client.post(f"/api/suggestions/{suggestion.id}/add-to-roadmap/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, SuggestedItem.Status.ADDED_TO_ROADMAP)
        task = RoadmapTask.objects.get(id=response.data["roadmap_task_id"])
        self.assertEqual(task.user, self.user1)
        self.assertEqual(task.linked_university, university)
        self.assertEqual(task.linked_application, application)
        self.assertEqual(task.source_type, RoadmapTask.SourceType.PLANNING_WINDOW)

    def test_add_suggestion_to_roadmap_is_idempotent_and_preserves_source(self):
        suggestion = SuggestedItem.objects.create(
            user=self.user1,
            suggestion_type=SuggestedItem.SuggestionType.PROFILE_GAP,
            title="Verify official source",
            description="Check the official admissions source before planning.",
            priority=SuggestedItem.Priority.HIGH,
            source_type=SuggestedItem.SourceType.MISSING_DATA_WARNING,
            source_url="https://example.com/source",
            evidence_note="Official date not verified yet.",
            dedup_key="verify:source",
        )

        self.client.force_authenticate(self.user1)
        first_response = self.client.post(f"/api/suggestions/{suggestion.id}/add-to-roadmap/")
        second_response = self.client.post(f"/api/suggestions/{suggestion.id}/add-to-roadmap/")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED, first_response.data)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED, second_response.data)
        self.assertEqual(first_response.data["roadmap_task_id"], second_response.data["roadmap_task_id"])
        self.assertEqual(
            RoadmapTask.objects.filter(
                user=self.user1,
                dedup_key=f"suggestion:{suggestion.id}",
            ).count(),
            1,
        )
        task = RoadmapTask.objects.get(id=first_response.data["roadmap_task_id"])
        self.assertEqual(task.source_url, "https://example.com/source")

    def test_added_suggestion_is_removed_from_active_list(self):
        suggestion = SuggestedItem.objects.create(
            user=self.user1,
            suggestion_type=SuggestedItem.SuggestionType.PROFILE_GAP,
            title="Add profile detail",
            priority=SuggestedItem.Priority.MEDIUM,
            source_type=SuggestedItem.SourceType.PROFILE_BASED,
            dedup_key="profile:add-detail",
        )

        self.client.force_authenticate(self.user1)
        self.client.post(f"/api/suggestions/{suggestion.id}/add-to-roadmap/")
        response = self.client.get("/api/suggestions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(suggestion.id, [item["id"] for item in response.data["results"]])

    def test_dismiss_suggestion_persists_from_active_list(self):
        suggestion = SuggestedItem.objects.create(
            user=self.user1,
            suggestion_type=SuggestedItem.SuggestionType.PROFILE_GAP,
            title="Dismissible suggestion",
            priority=SuggestedItem.Priority.LOW,
            source_type=SuggestedItem.SourceType.PROFILE_BASED,
            dedup_key="profile:dismiss",
        )

        self.client.force_authenticate(self.user1)
        dismiss_response = self.client.patch(f"/api/suggestions/{suggestion.id}/dismiss/")
        list_response = self.client.get("/api/suggestions/")

        self.assertEqual(dismiss_response.status_code, status.HTTP_200_OK, dismiss_response.data)
        self.assertEqual(dismiss_response.data["status"], SuggestedItem.Status.DISMISSED)
        self.assertNotIn(suggestion.id, [item["id"] for item in list_response.data["results"]])

    def test_cannot_add_another_users_suggestion_to_roadmap(self):
        suggestion = SuggestedItem.objects.create(
            user=self.user1,
            suggestion_type=SuggestedItem.SuggestionType.PROFILE_GAP,
            title="Private suggestion",
            priority=SuggestedItem.Priority.MEDIUM,
            source_type=SuggestedItem.SourceType.PROFILE_BASED,
            dedup_key="private",
        )

        self.client.force_authenticate(self.user2)
        response = self.client.post(f"/api/suggestions/{suggestion.id}/add-to-roadmap/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
