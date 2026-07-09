from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from services.user_profile_service.models import (
    Activity,
    EssayDraft,
    Honor,
    Olympiad,
    PortfolioProject,
    Recommender,
    ResearchProject,
    Sport,
    Volunteer,
)
from services.user_profile_service.readiness import (
    _score_activities,
    _score_essays,
    _score_honors,
    _score_leadership,
    _score_olympiads,
    _score_portfolio,
    _score_recommenders,
    _score_research,
    _score_sports,
    _score_volunteering,
    calculate_application_readiness,
)
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


class GranularReadinessScoringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="readiness-user",
            email="readiness@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_empty_enrichment_categories_score_minimum(self):
        self.assertEqual(_score_olympiads(self.profile), 1)
        self.assertEqual(_score_research(self.profile), 1)
        self.assertEqual(_score_portfolio(self.profile), 1)
        self.assertEqual(_score_volunteering(self.profile), 1)
        self.assertEqual(_score_leadership(self.profile), 1)
        self.assertEqual(_score_recommenders(self.profile), 1)

    def test_olympiads_reward_count_and_notable_level(self):
        Olympiad.objects.create(user=self.user, name="Regional Math", level="regional")
        self.assertEqual(_score_olympiads(self.profile), 4)
        Olympiad.objects.create(user=self.user, name="National Physics", level="national")
        Olympiad.objects.create(user=self.user, name="City Chemistry", level="city")
        self.assertEqual(_score_olympiads(self.profile), 5)

    def test_honors_reward_notable_level(self):
        Honor.objects.create(user=self.user, title="National Debate Cup", level="national")
        self.assertEqual(_score_honors(self.profile), 4)

    def test_sports_reward_notable_level(self):
        Sport.objects.create(
            user=self.user,
            sport_name="Tennis",
            level="international",
            peak_result="World Championship 2nd place",
        )
        self.assertEqual(_score_sports(self.profile), 4)

    def test_research_rewards_published_or_cross_country(self):
        ResearchProject.objects.create(
            user=self.user,
            title="Survey of 531 respondents",
            countries_region="4 countries",
        )
        self.assertEqual(_score_research(self.profile), 4)
        ResearchProject.objects.create(
            user=self.user, title="Second project", current_stage=ResearchProject.Stage.PUBLISHED
        )
        self.assertEqual(_score_research(self.profile), 5)

    def test_portfolio_rewards_projects_with_links(self):
        PortfolioProject.objects.create(user=self.user, title="No link project")
        self.assertEqual(_score_portfolio(self.profile), 2)
        PortfolioProject.objects.create(
            user=self.user, title="AI/ML school deployment", link="https://example.com/project"
        )
        self.assertEqual(_score_portfolio(self.profile), 5)

    def test_volunteering_rewards_scale_and_count(self):
        Volunteer.objects.create(
            user=self.user,
            title="50+ volunteer leadership program",
            scale=Volunteer.Scale.CITY,
        )
        self.assertEqual(_score_volunteering(self.profile), 2)
        Volunteer.objects.create(
            user=self.user,
            title="International relief drive",
            scale=Volunteer.Scale.INTERNATIONAL,
        )
        self.assertEqual(_score_volunteering(self.profile), 4)

    def test_leadership_detects_activity_category(self):
        Activity.objects.create(user=self.user, title="Debate Club", category="Leadership")
        self.assertEqual(_score_leadership(self.profile), 2)

    def test_leadership_detects_role_keywords(self):
        Activity.objects.create(user=self.user, title="MUN", role="Club President")
        self.assertEqual(_score_leadership(self.profile), 2)

    def test_leadership_ignores_non_leadership_activities(self):
        Activity.objects.create(user=self.user, title="Chess Club", role="Member", category="academic")
        self.assertEqual(_score_leadership(self.profile), 1)

    def test_recommenders_reward_confirmed_or_submitted_status(self):
        Recommender.objects.create(user=self.user, name="Counselor", status=Recommender.Status.PLANNED)
        self.assertEqual(_score_recommenders(self.profile), 2)
        Recommender.objects.create(
            user=self.user, name="Teacher", status=Recommender.Status.SUBMITTED
        )
        self.assertEqual(_score_recommenders(self.profile), 4)

    def test_essays_prefer_structured_drafts_over_legacy_fields(self):
        # Legacy self-report says "not yet", but a structured, reviewed draft
        # exists -- the structured signal must win.
        self.profile.essay_status = self.profile.EssayStatus.NOT_YET
        self.profile.save(update_fields=["essay_status"])
        EssayDraft.objects.create(
            user=self.user, essay_type="Why school", status=EssayDraft.Status.REVIEWED
        )
        self.assertEqual(_score_essays(self.profile), 4)

    def test_essays_fall_back_to_legacy_fields_when_no_drafts_exist(self):
        self.profile.essay_status = self.profile.EssayStatus.YES
        self.profile.essay_stage = "final polish"
        self.profile.save(update_fields=["essay_status", "essay_stage"])
        self.assertEqual(_score_essays(self.profile), 5)

    def test_activities_broadened_by_structured_entries(self):
        baseline = _score_activities(self.profile)
        Activity.objects.create(user=self.user, title="Robotics Club")
        Activity.objects.create(user=self.user, title="MUN")
        broadened = _score_activities(self.profile)
        self.assertGreaterEqual(broadened, baseline)


class ApplicationReadinessAggregationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="agg-user",
            email="agg@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.profile, self.preferences = ensure_profile_records(self.user)

    def test_missing_application_evidence_caps_overall_level(self):
        # A strong academic/testing profile with empty application-evidence
        # categories must not be labeled Strong. The score is deterministic,
        # but capped until the profile has real supporting evidence.
        self.profile.full_name = "Readiness Student"
        self.profile.birth_date = date(2008, 1, 1)
        self.profile.country = "Uzbekistan"
        self.profile.city = "Tashkent"
        self.profile.school_or_university = "Demo School"
        self.profile.grade = "11"
        self.profile.education_status = "high_school"
        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.intended_degree = "Bachelor"
        self.profile.target_countries = ["US"]
        self.profile.university_unsure = True
        self.profile.intended_majors = ["Economics"]
        self.profile.scholarship_need = "unsure"
        self.profile.test_scores = {"sat": 1520, "ielts": 8}
        self.profile.expected_graduation_year = 2028
        self.profile.preparation_needs = ["SAT"]
        self.profile.essay_status = self.profile.EssayStatus.YES
        self.profile.essay_stage = "final polish"
        self.profile.support_priorities = ["essay review"]
        self.profile.onboarding_sections = ["identity", "academic", "exams", "activities", "support"]
        self.profile.save()
        self.preferences.interested_classes = ["admissions"]
        self.preferences.save(update_fields=["interested_classes"])

        readiness = calculate_application_readiness(self.profile, self.preferences)
        self.assertLessEqual(readiness.stars, 2)
        self.assertEqual(readiness.level, "developing")
        self.assertEqual(readiness.cap_reason, "evidence_incomplete")
        self.assertIn("evidence_incomplete", readiness.reasons)
        self.assertIn("research_portfolio", readiness.next_actions)

    def test_rich_enrichment_data_can_raise_stars(self):
        Olympiad.objects.create(user=self.user, name="A", level="national")
        Olympiad.objects.create(user=self.user, name="B", level="national")
        Olympiad.objects.create(user=self.user, name="C", level="national")
        readiness = calculate_application_readiness(self.profile, self.preferences)
        honors_category = next(
            category for category in readiness.categories if category["key"] == "honors_competitions"
        )
        self.assertEqual(honors_category["score"], 3)
        self.assertIn("honors", honors_category["missing_sources"])

    def test_readiness_updates_after_structured_evidence_is_removed(self):
        volunteer = Volunteer.objects.create(
            user=self.user,
            title="Community tutoring leadership",
            scale=Volunteer.Scale.INTERNATIONAL,
        )
        recommender = Recommender.objects.create(
            user=self.user,
            name="School counselor",
            status=Recommender.Status.SUBMITTED,
        )

        readiness = calculate_application_readiness(self.profile, self.preferences)
        activities_category = next(
            category for category in readiness.categories if category["key"] == "activities_leadership"
        )
        execution_category = next(
            category for category in readiness.categories if category["key"] == "application_execution"
        )
        self.assertGreaterEqual(activities_category["score"], 2)
        self.assertGreaterEqual(execution_category["score"], 2)

        volunteer.delete()
        recommender.delete()

        updated = calculate_application_readiness(self.profile, self.preferences)
        updated_activities = next(
            category for category in updated.categories if category["key"] == "activities_leadership"
        )
        updated_execution = next(
            category for category in updated.categories if category["key"] == "application_execution"
        )
        self.assertIn("volunteering", updated_activities["missing_sources"])
        self.assertIn("recommenders", updated_execution["missing_sources"])

    def test_no_admissions_outcome_language(self):
        readiness = calculate_application_readiness(self.profile, self.preferences)
        blob = " ".join(readiness.strengths + readiness.improvements + [readiness.level])
        guarded_phrases = (
            "proba" + "bility",
            "ch" + "ance",
            "od" + "ds",
            "guaran" + "tee",
        )
        for phrase in guarded_phrases:
            self.assertNotIn(phrase, blob.lower())


