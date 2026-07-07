from django.test import TestCase

from services.university_service.ai_context import get_university_ai_context
from services.university_service.models import (
    University,
    UniversityGuidanceContext,
    UniversitySignalWeights,
)


def create_full_university() -> University:
    university = University.objects.create(
        slug="context-university",
        name="Context University",
        country="Demoland",
        city="Sample City",
        official_website="https://example.com/context-university",
        is_published=True,
        profile_evidence_notes="Values transcript + prerequisites evidence.",
        activities_notes="Sustained field activities preferred.",
    )
    UniversityGuidanceContext.objects.create(
        university=university,
        recommendation_letters="Two academic references.",
        what_they_look_for="Academic fit and initiative.",
        preferred_student_profile="High marks and language readiness.",
        who_they_seek="Students with field output.",
        student_traits_mentioned="Curiosity; rigor; resilience.",
        official_admissions_messaging="Course fit and prerequisites.",
        student_life_page_signals="Clubs matched to field interest.",
        essay_themes="Course motivation; preparation.",
        research_leadership_themes="Build/test/publish measurable outcome.",
        personality_traits_mentioned="Disciplined curiosity.",
        academic_interests_mentioned="Architecture; Design.",
        institutional_values="Academic rigor; integrity.",
        sample_admitted_essays="Motivation letter, 500-1000 words.",
        notes="Internal admin-only note.",
    )
    UniversitySignalWeights.objects.create(university=university, profile_evidence_score=9)
    return university


class GetUniversityAiContextTests(TestCase):
    def test_unknown_purpose_raises_value_error(self):
        university = create_full_university()
        with self.assertRaises(ValueError):
            get_university_ai_context(university.id, "not_a_real_purpose")

    def test_missing_university_returns_not_found_without_raising(self):
        result = get_university_ai_context(999999, "essay_review")
        self.assertFalse(result["found"])
        self.assertEqual(result["fields"], {})

    def test_essay_review_returns_only_whitelisted_fields(self):
        university = create_full_university()
        result = get_university_ai_context(university.id, "essay_review")
        self.assertTrue(result["found"])
        self.assertIn("official_admissions_messaging", result["fields"])
        self.assertIn("sample_admitted_essays", result["fields"])
        self.assertIn("essay_themes", result["fields"])
        # Fields belonging to other purposes must not leak in.
        self.assertNotIn("recommendation_letters", result["fields"])
        self.assertNotIn("who_they_seek", result["fields"])
        self.assertNotIn("notes", result["fields"])  # admin-only, never any purpose

    def test_why_us_review_uses_the_same_fields_as_essay_review(self):
        university = create_full_university()
        essay = get_university_ai_context(university.id, "essay_review")
        why_us = get_university_ai_context(university.id, "why_us_review")
        self.assertEqual(set(essay["fields"]), set(why_us["fields"]))

    def test_fit_analysis_returns_only_whitelisted_fields(self):
        university = create_full_university()
        result = get_university_ai_context(university.id, "fit_analysis")
        self.assertIn("what_they_look_for", result["fields"])
        self.assertIn("preferred_student_profile", result["fields"])
        self.assertIn("who_they_seek", result["fields"])
        self.assertNotIn("recommendation_letters", result["fields"])
        self.assertNotIn("sample_admitted_essays", result["fields"])

    def test_recommendation_prep_returns_only_whitelisted_fields(self):
        university = create_full_university()
        result = get_university_ai_context(university.id, "recommendation_prep")
        self.assertIn("recommendation_letters", result["fields"])
        self.assertIn("what_they_look_for", result["fields"])
        self.assertIn("student_traits_mentioned", result["fields"])
        self.assertNotIn("institutional_values", result["fields"])

    def test_profile_improvement_combines_public_and_guidance_fields(self):
        university = create_full_university()
        result = get_university_ai_context(university.id, "profile_improvement")
        self.assertIn("profile_evidence_notes", result["fields"])
        self.assertIn("activities_notes", result["fields"])
        self.assertIn("research_leadership_themes", result["fields"])
        self.assertNotIn("what_they_look_for", result["fields"])

    def test_never_includes_system_signal_scores(self):
        university = create_full_university()
        for purpose in ("essay_review", "why_us_review", "fit_analysis", "recommendation_prep", "profile_improvement"):
            result = get_university_ai_context(university.id, purpose)
            self.assertNotIn("profile_evidence_score", result["fields"])
            serialized_keys = "".join(result["fields"].keys())
            self.assertNotIn("score", serialized_keys)

    def test_missing_guidance_context_returns_empty_fields_not_error(self):
        university = University.objects.create(
            slug="no-guidance-university",
            name="No Guidance University",
            country="Demoland",
            city="Sample City",
            official_website="https://example.com/no-guidance-university",
            is_published=True,
        )
        result = get_university_ai_context(university.id, "fit_analysis")
        self.assertTrue(result["found"])
        self.assertEqual(result["fields"], {})
