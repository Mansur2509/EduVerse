from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from services.profile_assessment_service.profile_strength import (
    ACADEMIC_DATA_INCOMPLETE,
    GPA_RANGE_UNKNOWN,
    calculate_academic_strength,
    calculate_application_readiness,
    calculate_extracurricular_strength,
    calculate_practical_fit,
    calculate_profile_strength,
)
from services.user_profile_service.models import Activity
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()
STRONG_PASSWORD = "Strong-Development-Password-842!"


def _make_user(email="strength@example.com"):
    return User.objects.create_user(username=email, email=email, password=STRONG_PASSWORD)


class ProfileStrengthShapeTests(TestCase):
    """022 Phase 1: structural guarantees of the four-dimension model."""

    def setUp(self):
        self.user = _make_user()
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_never_exposes_a_single_admission_chance(self):
        result = calculate_profile_strength(self.profile)

        self.assertEqual(
            set(result.keys()),
            {
                "academic_strength",
                "extracurricular_strength",
                "application_readiness",
                "practical_fit",
                "overall_confidence",
                "disclaimer",
            },
        )
        for dimension_key in (
            "academic_strength",
            "extracurricular_strength",
            "application_readiness",
            "practical_fit",
        ):
            self.assertIn("score", result[dimension_key])
            self.assertIn("confidence", result[dimension_key])
            self.assertIn("components", result[dimension_key])

    def test_empty_profile_produces_low_confidence_not_a_crash(self):
        result = calculate_profile_strength(self.profile)

        self.assertLess(result["overall_confidence"], 0.5)
        self.assertLess(result["academic_strength"]["confidence"], 0.5)


class AcademicStrengthTests(TestCase):
    def setUp(self):
        self.user = _make_user("academic@example.com")
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_missing_gpa_is_reported_as_unknown_not_penalized_to_zero(self):
        result = calculate_academic_strength(self.profile)

        gpa_component = next(c for c in result.components if c.key == "gpa")
        self.assertIsNone(gpa_component.score)
        self.assertIn(GPA_RANGE_UNKNOWN, gpa_component.reason_codes)
        self.assertIn(ACADEMIC_DATA_INCOMPLETE, gpa_component.reason_codes)

    def test_strong_gpa_with_no_benchmark_still_scores_on_its_own_merit(self):
        self.profile.original_gpa_value = "3.95"
        self.profile.original_gpa_scale = "4.00"
        self.profile.original_gpa_scale_type = self.profile.GpaScaleType.FOUR_POINT
        self.profile.save()

        result = calculate_academic_strength(self.profile)

        gpa_component = next(c for c in result.components if c.key == "gpa")
        self.assertIsNotNone(gpa_component.score)
        self.assertGreaterEqual(gpa_component.score, 90)


class ExtracurricularStrengthTests(TestCase):
    def setUp(self):
        self.user = _make_user("ec@example.com")
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_no_activities_does_not_crash_and_reports_missing(self):
        result = calculate_extracurricular_strength(self.profile)

        self.assertEqual(result.score, 50)
        self.assertLess(result.confidence, 0.3)

    def test_uncorroborated_founder_title_is_not_automatically_strong(self):
        Activity.objects.create(
            user=self.user,
            title="Solo club",
            role="Founder",
            category="community",
            description="",
        )

        result = calculate_extracurricular_strength(self.profile)

        strongest = next(c for c in result.components if c.key == "strongest_activity")
        # An uncorroborated founder title (no duration, no proof, no
        # description) must not reach the top of the 0-100 range.
        self.assertLess(strongest.score, 70)

    def test_corroborated_leadership_scores_higher_than_uncorroborated(self):
        Activity.objects.create(
            user=self.user,
            title="Uncorroborated club",
            role="Founder",
            category="community",
            description="",
        )
        uncorroborated_result = calculate_extracurricular_strength(self.profile)

        Activity.objects.all().delete()
        Activity.objects.create(
            user=self.user,
            title="Corroborated club",
            role="Founder",
            category="community",
            start_date=date.today() - timedelta(days=800),
            hours_per_week="8",
            scale=Activity.Scale.NATIONAL,
            proof_link="https://example.com/proof",
            description="Founded and grew this club to 40 active members over two years, "
            "organizing 12 events with measurable community turnout.",
            impact_number="40 members, 12 events",
        )
        corroborated_result = calculate_extracurricular_strength(self.profile)

        self.assertGreater(corroborated_result.score, uncorroborated_result.score)

    def test_duplicate_activity_is_not_double_counted(self):
        Activity.objects.create(user=self.user, title="Robotics Club", role="Member", category="stem")
        Activity.objects.create(user=self.user, title="robotics club", role="Member", category="stem")

        records_count = len(
            calculate_extracurricular_strength(self.profile).components
        )
        # Structural check: the dedup logic collapses same-title duplicates
        # into a single record, so scoring never sees two entries for one
        # activity. We assert indirectly via the underlying collector.
        from services.profile_assessment_service.profile_strength import _collect_records

        self.assertEqual(len(_collect_records(self.user)), 1)
        self.assertGreaterEqual(records_count, 1)


class ApplicationReadinessTests(TestCase):
    def setUp(self):
        self.user = _make_user("readiness@example.com")
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_no_essays_reports_missing_not_zero(self):
        result = calculate_application_readiness(self.profile)

        essay_component = next(c for c in result.components if c.key == "essay_readiness")
        self.assertIsNone(essay_component.score)
        self.assertIn("ESSAYS_MISSING", essay_component.reason_codes)


class PracticalFitTests(TestCase):
    def setUp(self):
        self.user = _make_user("practical@example.com")
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_unspecified_preferences_are_flagged_not_scored_low(self):
        result = calculate_practical_fit(self.profile)

        major_component = next(c for c in result.components if c.key == "major_specified")
        self.assertIsNone(major_component.score)
        self.assertIn("MAJOR_NOT_SPECIFIED", major_component.reason_codes)

    def test_specified_preferences_score_highly(self):
        self.profile.intended_major = "Computer Science"
        self.profile.target_countries = ["United States"]
        self.profile.annual_budget_amount = "40000"
        self.profile.scholarship_need = self.profile.ScholarshipNeed.YES
        self.profile.save()

        result = calculate_practical_fit(self.profile)

        self.assertGreaterEqual(result.score, 90)
