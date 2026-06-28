from django.test import SimpleTestCase

from services.university_service.seed_data import REAL_UNIVERSITIES

# Fields that represent an admissions/stat/cost/deadline data point and must
# therefore carry a verification record whenever they are set. Identity-ish
# fields (name, country, city, website/portal URLs, summary, institution
# type) are exempt since they are not "admissions/stat/cost/deadline" facts.
VERIFIABLE_FIELDS = {
    "test_policy",
    "acceptance_rate",
    "gpa_average",
    "sat_average",
    "sat_p25",
    "sat_p75",
    "ielts_minimum",
    "tuition_amount",
    "application_deadline",
    "scholarship_available",
    "essay_requirements",
    "qs_ranking",
}


class SeedDataIntegrityTests(SimpleTestCase):
    def test_every_verifiable_non_null_field_has_a_verification_record(self):
        failures = []
        for entry in REAL_UNIVERSITIES:
            verified_fields = {v["field_name"] for v in entry.get("verifications", [])}
            for field in VERIFIABLE_FIELDS:
                value = entry.get(field)
                if value is not None and value != "" and field not in verified_fields:
                    failures.append(f"{entry['slug']}.{field}")
        self.assertEqual(
            failures,
            [],
            f"These fields are set but missing a verification record: {failures}",
        )

    def test_every_verification_has_a_source_url_and_status(self):
        valid_statuses = {"verified", "partial", "estimated"}
        for entry in REAL_UNIVERSITIES:
            for verification in entry.get("verifications", []):
                self.assertTrue(
                    verification.get("source_url", "").startswith("http"),
                    f"{entry['slug']}.{verification['field_name']} has no valid source_url",
                )
                self.assertIn(
                    verification.get("status"),
                    valid_statuses,
                    f"{entry['slug']}.{verification['field_name']} has an invalid status",
                )

    def test_all_real_universities_have_unique_slugs(self):
        slugs = [entry["slug"] for entry in REAL_UNIVERSITIES]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_expected_university_count(self):
        self.assertEqual(len(REAL_UNIVERSITIES), 15)
