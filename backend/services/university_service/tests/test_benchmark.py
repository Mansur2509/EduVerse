from statistics import mean

from django.contrib.auth import get_user_model
from django.test import TestCase

from services.university_service.benchmark import (
    BENCHMARK_SOURCE_COUNTRY_AVERAGE,
    BENCHMARK_SOURCE_DREAM_UNIVERSITIES,
    BENCHMARK_SOURCE_GLOBAL_AVERAGE,
    BENCHMARK_SOURCE_GLOBAL_MAJOR_AVERAGE,
    BENCHMARK_SOURCE_MAJOR_COUNTRY_AVERAGE,
    BENCHMARK_SOURCE_UNAVAILABLE,
    resolve_benchmark,
)
from services.university_service.models import UniversityProgram, UniversitySignalWeights
from services.university_service.tests.test_universities import create_university
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()

ALL_TENS = {
    "profile_evidence_score": 10,
    "activities_score": 10,
    "honors_olympiads_score": 10,
    "research_experience_score": 10,
    "portfolio_score": 10,
    "subject_passion_score": 10,
    "curiosity_score": 10,
    "originality_score": 10,
    "leadership_score": 10,
    "community_impact_score": 10,
    "research_fit_score": 10,
    "olympiads_score": 10,
}


class ResolveBenchmarkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="benchmarkchain", email="benchmarkchain@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)

    def _make_university(self, slug, *, country, score, cluster=None, program=True, **academic_overrides):
        university = create_university(slug, country=country, **academic_overrides)
        UniversitySignalWeights.objects.create(university=university, **{k: score for k in ALL_TENS})
        if program and cluster:
            UniversityProgram.objects.create(
                university=university, name=f"{slug} program", major_cluster=cluster
            )
        return university

    def test_no_data_anywhere_returns_unavailable(self):
        result = resolve_benchmark(self.profile)
        self.assertEqual(result.source, BENCHMARK_SOURCE_UNAVAILABLE)
        self.assertEqual(result.sample_size, 0)
        self.assertEqual(result.scores, {})

    def test_dream_universities_used_first_when_available(self):
        self.profile.target_universities = ["Dream U 1", "Dream U 2", "Dream U 3"]
        self.profile.save()
        for i in range(3):
            university = create_university(f"dream-u-{i}", name=f"Dream U {i + 1}")
            UniversitySignalWeights.objects.create(university=university, **ALL_TENS)
        # Also seed unrelated global universities that should be ignored while
        # the dream-university tier has enough data.
        for i in range(5):
            self._make_university(f"other-{i}", country="Global Land", score=2)

        result = resolve_benchmark(self.profile)
        self.assertEqual(result.source, BENCHMARK_SOURCE_DREAM_UNIVERSITIES)
        self.assertEqual(result.sample_size, 3)
        self.assertEqual(result.scores["activities"], 10)

    def test_major_and_country_fallback_used_when_no_dream_universities(self):
        self.profile.intended_majors = ["Computer Science"]
        self.profile.target_countries = ["United States"]
        self.profile.save()
        for i in range(3):
            self._make_university(
                f"cs-us-{i}",
                country="United States",
                score=8,
                cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            )
        # Non-matching country/major noise.
        for i in range(3):
            self._make_university(f"noise-{i}", country="Kenya", score=1)

        result = resolve_benchmark(self.profile)
        self.assertEqual(result.source, BENCHMARK_SOURCE_MAJOR_COUNTRY_AVERAGE)
        self.assertEqual(result.sample_size, 3)
        self.assertEqual(result.scores["activities"], 8)

    def test_country_fallback_used_when_major_country_tier_too_thin(self):
        self.profile.intended_majors = ["Computer Science"]
        self.profile.target_countries = ["United States"]
        self.profile.save()
        # Only 1 CS university in the US -- below MINIMUM_BENCHMARK_SAMPLE_SIZE.
        self._make_university(
            "lonely-cs-us",
            country="United States",
            score=9,
            cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
        )
        for i in range(3):
            self._make_university(f"us-general-{i}", country="United States", score=6)

        result = resolve_benchmark(self.profile)
        self.assertEqual(result.source, BENCHMARK_SOURCE_COUNTRY_AVERAGE)
        self.assertEqual(result.sample_size, 4)

    def test_global_major_fallback_used_when_no_country_preference(self):
        self.profile.intended_majors = ["Computer Science"]
        self.profile.target_countries = []
        self.profile.save()
        for i in range(3):
            self._make_university(
                f"cs-global-{i}",
                country=f"Country{i}",
                score=7,
                cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            )

        result = resolve_benchmark(self.profile)
        self.assertEqual(result.source, BENCHMARK_SOURCE_GLOBAL_MAJOR_AVERAGE)
        self.assertEqual(result.sample_size, 3)

    def test_global_average_used_as_last_resort(self):
        self.profile.intended_majors = []
        self.profile.target_countries = []
        self.profile.save()
        for i in range(3):
            self._make_university(f"anywhere-{i}", country=f"Land{i}", score=5)

        result = resolve_benchmark(self.profile)
        self.assertEqual(result.source, BENCHMARK_SOURCE_GLOBAL_AVERAGE)
        self.assertEqual(result.sample_size, 3)

    def test_invalid_and_missing_values_are_ignored_not_zeroed(self):
        self.profile.target_universities = ["Partial U 1", "Partial U 2", "Partial U 3"]
        self.profile.save()
        for i in range(3):
            university = create_university(f"partial-u-{i}", name=f"Partial U {i + 1}")
            UniversitySignalWeights.objects.create(
                university=university,
                profile_evidence_score=8,
                activities_score=None,  # missing -- must not count as 0
            )

        result = resolve_benchmark(self.profile)
        self.assertEqual(result.source, BENCHMARK_SOURCE_DREAM_UNIVERSITIES)
        self.assertEqual(result.scores["profile_evidence"], 8)
        self.assertNotIn("activities", result.scores)

    def test_academic_numbers_averaged_alongside_signal_dimensions(self):
        self.profile.target_universities = ["Academic U 1", "Academic U 2", "Academic U 3"]
        self.profile.save()
        gpas = [3.0, 3.6, 3.9]
        for i, gpa in enumerate(gpas):
            university = create_university(f"academic-u-{i}", name=f"Academic U {i + 1}", gpa_average=gpa)
            UniversitySignalWeights.objects.create(university=university, **ALL_TENS)

        result = resolve_benchmark(self.profile)
        self.assertAlmostEqual(result.academic["gpa_average"], round(mean(gpas), 2))

    def test_never_imports_or_calls_any_ai_client(self):
        import services.university_service.benchmark as benchmark_module

        source = benchmark_module.__file__
        with open(source, encoding="utf-8") as handle:
            content = handle.read()
        self.assertNotIn("gemini", content.lower())
        self.assertNotIn("ai_gateway", content.lower())
