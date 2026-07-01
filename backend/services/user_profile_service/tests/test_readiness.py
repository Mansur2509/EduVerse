from django.contrib.auth import get_user_model
from django.test import TestCase

from services.user_profile_service.models import (
    Activity,
    EssayDraft,
    Olympiad,
    PortfolioProject,
    Recommender,
    ResearchProject,
    Volunteer,
)
from services.user_profile_service.readiness import (
    ENRICHMENT_COMPONENTS,
    _score_activities,
    _score_essays,
    _score_leadership,
    _score_olympiads,
    _score_portfolio,
    _score_recommenders,
    _score_research,
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

    def test_missing_niche_categories_do_not_drag_down_stars(self):
        # A strong core profile (gpa/exams/timeline) with zero olympiads,
        # research, sports, portfolio, or volunteering must not be scored as
        # if those absences were weaknesses dragging the star average down.
        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1520, "ielts": 8}
        self.profile.expected_graduation_year = 2028
        self.profile.essay_status = self.profile.EssayStatus.YES
        self.profile.essay_stage = "final polish"
        self.profile.save()

        readiness = calculate_application_readiness(self.profile, self.preferences)
        core_only_components = {
            key: value
            for key, value in readiness.score_components.items()
            if key not in ENRICHMENT_COMPONENTS and key != "published_ranges"
        }
        # None of the empty enrichment categories should be able to pull the
        # star rating below what the core components alone would produce.
        self.assertGreaterEqual(
            readiness.stars, round(sum(core_only_components.values()) / len(core_only_components))
        )
        # But the empty categories are still visible for a next-action nudge.
        self.assertIn("olympiads", readiness.improvements)
        self.assertIn("research", readiness.improvements)

    def test_rich_enrichment_data_can_raise_stars(self):
        Olympiad.objects.create(user=self.user, name="A", level="national")
        Olympiad.objects.create(user=self.user, name="B", level="national")
        Olympiad.objects.create(user=self.user, name="C", level="national")
        readiness = calculate_application_readiness(self.profile, self.preferences)
        self.assertEqual(readiness.score_components["olympiads"], 5)
        self.assertIn("olympiads", readiness.strengths)

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
