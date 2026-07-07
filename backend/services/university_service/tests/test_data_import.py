import csv
import tempfile
from pathlib import Path

from django.test import TestCase

from services.university_service.data_import import (
    ImportConfigurationError,
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
            "Majors": "Physics; Chemistry; Physics",
            "SAT 25th": "1400",
            "SAT 50th": "Not used",
            "SAT 75th": "1500",
            "IELTS Minimum": "6.5",
            "Average GPA": "3.80",
            "Acceptance Rate": "12.5",
            "QS World University Ranking": "42nd overall, QS WUR 2027",
            "Tuition": "$40,000",
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
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="")
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

    def test_parse_optional_int_extracts_leading_number(self):
        value, warning = parse_optional_int("1520")
        self.assertEqual(value, 1520)
        self.assertIsNone(warning)

    def test_parse_optional_int_warns_on_unparseable_text(self):
        value, warning = parse_optional_int("varies by program")
        self.assertIsNone(value)
        self.assertIsNotNone(warning)

    def test_parse_optional_decimal_extracts_first_number_from_prose(self):
        value, warning = parse_optional_decimal(
            "6.5 standard / 7.0 higher by course", max_digits=3, decimal_places=1
        )
        self.assertEqual(value, 6.5)
        self.assertIsNone(warning)

    def test_parse_optional_decimal_warns_on_out_of_range_value(self):
        value, warning = parse_optional_decimal("99999", max_digits=3, decimal_places=1)
        self.assertIsNone(value)
        self.assertIsNotNone(warning)

    def test_parse_score_0_10_rejects_out_of_range(self):
        value, warning = parse_score_0_10("15")
        self.assertIsNone(value)
        self.assertIsNotNone(warning)

    def test_parse_score_0_10_accepts_valid_range(self):
        value, warning = parse_score_0_10("7")
        self.assertEqual(value, 7)
        self.assertIsNone(warning)

    def test_parse_qs_ranking_extracts_rank_and_year(self):
        rank, year, warning = parse_qs_ranking("1st overall, QS WUR 2027")
        self.assertEqual(rank, 1)
        self.assertEqual(year, 2027)
        self.assertIsNone(warning)

    def test_split_majors_dedupes_case_insensitively(self):
        majors = split_majors("Physics; Chemistry; physics; Biology")
        self.assertEqual(majors, ["Physics", "Chemistry", "Biology"])

    def test_normalized_key_strips_trailing_parenthetical(self):
        key_a = normalized_university_key("Massachusetts Institute of Technology (MIT)", "USA")
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

    def test_missing_file_raises_configuration_error(self):
        with self.assertRaises(ImportConfigurationError):
            import_universities_data("C:/does/not/exist.csv", commit=False)

    def test_unsupported_extension_raises_configuration_error(self):
        path = self._write([sample_row()])
        renamed = path.rsplit(".", 1)[0] + ".docx"
        Path(path).rename(renamed)
        self._temp_files.append(renamed)
        with self.assertRaises(ImportConfigurationError):
            import_universities_data(renamed, commit=False)

    def test_dry_run_never_writes_to_the_database(self):
        path = self._write([sample_row()])
        summary = import_universities_data(path, commit=False)
        self.assertEqual(summary.created, 1)
        self.assertEqual(University.objects.count(), 0)

    def test_commit_creates_university_guidance_and_signal_rows(self):
        path = self._write([sample_row()])
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.created, 1)
        university = University.objects.get(name="Sample University")
        self.assertTrue(university.is_published)
        self.assertEqual(university.country, "Testland")
        self.assertEqual(university.majors_list, ["Physics", "Chemistry"])
        self.assertEqual(university.sat_p25, 1400)
        self.assertIsNone(university.sat_p50)  # "Not used" -> intentionally blank
        self.assertEqual(university.sat_p75, 1500)
        self.assertEqual(university.qs_ranking, 42)
        self.assertEqual(university.qs_ranking_year, 2027)

        guidance = UniversityGuidanceContext.objects.get(university=university)
        self.assertEqual(guidance.what_they_look_for, "Curiosity and rigor.")
        self.assertEqual(guidance.notes, "Internal admin note, never public.")
        self.assertIn("What They Look For", guidance.raw_context_json)

        signals = UniversitySignalWeights.objects.get(university=university)
        self.assertEqual(signals.profile_evidence_score, 8)
        self.assertEqual(signals.activities_score, 9)

    def test_missing_required_field_is_skipped_not_fatal(self):
        rows = [sample_row(Name="Good University"), sample_row(Name="", City="")]
        path = self._write(rows)
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.created, 1)
        self.assertEqual(summary.skipped_errors, 1)
        self.assertEqual(summary.missing_required, 1)
        self.assertEqual(University.objects.count(), 1)

    def test_existing_university_is_not_overwritten_without_update_existing_flag(self):
        University.objects.create(
            name="Sample University",
            country="Testland",
            city="Old City",
            slug="sample-university",
            official_website="https://old.example.edu/",
            is_published=True,
        )
        path = self._write([sample_row(**{"Official Website": "https://new.example.edu/"})])
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.skipped_existing, 1)
        self.assertEqual(summary.created, 0)
        university = University.objects.get(name="Sample University")
        self.assertEqual(university.official_website, "https://old.example.edu/")
        self.assertEqual(university.city, "Old City")
        # Guidance/signal rows are still populated -- nothing to protect there.
        self.assertTrue(UniversityGuidanceContext.objects.filter(university=university).exists())
        self.assertTrue(UniversitySignalWeights.objects.filter(university=university).exists())

    def test_existing_university_is_overwritten_with_update_existing_flag(self):
        University.objects.create(
            name="Sample University",
            country="Testland",
            city="Old City",
            slug="sample-university",
            official_website="https://old.example.edu/",
            is_published=True,
        )
        path = self._write([sample_row(**{"Official Website": "https://new.example.edu/"})])
        summary = import_universities_data(path, commit=True, update_existing=True)
        self.assertEqual(summary.updated, 1)
        university = University.objects.get(name="Sample University")
        self.assertEqual(university.official_website, "https://new.example.edu/")

    def test_limit_only_processes_first_n_rows(self):
        rows = [sample_row(Name=f"University {i}") for i in range(5)]
        path = self._write(rows)
        summary = import_universities_data(path, commit=False, limit=2)
        self.assertEqual(summary.rows_read, 2)

    def test_duplicate_keys_within_file_are_reported(self):
        rows = [sample_row(), sample_row()]
        path = self._write(rows)
        summary = import_universities_data(path, commit=False)
        self.assertEqual(summary.duplicate_keys_in_file, 1)

    def test_invalid_url_is_dropped_with_warning_not_stored(self):
        path = self._write([sample_row(**{"Official Website": "not a url"})])
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.created, 1)
        university = University.objects.get(name="Sample University")
        self.assertEqual(university.official_website, "")
        self.assertTrue(any("Official Website" in w for w in summary.warnings))

    def test_out_of_range_score_is_rejected_not_stored(self):
        path = self._write([sample_row(**{"Profile Evidence Score": "99"})])
        summary = import_universities_data(path, commit=True)
        university = University.objects.get(name="Sample University")
        signals = UniversitySignalWeights.objects.get(university=university)
        self.assertIsNone(signals.profile_evidence_score)
        self.assertTrue(any("Profile Evidence Score" in w for w in summary.warnings))

    def test_unparseable_ielts_text_is_preserved_in_testing_policy_notes(self):
        path = self._write(
            [sample_row(**{"IELTS Minimum": "No fixed IELTS minimum published; contact admissions"})]
        )
        import_universities_data(path, commit=True)
        university = University.objects.get(name="Sample University")
        self.assertIsNone(university.ielts_minimum)
        self.assertIn("No fixed IELTS minimum published", university.standardized_testing_policy_text)

    def test_tsv_file_is_supported(self):
        path = tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False, encoding="utf-8", newline="").name
        self._temp_files = getattr(self, "_temp_files", []) + [path]
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FULL_HEADERS, delimiter="\t")
            writer.writeheader()
            writer.writerow(sample_row())
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.created, 1)

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

    def test_one_bad_row_does_not_abort_the_whole_import(self):
        # A row that raises mid-processing (simulated via an absurd combination
        # that still parses) must not prevent later good rows from importing.
        rows = [sample_row(Name="", City=""), sample_row(Name="Second University")]
        path = self._write(rows)
        summary = import_universities_data(path, commit=True)
        self.assertEqual(summary.created, 1)
        self.assertTrue(University.objects.filter(name="Second University").exists())

    def test_no_ai_call_is_made_during_import(self):
        # Structural guard: the import module must never import the Gemini
        # gateway. A regression here would violate the "no AI calls" hard rule.
        import services.university_service.data_import as data_import_module

        source = Path(data_import_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("gemini", source.lower())
        self.assertNotIn("ai_gateway", source.lower())
