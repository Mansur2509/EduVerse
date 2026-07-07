import csv
import tempfile
from pathlib import Path

from django.test import TestCase

from services.university_service.data_import import (
    ImportConfigurationError,
    clean_raw_cell,
    import_universities_data,
    normalized_university_key,
    parse_optional_decimal,
    parse_optional_int,
    parse_qs_ranking,
    parse_score_0_10,
    split_majors,
)
from services.university_service.models import (
    University,
    UniversityDataImportBatch,
    UniversityDataImportRowLog,
    UniversityGuidanceContext,
    UniversitySignalWeights,
)

FULL_HEADERS = [
    "Name",
    "Country",
    "City",
    "Official Website",
    "Admissions URL",
    "Admissions Website",
    "Financial Aid Website",
    "Application Portal",
    "International Students Office",
    "Virtual Info Session",
    "Majors",
    "Deadlines",
    "Admissions Cycle Target",
    "Standardized Testing Policy",
    "SAT 25th",
    "SAT 50th",
    "SAT 75th",
    "IELTS Minimum",
    "IELTS Competitive",
    "Average GPA",
    "Acceptance Rate",
    "QS World University Ranking",
    "QS Overall Score",
    "Tuition",
    "Scholarships",
    "Need-based Aid",
    "Merit Scholarship",
    "Other Scholarships",
    "Scholarship Links",
    "AP Recommendations by Major",
    "Application Requirements",
    "Essays",
    "Profile Evidence",
    "Activities",
    "Honors / Olympiads",
    "Research Experience",
    "Portfolio",
    "Essay Drafts",
    "Recommendation Letters",
    "What They Look For",
    "Preferred Student Profile",
    "Who They Seek",
    "Student Traits Mentioned by University",
    "Alumni Profile Evidence",
    "Published Admitted Student Essays",
    "Official Admissions Messaging",
    "Student Life Page Signals",
    "Graduate/Alumni Outcomes",
    "Sample Admitted Essays",
    "Essay Themes",
    "Research/Leadership Themes",
    "Personality Traits Mentioned",
    "Academic Interests Mentioned",
    "Institutional Values",
    "Source URLs",
    "Last Verified Date",
    "Verification Status",
    "Data Source",
    "Notes",
    "Profile Evidence Score",
    "Activities Score",
    "Honors / Olympiads Score",
    "Research Experience Score",
    "Portfolio Score",
    "Subject Passion Score",
    "Curiosity Score",
    "Originality Score",
    "Leadership Score",
    "Community Impact Score",
    "Research Fit Score",
    "Olympiads Score",
    "Profile Scoring Source",
]


def sample_row(**overrides) -> dict:
    row = {header: "" for header in FULL_HEADERS}
    row.update(
        {
            "Name": "Sample University",
            "Country": "Testland",
            "City": "Test City",
            "Official Website": "https://sample.example.edu/",
            "Admissions URL": "https://sample.example.edu/admissions?utm_source=test",
            "Majors": "Physics; Chemistry; Physics",
            "Deadlines": "Regular Decision: January 5",
            "SAT 25th": "1400",
            "SAT 50th": "1450",
            "SAT 75th": "1500",
            "IELTS Minimum": "6.5",
            "Average GPA": "3.80",
            "Acceptance Rate": "12.5%",
            "QS World University Ranking": "42nd overall, QS WUR 2027",
            "Tuition": "$40,000",
            "Scholarships": "Dean Scholarship",
            "What They Look For": "Curiosity and rigor.",
            "Notes": "Internal admin note, never public.",
            "Last Verified Date": "2026-01-15",
            "Profile Evidence Score": "8",
            "Activities Score": "9",
        }
    )
    row.update(overrides)
    return row


