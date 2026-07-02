from datetime import date

from django.test import SimpleTestCase

from services.university_service.deadline_normalization import (
    CONFIDENCE_MISSING,
    CONFIDENCE_NORMALIZED,
    CONFIDENCE_SOURCE_ONLY,
    normalize_deadline_for_graduation_year,
)


class NormalizeDeadlineForGraduationYearTests(SimpleTestCase):
    def test_november_deadline_normalizes_to_year_before_graduation(self):
        result = normalize_deadline_for_graduation_year(date(2025, 11, 1), 2027)
        self.assertEqual(result.normalized_date, date(2026, 11, 1))
        self.assertEqual(result.normalized_year, 2026)
        self.assertEqual(result.confidence, CONFIDENCE_NORMALIZED)
        self.assertEqual(result.cycle_label, "2026-2027")

    def test_january_deadline_normalizes_to_graduation_year(self):
        result = normalize_deadline_for_graduation_year(date(2026, 1, 1), 2027)
        self.assertEqual(result.normalized_date, date(2027, 1, 1))
        self.assertEqual(result.normalized_year, 2027)
        self.assertEqual(result.cycle_label, "2026-2027")

    def test_december_deadline_for_later_graduation_year(self):
        result = normalize_deadline_for_graduation_year(date(2025, 12, 15), 2028)
        self.assertEqual(result.normalized_date, date(2027, 12, 15))
        self.assertEqual(result.normalized_year, 2027)

    def test_february_deadline_for_later_graduation_year(self):
        result = normalize_deadline_for_graduation_year(date(2026, 2, 15), 2028)
        self.assertEqual(result.normalized_date, date(2028, 2, 15))
        self.assertEqual(result.normalized_year, 2028)

    def test_boundary_months_august_and_july(self):
        august = normalize_deadline_for_graduation_year(date(2025, 8, 1), 2027)
        self.assertEqual(august.normalized_date, date(2026, 8, 1))
        july = normalize_deadline_for_graduation_year(date(2025, 7, 31), 2027)
        self.assertEqual(july.normalized_date, date(2027, 7, 31))

    def test_missing_graduation_year_keeps_source_only(self):
        result = normalize_deadline_for_graduation_year(date(2025, 11, 1), None)
        self.assertIsNone(result.normalized_date)
        self.assertIsNone(result.normalized_year)
        self.assertEqual(result.confidence, CONFIDENCE_SOURCE_ONLY)
        self.assertEqual(result.source_month, 11)
        self.assertEqual(result.source_day, 1)

    def test_missing_source_date_returns_missing(self):
        result = normalize_deadline_for_graduation_year(None, 2027)
        self.assertIsNone(result.normalized_date)
        self.assertIsNone(result.source_month)
        self.assertEqual(result.confidence, CONFIDENCE_MISSING)

    def test_missing_both_returns_missing(self):
        result = normalize_deadline_for_graduation_year(None, None)
        self.assertEqual(result.confidence, CONFIDENCE_MISSING)

    def test_leap_day_source_falls_back_to_feb_28_on_non_leap_year(self):
        # Feb 29, 2024 source deadline; graduation year 2025 -> normalized
        # year 2025 (Jan-Jul bucket), which is not a leap year.
        result = normalize_deadline_for_graduation_year(date(2024, 2, 29), 2025)
        self.assertEqual(result.normalized_date, date(2025, 2, 28))
        self.assertEqual(result.normalized_year, 2025)

    def test_leap_day_source_on_leap_normalized_year_keeps_feb_29(self):
        result = normalize_deadline_for_graduation_year(date(2024, 2, 29), 2028)
        self.assertEqual(result.normalized_date, date(2028, 2, 29))

    def test_display_date_prefers_normalized_over_source(self):
        result = normalize_deadline_for_graduation_year(date(2025, 11, 1), 2027)
        self.assertEqual(result.display_date, date(2026, 11, 1))

    def test_display_date_falls_back_to_source_when_no_graduation_year(self):
        result = normalize_deadline_for_graduation_year(date(2025, 11, 1), None)
        self.assertEqual(result.display_date, date(2025, 11, 1))
