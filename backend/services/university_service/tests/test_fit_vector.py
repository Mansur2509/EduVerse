from django.test import SimpleTestCase

from services.university_service.fit_vector import (
    SIGNAL_NAMES,
    compare_student_vector_to_university_weights,
)

FULL_STUDENT_VECTOR = {name: 7 for name in SIGNAL_NAMES}
FULL_UNIVERSITY_WEIGHTS = {name: 7 for name in SIGNAL_NAMES}


class CompareStudentVectorToUniversityWeightsTests(SimpleTestCase):
    def test_equal_scores_meet_or_exceed_with_strong_alignment(self):
        result = compare_student_vector_to_university_weights(FULL_STUDENT_VECTOR, FULL_UNIVERSITY_WEIGHTS)
        self.assertEqual(result.counts_by_severity["meets_or_exceeds"], len(SIGNAL_NAMES))
        self.assertEqual(result.total_gap_score, 0)
        self.assertEqual(result.fit_band, "strong_alignment")
        self.assertEqual(result.signals_compared, len(SIGNAL_NAMES))
        self.assertEqual(result.signals_missing_data, 0)

    def test_student_exceeding_weights_still_meets_or_exceeds(self):
        student = {name: 10 for name in SIGNAL_NAMES}
        weights = {name: 3 for name in SIGNAL_NAMES}
        result = compare_student_vector_to_university_weights(student, weights)
        self.assertEqual(result.counts_by_severity["meets_or_exceeds"], len(SIGNAL_NAMES))
        self.assertLess(result.total_gap_score, 0)
        self.assertEqual(result.fit_band, "strong_alignment")

    def test_gap_of_one_is_minor_gap(self):
        student = dict(FULL_STUDENT_VECTOR)
        weights = dict(FULL_UNIVERSITY_WEIGHTS)
        weights["curiosity"] = 8  # gap = 1
        result = compare_student_vector_to_university_weights(student, weights)
        curiosity_gap = next(g for g in result.per_signal if g.signal == "curiosity")
        self.assertEqual(curiosity_gap.gap, 1)
        self.assertEqual(curiosity_gap.severity, "minor_gap")

    def test_gap_of_two_is_important_gap(self):
        student = dict(FULL_STUDENT_VECTOR)
        weights = dict(FULL_UNIVERSITY_WEIGHTS)
        weights["leadership"] = 9  # gap = 2
        result = compare_student_vector_to_university_weights(student, weights)
        leadership_gap = next(g for g in result.per_signal if g.signal == "leadership")
        self.assertEqual(leadership_gap.gap, 2)
        self.assertEqual(leadership_gap.severity, "important_gap")

    def test_gap_of_three_or_more_is_significant_gap(self):
        student = dict(FULL_STUDENT_VECTOR)
        weights = dict(FULL_UNIVERSITY_WEIGHTS)
        weights["research_fit"] = 10  # gap = 3
        result = compare_student_vector_to_university_weights(student, weights)
        research_gap = next(g for g in result.per_signal if g.signal == "research_fit")
        self.assertEqual(research_gap.gap, 3)
        self.assertEqual(research_gap.severity, "significant_gap")

    def test_missing_signal_on_either_side_is_insufficient_data_and_excluded_from_total(self):
        student = dict(FULL_STUDENT_VECTOR)
        student["olympiads"] = None
        weights = dict(FULL_UNIVERSITY_WEIGHTS)
        weights["portfolio"] = None
        result = compare_student_vector_to_university_weights(student, weights)
        self.assertEqual(result.signals_missing_data, 2)
        self.assertEqual(result.signals_compared, len(SIGNAL_NAMES) - 2)
        olympiads_gap = next(g for g in result.per_signal if g.signal == "olympiads")
        self.assertEqual(olympiads_gap.severity, "insufficient_data")
        self.assertIsNone(olympiads_gap.gap)
        portfolio_gap = next(g for g in result.per_signal if g.signal == "portfolio")
        self.assertEqual(portfolio_gap.severity, "insufficient_data")

    def test_missing_signal_from_dict_entirely_is_treated_as_insufficient_data(self):
        student = {name: 7 for name in SIGNAL_NAMES if name != "curiosity"}
        result = compare_student_vector_to_university_weights(student, FULL_UNIVERSITY_WEIGHTS)
        curiosity_gap = next(g for g in result.per_signal if g.signal == "curiosity")
        self.assertEqual(curiosity_gap.severity, "insufficient_data")

    def test_two_significant_gaps_yield_stretch_alignment(self):
        student = dict(FULL_STUDENT_VECTOR)
        weights = dict(FULL_UNIVERSITY_WEIGHTS)
        weights["research_fit"] = 10
        weights["olympiads"] = 10
        result = compare_student_vector_to_university_weights(student, weights)
        self.assertEqual(result.counts_by_severity["significant_gap"], 2)
        self.assertEqual(result.fit_band, "stretch_alignment")

    def test_three_significant_gaps_yield_high_stretch_alignment(self):
        student = dict(FULL_STUDENT_VECTOR)
        weights = dict(FULL_UNIVERSITY_WEIGHTS)
        weights["research_fit"] = 10
        weights["olympiads"] = 10
        weights["leadership"] = 10
        result = compare_student_vector_to_university_weights(student, weights)
        self.assertEqual(result.counts_by_severity["significant_gap"], 3)
        self.assertEqual(result.fit_band, "high_stretch_alignment")

    def test_only_important_gaps_within_threshold_is_good_alignment(self):
        student = dict(FULL_STUDENT_VECTOR)
        weights = dict(FULL_UNIVERSITY_WEIGHTS)
        weights["curiosity"] = 9  # gap = 2
        weights["leadership"] = 9  # gap = 2
        result = compare_student_vector_to_university_weights(student, weights)
        self.assertEqual(result.counts_by_severity["important_gap"], 2)
        self.assertEqual(result.counts_by_severity["significant_gap"], 0)
        self.assertEqual(result.fit_band, "good_alignment")

    def test_result_never_contains_probability_or_guarantee_language(self):
        result = compare_student_vector_to_university_weights(FULL_STUDENT_VECTOR, FULL_UNIVERSITY_WEIGHTS)
        forbidden = ("probability", "chance", "guarantee", "odds", "%")
        band_and_severities = result.fit_band + "".join(result.counts_by_severity.keys())
        for word in forbidden:
            self.assertNotIn(word, band_and_severities.lower())

    def test_all_signals_missing_still_returns_a_valid_named_band(self):
        empty = dict.fromkeys(SIGNAL_NAMES)
        result = compare_student_vector_to_university_weights(empty, empty)
        self.assertEqual(result.signals_compared, 0)
        self.assertEqual(result.signals_missing_data, len(SIGNAL_NAMES))
        # Documented caller contract: fit_band is only meaningful when
        # signals_compared > 0, but it must still resolve to one of the five
        # named bands rather than raising or returning something unexpected.
        self.assertIn(
            result.fit_band,
            {
                "strong_alignment",
                "good_alignment",
                "moderate_alignment",
                "stretch_alignment",
                "high_stretch_alignment",
            },
        )
