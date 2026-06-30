from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from services.application_service.models import ApplicationTrackerItem
from services.exam_content_service.models import OfficialExamDate
from services.roadmap_service.models import RoadmapPlan, RoadmapTask
from services.roadmap_service.roadmap_generator import generate_roadmap
from services.university_service.models import (
    SavedUniversity,
    University,
    UniversityFieldVerification,
)
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


def create_university(slug, **overrides):
    defaults = {
        "name": slug.replace("-", " ").title(),
        "country": "Demoland",
        "city": "Sample City",
        "official_website": f"https://example.com/{slug}",
        "summary": "Fictional record for tests.",
        "is_published": True,
        "admissions_url": f"https://example.com/{slug}/admissions",
    }
    defaults.update(overrides)
    return University.objects.create(slug=slug, **defaults)


class RoadmapGenerationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student1", email="student1@test.com", password="testpass123"
        )
        self.today = timezone.now().date()

    def test_generate_roadmap_for_empty_profile_creates_profile_gap_tasks(self):
        plan, warnings = generate_roadmap(self.user)

        self.assertIsInstance(plan, RoadmapPlan)
        self.assertIn("no_graduation_year", warnings)
        self.assertIn("no_shortlisted_universities", warnings)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))
        self.assertIn("profile_gap:activities", task_keys)
        self.assertIn("profile_gap:honors_olympiads", task_keys)
        # No exam, deadline, or scholarship tasks should appear without data.
        self.assertFalse(any(key.startswith("university_deadline") for key in task_keys))
        self.assertFalse(any(key.startswith("scholarship") for key in task_keys))

    def test_generate_roadmap_creates_task_for_not_started_essay(self):
        from services.essay_service.models import EssayWorkspace

        EssayWorkspace.objects.create(user=self.user, title="Common App essay", draft_text="")
        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))
        self.assertTrue(any(key.startswith("essay_workspace:") for key in task_keys))
        task = plan.tasks.get(dedup_key__startswith="essay_workspace:")
        self.assertEqual(task.category, RoadmapTask.Category.ESSAYS)
        self.assertEqual(task.source_type, RoadmapTask.SourceType.ESSAY_STATUS)

    def test_generate_roadmap_skips_essay_in_progress(self):
        from services.essay_service.models import EssayWorkspace

        EssayWorkspace.objects.create(
            user=self.user,
            title="Common App essay",
            draft_text="A solid draft already in progress.",
            status=EssayWorkspace.Status.DRAFTING,
        )
        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))
        self.assertFalse(any(key.startswith("essay_workspace:") for key in task_keys))

    def test_regenerating_roadmap_does_not_duplicate_essay_task(self):
        from services.essay_service.models import EssayWorkspace

        EssayWorkspace.objects.create(user=self.user, title="Common App essay", draft_text="")
        generate_roadmap(self.user)
        plan, _ = generate_roadmap(self.user)
        matching = [k for k in plan.tasks.values_list("dedup_key", flat=True) if k.startswith("essay_workspace:")]
        self.assertEqual(len(matching), 1)

    def test_generate_roadmap_with_structured_profile_skips_satisfied_gaps(self):
        from services.user_profile_service.models import Activity

        profile, _ = ensure_profile_records(self.user)
        profile.intended_majors = ["Computer Science"]
        profile.save()
        Activity.objects.create(user=self.user, title="Coding Club")

        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))

        self.assertNotIn("profile_gap:activities", task_keys)
        # Computer Science is a portfolio-relevant major with no portfolio project.
        self.assertIn("profile_gap:portfolio", task_keys)

    def test_generate_roadmap_creates_university_deadline_reminders(self):
        deadline = self.today + timedelta(days=90)
        university = create_university(
            "deadline-university",
            application_deadline=deadline,
        )
        UniversityFieldVerification.objects.create(
            university=university,
            field_name="application_deadline",
            status="verified",
            source_url="https://example.com/deadline-university/official-deadline",
            last_verified_date=self.today,
        )
        SavedUniversity.objects.create(user=self.user, university=university)

        plan, _ = generate_roadmap(self.user)
        deadline_tasks = plan.tasks.filter(source_type=RoadmapTask.SourceType.UNIVERSITY_DEADLINE)

        self.assertEqual(deadline_tasks.count(), 5)  # 60/30/14/7-day reminders + final submission
        for task in deadline_tasks:
            self.assertEqual(task.source_url, "https://example.com/deadline-university/official-deadline")
            self.assertEqual(task.linked_university_id, university.id)
        final_task = deadline_tasks.get(dedup_key=f"university_deadline:{university.id}:final")
        self.assertEqual(final_task.due_date, deadline)

    def test_application_tracker_counts_as_target_for_roadmap_generation(self):
        deadline = self.today + timedelta(days=90)
        university = create_university(
            "tracked-deadline-university",
            application_deadline=deadline,
        )
        ApplicationTrackerItem.objects.create(user=self.user, university=university)

        plan, warnings = generate_roadmap(self.user)

        self.assertNotIn("no_shortlisted_universities", warnings)
        self.assertTrue(
            plan.tasks.filter(
                dedup_key=f"university_deadline:{university.id}:final",
                linked_university=university,
            ).exists()
        )

    def test_sat_gap_uses_planning_window_not_official_date(self):
        profile, _ = ensure_profile_records(self.user)
        profile.expected_graduation_year = self.today.year + 2
        profile.test_scores = {"sat": 1200}
        profile.save()
        university = create_university("sat-target-university", sat_p75=1500)
        SavedUniversity.objects.create(user=self.user, university=university)

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key="exam_gap:sat_improve")

        self.assertEqual(task.source_type, RoadmapTask.SourceType.PLANNING_WINDOW)
        self.assertIsNotNone(task.due_date)
        self.assertEqual(task.source_url, "")
        self.assertIn("Planning window only", task.evidence_note)

    def test_planned_sat_without_official_source_creates_verify_task(self):
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {
            "taken": [],
            "planned": [{"name": "SAT", "exam_type": "SAT", "target_score": "1500"}],
        }
        profile.save()

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key="official_exam_date_missing:SAT")

        self.assertIsNone(task.due_date)
        self.assertEqual(task.source_url, "")
        self.assertIn("College Board", task.evidence_note)

    def test_verified_sat_date_uses_college_board_source(self):
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {
            "taken": [],
            "planned": [{"name": "SAT", "exam_type": "SAT", "target_score": "1500"}],
        }
        profile.save()
        official = OfficialExamDate.objects.create(
            exam_type=OfficialExamDate.ExamType.SAT,
            name="SAT Test Date",
            test_date=self.today + timedelta(days=90),
            registration_deadline=self.today + timedelta(days=45),
            academic_year=f"{self.today.year}-{self.today.year + 1}",
            source_url="https://satsuite.collegeboard.org/sat/dates-deadlines",
            last_verified_date=self.today,
            verification_status=OfficialExamDate.VerificationStatus.VERIFIED,
        )

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key=f"official_exam_date:{official.id}")

        self.assertEqual(task.due_date, official.registration_deadline)
        self.assertEqual(task.source_url, official.source_url)
        self.assertIn("Official SAT test date", task.evidence_note)

    def test_verified_sat_date_rejects_non_college_board_source(self):
        with self.assertRaises(ValidationError):
            OfficialExamDate.objects.create(
                exam_type=OfficialExamDate.ExamType.SAT,
                name="Unofficial SAT date",
                test_date=self.today + timedelta(days=90),
                academic_year=f"{self.today.year}-{self.today.year + 1}",
                source_url="https://example.com/sat-dates",
                last_verified_date=self.today,
                verification_status=OfficialExamDate.VerificationStatus.VERIFIED,
            )

    def test_no_invented_deadline_when_university_deadline_missing(self):
        university = create_university("no-deadline-university", application_deadline=None)
        SavedUniversity.objects.create(user=self.user, university=university)

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key=f"university_deadline_missing:{university.id}")

        self.assertIsNone(task.due_date)
        self.assertEqual(task.source_type, RoadmapTask.SourceType.PROFILE_GAP)
        self.assertNotEqual(task.source_url, "")

    def test_source_url_only_present_when_official_source_exists(self):
        profile, _ = ensure_profile_records(self.user)
        profile.gpa = "3.0"
        profile.gpa_scale = "4.0"
        profile.save()

        no_url_university = create_university(
            "no-url-university", admissions_url="", official_website="https://example.com/no-url-university"
        )
        SavedUniversity.objects.create(user=self.user, university=no_url_university)

        plan, _ = generate_roadmap(self.user)
        gap_tasks = plan.tasks.filter(category=RoadmapTask.Category.ACTIVITIES)
        for task in gap_tasks:
            self.assertEqual(task.source_url, "")

    def test_deadline_task_priority_reflects_urgency(self):
        urgent_deadline = self.today + timedelta(days=10)
        university = create_university("urgent-university", application_deadline=urgent_deadline)
        SavedUniversity.objects.create(user=self.user, university=university)

        plan, _ = generate_roadmap(self.user)
        final_task = plan.tasks.get(dedup_key=f"university_deadline:{university.id}:final")

        self.assertEqual(final_task.priority, RoadmapTask.Priority.URGENT)

    def test_regenerating_roadmap_does_not_duplicate_tasks(self):
        generate_roadmap(self.user)
        first_count = RoadmapTask.objects.filter(user=self.user).count()
        generate_roadmap(self.user)
        second_count = RoadmapTask.objects.filter(user=self.user).count()

        self.assertEqual(first_count, second_count)

    def test_completing_a_task_does_not_delete_it(self):
        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.first()
        task.status = RoadmapTask.Status.COMPLETED
        task.save()

        self.assertTrue(RoadmapTask.objects.filter(pk=task.pk).exists())


class RoadmapApiTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="apiuser1", email="apiuser1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="apiuser2", email="apiuser2@test.com", password="testpass123"
        )

    def test_plan_requires_authentication(self):
        response = self.client.get("/api/roadmap/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_plan_returns_none_before_generation(self):
        self.client.force_authenticate(self.user1)
        response = self.client.get("/api/roadmap/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["plan"])

    def test_generate_creates_plan_and_tasks(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/roadmap/generate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["plan"]["tasks"]), 0)
        self.assertIn("missing_data_warnings", response.data)

    def test_plan_endpoint_returns_generated_plan(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        response = self.client.get("/api/roadmap/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["plan"])
        self.assertGreater(len(response.data["plan"]["tasks"]), 0)

    def test_tasks_are_self_only(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")

        self.client.force_authenticate(self.user2)
        response = self.client.get("/api/roadmap/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_cannot_access_another_users_task(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        task_id = RoadmapTask.objects.filter(user=self.user1).first().id

        self.client.force_authenticate(self.user2)
        response = self.client.get(f"/api/roadmap/tasks/{task_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_complete_another_users_task(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        task_id = RoadmapTask.objects.filter(user=self.user1).first().id

        self.client.force_authenticate(self.user2)
        response = self.client.post(f"/api/roadmap/tasks/{task_id}/complete/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manual_task_create(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(
            "/api/roadmap/tasks/",
            {
                "title": "Email my counselor",
                "description": "Ask about recommendation letter timing.",
                "category": "recommendations",
                "priority": "medium",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["source_type"], "manual")
        self.assertTrue(RoadmapTask.objects.filter(user=self.user1, title="Email my counselor").exists())

    def test_manual_task_requires_title(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(
            "/api/roadmap/tasks/",
            {"description": "No title here", "category": "recommendations"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_task_can_be_updated(self):
        self.client.force_authenticate(self.user1)
        create_response = self.client.post(
            "/api/roadmap/tasks/",
            {"title": "Draft essay outline", "category": "essays", "priority": "low"},
            format="json",
        )
        task_id = create_response.data["id"]

        response = self.client.patch(
            f"/api/roadmap/tasks/{task_id}/",
            {"priority": "high", "due_date": str(date.today() + timedelta(days=5))},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["priority"], "high")

    def test_manual_task_can_be_deleted(self):
        self.client.force_authenticate(self.user1)
        create_response = self.client.post(
            "/api/roadmap/tasks/",
            {"title": "Temporary task", "category": "recommendations"},
            format="json",
        )
        task_id = create_response.data["id"]

        response = self.client.delete(f"/api/roadmap/tasks/{task_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RoadmapTask.objects.filter(pk=task_id).exists())

    def test_generated_task_cannot_be_deleted(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        task = RoadmapTask.objects.filter(user=self.user1).first()

        response = self.client.delete(f"/api/roadmap/tasks/{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(RoadmapTask.objects.filter(pk=task.id).exists())

    def test_complete_task(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        task = RoadmapTask.objects.filter(user=self.user1).first()

        response = self.client.post(f"/api/roadmap/tasks/{task.id}/complete/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "completed")
        self.assertIsNotNone(response.data["completed_at"])
        self.assertTrue(RoadmapTask.objects.filter(pk=task.id).exists())

    def test_skip_generated_task(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        task = RoadmapTask.objects.filter(user=self.user1).first()

        response = self.client.post(f"/api/roadmap/tasks/{task.id}/skip/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "skipped")
        self.assertTrue(RoadmapTask.objects.filter(pk=task.id).exists())

    def test_task_filters_by_status_category_priority(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")

        response = self.client.get("/api/roadmap/tasks/", {"status": "todo"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item["status"] == "todo" for item in response.data["results"]))

        response = self.client.get("/api/roadmap/tasks/", {"category": "activities"})
        self.assertTrue(all(item["category"] == "activities" for item in response.data["results"]))

    def test_generated_task_cannot_change_category_via_patch(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        task = RoadmapTask.objects.filter(user=self.user1).first()

        response = self.client.patch(
            f"/api/roadmap/tasks/{task.id}/", {"category": "events"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
