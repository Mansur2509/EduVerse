from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from services.university_service.major_matching import (
    infer_major_clusters,
    match_programs_to_profile,
    score_program_fit,
)
from services.university_service.models import UniversityProgram, UniversitySubjectRanking
from services.university_service.tests.test_universities import create_university
from services.user_profile_service.models import (
    Olympiad,
    PortfolioProject,
    ResearchProject,
    Volunteer,
)
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


class MajorMatchingServiceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="major-match", email="major-match@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)

    def test_major_inference_supports_finance_ml_and_psychology(self):
        self.profile.intended_majors = ["Finance", "Machine Learning", "Psychology"]
        self.profile.save(update_fields=["intended_majors"])

        inference = infer_major_clusters(self.profile)

        self.assertIn(UniversityProgram.MajorCluster.BUSINESS_ECONOMICS_FINANCE, inference.clusters)
        self.assertIn(UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA, inference.clusters)
        self.assertIn(UniversityProgram.MajorCluster.PSYCHOLOGY_COGNITIVE_SCIENCE, inference.clusters)
        self.assertEqual(inference.confidence, "high")

    def test_law_politics_maps_to_ir_and_policy_clusters(self):
        self.profile.intended_majors = ["International Relations and Public Policy"]
        self.profile.save(update_fields=["intended_majors"])

        inference = infer_major_clusters(self.profile)

        self.assertIn(UniversityProgram.MajorCluster.LAW_POLITICS_IR, inference.clusters)
        self.assertIn(UniversityProgram.MajorCluster.PUBLIC_POLICY_SOCIAL_IMPACT, inference.clusters)

    def test_no_major_profile_returns_low_confidence_without_crashing(self):
        self.profile.intended_majors = []
        self.profile.intended_major = ""
        self.profile.interests = []
        self.profile.career_interests = []
        self.profile.save()

        inference = infer_major_clusters(self.profile)

        self.assertIsNone(inference.primary_major_cluster)
        self.assertEqual(inference.confidence, "low")
        self.assertIn("intended_major", inference.missing_data)
        self.assertIn("academic_interests", inference.missing_data)

    def test_profile_evidence_can_infer_cluster_without_declared_major(self):
        self.profile.intended_majors = []
        self.profile.intended_major = ""
        self.profile.save()
        ResearchProject.objects.create(
            user=self.user,
            title="Machine learning research",
            field="AI",
            research_question="How can models classify student behavior?",
        )

        inference = infer_major_clusters(self.profile)

        self.assertEqual(
            inference.primary_major_cluster,
            UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
        )
        self.assertEqual(inference.confidence, "medium")

    def test_program_fit_uses_evidence_without_dominating_academics(self):
        university = create_university("program-fit-academic-priority", acceptance_rate="40.00")
        program = UniversityProgram.objects.create(
            university=university,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            research_heavy=True,
            source_confidence=UniversityProgram.SourceConfidence.VERIFIED,
        )
        self.profile.intended_majors = ["Computer Science"]
        self.profile.gpa = "4.00"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1550}
        self.profile.save()

        strong_academics = score_program_fit(self.profile, program)

        weaker_user = User.objects.create_user(
            username="evidence-heavy", email="evidence-heavy@test.com", password="testpass123"
        )
        weaker_profile, _ = ensure_profile_records(weaker_user)
        weaker_profile.intended_majors = ["Computer Science"]
        weaker_profile.gpa = "2.40"
        weaker_profile.gpa_scale = "4.00"
        weaker_profile.test_scores = {"sat": 900}
        weaker_profile.save()
        ResearchProject.objects.create(user=weaker_user, title="AI research", field="AI")
        PortfolioProject.objects.create(
            user=weaker_user,
            title="Data app",
            tech_stack="Python, ML",
            description="Built a data-analysis prototype.",
        )
        Olympiad.objects.create(user=weaker_user, name="Math olympiad", subject="Math")

        evidence_heavy = score_program_fit(weaker_profile, program)

        self.assertGreater(strong_academics["program_fit_score"], evidence_heavy["program_fit_score"])
        self.assertIn("research_relevant", evidence_heavy["preparation_strengths"])
        self.assertIn("portfolio_relevant", evidence_heavy["preparation_strengths"])

    def test_subject_ranking_boosts_only_when_verified_ranking_exists(self):
        self.profile.intended_majors = ["Computer Science"]
        self.profile.save(update_fields=["intended_majors"])
        ranked_university = create_university("subject-ranked-university")
        ranked_program = UniversityProgram.objects.create(
            university=ranked_university,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            source_confidence=UniversityProgram.SourceConfidence.VERIFIED,
        )
        UniversitySubjectRanking.objects.create(
            university=ranked_university,
            program=ranked_program,
            subject_area="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            rank=20,
            source_name="QS Subject",
            source_url="https://example.com/subject",
            ranking_year=2026,
            last_verified_date=timezone.now().date(),
            confidence=UniversitySubjectRanking.Confidence.VERIFIED,
        )
        unranked_university = create_university("subject-unranked-university")
        unranked_program = UniversityProgram.objects.create(
            university=unranked_university,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            source_confidence=UniversityProgram.SourceConfidence.VERIFIED,
        )

        ranked = score_program_fit(self.profile, ranked_program)
        unranked = score_program_fit(self.profile, unranked_program)

        self.assertGreater(ranked["program_fit_score"], unranked["program_fit_score"])
        self.assertEqual(ranked["subject_ranking"]["rank"], 20)
        self.assertIsNone(unranked["subject_ranking"])

    def test_missing_program_data_returns_low_confidence_warning(self):
        university = create_university("no-program-match-data")

        summary = match_programs_to_profile(self.profile, university)

        self.assertFalse(summary["program_data_verified"])
        self.assertEqual(summary["confidence"], "low")
        self.assertEqual(summary["recommended_programs"], [])
        self.assertIn("program_level_data", summary["missing_data"])

    def test_unrelated_programs_are_not_reported_as_matches(self):
        self.profile.intended_majors = ["Finance"]
        self.profile.save(update_fields=["intended_majors"])
        university = create_university("unrelated-programs")
        UniversityProgram.objects.create(
            university=university,
            name="Fine Arts",
            major_cluster=UniversityProgram.MajorCluster.DESIGN_ARTS,
        )
        Volunteer.objects.create(user=self.user, title="Community tutoring")

        summary = match_programs_to_profile(self.profile, university)

        self.assertEqual(summary["recommended_programs"], [])
        self.assertTrue(summary["program_data_verified"])
        self.assertIn("profile_major_context", summary["missing_data"])
