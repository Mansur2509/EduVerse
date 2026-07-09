from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from services.application_service.models import ApplicationTrackerItem
from services.exam_content_service.models import OfficialExamDate
from services.profile_assessment_service.models import AIProfileAssessment
from services.profile_assessment_service.services import (
    PROFILE_ASSESSMENT_CATEGORIES,
    compute_profile_snapshot_hash,
)
from services.roadmap_service.models import RoadmapPlan, RoadmapTask
from services.roadmap_service.roadmap_generator import generate_roadmap
from services.university_service.models import (
    SavedUniversity,
    University,
    UniversityFieldVerification,
)
from services.user_profile_service.models import Recommender
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


def graduation_year_for_cycle_date(value: date) -> int:
    return value.year + 1 if value.month >= 8 else value.year


def make_assessment(user, *, deterministic_scores=None, readiness_scores=None):
    """Snapshot hash is computed from the user's *current* profile state so
    `get_latest_valid_assessment` (which re-derives and compares this hash)
    treats the fixture as valid -- create this only after all profile setup.
    """
    return AIProfileAssessment.objects.create(
        user=user,
        profile_snapshot_hash=compute_profile_snapshot_hash(user),
        overall_profile_score=50,
        expires_at=timezone.now() + timedelta(days=1),
        deterministic_scores=deterministic_scores or {},
        readiness_scores=readiness_scores or {},
        **{category: 5 for category in PROFILE_ASSESSMENT_CATEGORIES},
    )


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

    def test_generate_roadmap_creates_task_for_suggested_application_essay(self):
        from services.essay_service.models import EssayWorkspace

        university = create_university("suggested-essay-university")
        application = ApplicationTrackerItem.objects.create(user=self.user, university=university)
        essay = EssayWorkspace.objects.create(
            user=self.user,
            university=university,
            application=application,
            title="Suggested supplement",
            essay_type=EssayWorkspace.EssayType.SUPPLEMENT,
            status=EssayWorkspace.Status.SUGGESTED,
            due_date=self.today + timedelta(days=45),
            source_url="https://example.com/suggested-essay-source",
        )

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key=f"essay_workspace:{essay.id}:suggested")

        self.assertEqual(task.category, RoadmapTask.Category.ESSAYS)
        self.assertEqual(task.linked_application, application)
        self.assertEqual(task.linked_university, university)
        self.assertEqual(task.due_date, essay.due_date)
        self.assertEqual(task.source_url, essay.source_url)

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
        profile, _ = ensure_profile_records(self.user)
        profile.expected_graduation_year = graduation_year_for_cycle_date(deadline)
        profile.save(update_fields=["expected_graduation_year"])
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
        profile, _ = ensure_profile_records(self.user)
        profile.expected_graduation_year = graduation_year_for_cycle_date(deadline)
        profile.save(update_fields=["expected_graduation_year"])
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
        OfficialExamDate.objects.all().delete()
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
        OfficialExamDate.objects.all().delete()
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

    def test_partial_college_board_sat_date_is_still_used_with_status_note(self):
        OfficialExamDate.objects.all().delete()
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {
            "taken": [],
            "planned": [{"name": "SAT", "exam_type": "SAT", "target_score": "1500"}],
        }
        profile.save()
        official = OfficialExamDate.objects.create(
            exam_type=OfficialExamDate.ExamType.SAT,
            name="Partial SAT Test Date",
            test_date=self.today + timedelta(days=90),
            registration_deadline=self.today + timedelta(days=45),
            academic_year=f"{self.today.year}-{self.today.year + 1}",
            source_url="https://satsuite.collegeboard.org/sat/dates-deadlines",
            last_verified_date=self.today,
            verification_status=OfficialExamDate.VerificationStatus.PARTIAL,
        )

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key=f"official_exam_date:{official.id}")

        self.assertEqual(task.due_date, official.registration_deadline)
        self.assertIn("Verification status: partial", task.evidence_note)

    def test_ielts_plan_creates_official_link_task_not_a_fake_date(self):
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {
            "taken": [],
            "planned": [{"name": "IELTS", "exam_type": "IELTS", "target_score": "7.5"}],
        }
        profile.save()

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key="official_exam_link:IELTS")

        self.assertIsNone(task.due_date)
        self.assertEqual(task.source_url, "https://www.ielts.org")

    def test_toefl_plan_creates_official_link_task(self):
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {
            "taken": [],
            "planned": [{"name": "TOEFL", "exam_type": "TOEFL", "target_score": "110"}],
        }
        profile.save()

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key="official_exam_link:TOEFL")

        self.assertIsNone(task.due_date)
        self.assertEqual(task.source_url, "https://www.ets.org/toefl")

    def test_act_plan_creates_official_link_task(self):
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {
            "taken": [],
            "planned": [{"name": "ACT", "exam_type": "ACT", "target_score": "34"}],
        }
        profile.save()

        plan, _ = generate_roadmap(self.user)
        task = plan.tasks.get(dedup_key="official_exam_link:ACT")

        self.assertIsNone(task.due_date)
        self.assertEqual(task.source_url, "https://www.act.org")

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
        profile, _ = ensure_profile_records(self.user)
        profile.expected_graduation_year = graduation_year_for_cycle_date(urgent_deadline)
        profile.save(update_fields=["expected_graduation_year"])
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

    def test_recommendation_letters_task_created_when_targets_exist(self):
        university = create_university("recommenders-university")
        SavedUniversity.objects.create(user=self.user, university=university)

        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))

        self.assertIn("profile_gap:recommendation_letters", task_keys)
        task = plan.tasks.get(dedup_key="profile_gap:recommendation_letters")
        self.assertEqual(task.category, RoadmapTask.Category.RECOMMENDATIONS)
        self.assertEqual(task.estimated_effort, RoadmapTask.EstimatedEffort.SHORT)

    def test_recommendation_letters_task_absent_without_targets(self):
        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))

        self.assertNotIn("profile_gap:recommendation_letters", task_keys)

    def test_recommendation_letters_task_absent_when_recommender_exists(self):
        university = create_university("recommenders-university-2")
        SavedUniversity.objects.create(user=self.user, university=university)
        Recommender.objects.create(user=self.user, name="Ms. Rivera")

        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))

        self.assertNotIn("profile_gap:recommendation_letters", task_keys)

    def test_assessment_gap_creates_task_from_cached_gpa_benchmark(self):
        make_assessment(
            self.user,
            deterministic_scores={"gpa": {"student": 3.0, "benchmark": 3.6, "status": "below_benchmark"}},
        )

        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))

        self.assertIn("assessment_gap:gpa_below_benchmark", task_keys)
        task = plan.tasks.get(dedup_key="assessment_gap:gpa_below_benchmark")
        self.assertEqual(task.source_type, RoadmapTask.SourceType.CACHED_ASSESSMENT)
        self.assertEqual(task.linked_score_dimension, "academic_readiness")
        self.assertEqual(task.priority, RoadmapTask.Priority.MEDIUM)
        self.assertEqual(task.category, RoadmapTask.Category.PROFILE)

    def test_assessment_gap_absent_without_any_assessment(self):
        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))

        self.assertFalse(any(key.startswith("assessment_gap:") for key in task_keys))

    def test_assessment_gap_skips_testing_readiness_dimension(self):
        # sat/ielts benchmark gaps are intentionally left to _exam_gaps so the
        # roadmap never shows two near-duplicate "improve your score" tasks.
        make_assessment(
            self.user,
            deterministic_scores={
                "sat": {
                    "student": 1200,
                    "benchmark_p25": 1300,
                    "benchmark_p75": 1500,
                    "benchmark_average": 1400,
                    "status": "below_benchmark",
                }
            },
        )

        plan, _ = generate_roadmap(self.user)
        task_keys = set(plan.tasks.values_list("dedup_key", flat=True))

        self.assertFalse(any(key.startswith("assessment_gap:") for key in task_keys))

    def test_assessment_gap_not_duplicated_on_regeneration(self):
        make_assessment(
            self.user,
            deterministic_scores={"gpa": {"student": 3.0, "benchmark": 3.6, "status": "below_benchmark"}},
        )

        generate_roadmap(self.user)
        first_count = RoadmapTask.objects.filter(
            user=self.user, dedup_key="assessment_gap:gpa_below_benchmark"
        ).count()
        generate_roadmap(self.user)
        second_count = RoadmapTask.objects.filter(
            user=self.user, dedup_key="assessment_gap:gpa_below_benchmark"
        ).count()

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)


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

    def test_plan_and_task_list_query_count_does_not_grow_with_task_count(self):
        # Regression guard for RoadmapPlanSerializer.get_tasks() and
        # RoadmapTaskViewSet.get_queryset(), which both select_related the
        # FKs the serializer dereferences (linked_university,
        # linked_application__university, linked_event) -- a query count
        # that grows with N here means one of those was dropped.
        self.client.force_authenticate(self.user1)
        plan = RoadmapPlan.objects.create(user=self.user1)

        def make_tasks(count, offset):
            for index in range(count):
                university = create_university(f"query-count-university-{offset + index}")
                application = ApplicationTrackerItem.objects.create(
                    user=self.user1, university=university
                )
                RoadmapTask.objects.create(
                    user=self.user1,
                    plan=plan,
                    title=f"Task {offset + index}",
                    category=RoadmapTask.Category.UNIVERSITIES,
                    linked_university=university,
                    linked_application=application,
                    dedup_key=f"query-count:{offset + index}",
                )

        make_tasks(3, offset=0)
        with CaptureQueriesContext(connection) as small:
            plan_response = self.client.get("/api/roadmap/")
            tasks_response = self.client.get("/api/roadmap/tasks/")
        self.assertEqual(plan_response.status_code, status.HTTP_200_OK)
        self.assertEqual(tasks_response.status_code, status.HTTP_200_OK)

        make_tasks(6, offset=3)
        with CaptureQueriesContext(connection) as large:
            plan_response = self.client.get("/api/roadmap/")
            tasks_response = self.client.get("/api/roadmap/tasks/")
        self.assertEqual(plan_response.status_code, status.HTTP_200_OK)
        self.assertEqual(tasks_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(tasks_response.data["results"]), 9)

        self.assertEqual(len(small), len(large))

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

    def test_task_filters_by_university_application_exam_source_and_kind(self):
        self.client.force_authenticate(self.user1)
        plan = RoadmapPlan.objects.create(user=self.user1, title="Filter plan")
        university = create_university("filter-university")
        application = ApplicationTrackerItem.objects.create(user=self.user1, university=university)
        matching = RoadmapTask.objects.create(
            user=self.user1,
            plan=plan,
            title="Register for SAT",
            description="Confirm SAT timing.",
            category=RoadmapTask.Category.EXAMS,
            priority=RoadmapTask.Priority.HIGH,
            source_type=RoadmapTask.SourceType.PLANNING_WINDOW,
            linked_university=university,
            linked_application=application,
            generated_reason="SAT planning item.",
        )
        RoadmapTask.objects.create(
            user=self.user1,
            plan=plan,
            title="Manual counselor email",
            category=RoadmapTask.Category.RECOMMENDATIONS,
            priority=RoadmapTask.Priority.LOW,
            source_type=RoadmapTask.SourceType.MANUAL,
        )

        response = self.client.get(
            "/api/roadmap/tasks/",
            {
                "linked_university": str(university.id),
                "linked_application": str(application.id),
                "exam": "SAT",
                "source_type": RoadmapTask.SourceType.PLANNING_WINDOW,
                "task_kind": "generated",
                "priority": RoadmapTask.Priority.HIGH,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], matching.id)
        self.assertEqual(response.data["results"][0]["linked_application"], application.id)
        self.assertEqual(response.data["results"][0]["task_kind"], "generated")

    def test_list_view_excludes_timeline_markers_but_timeline_view_includes_them(self):
        self.client.force_authenticate(self.user1)
        today = timezone.now().date()
        profile, _ = ensure_profile_records(self.user1)
        deadline = today + timedelta(days=90)
        profile.expected_graduation_year = graduation_year_for_cycle_date(deadline)
        profile.save(update_fields=["expected_graduation_year"])
        university = create_university(
            "timeline-marker-university",
            application_deadline=deadline,
        )
        SavedUniversity.objects.create(user=self.user1, university=university)
        self.client.post("/api/roadmap/generate/")

        list_response = self.client.get("/api/roadmap/tasks/", {"view": "list"})
        timeline_response = self.client.get("/api/roadmap/tasks/", {"view": "timeline"})

        self.assertEqual(list_response.status_code, status.HTTP_200_OK, list_response.data)
        self.assertFalse(any(item["is_timeline_marker"] for item in list_response.data["results"]))
        self.assertTrue(any(item["is_timeline_marker"] for item in timeline_response.data["results"]))
        self.assertTrue(
            any(
                item["title"] == f"Submit your application to {university.name}"
                for item in list_response.data["results"]
            )
        )

    def test_skipped_generated_task_does_not_appear_in_active_status_filter(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        task = RoadmapTask.objects.filter(user=self.user1).first()
        self.client.post(f"/api/roadmap/tasks/{task.id}/skip/")

        response = self.client.get("/api/roadmap/tasks/", {"status": "todo"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(task.id, [item["id"] for item in response.data["results"]])

    def test_generated_task_cannot_change_category_via_patch(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/roadmap/generate/")
        task = RoadmapTask.objects.filter(user=self.user1).first()

        response = self.client.patch(
            f"/api/roadmap/tasks/{task.id}/", {"category": "events"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
