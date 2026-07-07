"""Regression guard: the internal guidance/context layer and the system-only
scoring vector must never reach a student-facing API response, no matter
which university endpoint is used.
"""

from pathlib import Path

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from services.university_service.models import (
    University,
    UniversityGuidanceContext,
    UniversitySignalWeights,
)

User = get_user_model()

# Substrings that would only appear if a guidance/system field leaked into a
# response body. Deliberately distinctive (not generic words like "notes")
# so this check can't accidentally pass by coincidence.
FORBIDDEN_RESPONSE_MARKERS = (
    "guidance_context",
    "signal_weights",
    "recommendation_letters",
    "what_they_look_for",
    "preferred_student_profile",
    "who_they_seek",
    "student_traits_mentioned",
    "official_admissions_messaging",
    "institutional_values",
    "raw_context_json",
    "profile_evidence_score",
    "activities_score",
    "honors_olympiads_score",
    "research_experience_score",
    "portfolio_score",
    "subject_passion_score",
    "curiosity_score",
    "originality_score",
    "leadership_score",
    "community_impact_score",
    "research_fit_score",
    "olympiads_score",
    "profile_scoring_source",
    "SECRET-GUIDANCE-VALUE",
    "SECRET-SIGNAL-SOURCE",
)


def create_university_with_hidden_layers(slug="hidden-layer-university") -> University:
    university = University.objects.create(
        slug=slug,
        name="Hidden Layer University",
        country="Demoland",
        city="Sample City",
        official_website=f"https://example.com/{slug}",
        is_published=True,
    )
    UniversityGuidanceContext.objects.create(
        university=university,
        what_they_look_for="Students with strong research records.",
        notes="Internal-only admin note.",
        raw_context_json={"What They Look For": "Students with strong research records."},
    )
    UniversitySignalWeights.objects.create(
        university=university,
        profile_evidence_score=9,
        activities_score=7,
        profile_scoring_source="SECRET-SIGNAL-SOURCE",
    )
    return university


class UniversityDataLeakageTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="leakage-student", email="leakage-student@test.com", password="testpass123"
        )
        self.university = create_university_with_hidden_layers()
        self.client.force_authenticate(self.user)

    def test_university_detail_response_never_contains_guidance_or_signal_fields(self):
        response = self.client.get(f"/api/v1/universities/{self.university.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        for marker in FORBIDDEN_RESPONSE_MARKERS:
            self.assertNotIn(marker, body, f"leaked marker: {marker}")

    def test_university_list_response_never_contains_guidance_or_signal_fields(self):
        response = self.client.get("/api/v1/universities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        for marker in FORBIDDEN_RESPONSE_MARKERS:
            self.assertNotIn(marker, body, f"leaked marker: {marker}")

    def test_university_compare_response_never_contains_guidance_or_signal_fields(self):
        other = create_university_with_hidden_layers(slug="hidden-layer-university-two")
        response = self.client.get(f"/api/v1/universities/compare/?ids={self.university.id},{other.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        for marker in FORBIDDEN_RESPONSE_MARKERS:
            self.assertNotIn(marker, body, f"leaked marker: {marker}")

    def test_recommendations_response_never_contains_guidance_or_signal_fields(self):
        response = self.client.get("/api/v1/universities/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        for marker in FORBIDDEN_RESPONSE_MARKERS:
            self.assertNotIn(marker, body, f"leaked marker: {marker}")

    def test_shortlist_response_never_contains_guidance_or_signal_fields(self):
        self.client.post(f"/api/v1/universities/{self.university.slug}/shortlist/")
        response = self.client.get("/api/v1/universities/shortlist/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        for marker in FORBIDDEN_RESPONSE_MARKERS:
            self.assertNotIn(marker, body, f"leaked marker: {marker}")

    def test_serializers_module_never_references_hidden_models(self):
        # Structural guard: if a future change ever wires
        # UniversityGuidanceContext/UniversitySignalWeights into a public
        # serializer, this test fails even before an API test would catch it.
        import services.university_service.serializers as serializers_module

        source = Path(serializers_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("UniversityGuidanceContext", source)
        self.assertNotIn("UniversitySignalWeights", source)

    def test_public_university_fields_added_for_bulk_import_are_visible(self):
        # Sanity check the other direction: the *public* fields added for the
        # bulk import (columns 1-38) are genuinely served, not accidentally
        # excluded too.
        self.university.majors_list = ["Physics", "Chemistry"]
        self.university.admissions_cycle_target = "Fall 2027"
        self.university.save(update_fields=["majors_list", "admissions_cycle_target"])
        response = self.client.get(f"/api/v1/universities/{self.university.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["majors_list"], ["Physics", "Chemistry"])
        self.assertEqual(response.data["admissions_cycle_target"], "Fall 2027")
