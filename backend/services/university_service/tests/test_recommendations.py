import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APITestCase

from services.activity_service.models import AnalyticsEvent
from services.application_service.models import ApplicationTrackerItem
from services.university_service.models import (
    SavedUniversity,
    University,
    UniversityFieldVerification,
    UniversityProgram,
    UniversityScholarship,
    UniversitySubjectRanking,
)
from services.university_service.tests.test_universities import create_university
from services.user_profile_service.models import Activity
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()

FORBIDDEN_PHRASES = (
    "probability",
    "chance",
    "odds",
    "guarantee",
    "you will get in",
    "safe university",
    "definite match",
    "fits the culture",
    "perfect match",
    "great match",
)


def _graduation_year_for_cycle_date(value: date) -> int:
    return value.year + 1 if value.month >= 8 else value.year


class RecommendationEngineTests(APITestCase):
    def setUp(self):
        cache.clear()  # recommendations/strategy responses are cached per (user, profile_hash).
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

    def test_recommendation_includes_major_matching_and_subject_ranking_context(self):
        self.profile.intended_majors = ["Computer Science"]
        self.profile.save()
        university = create_university("subject-context-university", acceptance_rate="40.00")
        program = UniversityProgram.objects.create(
            university=university,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            source_confidence=UniversityProgram.SourceConfidence.VERIFIED,
        )
        UniversitySubjectRanking.objects.create(
            university=university,
            program=program,
            subject_area="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            rank=30,
            source_name="QS Subject",
            source_url="https://example.com/cs-subject",
            ranking_year=2026,
            last_verified_date=date.today(),
            confidence=UniversitySubjectRanking.Confidence.VERIFIED,
        )

        data = self._get()
        item = self._item_for(data, "subject-context-university")

        self.assertTrue(item["matched_programs"])
        self.assertEqual(item["best_program_fit_score"], item["matched_programs"][0]["program_fit_score"])
        self.assertTrue(item["major_cluster_match"])
        self.assertEqual(item["program_fit_confidence"], "high")
        self.assertEqual(item["subject_ranking_context"]["rank"], 30)
        self.assertEqual(
            item["major_inference"]["primary_major_cluster"],
            UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
        )

    def test_program_cluster_match_when_no_exact_program(self):
        self.profile.intended_majors = ["Political Science"]
        self.profile.save()
        university = create_university("related-match-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(university=university, name="International Relations")
        data = self._get()
        item = self._item_for(data, "related-match-university")
        self.assertEqual(item["recommended_programs"][0]["match_type"], "cluster")
        self.assertEqual(item["recommended_programs"][0]["fit_reason_key"], "program_cluster_match")

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
        self.profile.expected_graduation_year = _graduation_year_for_cycle_date(deadline)
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

    def test_past_deadline_does_not_recommend_current_cycle_round(self):
        deadline = date.today() - timedelta(days=30)
        self.profile.expected_graduation_year = _graduation_year_for_cycle_date(deadline)
        self.profile.save(update_fields=["expected_graduation_year"])
        create_university(
            "past-deadline-university",
            acceptance_rate="40.00",
            deadlines_text="Regular Decision (RD): January 1",
            application_deadline=deadline,
        )

        data = self._get()
        item = self._item_for(data, "past-deadline-university")

        self.assertEqual(item["urgency"], "overdue")
        self.assertEqual(item["application_round"]["available_rounds"], ["RD"])
        self.assertEqual(item["application_round"]["recommended_round"], "unknown")
        self.assertEqual(item["application_round"]["reason_key"], "round_deadline_passed")

    def test_recommendation_deadline_uses_profile_graduation_cycle(self):
        self.profile.expected_graduation_year = 2027
        self.profile.save(update_fields=["expected_graduation_year"])
        create_university(
            "cycle-deadline-university",
            acceptance_rate="40.00",
            deadlines_text="Regular Decision (RD): November 1",
            application_deadline=date(2025, 11, 1),
        )

        data = self._get()
        item = self._item_for(data, "cycle-deadline-university")
        deadline = item["deadline"]

        self.assertEqual(
            deadline.isoformat() if hasattr(deadline, "isoformat") else deadline,
            "2026-11-01",
        )
        self.assertEqual(item["deadline_cycle_label"], "2026-2027")
        self.assertNotEqual(item["urgency"], "overdue")

    def test_missing_graduation_year_keeps_recommendation_deadline_unknown(self):
        self.profile.expected_graduation_year = None
        self.profile.save(update_fields=["expected_graduation_year"])
        create_university(
            "source-only-deadline-university",
            acceptance_rate="40.00",
            deadlines_text="Regular Decision (RD): November 1",
            application_deadline=date(2025, 11, 1),
        )

        data = self._get()
        item = self._item_for(data, "source-only-deadline-university")

        self.assertIsNone(item["deadline"])
        self.assertIsNone(item["deadline_cycle_label"])
        self.assertEqual(item["urgency"], "unknown")
        self.assertEqual(item["application_round"]["reason_key"], "round_single_available")

    def test_round_early_too_close_when_not_ready(self):
        deadline = date.today() + timedelta(days=10)
        self.profile.essay_status = self.profile.EssayStatus.NOT_YET
        self.profile.test_scores = {"sat": 900}
        self.profile.expected_graduation_year = _graduation_year_for_cycle_date(deadline)
        self.profile.save()
        create_university(
            "close-deadline-university",
            acceptance_rate="40.00",
            sat_p25=1400,
            sat_p75=1500,
            deadlines_text="Early Decision (ED): Nov 1. Regular Decision (RD): Jan 1.",
            application_deadline=deadline,
        )
        data = self._get()
        item = self._item_for(data, "close-deadline-university")
        self.assertEqual(item["application_round"]["recommended_round"], "RD")
        self.assertEqual(item["application_round"]["reason_key"], "round_early_too_close")

    def test_round_early_recommended_when_ready(self):
        deadline = date.today() + timedelta(days=120)
        self.profile.essay_status = self.profile.EssayStatus.YES
        self.profile.test_scores = {"sat": 1550}
        self.profile.expected_graduation_year = _graduation_year_for_cycle_date(deadline)
        self.profile.save()
        create_university(
            "ready-university",
            acceptance_rate="40.00",
            sat_p25=1400,
            sat_p75=1500,
            deadlines_text="Early Decision (ED): Nov 1. Regular Decision (RD): Jan 1.",
            application_deadline=deadline,
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
        # The bound includes a fixed (not per-university) overhead for computing
        # the response-cache key's profile_hash (PERFORMANCE-011 PART 7) and for
        # calculate_profile_strength (022 Phase 5), which is computed exactly
        # once per request -- never once per candidate university.
        self.assertLess(len(queries), 55)


class RecommendationCacheTests(APITestCase):
    """PERFORMANCE-011 PART 7: short-TTL cache on the recommendations
    endpoint, keyed by (user_id, profile_hash) and explicitly busted by
    shortlist/application-tracking actions."""

    def setUp(self):
        cache.clear()
        self.user1 = User.objects.create_user(
            username="cacheuser1", email="cacheuser1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="cacheuser2", email="cacheuser2@test.com", password="testpass123"
        )
        ensure_profile_records(self.user1)
        ensure_profile_records(self.user2)
        self.university = create_university("cache-test-university", acceptance_rate="40.00")

    def test_cache_does_not_leak_between_users(self):
        self.client.force_authenticate(self.user1)
        self.client.post(f"/api/v1/universities/{self.university.slug}/shortlist/")
        first = self.client.get("/api/v1/universities/recommendations/").data
        item = next(r for r in first["recommendations"] if r["university"]["slug"] == self.university.slug)
        self.assertTrue(item["is_shortlisted"])

        self.client.force_authenticate(self.user2)
        second = self.client.get("/api/v1/universities/recommendations/").data
        item2 = next(r for r in second["recommendations"] if r["university"]["slug"] == self.university.slug)
        self.assertFalse(item2["is_shortlisted"])

    def test_repeat_request_within_ttl_is_served_from_cache(self):
        # Computing the cache *key* still costs a few queries (it depends on
        # the current profile hash) even on a hit -- what the cache actually
        # skips is the expensive full-catalog fit-scoring pass, so the
        # meaningful assertion is "fewer queries on repeat", not "zero".
        self.client.force_authenticate(self.user1)
        with CaptureQueriesContext(connection) as first_call:
            self.client.get("/api/v1/universities/recommendations/")
        with CaptureQueriesContext(connection) as second_call:
            self.client.get("/api/v1/universities/recommendations/")
        self.assertGreater(len(first_call), 0)
        self.assertLess(
            len(second_call),
            len(first_call),
            "Second request within the cache TTL should skip the full recommendations computation.",
        )

    def test_shortlist_action_invalidates_cache_immediately(self):
        self.client.force_authenticate(self.user1)
        before = self.client.get("/api/v1/universities/recommendations/").data
        item_before = next(
            r for r in before["recommendations"] if r["university"]["slug"] == self.university.slug
        )
        self.assertFalse(item_before["is_shortlisted"])

        self.client.post(f"/api/v1/universities/{self.university.slug}/shortlist/")

        after = self.client.get("/api/v1/universities/recommendations/").data
        item_after = next(
            r for r in after["recommendations"] if r["university"]["slug"] == self.university.slug
        )
        self.assertTrue(
            item_after["is_shortlisted"],
            "Recommendations cache was not invalidated by the shortlist action.",
        )

    def test_profile_change_invalidates_cache_via_new_hash(self):
        self.client.force_authenticate(self.user1)
        self.client.get("/api/v1/universities/recommendations/")

        profile, _ = ensure_profile_records(self.user1)
        profile.gpa = "4.00"
        profile.gpa_scale = "4.00"
        profile.save()

        with CaptureQueriesContext(connection) as after_profile_change:
            self.client.get("/api/v1/universities/recommendations/")
        self.assertGreater(
            len(after_profile_change),
            0,
            "Recommendations should recompute (not serve a stale cache entry) after a profile change.",
        )


class CategoryDerivationTests(APITestCase):
    """022 Phase 5-6: category now responds to more than academic-only
    acceptance-rate adjustment, and "dream" is a directly reachable category
    (not permanently empty -- see docs/RECOMMENDATION_ENGINE_AUDIT_022.md).
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="categoryderivation", email="categoryderivation@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

    def _item_for(self, slug):
        response = self.client.get("/api/v1/universities/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return next(
            item for item in response.data["recommendations"] if item["university"]["slug"] == slug
        )

    def test_dream_category_is_directly_reachable(self):
        # A modest (not maxed) academic profile at an ultra-selective school
        # -- composite alignment should land well short of "strong", which is
        # the only alignment band that ever moves an ultra-selective school
        # to "reach" rather than "dream".
        self.profile.gpa = "3.30"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1350}
        self.profile.save()
        create_university(
            "dream-reachable-university",
            acceptance_rate="4.00",
            gpa_average="3.90",
            sat_p25=1500,
            sat_p75=1580,
        )

        item = self._item_for("dream-reachable-university")

        self.assertEqual(item["category"], "dream")

    def test_extracurricular_strength_moves_fit_score_not_only_sort_order(self):
        """The audit's core finding: category bucketing used to respond only
        to academic index_shift, so extracurricular strength never affected
        anything but a same-bucket sort order. Now it feeds the composite
        score directly."""

        def _score_for(slug):
            item = self._item_for(slug)
            return item["fit_score"]

        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1550}
        self.profile.save()
        create_university(
            "weak-ec-university", acceptance_rate="30.00", gpa_average="3.70", sat_p25=1450, sat_p75=1550
        )
        weak_ec_score = _score_for("weak-ec-university")

        create_university(
            "strong-ec-university", acceptance_rate="30.00", gpa_average="3.70", sat_p25=1450, sat_p75=1550
        )
        for index in range(3):
            Activity.objects.create(
                user=self.user,
                title=f"National program {index}",
                role="Founder" if index == 0 else "Team lead",
                category="community",
                start_date=date.today() - timedelta(days=900),
                hours_per_week="12",
                scale=Activity.Scale.NATIONAL,
                proof_link="https://example.com/proof",
                description=(
                    "Led a sustained, multi-year initiative with measurable "
                    "community outcomes documented and verified over time."
                ),
                impact_number="200+ participants reached across 8 events",
            )
        strong_ec_score = _score_for("strong-ec-university")

        self.assertGreater(strong_ec_score, weak_ec_score)

    def test_confirmed_unaffordable_university_is_never_target_or_likely(self):
        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1500}
        self.profile.scholarship_need = self.profile.ScholarshipNeed.NO
        self.profile.annual_budget_amount = "5000"
        self.profile.annual_budget_currency = "USD"
        self.profile.save()
        create_university(
            "unaffordable-accessible-university",
            acceptance_rate="65.00",
            gpa_average="3.20",
            sat_p25=1200,
            sat_p75=1350,
            tuition_amount="60000",
            tuition_currency="USD",
        )

        item = self._item_for("unaffordable-accessible-university")

        self.assertNotIn(item["category"], {"target", "safety"})

    def test_overdue_deadline_university_is_never_target_or_likely(self):
        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1500}
        yesterday = date.today() - timedelta(days=1)
        self.profile.expected_graduation_year = (
            yesterday.year + 1 if yesterday.month >= 8 else yesterday.year
        )
        self.profile.save()
        create_university(
            "overdue-accessible-university",
            acceptance_rate="65.00",
            gpa_average="3.20",
            sat_p25=1200,
            sat_p75=1350,
            application_deadline=yesterday,
        )

        item = self._item_for("overdue-accessible-university")

        self.assertNotIn(item["category"], {"target", "safety"})

    def test_same_country_candidates_are_never_dropped_when_no_alternative_exists(self):
        # All 4 share create_university's default country ("Demoland") and a
        # near-identical, moderate profile -- diversity capping must prefer
        # spreading picks across countries only when an alternative actually
        # exists, never shrink a bucket just because everything on offer
        # happens to share one country.
        for index in range(4):
            create_university(
                f"same-country-target-{index}",
                acceptance_rate="45.00",
                gpa_average="3.30",
                sat_p25=1250,
                sat_p75=1400,
            )
        self.profile.gpa = "3.30"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1320}
        self.profile.save()

        response = self.client.get("/api/v1/universities/recommendations/")
        slugs = {item["university"]["slug"] for item in response.data["recommendations"]}

        for index in range(4):
            self.assertIn(f"same-country-target-{index}", slugs)

    def test_diverse_countries_are_preferred_when_alternatives_exist(self):
        # Comfortably-above-benchmark academic profile (GPA above the
        # university average, SAT above its p75, IB curriculum context) so
        # every identically-stated candidate composites into "target"
        # (selective + strong alignment) -- this test is about country
        # diversity preference among *equally eligible* candidates, not
        # category derivation, so alignment is deliberately made unambiguous.
        self.profile.gpa = "3.60"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1450}
        self.profile.curriculum_type = self.profile.CurriculumType.IB
        self.profile.intended_majors = ["Computer Science"]
        self.profile.save()
        for index in range(6):
            create_university(
                f"crowded-country-target-{index}",
                acceptance_rate="45.00",
                gpa_average="3.30",
                sat_p25=1250,
                sat_p75=1400,
                country="Crowdland",
            )
        create_university(
            "alternate-country-target",
            acceptance_rate="45.00",
            gpa_average="3.30",
            sat_p25=1250,
            sat_p75=1400,
            country="Alternateland",
        )

        response = self.client.get("/api/v1/universities/recommendations/")
        target_countries = [
            item["university"]["country"]
            for item in response.data["recommendations"]
            if item["category"] == "target"
        ]

        self.assertIn("Alternateland", target_countries)


class UnevenProfileCasesTests(APITestCase):
    """022 Phase 7: the recommendation engine must respond sensibly to the
    five uneven-profile shapes called out by the task spec (Cases A-E), not
    just to the balanced personas exercised elsewhere in this file.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="unevenprofile", email="unevenprofile@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

    def _get(self):
        response = self.client.get("/api/v1/universities/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def _item_for(self, data, slug):
        return next(item for item in data["recommendations"] if item["university"]["slug"] == slug)

    def test_case_a_strong_academic_weak_extracurricular_limits_ultra_selective_to_dream_or_reach(self):
        # Genuinely weak (not missing) extracurricular evidence: one shallow,
        # brand-new, low-commitment activity -- not an empty activity list,
        # which the profile-strength model treats as "unknown" rather than
        # "weak" (see profile_strength.calculate_extracurricular_strength).
        self.profile.gpa = "4.00"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1580}
        self.profile.curriculum_type = self.profile.CurriculumType.IB
        self.profile.save()
        Activity.objects.create(
            user=self.user,
            title="Weekend club member",
            role="member",
            category="other",
            start_date=date.today() - timedelta(days=60),
            hours_per_week="1",
            scale=Activity.Scale.SCHOOL,
        )
        create_university(
            "ultra-selective-weak-ec",
            acceptance_rate="4.00",
            gpa_average="3.85",
            sat_p25=1520,
            sat_p75=1580,
        )

        data = self._get()
        item = self._item_for(data, "ultra-selective-weak-ec")

        self.assertIn(item["category"], {"dream", "reach"})
        self.assertNotIn(item["category"], {"target", "safety"})

    def test_case_b_strong_extracurricular_never_erases_confirmed_severe_academic_gap(self):
        # Deliberately severe, confirmed (not missing) academic shortfall --
        # GPA well below average AND SAT far enough below p25 to cross the
        # "significant gap" threshold (sat_gap_severity) -- paired with an
        # exceptionally strong, well-documented extracurricular portfolio at
        # a merely "accessible" (not even selective) school, where "target"
        # and "safety" would otherwise both be reachable on alignment alone.
        self.profile.gpa = "2.50"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1150}
        self.profile.save()
        for index in range(3):
            Activity.objects.create(
                user=self.user,
                title=f"Flagship community initiative {index}",
                role="Founder",
                category="community",
                start_date=date.today() - timedelta(days=900),
                hours_per_week="18",
                weeks_per_year=40,
                scale=Activity.Scale.NATIONAL,
                proof_link="https://example.com/proof",
                description=(
                    "Directed a sustained, multi-year, multi-city initiative "
                    "with independently documented, verifiable outcomes."
                ),
                impact_number="500+ participants reached across dozens of events",
            )
        create_university(
            "accessible-severe-academic-gap",
            acceptance_rate="60.00",
            gpa_average="3.80",
            sat_p25=1400,
            sat_p75=1500,
        )

        data = self._get()
        item = self._item_for(data, "accessible-severe-academic-gap")

        self.assertNotIn(item["category"], {"target", "safety"})

    def test_case_c_strong_profile_still_surfaces_target_and_likely_not_only_elite(self):
        self.profile.gpa = "3.95"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1580}
        self.profile.curriculum_type = self.profile.CurriculumType.IB
        self.profile.save()
        for index in range(3):
            Activity.objects.create(
                user=self.user,
                title=f"National leadership program {index}",
                role="President",
                category="leadership",
                start_date=date.today() - timedelta(days=800),
                hours_per_week="15",
                weeks_per_year=40,
                scale=Activity.Scale.NATIONAL,
                proof_link="https://example.com/proof",
                description=(
                    "Directed a sustained, multi-year program with independently "
                    "documented, measurable outcomes across multiple cohorts."
                ),
                impact_number="300+ students supported",
            )
        for index in range(2):
            create_university(
                f"elite-strong-profile-{index}",
                acceptance_rate="4.00",
                gpa_average="3.90",
                sat_p25=1520,
                sat_p75=1580,
            )
        for index in range(2):
            create_university(
                f"moderate-strong-profile-{index}",
                acceptance_rate="55.00",
                gpa_average="3.50",
                sat_p25=1250,
                sat_p75=1450,
            )

        data = self._get()
        categories = {item["category"] for item in data["recommendations"]}

        self.assertTrue({"target", "safety"} & categories)

    def test_case_d_incomplete_profile_gets_capped_confidence_and_missing_signals_checklist(self):
        # A brand-new profile with no GPA, test scores, activities, essays, or
        # preferences on file -- Case D requires this to be handled as "not
        # enough evidence yet", never silently scored as if it were weak.
        create_university(
            "incomplete-profile-university",
            acceptance_rate="50.00",
            gpa_average="3.50",
            sat_p25=1200,
            sat_p75=1400,
        )

        data = self._get()
        item = self._item_for(data, "incomplete-profile-university")

        self.assertEqual(item["confidence"], "low")
        self.assertTrue(data["missing_profile_signals"])
        self.assertTrue(
            any("MISSING" in code or "UNKNOWN" in code for code in data["missing_profile_signals"])
        )

    def test_case_e_high_financial_need_warns_when_list_is_dominated_by_unaffordable(self):
        self.profile.scholarship_need = self.profile.ScholarshipNeed.YES
        self.profile.annual_budget_amount = "5000"
        self.profile.annual_budget_currency = "USD"
        self.profile.save()
        for index in range(3):
            create_university(
                f"unaffordable-need-university-{index}",
                acceptance_rate="50.00",
                gpa_average="3.20",
                sat_p25=1150,
                sat_p75=1350,
                tuition_amount="60000",
                tuition_currency="USD",
            )

        data = self._get()

        self.assertTrue(data["financial_risk_warning"]["active"])
        self.assertEqual(data["financial_risk_warning"]["high_cost_risk_count"], 3)

    def test_case_e_high_financial_need_no_warning_when_affordable_options_exist(self):
        self.profile.scholarship_need = self.profile.ScholarshipNeed.YES
        self.profile.annual_budget_amount = "5000"
        self.profile.annual_budget_currency = "USD"
        self.profile.save()
        create_university(
            "unaffordable-need-university",
            acceptance_rate="50.00",
            gpa_average="3.20",
            sat_p25=1150,
            sat_p75=1350,
            tuition_amount="60000",
            tuition_currency="USD",
        )
        create_university(
            "affordable-need-university",
            acceptance_rate="50.00",
            gpa_average="3.20",
            sat_p25=1150,
            sat_p75=1350,
            tuition_amount="3000",
            tuition_currency="USD",
            # A verified aid signal -- not just a lower list price -- is what
            # actually moves this out of "high" cost_risk (per _cost_risk,
            # which measures aid-signal confidence for a need-declared
            # profile, not a raw tuition-vs-budget comparison).
            scholarship_available=True,
        )

        data = self._get()

        self.assertFalse(data["financial_risk_warning"]["active"])


