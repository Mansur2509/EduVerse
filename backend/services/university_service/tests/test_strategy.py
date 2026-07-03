import json

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from services.university_service.models import UniversityProgram
from services.university_service.strategy import ROUND_BUCKET_ORDER, build_application_strategy
from services.university_service.tests.test_universities import create_university
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()

FORBIDDEN_PHRASES = ("probability", "chance", "odds", "guarantee", "you will get in")


class ApplicationStrategyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="strategystudent", email="strategystudent@test.com", password="testpass123"
        )
        self.profile, self.preferences = ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

    def test_endpoint_returns_category_and_round_groupings(self):
        create_university("strategy-plain", acceptance_rate="40.00")
        response = self.client.get("/api/v1/universities/strategy/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data
        self.assertIn("by_category", data)
        self.assertIn("by_round", data)
        self.assertIn("by_country", data)
        self.assertIn("by_major_cluster", data)
        self.assertEqual(set(data["by_round"].keys()), set(ROUND_BUCKET_ORDER))

    def test_strategy_groups_by_country_and_major_cluster(self):
        self.profile.intended_majors = ["Computer Science"]
        self.profile.save(update_fields=["intended_majors"])
        university = create_university(
            "strategy-cs-school",
            country="United States",
            acceptance_rate="40.00",
        )
        UniversityProgram.objects.create(
            university=university,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
        )

        data = build_application_strategy(self.profile, self.preferences)

        self.assertIn("United States", data["by_country"])
        self.assertIn(
            UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            data["by_major_cluster"],
        )
        self.assertIn("United States", data["country_order"])
        self.assertIn(
            UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            data["major_cluster_order"],
        )

    def test_unverified_round_goes_to_unknown_bucket(self):
        create_university("strategy-no-round-text", acceptance_rate="40.00")
        data = build_application_strategy(self.profile, self.preferences)
        unknown_bucket = data["by_round"]["unknown_verify_round"]
        self.assertTrue(any(item["university"]["slug"] == "strategy-no-round-text" for item in unknown_bucket))
        item = next(item for item in unknown_bucket if item["university"]["slug"] == "strategy-no-round-text")
        self.assertEqual(item["round_confidence"], "unverified")

    def test_verified_round_is_not_placed_in_unknown_bucket(self):
        create_university(
            "strategy-rd-only",
            acceptance_rate="40.00",
            deadlines_text="Regular Decision (RD) deadline is January 1.",
        )
        data = build_application_strategy(self.profile, self.preferences)
        self.assertTrue(any(item["university"]["slug"] == "strategy-rd-only" for item in data["by_round"]["regular_decision"]))
        self.assertFalse(
            any(item["university"]["slug"] == "strategy-rd-only" for item in data["by_round"]["unknown_verify_round"])
        )

    def test_fewer_than_target_range_when_data_insufficient(self):
        create_university("strategy-only-school", acceptance_rate="40.00")
        data = build_application_strategy(self.profile, self.preferences)
        self.assertLess(len(data["schools"]), data["target_range"]["minimum"])
        self.assertTrue(data["data_scarcity"])

    def test_does_not_pad_with_fake_universities(self):
        create_university("strategy-only-school-2", acceptance_rate="40.00")
        data = build_application_strategy(self.profile, self.preferences)
        slugs = {item["university"]["slug"] for item in data["schools"]}
        self.assertEqual(slugs, {"strategy-only-school-2"})

    def test_current_and_conditional_fit_included(self):
        create_university("strategy-fit-fields", acceptance_rate="40.00")
        data = build_application_strategy(self.profile, self.preferences)
        item = data["schools"][0]
        self.assertIn("fit_score", item)
        self.assertIn("conditional_fit_score", item)

    def test_no_admission_probability_language_anywhere(self):
        create_university("strategy-forbidden-language", acceptance_rate="40.00")
        response = self.client.get("/api/v1/universities/strategy/")
        scoped = dict(response.data)
        scoped.pop("disclaimer", None)
        blob = json.dumps(scoped).lower()
        for phrase in FORBIDDEN_PHRASES:
            self.assertNotIn(phrase, blob)
