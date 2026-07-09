from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from services.application_service.models import ApplicationTrackerItem
from services.profile_assessment_service.models import AIProfileAssessment
from services.profile_assessment_service.services import PROFILE_ASSESSMENT_CATEGORIES
from services.profile_assessment_service.strategy import build_profile_strategy
from services.university_service.tests.test_universities import create_university
from services.user_profile_service.models import Recommender
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


class BuildProfileStrategyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="strategy-user", email="strategy@test.com", password="testpass123"
        )
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_no_tracked_applications_returns_safe_empty_state(self):
        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=None)

        self.assertFalse(result["has_tracked_applications"])
        self.assertFalse(result["has_verified_deadlines"])
        for bucket in ("overdue", "next_7_days", "next_30_days", "next_90_days", "before_deadline"):
            self.assertEqual(result[bucket], [])
        self.assertFalse(result["essay_plan"]["essays_missing"])
        self.assertIn("university_list_strategy", result)

    def test_deadline_within_seven_days_lands_in_next_7_days_bucket(self):
        university = create_university("strategy-soon-u")
        ApplicationTrackerItem.objects.create(
            user=self.user, university=university, deadline=date.today() + timedelta(days=5)
        )

        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=None)

        self.assertTrue(result["has_tracked_applications"])
        self.assertTrue(result["has_verified_deadlines"])
        kinds = [event["type"] for event in result["next_7_days"]]
        self.assertIn("submission_deadline", kinds)

    def test_deadline_in_sixty_days_lands_in_next_90_days_bucket(self):
        university = create_university("strategy-60d-u")
        ApplicationTrackerItem.objects.create(
            user=self.user, university=university, deadline=date.today() + timedelta(days=60)
        )

        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=None)

        kinds = [event["type"] for event in result["next_90_days"]]
        self.assertIn("submission_deadline", kinds)

    def test_deadline_beyond_ninety_days_lands_in_before_deadline_bucket(self):
        university = create_university("strategy-200d-u")
        ApplicationTrackerItem.objects.create(
            user=self.user, university=university, deadline=date.today() + timedelta(days=200)
        )

        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=None)

        kinds = [event["type"] for event in result["before_deadline"]]
        self.assertIn("submission_deadline", kinds)

    def test_overdue_deadline_lands_in_overdue_bucket(self):
        university = create_university("strategy-overdue-u")
        ApplicationTrackerItem.objects.create(
            user=self.user, university=university, deadline=date.today() - timedelta(days=3)
        )

        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=None)

        kinds = [event["type"] for event in result["overdue"]]
        self.assertIn("submission_deadline", kinds)

    def test_missing_deadline_is_reported_not_invented(self):
        university = create_university("strategy-missing-u")
        ApplicationTrackerItem.objects.create(user=self.user, university=university)

        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=None)

        self.assertFalse(result["has_verified_deadlines"])
        deadline_events = [
            event
            for bucket in ("overdue", "next_7_days", "next_30_days", "next_90_days", "before_deadline",
                            "unscheduled")
            for event in result[bucket]
            if event.get("type") == "submission_deadline"
        ]
        self.assertEqual(len(deadline_events), 1)
        self.assertEqual(deadline_events[0]["confidence"], "missing")

    def test_recommenders_are_surfaced_in_recommendation_letter_plan(self):
        Recommender.objects.create(
            user=self.user,
            name="Ms. Smith",
            relationship_role="Homeroom teacher",
            status=Recommender.Status.REQUESTED,
        )

        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=None)

        recommenders = result["recommendation_letter_plan"]["recommenders"]
        self.assertEqual(len(recommenders), 1)
        self.assertEqual(recommenders[0]["status"], "requested")

    def test_testing_plan_deduplicates_exam_type_across_applications(self):
        self.profile.test_scores = {"sat": 1350}
        self.profile.save()
        university_a = create_university("strategy-sat-a", sat_p75="1500")
        university_b = create_university("strategy-sat-b", sat_p75="1450")
        ApplicationTrackerItem.objects.create(user=self.user, university=university_a)
        ApplicationTrackerItem.objects.create(user=self.user, university=university_b)

        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=None)

        exam_types = [entry["exam"] for entry in result["testing_plan"]["exams"]]
        self.assertEqual(exam_types.count("SAT"), 1)

    def test_module_never_imports_ai_client(self):
        import inspect

        from services.profile_assessment_service import strategy as module

        source = inspect.getsource(module)
        self.assertNotIn("gemini", source.lower())
        self.assertNotIn("ai_gateway", source.lower())

    def test_cached_assessment_missing_evidence_drives_essay_and_activities_plans(self):
        assessment = AIProfileAssessment.objects.create(
            user=self.user,
            profile_snapshot_hash="hash",
            overall_profile_score=50,
            expires_at=timezone.now() + timedelta(days=1),
            deterministic_scores={
                "missing_evidence": {
                    "essays": True,
                    "recommendation_letters": False,
                    "activities": True,
                    "research": True,
                    "portfolio": False,
                    "honors": False,
                    "olympiads": False,
                    "volunteering": False,
                }
            },
            **{category: 5 for category in PROFILE_ASSESSMENT_CATEGORIES},
        )

        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=assessment)

        self.assertTrue(result["essay_plan"]["essays_missing"])
        self.assertEqual(result["essay_plan"]["next_action"], "start_essays")
        self.assertFalse(result["recommendation_letter_plan"]["recommendation_letters_missing"])
        self.assertEqual(
            result["recommendation_letter_plan"]["next_action"], "follow_up_recommendation_letters"
        )
        activities_gaps = result["activities_research_plan"]["missing_evidence"]
        self.assertTrue(activities_gaps["activities"])
        self.assertTrue(activities_gaps["research"])
        self.assertFalse(activities_gaps["portfolio"])
        self.assertIn("add_activities", result["activities_research_plan"]["next_actions"])
        self.assertIn("add_research", result["activities_research_plan"]["next_actions"])