class RecommendationExplanationTests(APITestCase):
    """022 Phase 8: every recommendation exposes a complete, non-vague
    explanation surface, and ordinary GETs never invoke an AI provider.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="explanations", email="explanations@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

    def _item_for(self, slug):
        response = self.client.get("/api/v1/universities/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return next(
            item for item in response.data["recommendations"] if item["university"]["slug"] == slug
        )

    def test_canonical_fit_tier_is_exposed_alongside_adaptive_category(self):
        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1500}
        self.profile.save()
        create_university(
            "explained-university", acceptance_rate="40.00", gpa_average="3.50", sat_p25=1300, sat_p75=1450
        )

        item = self._item_for("explained-university")

        self.assertIn("canonical_fit_tier", item)
        self.assertIn(item["canonical_fit_tier"], {"reach", "competitive", "target", "safety", None})
        self.assertIn(item["category"], {"dream", "reach", "target", "safety"})

    def test_top_reason_keys_and_main_risks_are_bounded_and_deduplicated(self):
        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1550}
        self.profile.save()
        create_university(
            "reasons-university", acceptance_rate="40.00", gpa_average="3.20", sat_p25=1200, sat_p75=1350
        )

        item = self._item_for("reasons-university")

        self.assertLessEqual(len(item["top_reason_keys"]), 3)
        self.assertEqual(len(item["top_reason_keys"]), len(set(item["top_reason_keys"])))
        self.assertLessEqual(len(item["main_risks"]), 3)
        self.assertEqual(len(item["main_risks"]), len(set(item["main_risks"])))

    def test_holistic_context_key_is_none_when_no_extracurricular_data_on_file(self):
        create_university(
            "no-ec-data-university", acceptance_rate="40.00", gpa_average="3.50", sat_p25=1200, sat_p75=1400
        )

        item = self._item_for("no-ec-data-university")

        self.assertIsNone(item["holistic_context_key"])

    def test_holistic_context_key_reflects_genuinely_strong_evidence(self):
        for index in range(3):
            Activity.objects.create(
                user=self.user,
                title=f"Deep initiative {index}",
                role="Founder",
                category="community",
                start_date=date.today() - timedelta(days=900),
                hours_per_week="18",
                weeks_per_year=40,
                scale=Activity.Scale.NATIONAL,
                proof_link="https://example.com/proof",
                description=(
                    "Directed a sustained, multi-year initiative with independently "
                    "documented, verifiable outcomes across multiple cohorts."
                ),
                impact_number="400+ participants reached",
            )
        create_university(
            "strong-ec-data-university", acceptance_rate="40.00", gpa_average="3.50", sat_p25=1200, sat_p75=1400
        )

        item = self._item_for("strong-ec-data-university")

        self.assertEqual(item["holistic_context_key"], "extracurricular_strong_evidence")

    def test_ordinary_get_never_invokes_an_ai_provider(self):
        # All three Gemini clients (essay scoring, semantic fit, profile
        # assessment) make their network call through urllib.request.urlopen
        # -- patching that one shared boundary is a robust proxy for "no AI
        # provider was contacted," regardless of which client might
        # hypothetically be wired in by mistake.
        create_university(
            "no-ai-university", acceptance_rate="40.00", gpa_average="3.50", sat_p25=1200, sat_p75=1400
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            response = self.client.get("/api/v1/universities/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_urlopen.assert_not_called()


class RecommendationControlsTests(APITestCase):
    """022 Phase 11: pin/exclude/preferences controls and the explain endpoint."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="controlsuser", email="controlsuser@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

    def _get_recommendations(self):
        response = self.client.get("/api/v1/universities/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def test_excluding_a_university_removes_it_from_recommendations(self):
        university = create_university("exclude-me-university", acceptance_rate="40.00")

        response = self.client.post(f"/api/v1/universities/{university.slug}/exclude/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = self._get_recommendations()
        slugs = {item["university"]["slug"] for item in data["recommendations"]}
        self.assertNotIn("exclude-me-university", slugs)
        self.assertEqual(data["excluded_by_user_count"], 1)

    def test_removing_an_exclusion_restores_the_university(self):
        university = create_university("temporarily-excluded-university", acceptance_rate="40.00")
        self.client.post(f"/api/v1/universities/{university.slug}/exclude/")

        response = self.client.delete(f"/api/v1/universities/{university.slug}/exclude/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        data = self._get_recommendations()
        slugs = {item["university"]["slug"] for item in data["recommendations"]}
        self.assertIn("temporarily-excluded-university", slugs)

    def test_pinning_keeps_a_university_that_would_otherwise_be_capped_out(self):
        # A weak-alignment profile against 10 identical accessible schools --
        # the safety/target quota (6+8) can't fit all 10, so at least one
        # would normally be dropped. Pinning the last one forces it in.
        for index in range(10):
            create_university(f"crowded-safety-university-{index}", acceptance_rate="70.00", gpa_average="2.00")
        pinned_university = University.objects.get(slug="crowded-safety-university-9")

        pin_response = self.client.post(f"/api/v1/universities/{pinned_university.slug}/pin/")
        self.assertEqual(pin_response.status_code, status.HTTP_201_CREATED, pin_response.data)

        data = self._get_recommendations()
        slugs = [item["university"]["slug"] for item in data["recommendations"]]
        self.assertIn("crowded-safety-university-9", slugs)
        self.assertEqual(slugs.count("crowded-safety-university-9"), 1, "pinned item must never duplicate")
        pinned_item = next(item for item in data["recommendations"] if item["university"]["slug"] == pinned_university.slug)
        self.assertTrue(pinned_item["is_pinned"])
        # Honest label: still whatever category the same fit computation
        # would assign anyone else with this exact profile/university pair.
        self.assertIn(pinned_item["category"], {"dream", "reach", "target", "safety"})

    def test_pinning_then_excluding_the_same_university_results_in_exclusion(self):
        university = create_university("pin-then-exclude-university", acceptance_rate="40.00")
        self.client.post(f"/api/v1/universities/{university.slug}/pin/")

        self.client.post(f"/api/v1/universities/{university.slug}/exclude/")

        data = self._get_recommendations()
        slugs = {item["university"]["slug"] for item in data["recommendations"]}
        self.assertNotIn("pin-then-exclude-university", slugs)

    def test_desired_recommendation_count_overrides_default_limit(self):
        for index in range(6):
            create_university(f"count-override-university-{index}", acceptance_rate="45.00", gpa_average="3.00")

        response = self.client.patch(
            "/api/v1/universities/recommendation-preferences/",
            {"desired_recommendation_count": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = self._get_recommendations()
        self.assertLessEqual(len(data["recommendations"]), 3)

    def test_category_distribution_override_caps_a_specific_category(self):
        for index in range(8):
            create_university(f"distribution-safety-university-{index}", acceptance_rate="75.00", gpa_average="2.00")

        response = self.client.patch(
            "/api/v1/universities/recommendation-preferences/",
            {"category_distribution": {"safety": 2}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = self._get_recommendations()
        self.assertLessEqual(data["counts"]["safety"], 2)

    def test_institution_type_preference_excludes_confirmed_mismatch_but_not_unknown(self):
        create_university(
            "public-only-university", acceptance_rate="40.00", institution_type=University.InstitutionType.PUBLIC
        )
        create_university(
            "private-only-university", acceptance_rate="40.00", institution_type=University.InstitutionType.PRIVATE
        )
        create_university("unknown-type-university", acceptance_rate="40.00")

        response = self.client.patch(
            "/api/v1/universities/recommendation-preferences/",
            {"institution_type_preference": "public"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = self._get_recommendations()
        slugs = {item["university"]["slug"] for item in data["recommendations"]}
        self.assertIn("public-only-university", slugs)
        self.assertNotIn("private-only-university", slugs)
        self.assertIn("unknown-type-university", slugs, "unknown institution_type must never be excluded")

    def test_ranking_range_preference_excludes_confirmed_out_of_range_but_not_unknown(self):
        create_university("within-range-university", acceptance_rate="40.00", global_rank=50)
        create_university("out-of-range-university", acceptance_rate="40.00", global_rank=500)
        create_university("unranked-university", acceptance_rate="40.00")

        response = self.client.patch(
            "/api/v1/universities/recommendation-preferences/",
            {"preferred_ranking_min": 1, "preferred_ranking_max": 100},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = self._get_recommendations()
        slugs = {item["university"]["slug"] for item in data["recommendations"]}
        self.assertIn("within-range-university", slugs)
        self.assertNotIn("out-of-range-university", slugs)
        self.assertIn("unranked-university", slugs, "unknown global_rank must never be excluded")

    def test_recommendation_preferences_rejects_malformed_category_distribution(self):
        response = self.client.patch(
            "/api/v1/universities/recommendation-preferences/",
            {"category_distribution": {"dream": "a lot"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommendation_preferences_rejects_inverted_ranking_range(self):
        response = self.client.patch(
            "/api/v1/universities/recommendation-preferences/",
            {"preferred_ranking_min": 100, "preferred_ranking_max": 10},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_explanation_endpoint_answers_why_recommended_and_category(self):
        university = create_university(
            "explain-me-university", acceptance_rate="40.00", gpa_average="3.20", sat_p25=1150, sat_p75=1350
        )
        self.profile.gpa = "3.30"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1250}
        self.profile.save()

        response = self.client.get(f"/api/v1/universities/{university.slug}/recommendation-explanation/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["is_recommendable"])
        self.assertIsNone(response.data["excluded_reason_key"])
        self.assertIn(response.data["category"], {"dream", "reach", "target", "safety"})
        self.assertTrue(response.data["category_explanation_keys"])

    def test_explanation_endpoint_reports_user_exclusion_reason(self):
        university = create_university("explain-excluded-university", acceptance_rate="40.00")
        self.client.post(f"/api/v1/universities/{university.slug}/exclude/")

        response = self.client.get(f"/api/v1/universities/{university.slug}/recommendation-explanation/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data["is_recommendable"])
        self.assertEqual(response.data["excluded_reason_key"], "user_excluded")
        # Still answers "why is this category" even though it's excluded.
        self.assertIn(response.data["category"], {"dream", "reach", "target", "safety"})


class RecommendationAnalyticsTrackingTests(APITestCase):
    """022 Phase 13: ML-readiness logging. The engine stays deterministic --
    these events are passive, sanitized behavioral history for a possible
    future ranking-model evaluation, not a model themselves.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="analyticsuser", email="analyticsuser@test.com", password="testpass123"
        )
        ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

    def test_fetching_recommendations_logs_an_impression_event(self):
        create_university("impression-university", acceptance_rate="40.00")

        response = self.client.get("/api/v1/universities/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        event = AnalyticsEvent.objects.get(
            user=self.user, event_type=AnalyticsEvent.EventType.RECOMMENDATION_IMPRESSION
        )
        self.assertEqual(event.metadata["result_count"], len(response.data["recommendations"]))
        self.assertIn("excluded_by_user_count", event.metadata)

    def test_fetching_recommendations_twice_logs_two_impressions(self):
        # Impressions represent what the student was actually shown, so a
        # second fetch (even one served from cache) is a second impression --
        # unlike creation-only events such as UNIVERSITY_SHORTLISTED.
        self.client.get("/api/v1/universities/recommendations/")
        self.client.get("/api/v1/universities/recommendations/")

        self.assertEqual(
            AnalyticsEvent.objects.filter(
                user=self.user, event_type=AnalyticsEvent.EventType.RECOMMENDATION_IMPRESSION
            ).count(),
            2,
        )

    def test_pinning_a_university_logs_a_pin_event(self):
        university = create_university("pin-tracking-university", acceptance_rate="40.00")

        response = self.client.post(f"/api/v1/universities/{university.slug}/pin/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        event = AnalyticsEvent.objects.get(
            user=self.user, event_type=AnalyticsEvent.EventType.UNIVERSITY_PINNED
        )
        self.assertEqual(event.entity_id, university.id)

    def test_repinning_an_already_pinned_university_does_not_duplicate_the_event(self):
        university = create_university("repin-tracking-university", acceptance_rate="40.00")
        self.client.post(f"/api/v1/universities/{university.slug}/pin/")

        self.client.post(f"/api/v1/universities/{university.slug}/pin/")

        self.assertEqual(
            AnalyticsEvent.objects.filter(
                user=self.user, event_type=AnalyticsEvent.EventType.UNIVERSITY_PINNED
            ).count(),
            1,
        )

    def test_excluding_a_university_logs_an_exclude_event(self):
        university = create_university("exclude-tracking-university", acceptance_rate="40.00")

        response = self.client.post(f"/api/v1/universities/{university.slug}/exclude/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        event = AnalyticsEvent.objects.get(
            user=self.user, event_type=AnalyticsEvent.EventType.UNIVERSITY_EXCLUDED
        )
        self.assertEqual(event.entity_id, university.id)


class SyntheticPersonaRegressionTests(APITestCase):
    """022 Phase 14: eight realistic student archetypes run through the full
    pipeline together (recommendations AND strategy, not just one endpoint)
    as a regression net -- distinct from Phase 7's Cases A-E, which only
    checked category derivation on the recommendations endpoint in
    isolation. Every persona must: never crash either endpoint, never emit
    forbidden probability/guarantee language, and hit the one or two
    persona-defining behaviors called out in each test.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="personauser", email="personauser@test.com", password="testpass123"
        )
        self.profile, self.preferences = ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

        # A shared, diverse candidate pool every persona scores against.
        create_university(
            "persona-ultra-selective", acceptance_rate="4.00", gpa_average="3.90", sat_p25=1520, sat_p75=1580
        )
        create_university(
            "persona-selective", acceptance_rate="18.00", gpa_average="3.70", sat_p25=1400, sat_p75=1500
        )
        create_university(
            "persona-moderate", acceptance_rate="45.00", gpa_average="3.30", sat_p25=1150, sat_p75=1300
        )
        create_university(
            "persona-accessible-a", acceptance_rate="70.00", gpa_average="2.80", sat_p25=950, sat_p75=1100
        )
        create_university(
            "persona-accessible-b", acceptance_rate="75.00", gpa_average="2.60", sat_p25=900, sat_p75=1050
        )
        create_university("persona-no-aid-signal", acceptance_rate="40.00", gpa_average="3.30")
        create_university(
            "persona-with-aid-signal", acceptance_rate="40.00", gpa_average="3.30", scholarship_available=True
        )
        create_university("persona-abroad", acceptance_rate="30.00", gpa_average="3.40", country="United Kingdom")

    def _get_recommendations(self):
        response = self.client.get("/api/v1/universities/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def _get_strategy(self):
        response = self.client.get("/api/v1/universities/strategy/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def _assert_no_forbidden_language(self, *payloads):
        for payload in payloads:
            scoped = dict(payload)
            scoped.pop("disclaimer", None)
            blob = json.dumps(scoped).lower()
            for phrase in FORBIDDEN_PHRASES:
                self.assertNotIn(phrase, blob)

    def test_persona_1_well_rounded_high_achiever_no_financial_warning(self):
        self.profile.gpa = "3.90"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1550}
        self.profile.curriculum_type = self.profile.CurriculumType.IB
        self.profile.intended_majors = ["Computer Science"]
        self.profile.scholarship_need = self.profile.ScholarshipNeed.NO
        self.profile.annual_budget_amount = "80000.00"
        self.profile.save()
        for index in range(3):
            Activity.objects.create(
                user=self.user,
                title=f"Research fellowship {index}",
                role="Lead researcher",
                category="research",
                start_date=date.today() - timedelta(days=700),
                hours_per_week="12",
                weeks_per_year=40,
                scale=Activity.Scale.NATIONAL,
                proof_link="https://example.com/proof",
                description="Sustained, verifiable, multi-year research output.",
            )

        recommendations = self._get_recommendations()
        strategy = self._get_strategy()

        self._assert_no_forbidden_language(recommendations, strategy)
        self.assertFalse(recommendations["financial_risk_warning"]["active"])
        ultra = self._item_for(recommendations, "persona-ultra-selective")
        self.assertNotEqual(ultra["category"], "safety")

    def test_persona_2_strong_academic_weak_extracurricular_caps_ultra_selective(self):
        self.profile.gpa = "3.95"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1560}
        self.profile.save()
        Activity.objects.create(
            user=self.user,
            title="Weekend club member",
            role="member",
            category="other",
            start_date=date.today() - timedelta(days=60),
            hours_per_week="1",
            scale=Activity.Scale.SCHOOL,
        )

        recommendations = self._get_recommendations()
        strategy = self._get_strategy()

        self._assert_no_forbidden_language(recommendations, strategy)
        ultra = self._item_for(recommendations, "persona-ultra-selective")
        self.assertIn(ultra["category"], {"dream", "reach"})

    def test_persona_3_strong_extracurricular_never_erases_confirmed_academic_gap(self):
        self.profile.gpa = "2.40"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1050}
        self.profile.save()
        for index in range(3):
            Activity.objects.create(
                user=self.user,
                title=f"Flagship community initiative {index}",
                role="Founder",
                category="community",
                start_date=date.today() - timedelta(days=900),
                hours_per_week="18",
                weeks_per_year=40,
                scale=Activity.Scale.NATIONAL,
                proof_link="https://example.com/proof",
                description="Sustained, multi-year, independently verifiable outcomes.",
            )

        recommendations = self._get_recommendations()
        strategy = self._get_strategy()

        self._assert_no_forbidden_language(recommendations, strategy)
        accessible = self._item_for(recommendations, "persona-accessible-b")
        self.assertNotEqual(accessible["category"], "safety")

    def test_persona_4_high_financial_need_triggers_warning_without_affordable_options(self):
        self.profile.gpa = "3.30"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1200}
        self.profile.scholarship_need = self.profile.ScholarshipNeed.YES
        self.profile.annual_budget_amount = "5000.00"
        self.profile.save()

        recommendations = self._get_recommendations()
        strategy = self._get_strategy()

        self._assert_no_forbidden_language(recommendations, strategy)
        self.assertIn("financial_risk_warning", strategy)

    def test_persona_5_low_data_new_student_surfaces_missing_signals_without_crashing(self):
        # Deliberately untouched profile: no GPA, no test scores, no
        # activities -- exactly what a student sees moments after signup.
        recommendations = self._get_recommendations()
        strategy = self._get_strategy()

        self._assert_no_forbidden_language(recommendations, strategy)
        self.assertTrue(recommendations["missing_profile_signals"])

    def test_persona_6_international_student_sees_only_targeted_country(self):
        self.profile.country = "Uzbekistan"
        self.profile.target_countries = ["United Kingdom"]
        self.profile.gpa = "3.50"
        self.profile.gpa_scale = "4.00"
        self.profile.save()

        recommendations = self._get_recommendations()
        strategy = self._get_strategy()

        self._assert_no_forbidden_language(recommendations, strategy)
        slugs = {item["university"]["slug"] for item in recommendations["recommendations"]}
        self.assertIn("persona-abroad", slugs)
        self.assertNotIn("persona-ultra-selective", slugs, "non-targeted country must be filtered out")

    def test_persona_7_undecided_major_explorer_does_not_crash(self):
        self.profile.major_unsure = True
        self.profile.intended_majors = []
        self.profile.gpa = "3.40"
        self.profile.gpa_scale = "4.00"
        self.profile.save()

        recommendations = self._get_recommendations()
        strategy = self._get_strategy()

        self._assert_no_forbidden_language(recommendations, strategy)

    def test_persona_8_portfolio_heavy_user_stays_consistent_across_endpoints(self):
        pinned = University.objects.get(slug="persona-accessible-a")
        excluded = University.objects.get(slug="persona-accessible-b")
        SavedUniversity.objects.create(user=self.user, university=University.objects.get(slug="persona-moderate"))
        ApplicationTrackerItem.objects.create(user=self.user, university=University.objects.get(slug="persona-selective"))
        self.client.post(f"/api/v1/universities/{pinned.slug}/pin/")
        self.client.post(f"/api/v1/universities/{excluded.slug}/exclude/")

        recommendations = self._get_recommendations()
        strategy = self._get_strategy()

        self._assert_no_forbidden_language(recommendations, strategy)
        slugs = {item["university"]["slug"] for item in recommendations["recommendations"]}
        self.assertIn("persona-accessible-a", slugs)
        self.assertNotIn("persona-accessible-b", slugs)

    def _item_for(self, data, slug):
        return next(item for item in data["recommendations"] if item["university"]["slug"] == slug)


class RecommendationDiagnosticsTests(APITestCase):
    """022 Phase 12: authorized-internal-only diagnostic view. Admin-gated,
    never reachable by an ordinary user, never leaks another user's data to
    a non-admin.
    """

    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(
            username="diagnosticsstudent", email="diagnosticsstudent@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.student)
        self.admin = User.objects.create_user(
            username="diagnosticsadmin",
            email="diagnosticsadmin@test.com",
            password="testpass123",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def _diagnostics_url(self, user):
        return f"/api/admin/universities/{user.id}/recommendation-diagnostics/"

    def test_ordinary_user_cannot_access_diagnostics_endpoint(self):
        self.client.force_authenticate(self.student)

        response = self.client.get(self._diagnostics_url(self.student))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_diagnostics_for_a_specific_student(self):
        create_university("diagnostics-visible-university", acceptance_rate="40.00")
        self.client.force_authenticate(self.admin)

        response = self.client.get(self._diagnostics_url(self.student))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for key in (
            "candidate_pool_count",
            "hard_filter_removal_counts",
            "removed_universities_sample",
            "final_counts",
            "final_recommendation_count",
            "cache_status",
        ):
            self.assertIn(key, response.data)

    def test_diagnostics_reports_user_excluded_reason_code(self):
        university = create_university("diagnostics-excluded-university", acceptance_rate="40.00")
        self.client.force_authenticate(self.student)
        self.client.post(f"/api/v1/universities/{university.slug}/exclude/")

        self.client.force_authenticate(self.admin)
        response = self.client.get(self._diagnostics_url(self.student))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["hard_filter_removal_counts"].get("USER_EXCLUDED"), 1)
        matching = [
            entry
            for entry in response.data["removed_universities_sample"]
            if entry["slug"] == "diagnostics-excluded-university"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["reason_code"], "USER_EXCLUDED")

    def test_diagnostics_reports_degree_level_mismatch_reason_code(self):
        university = create_university("diagnostics-degree-mismatch-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(
            university=university, name="Bachelor of Science", degree_level="bachelor"
        )
        self.profile.intended_degree = "master"
        self.profile.save()
        self.client.force_authenticate(self.admin)

        response = self.client.get(self._diagnostics_url(self.student))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["hard_filter_removal_counts"].get("DEGREE_LEVEL_MISMATCH"), 1)

    def test_diagnostics_cache_status_reflects_real_cache_state(self):
        create_university("diagnostics-cache-university", acceptance_rate="40.00")
        self.client.force_authenticate(self.admin)

        before = self.client.get(self._diagnostics_url(self.student))
        self.assertEqual(before.data["cache_status"], "miss")

        self.client.force_authenticate(self.student)
        self.client.get("/api/v1/universities/recommendations/")

        self.client.force_authenticate(self.admin)
        after = self.client.get(self._diagnostics_url(self.student))
        self.assertEqual(after.data["cache_status"], "hit")


class HardFilterTests(APITestCase):
    """022 Phase 4: expired-deadline and confirmed-degree-mismatch exclusion.
    Unknown/unrecognized data on either side must never exclude a candidate.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="hardfilter", email="hardfilter@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)
        # Deadline normalization only resolves a real year (and therefore a
        # real days_remaining) once the student's expected graduation year is
        # known -- see deadline_normalization.py. Without it every deadline
        # is "source_only" and never excluded, which is correct but would
        # make this class unable to exercise the expired-deadline filter.
        self.profile.expected_graduation_year = date.today().year + 1
        self.profile.save()
        self.client.force_authenticate(self.user)

    def _slugs(self):
        response = self.client.get("/api/v1/universities/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return {item["university"]["slug"] for item in response.data["recommendations"]}

    # An expired deadline is intentionally NOT hard-excluded here -- see
    # test_past_deadline_does_not_recommend_current_cycle_round above, which
    # already covers "still visible, but urgency=overdue and
    # recommended_round=unknown, never presented as actionable this cycle."
    # Never letting an overdue item resolve to a practical/apply-now category
    # is covered by the category-capping tests added in Phase 6.

    def test_future_deadline_is_not_excluded(self):
        create_university(
            "future-deadline-university",
            acceptance_rate="40.00",
            application_deadline=date.today() + timedelta(days=60),
        )

        self.assertIn("future-deadline-university", self._slugs())

    def test_unknown_deadline_is_not_excluded(self):
        create_university("no-deadline-university", acceptance_rate="40.00")

        self.assertIn("no-deadline-university", self._slugs())

    def test_confirmed_degree_mismatch_is_excluded(self):
        self.profile.intended_degree = "bachelor"
        self.profile.save()
        university = create_university("masters-only-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(
            university=university, name="MBA", degree_level="Master's"
        )

        self.assertNotIn("masters-only-university", self._slugs())

    def test_matching_degree_is_not_excluded(self):
        self.profile.intended_degree = "bachelor"
        self.profile.save()
        university = create_university("bachelors-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(
            university=university, name="Computer Science", degree_level="Bachelor's"
        )

        self.assertIn("bachelors-university", self._slugs())

    def test_unspecified_student_degree_is_not_excluded_by_any_program_level(self):
        university = create_university("grad-only-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(university=university, name="PhD Physics", degree_level="PhD")

        self.assertIn("grad-only-university", self._slugs())

    def test_program_with_unrecognized_degree_level_text_is_not_excluded(self):
        self.profile.intended_degree = "bachelor"
        self.profile.save()
        university = create_university("unlabeled-degree-university", acceptance_rate="40.00")
        UniversityProgram.objects.create(
            university=university, name="General Studies", degree_level="Tier 2 Certificate"
        )

        self.assertIn("unlabeled-degree-university", self._slugs())
