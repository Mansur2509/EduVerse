from django.contrib.auth import get_user_model
from django.test import TestCase

from services.profile_assessment_service.deterministic import (
    GAP_BELOW,
    GAP_MEETS_OR_EXCEEDS,
    GAP_NO_BENCHMARK,
    compute_deterministic_comparisons,
    compute_deterministic_student_scores,
)
from services.university_service.benchmark import BenchmarkResult
from services.university_service.fit_vector import SIGNAL_NAMES
from services.user_profile_service.models import Honor, ResearchProject
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()

FULL_BENCHMARK = BenchmarkResult(
    source="country_average",
    sample_size=5,
    scores={"activities": 7, "leadership": 6},
    academic={
        "gpa_average": 3.6,
        "sat_average": 1400,
        "sat_p25": 1300,
        "sat_p75": 1500,
        "ielts_minimum": 6.5,
        "ielts_competitive": 7.5,
    },
)

EMPTY_BENCHMARK = BenchmarkResult(source="unavailable", sample_size=0, scores={}, academic={})


class ComputeDeterministicComparisonsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="deterministicuser", email="deterministic@test.com", password="testpass123"
        )
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_gpa_meets_or_exceeds_benchmark(self):
        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.save()
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertEqual(result["gpa"]["status"], GAP_MEETS_OR_EXCEEDS)

    def test_gpa_below_benchmark(self):
        self.profile.gpa = "2.50"
        self.profile.gpa_scale = "4.00"
        self.profile.save()
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertEqual(result["gpa"]["status"], GAP_BELOW)

    def test_sat_within_p25_p75_range_is_not_flagged_as_flat_below(self):
        self.profile.test_scores = {"sat": 1350}
        self.profile.save()
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertEqual(result["sat"]["status"], "within_range")

    def test_ielts_meets_minimum_but_not_competitive(self):
        self.profile.test_scores = {"ielts": 6.5}
        self.profile.save()
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertEqual(result["ielts"]["status"], "meets_minimum_not_competitive")

    def test_missing_benchmark_data_reports_no_benchmark_not_a_gap(self):
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=EMPTY_BENCHMARK)
        self.assertEqual(result["gpa"]["status"], GAP_NO_BENCHMARK)
        self.assertEqual(result["sat"]["status"], GAP_NO_BENCHMARK)

    def test_toefl_absent_is_reported_as_not_present_not_zero(self):
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertFalse(result["toefl"]["present"])
        self.assertIsNone(result["toefl"]["student"])

    def test_missing_honors_flagged_true_when_none_exist(self):
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertTrue(result["missing_evidence"]["honors"])

    def test_missing_honors_flagged_false_once_one_exists(self):
        Honor.objects.create(user=self.user, title="Honor roll")
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertFalse(result["missing_evidence"]["honors"])

    def test_profile_completion_percentage_present(self):
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertIsInstance(result["profile_completion_percentage"], int)

    def test_score_gaps_reports_no_student_data_without_a_vector(self):
        result = compute_deterministic_comparisons(self.profile, self.preferences, benchmark=FULL_BENCHMARK)
        self.assertGreater(result["score_gaps"]["signals_missing_data"], 0)

    def test_score_gaps_uses_provided_student_vector(self):
        vector = {"activities": 9, "leadership": 9}
        result = compute_deterministic_comparisons(
            self.profile, self.preferences, benchmark=FULL_BENCHMARK, student_scores=vector
        )
        self.assertEqual(result["score_gaps"]["per_signal"]["activities"]["severity"], "meets_or_exceeds")

    def test_never_imports_or_calls_any_ai_client(self):
        import services.profile_assessment_service.deterministic as deterministic_module

        with open(deterministic_module.__file__, encoding="utf-8") as handle:
            content = handle.read()
        self.assertNotIn("gemini", content.lower())
        self.assertNotIn("ai_gateway", content.lower())


class ComputeDeterministicStudentScoresTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="fallbackscoreuser", email="fallbackscore@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)

    def test_returns_all_twelve_dimensions_as_integers_one_to_ten(self):
        scores = compute_deterministic_student_scores(self.profile)
        self.assertEqual(set(scores.keys()), set(SIGNAL_NAMES))
        for value in scores.values():
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 1)
            self.assertLessEqual(value, 10)

    def test_count_based_dimension_increases_with_more_evidence(self):
        baseline = compute_deterministic_student_scores(self.profile)
        ResearchProject.objects.create(user=self.user, title="Water quality study")
        with_one = compute_deterministic_student_scores(self.profile)
        self.assertGreater(with_one["research_experience"], baseline["research_experience"])

    def test_semantic_only_dimensions_use_fixed_neutral_value(self):
        scores = compute_deterministic_student_scores(self.profile)
        for dimension in ("profile_evidence", "subject_passion", "curiosity", "originality", "research_fit"):
            self.assertEqual(scores[dimension], 5)