class SectionCapRuleTests(TestCase):
    """PROTOCOL-008 PART 6's exact per-section caps -- each isolates one
    missing-evidence rule and confirms strong sub-scores elsewhere cannot
    inflate the capped section past the spec's stated ceiling."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="section-cap-user",
            email="sectioncap@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.profile, self.preferences = ensure_profile_records(self.user)

    def _section(self, readiness, key):
        return next(category for category in readiness.categories if category["key"] == key)

    def test_missing_essays_caps_application_execution_at_three(self):
        Recommender.objects.create(
            user=self.user, name="Counselor", status=Recommender.Status.SUBMITTED
        )
        Recommender.objects.create(
            user=self.user, name="Teacher", status=Recommender.Status.CONFIRMED
        )
        readiness = calculate_application_readiness(self.profile, self.preferences)
        execution = self._section(readiness, "application_execution")
        self.assertLessEqual(execution["score"], 3)
        self.assertIn("essays_missing", execution["cap_reasons"])

    def test_missing_recommenders_caps_application_execution_at_three(self):
        EssayDraft.objects.create(user=self.user, status=EssayDraft.Status.REVIEWED)
        EssayDraft.objects.create(user=self.user, status=EssayDraft.Status.SUBMITTED)
        readiness = calculate_application_readiness(self.profile, self.preferences)
        execution = self._section(readiness, "application_execution")
        self.assertLessEqual(execution["score"], 3)
        self.assertIn("recommendation_letters_missing", execution["cap_reasons"])

    def test_missing_activities_caps_every_section_at_three(self):
        Olympiad.objects.create(user=self.user, name="A", level="national")
        Olympiad.objects.create(user=self.user, name="B", level="national")
        Olympiad.objects.create(user=self.user, name="C", level="national")
        readiness = calculate_application_readiness(self.profile, self.preferences)
        for category in readiness.categories:
            self.assertLessEqual(category["score"], 3, category["key"])

    def test_missing_research_and_portfolio_caps_that_section_at_two(self):
        readiness = calculate_application_readiness(self.profile, self.preferences)
        research_portfolio = self._section(readiness, "research_portfolio")
        self.assertLessEqual(research_portfolio["score"], 2)
        self.assertIn("research_and_portfolio_missing", research_portfolio["cap_reasons"])

    def test_research_present_avoids_the_research_portfolio_cap(self):
        ResearchProject.objects.create(
            user=self.user, title="Study", current_stage=ResearchProject.Stage.PUBLISHED, countries_region="Global"
        )
        ResearchProject.objects.create(
            user=self.user, title="Study 2", current_stage=ResearchProject.Stage.PUBLISHED, countries_region="Global"
        )
        readiness = calculate_application_readiness(self.profile, self.preferences)
        research_portfolio = self._section(readiness, "research_portfolio")
        self.assertNotIn("research_and_portfolio_missing", research_portfolio["cap_reasons"])

    def test_missing_honors_caps_section_only_for_very_selective_target(self):
        from services.university_service.tests.test_universities import create_university

        create_university("selective-target-u", name="Selective Target U", acceptance_rate="4.00")
        self.profile.target_universities = ["Selective Target U"]
        self.profile.save()

        readiness = calculate_application_readiness(self.profile, self.preferences)
        honors = self._section(readiness, "honors_competitions")
        self.assertLessEqual(honors["score"], 2)
        self.assertIn("honors_missing_for_selective_target", honors["cap_reasons"])

    def test_missing_honors_does_not_cap_without_a_very_selective_target(self):
        readiness = calculate_application_readiness(self.profile, self.preferences)
        honors = self._section(readiness, "honors_competitions")
        self.assertNotIn("honors_missing_for_selective_target", honors["cap_reasons"])

    def test_testing_below_benchmark_caps_testing_readiness_even_with_strong_gpa(self):
        self.profile.gpa = "4.00"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1550}
        self.profile.save()
        deterministic_comparisons = {"sat": {"status": "below_benchmark"}, "ielts": {"status": "meets_or_exceeds"}}

        readiness = calculate_application_readiness(
            self.profile, self.preferences, deterministic_comparisons=deterministic_comparisons
        )
        testing = self._section(readiness, "testing_readiness")
        self.assertLessEqual(testing["score"], 3)
        self.assertIn("testing_below_benchmark", testing["cap_reasons"])

    def test_sections_output_has_the_exact_spec_shape(self):
        readiness = calculate_application_readiness(self.profile, self.preferences)
        self.assertEqual(len(readiness.sections), 6)
        for section in readiness.sections:
            for field in (
                "key",
                "score",
                "status",
                "main_strength",
                "main_risk",
                "missing_items",
                "next_action",
            ):
                self.assertIn(field, section)
