import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APITestCase

from services.application_service.models import ApplicationTrackerItem
from services.university_service.models import (
    SavedUniversity,
    UniversityFieldVerification,
    UniversityProgram,
    UniversityScholarship,
)
from services.university_service.tests.test_universities import create_university
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()

FORBIDDEN_PHRASES = ("probability", "chance", "odds", "guarantee", "you will get in")


class RecommendationEngineTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recengine", email="recengine@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

    def _get(self):
        response = self.client.get("/api/v1/universities/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def _item_for(self, data, slug):
        return next(item for item in data["recommendations"] if item["university"]["slug"] == slug)

    def test_no_admission_probability_language_anywhere(self):
        create_university("plain-university", acceptance_rate="40.00")
        data = self._get()
        # The disclaimer is the one sanctioned place that names "guarantee" (to
        # negate it); scan everything else in the payload for forbidden terms.
        scoped = dict(data)
        scoped.pop("disclaimer", None)
        blob = json.dumps(scoped).lower()
        for phrase in FORBIDDEN_PHRASES:
            self.assertNotIn(phrase, blob)
        self.assertIn("not an admissions prediction or guarantee", data["disclaimer"].lower())

    def test_ultra_selective_university_is_never_safety(self):
        self.profile.gpa = "4.00"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1600}
        self.profile.save()
        create_university(
            "ultra-selective",
            acceptance_rate="3.00",
            gpa_average="3.90",
            sat_p25=1500,
            sat_p75=1580,
        )
        data = self._get()
        item = self._item_for(data, "ultra-selective")
        self.assertNotEqual(item["category"], "safety")
        self.assertIn(item["category"], {"dream", "reach"})

    def test_low_acceptance_rate_never_becomes_safety_regardless_of_academic_strength(self):
        self.profile.gpa = "4.00"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1600}
        self.profile.save()
        create_university(
            "single-digit-acceptance",
            acceptance_rate="8.00",
            gpa_average="3.20",
            sat_p25=1200,
            sat_p75=1350,
        )
        data = self._get()
        item = self._item_for(data, "single-digit-acceptance")
        self.assertNotEqual(item["category"], "safety")

    def test_program_exact_match(self):
        self.profile.intended_majors = ["Computer Science"]
        self.profile.save()
        university = create_university("exact-match-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(university=university, name="Computer Science")
        data = self._get()
        item = self._item_for(data, "exact-match-university")
        self.assertTrue(item["program_data_verified"])
        self.assertEqual(item["recommended_programs"][0]["match_type"], "exact")
        self.assertEqual(item["recommended_programs"][0]["fit_reason_key"], "program_exact_match")

    def test_program_related_cluster_match_when_no_exact_program(self):
        self.profile.intended_majors = ["Political Science"]
        self.profile.save()
        university = create_university("related-match-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(university=university, name="International Relations")
        data = self._get()
        item = self._item_for(data, "related-match-university")
        self.assertEqual(item["recommended_programs"][0]["match_type"], "related")
        self.assertEqual(item["recommended_programs"][0]["fit_reason_key"], "program_related_match")

    def test_no_program_match_returns_empty_not_invented(self):
        self.profile.intended_majors = ["Basket Weaving"]
        self.profile.save()
        university = create_university("no-match-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(university=university, name="Computer Science")
        data = self._get()
        item = self._item_for(data, "no-match-university")
        self.assertEqual(item["recommended_programs"], [])
        self.assertTrue(item["program_data_verified"])

    def test_missing_program_data_is_reported_not_hidden(self):
        create_university("no-programs-university", acceptance_rate="40.00")
        data = self._get()
        item = self._item_for(data, "no-programs-university")
        self.assertEqual(item["recommended_programs"], [])
        self.assertFalse(item["program_data_verified"])

    def test_cost_risk_high_when_aid_needed_and_no_aid_signal(self):
        self.profile.scholarship_need = self.profile.ScholarshipNeed.YES
        self.profile.save()
        create_university(
            "no-aid-university",
            acceptance_rate="40.00",
            tuition_amount="55000.00",
            tuition_currency="USD",
            scholarship_available=False,
            financial_aid_url="",
        )
        data = self._get()
        item = self._item_for(data, "no-aid-university")
        self.assertEqual(item["cost_risk"], "high")

    def test_cost_risk_unknown_when_cost_not_verified(self):
        create_university("no-cost-university", acceptance_rate="40.00")
        data = self._get()
        item = self._item_for(data, "no-cost-university")
        self.assertEqual(item["cost_risk"], "unknown")

    def test_planned_retake_creates_conditional_note_without_boosting_current_score(self):
        self.profile.test_scores = {"sat": 1100}
        self.profile.exam_plans = {
            "planned": [{"exam_type": "SAT", "target_score": "1500", "date": "2099-01-01"}]
        }
        self.profile.save()
        create_university(
            "retake-university",
            acceptance_rate="40.00",
            sat_p25=1450,
            sat_p75=1520,
        )
        data = self._get()
        item = self._item_for(data, "retake-university")
        self.assertTrue(item["conditional_notes"])
        self.assertIn("may improve", item["conditional_notes"][0].lower())
        # Current academic subscore must reflect the CURRENT low score, not the
        # planned target -- a large SAT gap must still read as a real risk.
        self.assertLess(item["current_academic_subscore"], 60)

    def test_planned_exam_after_deadline_is_flagged(self):
        deadline = date.today() + timedelta(days=30)
        self.profile.test_scores = {"sat": 1100}
        self.profile.exam_plans = {
            "planned": [
                {
                    "exam_type": "SAT",
                    "target_score": "1500",
                    "date": (deadline + timedelta(days=10)).isoformat(),
                }
            ]
        }
        self.profile.save()
        create_university(
            "late-exam-university",
            acceptance_rate="40.00",
            application_deadline=deadline,
        )
        data = self._get()
        item = self._item_for(data, "late-exam-university")
        self.assertTrue(
            any("after the application deadline" in note for note in item["conditional_notes"])
        )

    def test_round_single_available(self):
        create_university(
            "single-round-university",
            acceptance_rate="40.00",
            deadlines_text="Regular Decision (RD): January 1",
        )
        data = self._get()
        item = self._item_for(data, "single-round-university")
        self.assertEqual(item["application_round"]["available_rounds"], ["RD"])
        self.assertEqual(item["application_round"]["recommended_round"], "RD")
        self.assertEqual(item["application_round"]["reason_key"], "round_single_available")

    def test_round_not_verified_when_no_labels_found(self):
        create_university("no-round-university", acceptance_rate="40.00", deadlines_text="")
        data = self._get()
        item = self._item_for(data, "no-round-university")
        self.assertEqual(item["application_round"]["available_rounds"], [])
        self.assertEqual(item["application_round"]["recommended_round"], "unknown")
        self.assertEqual(item["application_round"]["reason_key"], "round_not_verified")

    def test_round_early_too_close_when_not_ready(self):
        self.profile.essay_status = self.profile.EssayStatus.NOT_YET
        self.profile.test_scores = {"sat": 900}
        self.profile.save()
        create_university(
            "close-deadline-university",
            acceptance_rate="40.00",
            sat_p25=1400,
            sat_p75=1500,
            deadlines_text="Early Decision (ED): Nov 1. Regular Decision (RD): Jan 1.",
            application_deadline=date.today() + timedelta(days=10),
        )
        data = self._get()
        item = self._item_for(data, "close-deadline-university")
        self.assertEqual(item["application_round"]["recommended_round"], "RD")
        self.assertEqual(item["application_round"]["reason_key"], "round_early_too_close")

    def test_round_early_recommended_when_ready(self):
        self.profile.essay_status = self.profile.EssayStatus.YES
        self.profile.test_scores = {"sat": 1550}
        self.profile.save()
        create_university(
            "ready-university",
            acceptance_rate="40.00",
            sat_p25=1400,
            sat_p75=1500,
            deadlines_text="Early Decision (ED): Nov 1. Regular Decision (RD): Jan 1.",
            application_deadline=date.today() + timedelta(days=120),
        )
        data = self._get()
        item = self._item_for(data, "ready-university")
        self.assertEqual(item["application_round"]["recommended_round"], "ED")
        self.assertEqual(item["application_round"]["reason_key"], "round_early_recommended_ready")

    def test_deadline_confidence_verified_partial_and_missing(self):
        verified_university = create_university(
            "verified-deadline-university",
            acceptance_rate="40.00",
            application_deadline=date.today() + timedelta(days=60),
        )
        UniversityFieldVerification.objects.create(
            university=verified_university,
            field_name="application_deadline",
            status="verified",
            source_url="https://example.com/official",
            last_verified_date=date.today(),
        )
        create_university(
            "partial-deadline-university",
            acceptance_rate="40.00",
            application_deadline=date.today() + timedelta(days=60),
        )
        create_university("missing-deadline-university", acceptance_rate="40.00")

        data = self._get()
        verified_item = self._item_for(data, "verified-deadline-university")
        partial_item = self._item_for(data, "partial-deadline-university")
        missing_item = self._item_for(data, "missing-deadline-university")

        self.assertEqual(verified_item["deadline_confidence"], "verified")
        self.assertEqual(partial_item["deadline_confidence"], "partial")
        self.assertEqual(missing_item["deadline_confidence"], "missing")
        self.assertIsNone(missing_item["deadline"])
        self.assertIsNone(missing_item["days_remaining"])
        self.assertEqual(missing_item["urgency"], "unknown")

    def test_is_shortlisted_and_application_id_reflect_existing_state(self):
        tracked = create_university("tracked-university", acceptance_rate="40.00")
        shortlisted = create_university("shortlisted-university", acceptance_rate="40.00")
        create_university("untouched-university", acceptance_rate="40.00")

        application = ApplicationTrackerItem.objects.create(user=self.user, university=tracked)
        SavedUniversity.objects.create(user=self.user, university=shortlisted)

        data = self._get()
        tracked_item = self._item_for(data, "tracked-university")
        shortlisted_item = self._item_for(data, "shortlisted-university")
        untouched_item = self._item_for(data, "untouched-university")

        self.assertEqual(tracked_item["application_id"], application.id)
        self.assertFalse(tracked_item["is_shortlisted"])
        self.assertTrue(shortlisted_item["is_shortlisted"])
        self.assertIsNone(shortlisted_item["application_id"])
        self.assertFalse(untouched_item["is_shortlisted"])
        self.assertIsNone(untouched_item["application_id"])

    def test_is_international_reflects_home_country_difference(self):
        self.profile.country = "Uzbekistan"
        self.profile.save()
        create_university("abroad-university", country="United States", acceptance_rate="40.00")
        create_university("home-university", country="Uzbekistan", acceptance_rate="40.00")
        data = self._get()
        abroad = self._item_for(data, "abroad-university")
        home = self._item_for(data, "home-university")
        self.assertTrue(abroad["is_international"])
        self.assertFalse(home["is_international"])

    def test_is_international_is_unknown_when_home_country_missing(self):
        create_university("unknown-home-university", country="United States", acceptance_rate="40.00")
        data = self._get()
        item = self._item_for(data, "unknown-home-university")
        self.assertIsNone(item["is_international"])

    def test_balanced_quota_caps_dream_bucket(self):
        self.profile.gpa = "2.50"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 950}
        self.profile.save()
        for index in range(7):
            create_university(
                f"dream-university-{index}",
                acceptance_rate="3.00",
                gpa_average="3.90",
                sat_p25=1500,
                sat_p75=1580,
            )
        data = self._get()
        self.assertLessEqual(data["counts"]["dream"], 5)
        self.assertEqual(
            len([item for item in data["recommendations"] if item["category"] == "dream"]),
            data["counts"]["dream"],
        )

    def test_list_size_limited_when_too_few_candidates(self):
        create_university("only-university-one", acceptance_rate="40.00")
        create_university("only-university-two", acceptance_rate="50.00")
        data = self._get()
        self.assertTrue(data["list_size_limited"])
        self.assertLess(data["counts"]["total"], 20)

    def test_missing_country_preference_caps_confidence(self):
        self.profile.gpa = "4.00"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1550}
        self.profile.curriculum_type = self.profile.CurriculumType.IB
        self.profile.save()
        create_university(
            "high-confidence-university",
            acceptance_rate="40.00",
            gpa_average="3.20",
            sat_p25=1300,
            sat_p75=1450,
        )
        data = self._get()
        self.assertIn("preferred_countries", data["missing_preferences"])
        item = self._item_for(data, "high-confidence-university")
        self.assertIn(item["confidence"], {"low", "medium"})

    def test_query_count_does_not_explode_with_more_universities(self):
        for index in range(10):
            university = create_university(f"n-plus-one-university-{index}", acceptance_rate="40.00")
            UniversityProgram.objects.create(university=university, name="Computer Science")
            UniversityScholarship.objects.create(
                university=university,
                name="Merit award",
                official_url="https://example.com/aid",
            )
        with CaptureQueriesContext(connection) as queries:
            data = self._get()
        self.assertEqual(len(data["recommendations"]) > 0, True)
        # Bulk-prefetched relations plus two bulk shortlist/tracker lookups should
        # keep total queries well under one-per-university for 10 universities.
        self.assertLess(len(queries), 30)