def write_csv(rows: list[dict], *, headers: list[str] | None = None) -> str:
    headers = headers or FULL_HEADERS
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8",
        newline="",
    )
    writer = csv.DictWriter(handle, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({header: row.get(header, "") for header in headers})
    handle.close()
    return handle.name


class ParsingHelperTests(TestCase):
    def test_parse_optional_int_treats_not_used_as_intentional_blank(self):
        value, warning = parse_optional_int("Not used")
        self.assertIsNone(value)
        self.assertIsNone(warning)

    def test_parse_optional_int_extracts_plain_number(self):
        value, warning = parse_optional_int("1520")
        self.assertEqual(value, 1520)
        self.assertIsNone(warning)

    def test_parse_optional_decimal_rejects_prose(self):
        value, warning = parse_optional_decimal(
            "6.5 standard / 7.0 higher by course",
            max_digits=3,
            decimal_places=1,
        )
        self.assertIsNone(value)
        self.assertIsNotNone(warning)

    def test_parse_score_0_10_rejects_out_of_range(self):
        value, warning = parse_score_0_10("15")
        self.assertIsNone(value)
        self.assertIsNotNone(warning)

    def test_parse_qs_ranking_extracts_rank_and_year(self):
        rank, year, warning = parse_qs_ranking("1st overall, QS WUR 2027")
        self.assertEqual(rank, 1)
        self.assertEqual(year, 2027)
        self.assertIsNone(warning)

    def test_split_majors_dedupes_case_insensitively(self):
        majors = split_majors("Physics; Chemistry; physics; Biology")
        self.assertEqual(majors, ["Physics", "Chemistry", "Biology"])

    def test_normalized_key_handles_safe_aliases(self):
        key_a = normalized_university_key("MIT", "USA")
        key_b = normalized_university_key("Massachusetts Institute of Technology", "usa")
        self.assertEqual(key_a, key_b)


class ImportUniversitiesDataTests(TestCase):
    def tearDown(self):
        for path in getattr(self, "_temp_files", []):
            Path(path).unlink(missing_ok=True)

    def _write(self, rows: list[dict], **kwargs) -> str:
        path = write_csv(rows, **kwargs)
        self._temp_files = getattr(self, "_temp_files", []) + [path]
        return path

    def test_missing_required_columns_raises_configuration_error(self):
        path = self._write([sample_row()], headers=["Name", "City"])
        with self.assertRaises(ImportConfigurationError):
            import_universities_data(path, commit=False)

    def test_dry_run_never_writes_to_the_database(self):
        path = self._write([sample_row()])
        summary = import_universities_data(path)
        self.assertEqual(summary.created, 1)
        self.assertEqual(University.objects.count(), 0)
        self.assertEqual(UniversityDataImportBatch.objects.count(), 0)

    def test_commit_creates_university_guidance_signal_and_row_log(self):
        path = self._write([sample_row()])
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.created, 1)
        university = University.objects.get(name="Sample University")
        self.assertTrue(university.is_published)
        self.assertEqual(university.majors_list, ["Physics", "Chemistry"])
        self.assertEqual(university.sat_p25, 1400)
        self.assertEqual(university.sat_p50, 1450)
        self.assertEqual(university.qs_ranking, 42)
        self.assertEqual(university.qs_ranking_year, 2027)
        self.assertEqual(university.admissions_url, "https://sample.example.edu/admissions")

        guidance = UniversityGuidanceContext.objects.get(university=university)
        self.assertEqual(guidance.what_they_look_for, "Curiosity and rigor.")
        self.assertEqual(guidance.notes, "Internal admin note, never public.")

        signals = UniversitySignalWeights.objects.get(university=university)
        self.assertEqual(signals.profile_evidence_score, 8)
        self.assertEqual(signals.activities_score, 9)
        self.assertEqual(UniversityDataImportRowLog.objects.count(), 1)

    def test_bad_gpa_comment_cell_is_not_imported(self):
        bad = "average for this country is 4.5 but in other system it is a 3.6"
        cell = clean_raw_cell(bad, "Average GPA")
        self.assertIn(cell.status, {"skipped_generic_country_average", "skipped_commentary"})
        path = self._write([sample_row(**{"Average GPA": bad})])
        summary = import_universities_data(path, commit=True)
        university = University.objects.get(name="Sample University")
        self.assertIsNone(university.gpa_average)
        self.assertGreaterEqual(summary.generic_country_average_cells, 1)

    def test_placeholder_deadline_is_not_imported(self):
        deadline = "2026-2027 cycle: program/intake-specific deadlines; verify on official page"
        path = self._write([sample_row(Deadlines=deadline)])
        summary = import_universities_data(path, commit=True)
        university = University.objects.get(name="Sample University")
        self.assertEqual(university.deadlines_text, "")
        self.assertGreaterEqual(summary.placeholder_cells + summary.commentary_cells, 1)

    def test_generic_major_comment_is_not_imported(self):
        majors = "Program list varies by faculty/degree; verify exact undergraduate majors/courses."
        path = self._write([sample_row(Majors=majors)])
        import_universities_data(path, commit=True)
        university = University.objects.get(name="Sample University")
        self.assertEqual(university.majors_list, [])

    def test_valid_majors_are_accepted_normalized_and_deduped(self):
        path = self._write([sample_row(Majors="Computer Science; Economics; Chemical Engineering")])
        import_universities_data(path, commit=True)
        university = University.objects.get(name="Sample University")
        self.assertEqual(
            university.majors_list,
            ["Computer Science", "Economics", "Chemical Engineering"],
        )

    def test_existing_university_missing_field_is_filled_by_default(self):
        University.objects.create(
            name="Massachusetts Institute of Technology",
            country="USA",
            city="Cambridge",
            slug="mit",
            official_website="https://mit.edu/",
            is_published=True,
        )
        path = self._write(
            [
                sample_row(
                    Name="MIT",
                    Country="USA",
                    City="Cambridge",
                    **{"Official Website": "https://mit.edu/"},
                    **{"IELTS Minimum": "7.0"},
                )
            ]
        )
        summary = import_universities_data(path, commit=True)
        university = University.objects.get(slug="mit")
        self.assertEqual(university.ielts_minimum, 7.0)
        self.assertEqual(summary.updated, 1)

    def test_existing_good_field_conflict_is_not_overwritten(self):
        University.objects.create(
            name="Massachusetts Institute of Technology",
            country="USA",
            city="Cambridge",
            slug="mit",
            official_website="https://mit.edu/",
            ielts_minimum="7.0",
            is_published=True,
        )
        path = self._write(
            [
                sample_row(
                    Name="MIT",
                    Country="USA",
                    City="Cambridge",
                    **{"Official Website": "https://mit.edu/"},
                    **{"IELTS Minimum": "6.0"},
                )
            ]
        )
        summary = import_universities_data(path, commit=True)
        university = University.objects.get(slug="mit")
        self.assertEqual(university.ielts_minimum, 7.0)
        self.assertEqual(summary.conflicts, 1)
        self.assertEqual(summary.manual_review_entries[0].conflict_fields, "University.ielts_minimum")

    def test_duplicate_university_row_is_skipped_safely(self):
        rows = [sample_row(), sample_row(**{"IELTS Minimum": "7.0"})]
        path = self._write(rows)
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.created, 1)
        self.assertEqual(summary.skipped_duplicate_rows, 1)
        self.assertEqual(University.objects.count(), 1)

    def test_same_file_imported_twice_skips_already_imported_rows(self):
        path = self._write([sample_row()])
        first = import_universities_data(path, commit=True)
        second = import_universities_data(path, commit=True)
        self.assertEqual(first.created, 1)
        self.assertEqual(second.already_imported_rows, 1)
        self.assertEqual(UniversityDataImportRowLog.objects.count(), 1)

    def test_invalid_url_is_dropped_not_stored(self):
        path = self._write([sample_row(**{"Official Website": "see admissions website"})])
        summary = import_universities_data(path, commit=True)
        university = University.objects.get(name="Sample University")
        self.assertEqual(university.official_website, "")
        self.assertGreaterEqual(summary.placeholder_cells, 1)

    def test_valid_url_is_accepted_and_tracking_is_stripped(self):
        path = self._write([sample_row(**{"Admissions URL": "https://mitadmissions.org/apply/?utm_source=x"})])
        import_universities_data(path, commit=True)
        university = University.objects.get(name="Sample University")
        self.assertEqual(university.admissions_url, "https://mitadmissions.org/apply/")

    def test_audit_and_manual_review_csv_outputs_are_written(self):
        University.objects.create(
            name="Sample University",
            country="Testland",
            city="Test City",
            slug="sample-university",
            official_website="https://sample.example.edu/",
            ielts_minimum="7.0",
            is_published=True,
        )
        path = self._write([sample_row(**{"IELTS Minimum": "6.0"})])
        audit_path = tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name
        review_path = tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name
        self._temp_files.extend([audit_path, review_path])
        import_universities_data(
            path,
            commit=False,
            audit_out=audit_path,
            manual_review_out=review_path,
        )
        self.assertIn("field_name", Path(audit_path).read_text(encoding="utf-8"))
        self.assertIn("conflict_fields", Path(review_path).read_text(encoding="utf-8"))

    def test_xlsx_file_is_supported(self):
        openpyxl = __import__("openpyxl")
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(FULL_HEADERS)
        row = sample_row()
        sheet.append([row.get(header, "") for header in FULL_HEADERS])
        path = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
        workbook.save(path)
        self._temp_files = getattr(self, "_temp_files", []) + [path]
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.created, 1)

    def test_no_provider_call_is_made_during_import(self):
        import services.university_service.data_import as data_import_module

        source = Path(data_import_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("gemini", source.lower())
        self.assertNotIn("ai_gateway", source.lower())
