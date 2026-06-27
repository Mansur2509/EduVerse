from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from services.university_service.models import SavedUniversity, University
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
