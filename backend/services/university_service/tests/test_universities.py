from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from services.university_service.currency import normalize_university_costs
from services.university_service.models import (
    ExchangeRate,
    SavedUniversity,
    University,
    UniversityFieldVerification,
    UniversityProgram,
)
from services.university_service.services import calculate_university_fit
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


def create_university(slug, **overrides):
    defaults = {
        "name": slug.replace("-", " ").title(),
        "country": "Demoland",
        "city": "Sample City",
        "official_website": f"https://example.com/{slug}",
        "summary": "Fictional record for tests.",
        "is_published": True,
    }
    defaults.update(overrides)
    return University.objects.create(slug=slug, **defaults)


class UniversityCatalogTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student1", email="student1@test.com", password="testpass123"
        )
        self.published = create_university(
            "published-university", country="Sampleton", city="Northfield"
        )
        self.unpublished = create_university(
            "unpublished-university", is_published=False
        )

    def test_list_requires_authentication(self):
        response = self.client.get("/api/v1/universities/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_excludes_unpublished_for_non_admin(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/universities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertIn("published-university", slugs)
        self.assertNotIn("unpublished-university", slugs)

    def test_search_filters_by_name(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/universities/", {"search": "Northfield"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        response = self.client.get("/api/v1/universities/", {"search": "no-such-university"})
        self.assertEqual(response.data["count"], 0)
        response = self.client.get("/api/v1/universities/", {"country": "Sampleton"})
        self.assertEqual(response.data["count"], 1)

    def test_city_filter(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/universities/", {"city": "Northfield"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["slug"], "published-university")

    def test_verification_status_filter(self):
        UniversityFieldVerification.objects.create(
            university=self.published,
            field_name="acceptance_rate",
            status=UniversityFieldVerification.Status.VERIFIED,
            source_url="https://example.com/source",
            last_verified_date=timezone.now().date(),
            note="Official source check.",
        )
        partial = create_university("partial-university", country="Sampleton")
        UniversityFieldVerification.objects.create(
            university=partial,
            field_name="sat_p25",
            status=UniversityFieldVerification.Status.PARTIAL,
            source_url="https://example.com/source-partial",
            last_verified_date=timezone.now().date(),
            note="Partial official source check.",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(
            "/api/v1/universities/", {"verification_status": "verified"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertEqual(slugs, ["published-university"])

    def test_qs_ranking_ordering(self):
        top_ranked = create_university("top-ranked-university", qs_ranking=5)
        lower_ranked = create_university("lower-ranked-university", qs_ranking=200)
        unranked = create_university("unranked-university", qs_ranking=None)
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/universities/", {"ordering": "qs_ranking"})

        slugs = [item["slug"] for item in response.data["results"]]
        self.assertLess(slugs.index(top_ranked.slug), slugs.index(lower_ranked.slug))
        self.assertLess(slugs.index(lower_ranked.slug), slugs.index(unranked.slug))

    def test_qs_ranking_reverse_ordering_keeps_missing_last(self):
        top_ranked = create_university("reverse-top-ranked-university", qs_ranking=5)
        lower_ranked = create_university("reverse-lower-ranked-university", qs_ranking=200)
        unranked = create_university("reverse-unranked-university", qs_ranking=None)
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/universities/", {"ordering": "-qs_ranking"})

        slugs = [item["slug"] for item in response.data["results"]]
        self.assertLess(slugs.index(lower_ranked.slug), slugs.index(top_ranked.slug))
        self.assertLess(slugs.index(top_ranked.slug), slugs.index(unranked.slug))

    def test_retrieve_by_slug(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{self.published.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.published.name)
        self.assertFalse(response.data["is_shortlisted"])

    def test_retrieve_unpublished_not_found_for_non_admin(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{self.unpublished.slug}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DemoDataSeparationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student2", email="student2@test.com", password="testpass123"
        )
        self.real = create_university("real-university", is_demo=False)
        self.demo = create_university("demo-university", is_demo=True)

    def test_list_excludes_demo_universities_by_default(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/universities/")
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertIn("real-university", slugs)
        self.assertNotIn("demo-university", slugs)

    def test_list_includes_demo_universities_when_requested(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/universities/", {"include_demo": "true"})
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertIn("real-university", slugs)
        self.assertIn("demo-university", slugs)

    def test_retrieve_demo_university_still_works_directly(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{self.demo.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_demo"])


class FieldVerificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student3", email="student3@test.com", password="testpass123"
        )

    def test_field_verification_is_serialized(self):
        from services.university_service.models import UniversityFieldVerification

        university = create_university("verified-university", acceptance_rate="12.00")
        UniversityFieldVerification.objects.create(
            university=university,
            field_name="acceptance_rate",
            status="verified",
            source_url="https://example.com/source",
            last_verified_date="2026-06-28",
            note="Directly fetched from the official admissions page.",
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/")
        verifications = response.data["field_verifications"]
        self.assertEqual(len(verifications), 1)
        self.assertEqual(verifications[0]["field_name"], "acceptance_rate")
        self.assertEqual(verifications[0]["status"], "verified")
        self.assertEqual(verifications[0]["source_url"], "https://example.com/source")

    def test_field_without_verification_record_has_none(self):
        university = create_university("unverified-university", acceptance_rate="20.00")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/")
        self.assertEqual(response.data["field_verifications"], [])


class ProgramDisplayTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="program-user", email="program@test.com", password="testpass123"
        )
        self.university = create_university("program-display-university")

    def test_parenthetical_tracks_are_serialized_as_clean_display_names(self):
        UniversityProgram.objects.create(
            university=self.university,
            name="Engineering (Civil, Mechanical, EE, Aerospace, Chemical)",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/api/v1/universities/{self.university.slug}/")

        self.assertEqual(
            response.data["program_display_names"],
            [
                "Engineering — Civil",
                "Engineering — Mechanical",
                "Engineering — Electrical Engineering",
                "Engineering — Aerospace",
                "Engineering — Chemical",
            ],
        )

    def test_broken_parenthetical_sequence_keeps_parent_context(self):
        for name in ["Engineering (Civil", "Mechanical", "EE", "Aerospace", "Chemical)"]:
            UniversityProgram.objects.create(university=self.university, name=name)
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/api/v1/universities/{self.university.slug}/")

        self.assertEqual(
            response.data["program_display_names"],
            [
                "Engineering — Civil",
                "Engineering — Mechanical",
                "Engineering — Electrical Engineering",
                "Engineering — Aerospace",
                "Engineering — Chemical",
            ],
        )
        self.assertEqual(
            list(self.university.programs.order_by("id").values_list("name", flat=True)),
            ["Engineering (Civil", "Mechanical", "EE", "Aerospace", "Chemical)"],
        )


class ShortlistTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="testpass123"
        )
        self.university = create_university("shortlist-university")

    def test_add_to_shortlist(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(f"/api/v1/universities/{self.university.slug}/shortlist/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            SavedUniversity.objects.filter(user=self.user1, university=self.university).exists()
        )

    def test_add_to_shortlist_is_idempotent(self):
        self.client.force_authenticate(self.user1)
        self.client.post(f"/api/v1/universities/{self.university.slug}/shortlist/")
        response = self.client.post(f"/api/v1/universities/{self.university.slug}/shortlist/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            SavedUniversity.objects.filter(user=self.user1, university=self.university).count(), 1
        )

    def test_remove_from_shortlist(self):
        self.client.force_authenticate(self.user1)
        self.client.post(f"/api/v1/universities/{self.university.slug}/shortlist/")
        response = self.client.delete(f"/api/v1/universities/{self.university.slug}/shortlist/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            SavedUniversity.objects.filter(user=self.user1, university=self.university).exists()
        )

    def test_shortlist_is_self_only(self):
        SavedUniversity.objects.create(user=self.user2, university=self.university)
        self.client.force_authenticate(self.user1)
        response = self.client.get("/api/v1/universities/shortlist/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_university_serializer_reflects_shortlist_state(self):
        self.client.force_authenticate(self.user1)
        self.client.post(f"/api/v1/universities/{self.university.slug}/shortlist/")
        response = self.client.get(f"/api/v1/universities/{self.university.slug}/")
        self.assertTrue(response.data["is_shortlisted"])


class CompareTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="comparer", email="comparer@test.com", password="testpass123"
        )
        self.uni_a = create_university("compare-a")
        self.uni_b = create_university("compare-b")
        self.uni_c = create_university("compare-c")

    def test_compare_requires_between_two_and_four_ids(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            "/api/v1/universities/compare/", {"ids": str(self.uni_a.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_compare_returns_universities_in_order(self):
        self.client.force_authenticate(self.user)
        ids = f"{self.uni_b.id},{self.uni_a.id}"
        response = self.client.get("/api/v1/universities/compare/", {"ids": ids})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["slug"], "compare-b")
        self.assertEqual(response.data[1]["slug"], "compare-a")

    def test_compare_rejects_unknown_id(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            "/api/v1/universities/compare/",
            {"ids": f"{self.uni_a.id},999999"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FitAnalysisTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="fituser", email="fituser@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)

    def test_fit_with_no_data_returns_unknown_category(self):
        university = create_university("unknown-fit-university")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["category"])
        self.assertIn("profile_gpa", response.data["missing_fields"])
        self.assertIn("university_acceptance_rate", response.data["missing_fields"])
        self.assertIn("verify_university_data", response.data["next_actions"])

    def test_fit_uses_acceptance_rate_baseline(self):
        university = create_university(
            "reach-university", acceptance_rate="8.00", gpa_average=None, sat_average=None
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")
        self.assertEqual(response.data["category"], "reach")

        university2 = create_university(
            "safety-university", acceptance_rate="75.00", gpa_average=None, sat_average=None
        )
        response2 = self.client.get(f"/api/v1/universities/{university2.slug}/fit/")
        self.assertEqual(response2.data["category"], "safety")

    def test_fit_flags_limited_data_when_category_assigned_from_partial_university_stats(self):
        # Mirrors a real university like Harvard: acceptance rate is known but
        # GPA/SAT averages are not published anywhere official.
        university = create_university(
            "sparse-real-university",
            acceptance_rate="4.18",
            gpa_average=None,
            sat_average=None,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")
        self.assertEqual(response.data["category"], "dream")
        self.assertIn("limited_data_for_category", response.data["next_actions"])
        self.assertNotIn("verify_university_data", response.data["next_actions"])

    def test_fit_strengths_when_student_above_average(self):
        self.profile.gpa = "5.00"
        self.profile.gpa_scale = "5.00"
        self.profile.test_scores = {"sat": 1550}
        self.profile.save()

        university = create_university(
            "target-university",
            acceptance_rate="45.00",
            gpa_average="3.00",
            sat_average=1300,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")
        self.assertIn("gpa_above_average", response.data["strengths"])
        self.assertIn("sat_above_average", response.data["strengths"])
        self.assertEqual(response.data["category"], "safety")

    def test_fit_risks_when_student_below_average(self):
        self.profile.gpa = "2.50"
        self.profile.gpa_scale = "5.00"
        self.profile.test_scores = {"sat": 900}
        self.profile.save()

        university = create_university(
            "competitive-university",
            acceptance_rate="45.00",
            gpa_average="3.80",
            sat_average=1400,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")
        self.assertIn("gpa_below_average", response.data["risks"])
        self.assertIn("sat_below_average", response.data["risks"])
        self.assertEqual(response.data["category"], "reach")

    def test_fit_detects_risk_at_exact_threshold_despite_float_rounding(self):
        # 4.50/5.00*4.0 - 3.90 equals exactly -0.3 in decimal arithmetic, but float
        # division can land at -0.2999999999999999 and silently miss the threshold.
        self.profile.gpa = "4.50"
        self.profile.gpa_scale = "5.00"
        self.profile.save()

        university = create_university(
            "boundary-university",
            acceptance_rate="8.00",
            gpa_average="3.90",
            sat_average=None,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")
        self.assertIn("gpa_below_average", response.data["risks"])

    def test_fit_uses_normalized_gpa_not_raw_scale(self):
        self.profile.gpa = "4.80"
        self.profile.gpa_scale = "5.00"
        self.profile.save()

        university = create_university(
            "normalized-gpa-university",
            acceptance_rate="45.00",
            gpa_average="4.00",
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")

        self.assertNotIn("gpa_above_average", response.data["strengths"])
        self.assertEqual(
            Decimal(str(response.data["student_academic_context"]["original_gpa_value"])),
            Decimal("4.80"),
        )
        self.assertEqual(
            Decimal(str(response.data["student_academic_context"]["normalized_gpa_4"])),
            Decimal("3.84"),
        )

    def test_ielts_below_competitive_is_gap(self):
        self.profile.test_scores = {"ielts": 6.0}
        self.profile.save()
        university = create_university(
            "ielts-competitive-university",
            ielts_minimum="6.0",
            ielts_competitive="7.5",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn("ielts_below_competitive", fit["risks"])

    def test_ielts_below_minimum_is_blocking_gap(self):
        self.profile.test_scores = {"ielts": 6.0}
        self.profile.save()
        university = create_university(
            "ielts-minimum-university",
            ielts_minimum="6.5",
            ielts_competitive="7.5",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn("ielts_below_minimum", fit["risks"])
        self.assertLessEqual(fit["fit_score"], 55)

    def test_sat_below_25th_percentile_is_academic_risk(self):
        self.profile.test_scores = {"sat": 1200}
        self.profile.save()
        university = create_university(
            "sat-risk-university",
            sat_p25=1400,
            sat_p75=1550,
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn("sat_below_p25", fit["risks"])
        self.assertLessEqual(fit["fit_score"], 55)

    def test_large_sat_gap_penalizes_more_than_small_ielts_gap(self):
        self.profile.test_scores = {"sat": 1510, "ielts": 6.5}
        self.profile.save()
        small_ielts_gap_university = create_university(
            "small-ielts-gap-university",
            sat_average=1510,
            ielts_minimum="6.0",
            ielts_competitive="7.0",
        )
        small_ielts_fit = calculate_university_fit(
            self.profile,
            small_ielts_gap_university,
        )

        self.profile.test_scores = {"sat": 1220, "ielts": 7.0}
        self.profile.save()
        large_sat_gap_university = create_university(
            "large-sat-gap-university",
            sat_p25=1510,
            sat_p75=1560,
            ielts_minimum="6.0",
            ielts_competitive="7.0",
        )
        large_sat_fit = calculate_university_fit(self.profile, large_sat_gap_university)

        self.assertIn("ielts_below_competitive", small_ielts_fit["risks"])
        self.assertIn("sat_below_p25", large_sat_fit["risks"])
        self.assertGreater(
            small_ielts_fit["academic_subscore"],
            large_sat_fit["academic_subscore"],
        )

    def test_planned_retake_is_conditional_not_current_score_boost(self):
        self.profile.test_scores = {"sat": 1200}
        self.profile.exam_plans = {
            "taken": ["SAT"],
            "planned": [
                {
                    "name": "SAT",
                    "exam_type": "SAT",
                    "target_score": "1550",
                    "planned_retake": True,
                }
            ],
        }
        self.profile.save()
        university = create_university(
            "sat-conditional-university",
            sat_p25=1400,
            sat_p75=1550,
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn("sat_below_p25", fit["risks"])
        self.assertIn("plan_exam_retake", fit["next_actions"])
        self.assertTrue(fit["conditional_notes"])
        self.assertLessEqual(fit["fit_score"], 55)

    def test_ultra_selective_university_is_never_safety(self):
        self.profile.gpa = "4.00"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1600, "ielts": 9.0}
        self.profile.curriculum_type = "ib"
        self.profile.save()
        university = create_university(
            "ultra-selective-university",
            acceptance_rate="4.00",
            gpa_average="3.70",
            sat_p25=1450,
            sat_p75=1570,
            ielts_minimum="7.0",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn(fit["category"], {"dream", "reach"})
        self.assertNotEqual(fit["category"], "safety")

    def test_fit_source_notes_fall_back_to_official_website(self):
        university = create_university("source-notes-university")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")
        self.assertEqual(len(response.data["source_notes"]), 1)
        self.assertEqual(response.data["source_notes"][0]["url"], university.official_website)

    def test_fit_requires_authentication(self):
        university = create_university("auth-fit-university")
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ConditionalFitTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="conditional-fit", email="conditional@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)

    def test_no_conditional_fit_without_planned_targets(self):
        self.profile.test_scores = {"sat": 1200}
        self.profile.save()
        university = create_university(
            "no-plan-university", acceptance_rate="45.00", sat_p25=1400, sat_p75=1560
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIsNone(fit["conditional_fit_score"])
        self.assertIsNone(fit["conditional_targets"])

    def test_planned_sat_retake_produces_higher_conditional_fit(self):
        self.profile.gpa = "4.50"
        self.profile.gpa_scale = "5.00"
        self.profile.test_scores = {"sat": 1200, "ielts": 7.5}
        self.profile.exam_plans = {
            "taken": [],
            "planned": [
                {"exam_type": "SAT", "target_score": "1550", "planned_retake": True}
            ],
        }
        self.profile.save()
        university = create_university(
            "sat-retake-university",
            acceptance_rate="45.00",
            gpa_average="3.50",
            sat_p25=1400,
            sat_p75=1560,
            ielts_minimum="6.5",
            ielts_competitive="7.0",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn("sat_below_p25", fit["risks"])
        self.assertIsNotNone(fit["conditional_fit_score"])
        self.assertGreater(fit["conditional_fit_score"], fit["fit_score"])
        self.assertEqual(fit["conditional_targets"], {"sat": 1550})

    def test_planned_ielts_retake_produces_higher_conditional_fit(self):
        self.profile.test_scores = {"sat": 1500, "ielts": 5.5}
        self.profile.exam_plans = {
            "taken": [],
            "planned": [
                {"exam_type": "IELTS", "target_score": "7.0", "planned_retake": True}
            ],
        }
        self.profile.save()
        university = create_university(
            "ielts-retake-university",
            acceptance_rate="45.00",
            sat_average=1400,
            ielts_minimum="6.5",
            ielts_competitive="7.0",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn("ielts_below_minimum", fit["risks"])
        self.assertIsNotNone(fit["conditional_fit_score"])
        self.assertGreater(fit["conditional_fit_score"], fit["fit_score"])
        self.assertEqual(fit["conditional_targets"], {"ielts": 7.0})

    def test_target_below_current_score_is_ignored(self):
        self.profile.test_scores = {"sat": 1200}
        self.profile.exam_plans = {
            "taken": [],
            "planned": [{"exam_type": "SAT", "target_score": "1100"}],
        }
        self.profile.save()
        university = create_university(
            "low-target-university", acceptance_rate="45.00", sat_p25=1400, sat_p75=1560
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIsNone(fit["conditional_fit_score"])
        self.assertIsNone(fit["conditional_targets"])

    def test_conditional_fit_hidden_when_target_changes_nothing(self):
        # A target still deep inside the same severity band produces the same
        # estimate, and an unchanged estimate must not be presented as an
        # improvement path.
        self.profile.test_scores = {"sat": 1200}
        self.profile.exam_plans = {
            "taken": [],
            "planned": [{"exam_type": "SAT", "target_score": "1210"}],
        }
        self.profile.save()
        university = create_university(
            "same-band-university", acceptance_rate="45.00", sat_p25=1400, sat_p75=1560
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIsNone(fit["conditional_fit_score"])
        self.assertIsNone(fit["conditional_targets"])

    def test_conditional_fit_flows_into_recommendations_payload(self):
        from services.university_service.recommendations import (
            calculate_university_recommendations,
        )

        self.profile.gpa = "4.50"
        self.profile.gpa_scale = "5.00"
        self.profile.test_scores = {"sat": 1200, "ielts": 7.5}
        self.profile.exam_plans = {
            "taken": [],
            "planned": [{"exam_type": "SAT", "target_score": "1550"}],
        }
        self.profile.save()
        create_university(
            "rec-conditional-university",
            acceptance_rate="45.00",
            gpa_average="3.50",
            sat_p25=1400,
            sat_p75=1560,
        )

        payload = calculate_university_recommendations(self.profile)

        items = payload["recommendations"]
        self.assertTrue(items)
        item = next(
            entry for entry in items if entry["university"]["slug"] == "rec-conditional-university"
        )
        self.assertIn("conditional_fit_score", item)
        self.assertIsNotNone(item["conditional_fit_score"])
        self.assertGreater(item["conditional_fit_score"], item["fit_score"])
        self.assertEqual(item["conditional_targets"], {"sat": 1550})


class CurrencyNormalizationTests(APITestCase):
    def test_non_usd_tuition_converts_when_rate_exists(self):
        ExchangeRate.objects.create(
            currency_code="EUR",
            usd_rate="1.200000",
            effective_date=timezone.now().date(),
            source="Configured test rate",
            confidence="high",
        )
        university = create_university(
            "eur-cost-university",
            tuition_amount="100.00",
            tuition_currency="EUR",
        )

        normalize_university_costs(university, save=True)
        university.refresh_from_db()

        self.assertEqual(university.tuition_original_currency, "EUR")
        self.assertEqual(str(university.tuition_usd_amount), "120.00")
        self.assertEqual(university.currency_conversion_source, "Configured test rate")

    def test_unknown_currency_preserves_original_without_usd_conversion(self):
        university = create_university(
            "unknown-cost-university",
            tuition_amount="100.00",
            tuition_currency="ABC",
        )

        normalize_university_costs(university, save=True)
        university.refresh_from_db()

        self.assertEqual(university.tuition_original_currency, "ABC")
        self.assertIsNone(university.tuition_usd_amount)
        self.assertIn("USD conversion not available yet", university.cost_notes)


    def test_cost_sorting_uses_usd_normalized_field(self):
        high = create_university("high-usd-cost", tuition_usd_amount="200.00")
        low = create_university("low-usd-cost", tuition_usd_amount="100.00")

        self.client.force_authenticate(
            User.objects.create_user(
                username="sorter", email="sorter@test.com", password="testpass123"
            )
        )
        response = self.client.get(
            "/api/v1/universities/",
            {"ordering": "tuition_usd_amount"},
        )

        slugs = [item["slug"] for item in response.data["results"]]
        self.assertLess(slugs.index(low.slug), slugs.index(high.slug))


class RequirementThresholdFilterTests(APITestCase):
    def test_requirement_threshold_filters(self):
        create_university(
            "low-requirement-university",
            ielts_minimum="6.0",
            sat_average=1250,
            gpa_average="3.20",
            acceptance_rate="60.00",
        )
        create_university(
            "high-requirement-university",
            ielts_minimum="7.5",
            sat_average=1520,
            gpa_average="3.90",
            acceptance_rate="8.00",
        )
        create_university("no-data-university")

        self.client.force_authenticate(
            User.objects.create_user(
                username="filterer", email="filterer@test.com", password="testpass123"
            )
        )

        response = self.client.get("/api/v1/universities/", {"ielts_minimum__lte": "6.5"})
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertIn("low-requirement-university", slugs)
        self.assertNotIn("high-requirement-university", slugs)
        self.assertNotIn("no-data-university", slugs)

        response = self.client.get(
            "/api/v1/universities/",
            {"sat_average__gte": "1400", "sat_average__lte": "1600"},
        )
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertEqual(slugs, ["high-requirement-university"])

        response = self.client.get("/api/v1/universities/", {"gpa_average__lte": "3.50"})
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertEqual(slugs, ["low-requirement-university"])

        response = self.client.get("/api/v1/universities/", {"acceptance_rate__gte": "50"})
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertEqual(slugs, ["low-requirement-university"])


class RecommendationFoundationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recommender", email="recommender@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)
        self.profile.target_countries = ["United States"]
        self.profile.intended_majors = ["Computer Science"]
        self.profile.gpa = "4.80"
        self.profile.gpa_scale = "5.00"
        self.profile.test_scores = {"sat": 1450}
        self.profile.save()

    def test_recommendations_follow_preferred_country(self):
        create_university(
            "us-recommendation",
            country="United States",
            acceptance_rate="50.00",
            tuition_usd_amount="10000.00",
        )
        create_university(
            "asia-recommendation",
            country="Singapore",
            acceptance_rate="50.00",
            tuition_usd_amount="10000.00",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/universities/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        countries = {
            item["university"]["country"] for item in response.data["recommendations"]
        }
        self.assertEqual(countries, {"United States"})
        self.assertNotIn("probability", str(response.data).lower())
        self.assertNotIn("chance", str(response.data).lower())
