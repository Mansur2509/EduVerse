from django.test import SimpleTestCase

from services.university_service.services import best_sat_score, normalize_gpa_to_4


class NormalizeGpaTests(SimpleTestCase):
    def test_returns_none_when_gpa_missing(self):
        self.assertIsNone(normalize_gpa_to_4(None, "4.00"))

    def test_returns_none_when_scale_missing(self):
        self.assertIsNone(normalize_gpa_to_4("3.50", None))

    def test_returns_none_when_scale_is_zero(self):
        self.assertIsNone(normalize_gpa_to_4("3.50", "0"))

    def test_normalizes_to_4_scale(self):
        self.assertAlmostEqual(normalize_gpa_to_4("4.50", "5.00"), 3.6)

    def test_returns_same_value_when_already_on_4_scale(self):
        self.assertAlmostEqual(normalize_gpa_to_4("3.80", "4.00"), 3.8)

    def test_normalizes_with_clean_decimal_result(self):
        # 4.50 / 5.00 * 4.0 == 3.6 exactly in decimal arithmetic; float division can
        # land at 3.5999999999999996, so callers must round before threshold checks.
        self.assertEqual(round(normalize_gpa_to_4("4.50", "5.00"), 4), 3.6)


class BestSatScoreTests(SimpleTestCase):
    def test_returns_none_for_missing_key(self):
        self.assertIsNone(best_sat_score({}))

    def test_returns_none_for_non_dict(self):
        self.assertIsNone(best_sat_score(None))

    def test_reads_lowercase_key(self):
        self.assertEqual(best_sat_score({"sat": 1450}), 1450)

    def test_reads_uppercase_key(self):
        self.assertEqual(best_sat_score({"SAT": 1500}), 1500)

    def test_returns_none_for_non_numeric_value(self):
        self.assertIsNone(best_sat_score({"sat": "not-a-number"}))
