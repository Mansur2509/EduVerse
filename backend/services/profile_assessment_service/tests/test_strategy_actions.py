from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from services.application_service.models import ApplicationTrackerItem
from services.profile_assessment_service.models import AIProfileAssessment
from services.profile_assessment_service.services import PROFILE_ASSESSMENT_CATEGORIES
from services.profile_assessment_service.strategy import build_profile_strategy
from services.university_service.tests.test_universities import create_university
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


def _make_assessment(user, *, deterministic_scores=None, readiness_scores=None):
    return AIProfileAssessment.objects.create(
        user=user,
        profile_snapshot_hash="hash",
        overall_profile_score=50,
        expires_at=timezone.now() + timedelta(days=1),
        deterministic_scores=deterministic_scores or {},
        readiness_scores=readiness_scores or {},
        **{category: 5 for category in PROFILE_ASSESSMENT_CATEGORIES},
    )


class BuildStrategyActionListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="strategyactions", email="strategyactions@test.com", password="testpass123"
        )
        self.profile, self.preferences = ensure_profile_records(self.user)

    def _actions(self, *, assessment=None):
        result = build_profile_strategy(self.user, self.profile, self.preferences, assessment=assessment)
        return result["prioritized_actions"]

    def _by_title(self, actions, title):
        return next((action for action in actions if action["title"] == title), None)

    def test_gpa_gap_action_cross_references_only_the_matching_school(self):
        self.profile.gpa = "2.50"
        self.profile.gpa_scale = "4.00"
        self.profile.save()
        create_university("gap-matching-university", acceptance_rate="40.00", gpa_average="3.80")
        create_university("gap-nonmatching-university", acceptance_rate="40.00", gpa_average="2.40")
        assessment = _make_assessment(self.user, deterministic_scores={"gpa": {"status": "below_benchmark"}})

        actions = self._actions(assessment=assessment)
        action = self._by_title(actions, "gpa_below_benchmark")

        self.assertIsNotNone(action)
        self.assertEqual(action["category"], "academics")
        self.assertEqual(action["confidence"], "high")
        affected_slugs = {university["slug"] for university in action["affected_universities"]}
        self.assertIn("gap-matching-university", affected_slugs)
        self.assertNotIn("gap-nonmatching-university", affected_slugs)

    def test_essays_action_present_and_not_started_before_any_progress(self):
        university = create_university("essays-not-started-university")
        ApplicationTrackerItem.objects.create(user=self.user, university=university)

        actions = self._actions()
        action = self._by_title(actions, "essays_in_progress")

        self.assertIsNotNone(action)
        self.assertEqual(action["category"], "essays")
        self.assertEqual(action["completion_state"], "not_started")
        self.assertEqual(action["next_action"], "start_essays")
        self.assertEqual(action["affected_university_count"], 1)

    def test_essays_action_absent_once_all_tracked_applications_are_ready(self):
        university = create_university("essays-ready-university")
        ApplicationTrackerItem.objects.create(
            user=self.user, university=university, essays_status=ApplicationTrackerItem.TaskStatus.SUBMITTED
        )

        actions = self._actions()

        self.assertIsNone(self._by_title(actions, "essays_in_progress"))

    def test_financial_planning_flags_missing_budget_and_aid_signals(self):
        actions = self._actions()

        action = self._by_title(actions, "specify_budget_and_aid_need")

        self.assertIsNotNone(action)
        self.assertEqual(action["category"], "financial_planning")

    def test_financial_planning_silent_when_need_is_no_and_preferences_specified(self):
        self.profile.scholarship_need = self.profile.ScholarshipNeed.NO
        self.profile.annual_budget_amount = "20000"
        self.profile.annual_budget_currency = "USD"
        self.profile.save()

        actions = self._actions()

        self.assertIsNone(self._by_title(actions, "specify_budget_and_aid_need"))
        self.assertIsNone(self._by_title(actions, "financial_aid_forms_pending"))

    def test_university_research_action_when_search_preferences_missing(self):
        actions = self._actions()

        action = self._by_title(actions, "clarify_search_preferences")

        self.assertIsNotNone(action)
        self.assertEqual(action["category"], "university_research")

    def test_overdue_application_produces_application_timeline_action(self):
        university = create_university("overdue-timeline-university")
        ApplicationTrackerItem.objects.create(
            user=self.user, university=university, deadline=date.today() - timedelta(days=2)
        )

        actions = self._actions()
        action = self._by_title(actions, "deadlines_overdue")

        self.assertIsNotNone(action)
        self.assertEqual(action["category"], "application_timeline")
        self.assertEqual(action["urgency"], "overdue")
        affected_slugs = {university["slug"] for university in action["affected_universities"]}
        self.assertIn("overdue-timeline-university", affected_slugs)

    def test_overdue_action_sorts_before_a_low_urgency_gap_action(self):
        university = create_university("sort-order-university")
        ApplicationTrackerItem.objects.create(
            user=self.user, university=university, deadline=date.today() - timedelta(days=1)
        )
        assessment = _make_assessment(
            self.user, deterministic_scores={"sat": {"status": "within_range"}}
        )

        actions = self._actions(assessment=assessment)
        titles = [action["title"] for action in actions]

        self.assertIn("deadlines_overdue", titles)
        self.assertIn("sat_within_range", titles)
        self.assertLess(titles.index("deadlines_overdue"), titles.index("sat_within_range"))

    def test_every_action_has_the_full_required_field_shape(self):
        university = create_university("full-shape-university")
        ApplicationTrackerItem.objects.create(user=self.user, university=university)
        assessment = _make_assessment(self.user, deterministic_scores={"gpa": {"status": "below_benchmark"}})

        actions = self._actions(assessment=assessment)

        self.assertTrue(actions)
        required_keys = {
            "title",
            "category",
            "reason",
            "affected_universities",
            "affected_university_count",
            "urgency",
            "estimated_effort",
            "expected_strategic_value",
            "evidence_source",
            "deadline",
            "completion_state",
            "dependency",
            "confidence",
            "next_action",
        }
        for action in actions:
            self.assertTrue(required_keys.issubset(action.keys()), action)

    def test_module_never_imports_ai_client(self):
        import inspect

        from services.profile_assessment_service import strategy_actions as module

        source = inspect.getsource(module)
        self.assertNotIn("gemini", source.lower())
        self.assertNotIn("ai_gateway", source.lower())
