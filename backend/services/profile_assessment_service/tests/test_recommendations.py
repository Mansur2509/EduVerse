from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from services.profile_assessment_service.models import AIProfileAssessment
from services.profile_assessment_service.recommendations import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_URGENT,
    compute_profile_recommendations,
)
from services.profile_assessment_service.services import PROFILE_ASSESSMENT_CATEGORIES

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


def _section(key, *, cap_reasons=None):
    return {"key": key, "score": 3, "status": "solid", "cap_reasons": cap_reasons or []}


class ComputeProfileRecommendationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recuser", email="rec@test.com", password="testpass123"
        )

    def test_empty_assessment_produces_no_recommendations(self):
        assessment = _make_assessment(self.user)

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(recommendations, [])

    def test_essays_missing_cap_reason_produces_high_priority_recommendation(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={"missing_evidence": {"essays": True}},
            readiness_scores={
                "sections": [_section("application_execution", cap_reasons=["essays_missing"])]
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(len(recommendations), 1)
        item = recommendations[0]
        self.assertEqual(item["title"], "essays_missing")
        self.assertEqual(item["priority"], PRIORITY_HIGH)
        self.assertEqual(item["linked_dimension"], "application_execution")
        self.assertEqual(item["evidence_from_profile"], {"essays": True})
        self.assertEqual(item["next_action"], "start_essays")

    def test_activities_missing_is_urgent_priority(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={"missing_evidence": {"activities": True}},
            readiness_scores={
                "sections": [
                    _section("academic_readiness", cap_reasons=["activities_missing"]),
                    _section("testing_readiness", cap_reasons=["activities_missing"]),
                ]
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(len(recommendations), 1, "same cap_reason across sections must dedupe to one")
        self.assertEqual(recommendations[0]["priority"], PRIORITY_URGENT)

    def test_same_cap_reason_across_sections_is_deduplicated(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={"missing_evidence": {"honors": True, "olympiads": True}},
            readiness_scores={
                "sections": [
                    _section("honors_competitions", cap_reasons=["honors_missing_for_selective_target"]),
                ]
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["title"], "honors_missing_for_selective_target")

    def test_gpa_below_benchmark_produces_medium_priority_recommendation(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={"gpa": {"student": 3.0, "benchmark": 3.6, "status": "below_benchmark"}},
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(len(recommendations), 1)
        item = recommendations[0]
        self.assertEqual(item["title"], "gpa_below_benchmark")
        self.assertEqual(item["priority"], PRIORITY_MEDIUM)
        self.assertEqual(item["linked_dimension"], "academic_readiness")
        self.assertEqual(item["evidence_from_profile"], {"student": 3.0, "benchmark": 3.6})

    def test_sat_within_range_is_low_priority(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={
                "sat": {
                    "student": 1310,
                    "benchmark_p25": 1300,
                    "benchmark_p75": 1500,
                    "benchmark_average": 1400,
                    "status": "within_range",
                }
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(recommendations[0]["priority"], PRIORITY_LOW)
        self.assertEqual(recommendations[0]["title"], "sat_within_range")

    def test_meets_or_exceeds_status_produces_no_recommendation(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={"gpa": {"student": 3.9, "benchmark": 3.6, "status": "meets_or_exceeds"}},
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(recommendations, [])

    def test_signal_gap_maps_to_correct_dimension(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={
                "score_gaps": {
                    "per_signal": {
                        "research_experience": {"gap": -3, "severity": "significant_gap"},
                    }
                }
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(len(recommendations), 1)
        item = recommendations[0]
        self.assertEqual(item["title"], "research_experience_gap")
        self.assertEqual(item["priority"], PRIORITY_HIGH)
        self.assertEqual(item["linked_dimension"], "research_portfolio")
        self.assertEqual(item["evidence_from_profile"], {"gap": -3, "severity": "significant_gap"})

    def test_signal_gap_suppressed_when_dimension_already_covered_by_cap_reason(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={
                "missing_evidence": {"research": True, "portfolio": True},
                "score_gaps": {
                    "per_signal": {
                        "research_experience": {"gap": -3, "severity": "significant_gap"},
                        "portfolio": {"gap": -2, "severity": "important_gap"},
                    }
                },
            },
            readiness_scores={
                "sections": [
                    _section("research_portfolio", cap_reasons=["research_and_portfolio_missing"]),
                ]
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        titles = [item["title"] for item in recommendations]
        self.assertEqual(titles, ["research_and_portfolio_missing"])

    def test_multiple_signal_gaps_same_dimension_collapse_to_one(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={
                "score_gaps": {
                    "per_signal": {
                        "research_experience": {"gap": -3, "severity": "significant_gap"},
                        "portfolio": {"gap": -2, "severity": "important_gap"},
                    }
                }
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["linked_dimension"], "research_portfolio")

    def test_minor_and_no_data_severities_produce_no_recommendation(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={
                "score_gaps": {
                    "per_signal": {
                        "activities": {"gap": 0, "severity": "meets_or_exceeds"},
                        "leadership": {"gap": None, "severity": "insufficient_data"},
                    }
                }
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        self.assertEqual(recommendations, [])

    def test_recommendations_are_sorted_by_priority(self):
        assessment = _make_assessment(
            self.user,
            deterministic_scores={
                "missing_evidence": {"activities": True, "essays": True},
                "gpa": {"student": 3.0, "benchmark": 3.6, "status": "below_benchmark"},
                "sat": {
                    "student": 1310,
                    "benchmark_p25": 1300,
                    "benchmark_p75": 1500,
                    "benchmark_average": 1400,
                    "status": "within_range",
                },
            },
            readiness_scores={
                "sections": [
                    _section("application_execution", cap_reasons=["essays_missing"]),
                    _section("activities_leadership", cap_reasons=["activities_missing"]),
                ]
            },
        )

        recommendations = compute_profile_recommendations(assessment)

        priorities = [item["priority"] for item in recommendations]
        self.assertEqual(
            priorities,
            sorted(priorities, key=[PRIORITY_URGENT, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW].index),
        )
        self.assertEqual(recommendations[0]["priority"], PRIORITY_URGENT)

    def test_module_never_imports_ai_client(self):
        import inspect

        from services.profile_assessment_service import recommendations as module

        source = inspect.getsource(module)
        self.assertNotIn("gemini", source.lower())
        self.assertNotIn("ai_gateway", source.lower())
