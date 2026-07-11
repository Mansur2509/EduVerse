from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from services.profile_assessment_service.services import (
    QUALITATIVE_FIT_DIMENSIONS,
    compute_profile_snapshot_hash,
)
from services.university_service.currency import normalize_university_costs
from services.university_service.models import (
    ExchangeRate,
    SavedUniversity,
    University,
    UniversityDataSource,
    UniversityFieldVerification,
    UniversityProgram,
    UniversityRequirement,
    UniversityScholarship,
    UniversitySubjectRanking,
)
from services.university_service.services import calculate_university_fit
from services.user_profile_service.models import (
    Activity,
    Honor,
    Olympiad,
    ResearchProject,
    Sport,
    Volunteer,
)
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
        cache.clear()  # filter-options is cached; each test needs a clean slate.
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
        response = self.client.get("/api/v1/universities/", {"country": "sample"})
        self.assertEqual(response.data["count"], 1)

    def test_city_filter(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/universities/", {"city": "Northfield"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["slug"], "published-university")
        response = self.client.get("/api/v1/universities/", {"city": "north"})
        self.assertEqual(response.data["count"], 1)

    def test_combined_country_and_city_filter(self):
        create_university("south-sampleton-university", country="Sampleton", city="Southfield")
        create_university("north-other-country-university", country="Otherland", city="Northfield")
        self.client.force_authenticate(self.user)

        response = self.client.get(
            "/api/v1/universities/",
            {"country": "sample", "city": "north"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["slug"] for item in response.data["results"]],
            ["published-university"],
        )

    def test_filter_options_are_data_backed(self):
        create_university(
            "option-private-university",
            country="United States",
            city="Philadelphia",
            institution_type=University.InstitutionType.PRIVATE,
            currency_conversion_confidence="medium",
        )
        demo = create_university(
            "option-demo-university",
            country="Demo Country",
            city="Demo City",
            is_demo=True,
        )
        UniversityFieldVerification.objects.create(
            university=self.published,
            field_name="essay_requirements",
            status=UniversityFieldVerification.Status.PARTIAL,
            source_url="https://example.com/source",
            last_verified_date=timezone.now().date(),
        )
        program = UniversityProgram.objects.create(
            university=self.published,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
        )
        UniversitySubjectRanking.objects.create(
            university=self.published,
            program=program,
            subject_area="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            rank=25,
            source_name="QS Subject",
            source_url="https://example.com/qs-subject",
            ranking_year=2026,
            last_verified_date=timezone.now().date(),
            confidence=UniversitySubjectRanking.Confidence.PARTIAL,
        )
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/universities/filter-options/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("United States", response.data["countries"])
        self.assertIn("Philadelphia", response.data["cities"])
        self.assertIn("private", response.data["institution_types"])
        self.assertIn("medium", response.data["cost_confidences"])
        self.assertIn("partial", response.data["verification_statuses"])
        self.assertIn(
            UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            response.data["major_clusters"],
        )
        self.assertIn("Computer Science", response.data["program_names"])
        self.assertIn("Computer Science", response.data["subject_areas"])
        self.assertIn("QS Subject", response.data["ranking_sources"])
        slugs = [item["slug"] for item in response.data["universities"]]
        self.assertIn("option-private-university", slugs)
        self.assertNotIn(demo.slug, slugs)

    def test_filter_options_are_cached_across_requests(self):
        create_university("cached-option-university", country="Canada", city="Toronto")
        self.client.force_authenticate(self.user)

        first = self.client.get("/api/v1/universities/filter-options/")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertIn("Canada", first.data["countries"])

        # A university created after the first (now-cached) call must not
        # appear in a second call within the TTL, and the second call must
        # not touch the database at all -- proves the response is actually
        # served from cache rather than recomputed every request.
        create_university("post-cache-university", country="Uncached Country", city="Uncached City")
        with CaptureQueriesContext(connection) as queries:
            second = self.client.get("/api/v1/universities/filter-options/")

        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data, first.data)
        self.assertNotIn("Uncached Country", second.data["countries"])
        self.assertEqual(len(queries), 0)

    def test_institution_scholarship_and_confidence_filters(self):
        private_aid = create_university(
            "private-aid-university",
            institution_type=University.InstitutionType.PRIVATE,
            scholarship_available=True,
            currency_conversion_confidence="high",
        )
        create_university(
            "public-no-aid-university",
            institution_type=University.InstitutionType.PUBLIC,
            scholarship_available=False,
            currency_conversion_confidence="low",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(
            "/api/v1/universities/",
            {
                "institution_type": "private",
                "scholarship_available": "true",
                "currency_conversion_confidence": "high",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["slug"] for item in response.data["results"]], [private_aid.slug])

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

    def test_program_and_ranking_filters(self):
        ranked = create_university(
            "ranked-program-university",
            global_rank=12,
            the_rank=18,
            national_rank=2,
        )
        program = UniversityProgram.objects.create(
            university=ranked,
            name="Data Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            portfolio_required=True,
            research_heavy=True,
            source_confidence=UniversityProgram.SourceConfidence.VERIFIED,
        )
        UniversitySubjectRanking.objects.create(
            university=ranked,
            program=program,
            subject_area="Data Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            rank=40,
            source_name="QS Subject",
            source_url="https://example.com/data-ranking",
            ranking_year=2026,
            last_verified_date=timezone.now().date(),
            confidence=UniversitySubjectRanking.Confidence.VERIFIED,
        )
        create_university("unranked-program-university", global_rank=220)
        self.client.force_authenticate(self.user)

        response = self.client.get(
            "/api/v1/universities/",
            {
                "major_cluster": UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
                "program_search": "data",
                "subject_rank_max": "50",
                "global_rank_max": "50",
                "portfolio_required": "true",
                "research_heavy": "true",
                "source_confidence": "verified",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["slug"] for item in response.data["results"]],
            [ranked.slug],
        )

    def test_list_uses_compact_serializer_without_detail_or_import_fields(self):
        heavy = create_university(
            "heavy-catalog-university",
            majors_list=[f"Major {index}" for index in range(12)],
            essay_requirements="Long essay prompt text that belongs on detail only.",
            application_requirements="Long application requirements text.",
            standardized_testing_policy_text="Verbose testing policy.",
            data_quality_notes="Importer caveat for detail/source review.",
            need_based_aid_notes="Need-based aid details.",
            profile_evidence_notes="Internal matching notes.",
        )
        program = UniversityProgram.objects.create(
            university=heavy,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
        )
        UniversitySubjectRanking.objects.create(
            university=heavy,
            program=program,
            subject_area="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            rank=10,
            source_name="QS Subject",
            source_url="https://example.com/qs-cs",
            ranking_year=2026,
            last_verified_date=timezone.now().date(),
            confidence=UniversitySubjectRanking.Confidence.VERIFIED,
        )
        UniversityRequirement.objects.create(
            university=heavy,
            requirement_type="SAT",
            value="1500",
            notes="Detail-only requirement row.",
        )
        UniversityScholarship.objects.create(
            university=heavy,
            name="Detail Scholarship",
            summary="Scholarship detail text.",
            official_url="https://example.com/scholarship",
        )
        UniversityDataSource.objects.create(
            university=heavy,
            source_title="Official source",
            source_url="https://example.com/source",
        )
        UniversityFieldVerification.objects.create(
            university=heavy,
            field_name="acceptance_rate",
            status=UniversityFieldVerification.Status.VERIFIED,
            source_url="https://example.com/acceptance",
            last_verified_date=timezone.now().date(),
        )
        SavedUniversity.objects.create(user=self.user, university=heavy)
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/v1/universities/", {"search": heavy.name})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["results"][0]
        self.assertEqual(item["slug"], heavy.slug)
        self.assertTrue(item["is_shortlisted"])
        self.assertEqual(item["majors_list"], [f"Major {index}" for index in range(8)])
        excluded_fields = {
            "programs",
            "program_display_names",
            "subject_rankings",
            "program_matching",
            "requirements",
            "scholarships",
            "data_sources",
            "field_verifications",
            "budget_comparison",
            "essay_requirements",
            "application_requirements",
            "standardized_testing_policy_text",
            "data_quality_notes",
            "need_based_aid_notes",
            "profile_evidence_notes",
        }
        for field_name in excluded_fields:
            self.assertNotIn(field_name, item)

    def test_list_query_count_and_response_size_stay_compact_with_nested_data(self):
        for index in range(21):
            university = create_university(
                f"catalog-heavy-{index}",
                majors_list=[f"Major {index}-{item}" for item in range(10)],
                essay_requirements="Essay text that should not appear in list payload.",
                data_quality_notes="Importer notes should not appear in list payload.",
            )
            program = UniversityProgram.objects.create(
                university=university,
                name=f"Program {index}",
                major_cluster=UniversityProgram.MajorCluster.ENGINEERING,
            )
            UniversitySubjectRanking.objects.create(
                university=university,
                program=program,
                subject_area=f"Engineering {index}",
                major_cluster=UniversityProgram.MajorCluster.ENGINEERING,
                rank=index + 1,
                source_name="QS Subject",
                source_url=f"https://example.com/ranking-{index}",
                ranking_year=2026,
                last_verified_date=timezone.now().date(),
                confidence=UniversitySubjectRanking.Confidence.PARTIAL,
            )
            UniversityRequirement.objects.create(
                university=university,
                requirement_type="IELTS",
                value="7.0",
            )
            UniversityScholarship.objects.create(
                university=university,
                name=f"Scholarship {index}",
                summary="Detailed scholarship text.",
                official_url=f"https://example.com/scholarship-{index}",
            )
            UniversityDataSource.objects.create(
                university=university,
                source_title=f"Source {index}",
                source_url=f"https://example.com/source-{index}",
            )

        self.client.force_authenticate(self.user)

        with CaptureQueriesContext(connection) as captured:
            response = self.client.get("/api/v1/universities/", {"page": 1, "page_size": 21})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 21)
        self.assertLessEqual(len(captured.captured_queries), 6)
        self.assertLess(len(response.content), 45_000)

    def test_retrieve_serializes_missing_and_present_program_ranking_data(self):
        profile, _ = ensure_profile_records(self.user)
        profile.intended_majors = ["Computer Science"]
        profile.save(update_fields=["intended_majors"])
        program = UniversityProgram.objects.create(
            university=self.published,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            source_confidence=UniversityProgram.SourceConfidence.VERIFIED,
        )
        UniversitySubjectRanking.objects.create(
            university=self.published,
            program=program,
            subject_area="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            rank=35,
            source_name="QS Subject",
            source_url="https://example.com/cs-ranking",
            ranking_year=2026,
            last_verified_date=timezone.now().date(),
            confidence=UniversitySubjectRanking.Confidence.VERIFIED,
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/api/v1/universities/{self.published.slug}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["programs"][0]["subject_rankings"][0]["rank"], 35)
        self.assertEqual(
            response.data["program_matching"]["recommended_programs"][0]["major_cluster"],
            UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
        )

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

    def _shortlist_with_nested_program_data(self, count=5, slug="shortlist-heavy-university"):
        university = create_university(slug)
        for index in range(count):
            program = UniversityProgram.objects.create(
                university=university,
                name=f"Program {index}",
                major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            )
            UniversitySubjectRanking.objects.create(
                university=university,
                program=program,
                subject_area=f"Subject {index}",
                rank=index + 1,
                source_name="QS Subject",
                source_url="https://example.com/qs-subject",
                ranking_year=2026,
                last_verified_date=timezone.now().date(),
                confidence=UniversitySubjectRanking.Confidence.PARTIAL,
            )
        SavedUniversity.objects.create(user=self.user1, university=university)
        return university

    def test_shortlist_lite_mode_returns_compact_payload(self):
        university = self._shortlist_with_nested_program_data()
        self.client.force_authenticate(self.user1)

        response = self.client.get("/api/v1/universities/shortlist/?lite=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry = response.data["results"][0]
        self.assertEqual(
            set(entry["university"].keys()), {"id", "slug", "name", "country", "city"}
        )
        self.assertEqual(entry["university"]["id"], university.id)
        self.assertNotIn("programs", entry["university"])
        self.assertNotIn("subject_rankings", entry["university"])

    def test_shortlist_full_mode_still_returns_nested_university_detail(self):
        self._shortlist_with_nested_program_data()
        self.client.force_authenticate(self.user1)

        response = self.client.get("/api/v1/universities/shortlist/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry = response.data["results"][0]
        self.assertIn("programs", entry["university"])
        self.assertEqual(len(entry["university"]["programs"]), 5)

    def test_shortlist_full_mode_query_count_does_not_grow_with_program_count(self):
        # The exact query count includes a conditional one-off profile lookup
        # (get_budget_comparison) that can vary by one request-to-request for
        # reasons unrelated to this fix, so this asserts both the 10-program
        # and 25-program cases stay under a small, flat ceiling rather than
        # pinning an exact number or requiring bit-for-bit equality -- what
        # matters is that query count does not scale with program count.
        self._shortlist_with_nested_program_data(count=10)
        self.client.force_authenticate(self.user1)

        with CaptureQueriesContext(connection) as small:
            response = self.client.get("/api/v1/universities/shortlist/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(len(small.captured_queries), 15)

        SavedUniversity.objects.all().delete()
        self._shortlist_with_nested_program_data(count=25, slug="shortlist-heavy-university-2")
        with CaptureQueriesContext(connection) as large:
            response = self.client.get("/api/v1/universities/shortlist/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(len(large.captured_queries), 15)

    def test_shortlist_lite_mode_query_count_is_small(self):
        self._shortlist_with_nested_program_data(count=10)
        self.client.force_authenticate(self.user1)

        with self.assertNumQueries(3):
            response = self.client.get("/api/v1/universities/shortlist/?lite=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_shortlist_page_size_is_capped_below_global_default(self):
        for index in range(60):
            university = create_university(f"shortlist-cap-{index}")
            SavedUniversity.objects.create(user=self.user1, university=university)
        self.client.force_authenticate(self.user1)

        response = self.client.get("/api/v1/universities/shortlist/?lite=1&page_size=1000")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 50)
        self.assertEqual(response.data["count"], 60)


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

    def test_fit_does_not_fail_high_five_point_gpa_against_hundred_point_requirement(self):
        # Spec example: 4.75/5.0 (~95/100, ~3.80/4.0) is comfortably above an
        # 87/100 (~3.48/4.0) university requirement; raw-scale comparison would
        # wrongly read 4.75 as below a "87" benchmark.
        self.profile.gpa = "4.75"
        self.profile.gpa_scale = "5.00"
        self.profile.save()

        university = create_university(
            "hundred-point-benchmark-university",
            acceptance_rate="45.00",
            gpa_average="3.48",
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")

        self.assertIn("gpa_above_average", response.data["strengths"])
        self.assertNotIn("gpa_below_average", response.data["risks"])
        self.assertEqual(
            Decimal(str(response.data["student_academic_context"]["normalized_gpa_4"])),
            Decimal("3.80"),
        )

    def test_fit_compares_five_point_gpa_against_hundred_point_benchmark(self):
        self.profile.gpa = "4.90"
        self.profile.gpa_scale = "5.00"
        self.profile.curriculum_type = self.profile.CurriculumType.ACADEMIC_LYCEUM
        self.profile.ap_courses_count = 3
        self.profile.save()

        university = create_university(
            "hundred-scale-fit-university",
            acceptance_rate="45.00",
            gpa_average="88.00",
            gpa_average_scale="100.00",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("gpa_above_average", response.data["strengths"])
        self.assertNotIn("gpa_below_average", response.data["risks"])
        self.assertEqual(response.data["academic_fit"]["status"], "above_benchmark")
        self.assertAlmostEqual(
            response.data["academic_fit"]["normalized_student_gpa_percent"],
            98.0,
        )
        self.assertAlmostEqual(
            response.data["academic_fit"]["normalized_benchmark_percent"],
            88.0,
        )
        self.assertEqual(response.data["academic_fit"]["curriculum_type"], "academic_lyceum")
        self.assertEqual(
            response.data["academic_fit"]["curriculum_note"],
            "curriculum_context_available",
        )

    def test_fit_compares_four_point_gpa_against_hundred_point_benchmark(self):
        self.profile.gpa = "3.80"
        self.profile.gpa_scale = "4.00"
        self.profile.save()

        university = create_university(
            "four-to-hundred-fit-university",
            acceptance_rate="45.00",
            gpa_average="88.00",
            gpa_average_scale="100.00",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn("gpa_above_average", fit["strengths"])
        self.assertNotIn("gpa_below_average", fit["risks"])
        self.assertEqual(fit["academic_fit"]["status"], "above_benchmark")
        self.assertEqual(fit["academic_fit"]["normalized_student_gpa_percent"], 95.0)
        self.assertEqual(fit["academic_fit"]["normalized_benchmark_percent"], 88.0)

    def test_unknown_hundred_point_gpa_scale_does_not_create_false_gap(self):
        self.profile.gpa = "4.90"
        self.profile.gpa_scale = "5.00"
        self.profile.save()
        university = create_university(
            "unknown-scale-gpa-university",
            acceptance_rate="45.00",
            gpa_average="88.00",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertEqual(fit["academic_fit"]["status"], "unknown")
        self.assertEqual(fit["academic_fit"]["confidence"], "low")
        self.assertNotIn("gpa_below_average", fit["risks"])
        self.assertNotIn("gpa_above_average", fit["strengths"])

    def test_weighted_gpa_with_unknown_scale_does_not_normalize_above_100(self):
        self.profile.gpa = "4.90"
        self.profile.gpa_scale = "5.00"
        self.profile.save()
        university = create_university(
            "mit-style-weighted-gpa-university",
            acceptance_rate="8.00",
            gpa_average="4.17",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertEqual(fit["academic_fit"]["status"], "unknown")
        self.assertEqual(fit["academic_fit"]["confidence"], "low")
        self.assertIsNone(fit["academic_fit"]["normalized_benchmark_percent"])
        self.assertIn("scale is unrecorded", fit["academic_fit"]["benchmark_note"])
        self.assertNotIn("gpa_below_average", fit["risks"])
        self.assertNotIn("gpa_above_average", fit["strengths"])

    def test_five_point_gpa_meets_ninety_percent_benchmark_with_declared_scale(self):
        self.profile.gpa = "4.75"
        self.profile.gpa_scale = "5.00"
        self.profile.save()
        university = create_university(
            "ninety-percent-fit-university",
            acceptance_rate="45.00",
            gpa_average="90.00",
            gpa_average_scale="100.00",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn(fit["academic_fit"]["status"], {"above_benchmark", "meets_benchmark"})
        self.assertEqual(fit["academic_fit"]["normalized_student_gpa_percent"], 95.0)
        self.assertEqual(fit["academic_fit"]["normalized_benchmark_percent"], 90.0)
        self.assertLessEqual(fit["academic_fit"]["normalized_benchmark_percent"], 100.0)
        self.assertNotIn("gpa_below_average", fit["risks"])

    def test_high_five_point_gpa_above_eighty_eight_percent_declared_scale(self):
        # Spec example: 4.9/5.0 (98%) vs an explicit 88/100 benchmark.
        self.profile.gpa = "4.90"
        self.profile.gpa_scale = "5.00"
        self.profile.save()
        university = create_university(
            "eighty-eight-percent-fit-university-a",
            acceptance_rate="45.00",
            gpa_average="88.00",
            gpa_average_scale="100.00",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn(fit["academic_fit"]["status"], {"above_benchmark", "meets_benchmark"})
        self.assertEqual(fit["academic_fit"]["normalized_student_gpa_percent"], 98.0)
        self.assertEqual(fit["academic_fit"]["normalized_benchmark_percent"], 88.0)
        self.assertLessEqual(fit["academic_fit"]["normalized_benchmark_percent"], 100.0)
        self.assertNotIn("gpa_below_average", fit["risks"])

    def test_four_point_gpa_above_eighty_eight_percent_declared_scale(self):
        # Spec example: 3.8/4.0 (95%) vs an explicit 88/100 benchmark.
        self.profile.gpa = "3.80"
        self.profile.gpa_scale = "4.00"
        self.profile.save()
        university = create_university(
            "eighty-eight-percent-fit-university-b",
            acceptance_rate="45.00",
            gpa_average="88.00",
            gpa_average_scale="100.00",
        )

        fit = calculate_university_fit(self.profile, university)

        self.assertIn(fit["academic_fit"]["status"], {"above_benchmark", "meets_benchmark"})
        self.assertEqual(fit["academic_fit"]["normalized_student_gpa_percent"], 95.0)
        self.assertEqual(fit["academic_fit"]["normalized_benchmark_percent"], 88.0)
        self.assertLessEqual(fit["academic_fit"]["normalized_benchmark_percent"], 100.0)
        self.assertNotIn("gpa_below_average", fit["risks"])

    def test_fit_get_uses_cached_qualitative_scores_without_ai_call(self):
        from services.profile_assessment_service.models import AIProfileAssessment

        self.profile.intended_majors = ["Computer Science"]
        self.profile.save()
        category_scores = {
            "profile_evidence_score": 7,
            "activities_score": 7,
            "honors_olympiads_score": 7,
            "research_experience_score": 7,
            "portfolio_score": 7,
            "subject_passion_score": 7,
            "curiosity_score": 7,
            "originality_score": 7,
            "leadership_score": 7,
            "community_impact_score": 7,
            "research_fit_score": 7,
            "olympiads_score": 7,
        }
        qualitative_scores = {
            dimension: {
                "score": 9,
                "evidence": "Strong saved profile signal.",
                "confidence": "high",
            }
            for dimension in QUALITATIVE_FIT_DIMENSIONS
        }
        AIProfileAssessment.objects.create(
            user=self.user,
            profile_snapshot_hash=compute_profile_snapshot_hash(self.user),
            overall_profile_score=75,
            confidence="high",
            qualitative_fit_scores=qualitative_scores,
            expires_at=timezone.now() + timezone.timedelta(days=30),
            **category_scores,
        )
        university = create_university(
            "cached-qualitative-fit-university",
            acceptance_rate="45.00",
        )
        UniversityProgram.objects.create(
            university=university,
            name="Computer Science",
            major_cluster=UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
        )

        with patch(
            "services.profile_assessment_service.services.get_profile_assessment_client"
        ) as client_factory:
            fit = calculate_university_fit(self.profile, university)

        client_factory.assert_not_called()
        self.assertEqual(fit["qualitative_fit_status"], "fresh")
        self.assertIsNotNone(fit["personal_fit_score"])
        self.assertEqual(fit["personal_fit_context"]["major_cluster"], "computer_science_ai_data")

    def test_fit_normalizes_ten_point_gpa_for_comparison(self):
        # Spec example: 9/10 -> 90/100 -> 3.60/4.0.
        self.profile.gpa = "9.00"
        self.profile.gpa_scale = "10.00"
        self.profile.save()

        university = create_university(
            "ten-point-benchmark-university",
            acceptance_rate="45.00",
            gpa_average="3.50",
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")

        self.assertEqual(
            Decimal(str(response.data["student_academic_context"]["normalized_gpa_4"])),
            Decimal("3.60"),
        )

    def test_fit_normalizes_twenty_point_gpa_for_comparison(self):
        # Spec example: 17/20 -> 85/100 -> 3.40/4.0.
        self.profile.gpa = "17.00"
        self.profile.gpa_scale = "20.00"
        self.profile.save()

        university = create_university(
            "twenty-point-benchmark-university",
            acceptance_rate="45.00",
            gpa_average="3.10",
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/v1/universities/{university.slug}/fit/")

        self.assertIn("gpa_above_average", response.data["strengths"])
        self.assertEqual(
            Decimal(str(response.data["student_academic_context"]["normalized_gpa_4"])),
            Decimal("3.40"),
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

    def test_optional_evidence_improves_profile_fit_without_dominating_academics(self):
        self.profile.gpa = "2.80"
        self.profile.gpa_scale = "4.00"
        self.profile.test_scores = {"sat": 1180}
        self.profile.intended_majors = ["Computer Science"]
        self.profile.save()
        university = create_university(
            "evidence-weight-university",
            acceptance_rate="45.00",
            gpa_average="3.80",
            sat_p25=1450,
            sat_p75=1550,
        )
        UniversityProgram.objects.create(university=university, name="Computer Science")

        weak_fit = calculate_university_fit(self.profile, university)
        ResearchProject.objects.create(
            user=self.user,
            title="Independent CS research",
            field="Computer Science",
            current_stage="completed",
        )
        Activity.objects.create(
            user=self.user,
            title="Programming club",
            category="leadership",
        )
        if hasattr(self.profile, "_optional_evidence_counts_cache"):
            delattr(self.profile, "_optional_evidence_counts_cache")
        stronger_fit = calculate_university_fit(self.profile, university)

        self.assertGreater(
            stronger_fit["profile_evidence"]["evidence_subscore"],
            weak_fit["profile_evidence"]["evidence_subscore"],
        )
        self.assertIn(
            "research_relevant_to_program_context",
            stronger_fit["profile_evidence"]["program_relevance_notes"],
        )
        self.assertLess(stronger_fit["profile_subscore"], stronger_fit["academic_subscore"] + 60)
        self.assertLessEqual(stronger_fit["fit_score"], 55)

    def test_missing_optional_evidence_lowers_evidence_confidence(self):
        university = create_university("unknown-evidence-policy-university")

        fit = calculate_university_fit(self.profile, university)

        self.assertEqual(fit["profile_evidence"]["confidence"], "low")
        self.assertIn(
            "evidence_weighting_needs_verification",
            fit["profile_evidence"]["program_relevance_notes"],
        )
        self.assertIn("research", fit["profile_evidence"]["missing_evidence"])

    def test_evidence_contributions_are_sorted_by_impact_not_definition_order(self):
        # Populate 6+ of the 9 optional-evidence categories so a naive "first 5
        # in OPTIONAL_EVIDENCE_WEIGHTS order" truncation would silently drop a
        # category that actually scored higher than one it kept.
        university = create_university("evidence-sort-university")
        ResearchProject.objects.create(
            user=self.user,
            title="Independent research",
            field="Biology",
            current_stage="completed",
        )
        Activity.objects.create(user=self.user, title="Club lead", category="leadership")
        Honor.objects.create(user=self.user, title="Honor roll")
        Olympiad.objects.create(user=self.user, name="Math olympiad", subject="Math")
        Sport.objects.create(user=self.user, sport_name="Soccer")
        Volunteer.objects.create(user=self.user, title="Shelter volunteering")

        fit = calculate_university_fit(self.profile, university)
        contributions = fit["profile_evidence"]["category_contributions"]

        present = [item for item in contributions if item["count"] > 0]
        self.assertGreaterEqual(len(present), 6)
        # All present-evidence entries must sort ahead of absent ones.
        present_indexes = [
            index for index, item in enumerate(contributions) if item["count"] > 0
        ]
        self.assertEqual(present_indexes, list(range(len(present_indexes))))
        # Within the present entries, score must be non-increasing.
        scores = [item["score"] for item in present]
        self.assertEqual(scores, sorted(scores, reverse=True))


class UniversityBenchmarkComparisonTests(APITestCase):
    """`calculate_university_fit` folding in `compare_student_vector_to_
    university_weights` (PART 7 of HOTFIX-007): a per-university comparison
    against `UniversitySignalWeights`, not a flat, university-agnostic score.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="benchmarkuser", email="benchmark@test.com", password="testpass123"
        )
        self.profile, _ = ensure_profile_records(self.user)

    def _attach_assessment(self, **score_overrides):
        from services.profile_assessment_service.models import AIProfileAssessment

        scores = {
            "profile_evidence_score": 7,
            "activities_score": 7,
            "honors_olympiads_score": 7,
            "research_experience_score": 7,
            "portfolio_score": 7,
            "subject_passion_score": 7,
            "curiosity_score": 7,
            "originality_score": 7,
            "leadership_score": 7,
            "community_impact_score": 7,
            "research_fit_score": 7,
            "olympiads_score": 7,
        }
        scores.update(score_overrides)
        assessment = AIProfileAssessment.objects.create(
            user=self.user,
            profile_snapshot_hash="test-hash",
            overall_profile_score=7,
            confidence="high",
            expires_at=timezone.now() + timezone.timedelta(days=300),
            **scores,
        )
        # Bypass hash/staleness matching (exercised separately by
        # profile_assessment_service tests) to isolate the comparison logic.
        self.profile._current_profile_assessment_cache = assessment
        return assessment

    def test_no_signal_weights_leaves_score_and_strengths_unchanged(self):
        university = create_university("no-benchmark-university")
        self._attach_assessment()
        fit = calculate_university_fit(self.profile, university)
        comparison = fit["profile_evidence"]["benchmark_comparison"]
        self.assertFalse(comparison["available"])
        self.assertEqual(comparison["reason"], "university_benchmark_not_published")
        self.assertNotIn("benchmark_alignment_strong", fit["strengths"])
        self.assertNotIn("benchmark_alignment_stretch", fit["risks"])

    def test_no_assessment_leaves_comparison_unavailable(self):
        from services.university_service.models import UniversitySignalWeights

        university = create_university("assessment-missing-university")
        UniversitySignalWeights.objects.create(
            university=university, **{f"{name}_score": 7 for name in _ALL_SIGNAL_NAMES}
        )
        fit = calculate_university_fit(self.profile, university)
        comparison = fit["profile_evidence"]["benchmark_comparison"]
        self.assertFalse(comparison["available"])
        self.assertEqual(comparison["reason"], "profile_assessment_not_run")

    def test_strong_alignment_adds_strength_and_boosts_score(self):
        from services.university_service.models import UniversitySignalWeights

        university = create_university("strong-alignment-university")
        UniversitySignalWeights.objects.create(
            university=university, **{f"{name}_score": 5 for name in _ALL_SIGNAL_NAMES}
        )
        self._attach_assessment()  # student vector is all 7s, university wants 5s
        fit = calculate_university_fit(self.profile, university)
        comparison = fit["profile_evidence"]["benchmark_comparison"]
        self.assertTrue(comparison["available"])
        self.assertEqual(comparison["fit_band"], "strong_alignment")
        self.assertIn("benchmark_alignment_strong", fit["strengths"])
        self.assertNotIn("benchmark_alignment_stretch", fit["risks"])

    def test_high_stretch_alignment_adds_risk_and_lowers_score(self):
        from services.university_service.models import UniversitySignalWeights

        university_a = create_university("baseline-university")
        UniversitySignalWeights.objects.create(
            university=university_a, **{f"{name}_score": 5 for name in _ALL_SIGNAL_NAMES}
        )
        university_b = create_university("high-stretch-university")
        UniversitySignalWeights.objects.create(
            university=university_b,
            profile_evidence_score=10,
            activities_score=10,
            honors_olympiads_score=10,
            research_experience_score=10,
            portfolio_score=5,
            subject_passion_score=5,
            curiosity_score=5,
            originality_score=5,
            leadership_score=5,
            community_impact_score=5,
            research_fit_score=5,
            olympiads_score=5,
        )
        self._attach_assessment()
        baseline_fit = calculate_university_fit(self.profile, university_a)
        stretch_fit = calculate_university_fit(self.profile, university_b)
        comparison = stretch_fit["profile_evidence"]["benchmark_comparison"]
        self.assertTrue(comparison["available"])
        self.assertEqual(comparison["fit_band"], "high_stretch_alignment")
        self.assertIn("benchmark_alignment_stretch", stretch_fit["risks"])
        self.assertLess(
            stretch_fit["profile_evidence"]["evidence_subscore"],
            baseline_fit["profile_evidence"]["evidence_subscore"],
        )

    def test_benchmark_comparison_never_exposes_raw_scores_or_weights(self):
        from services.university_service.models import UniversitySignalWeights

        university = create_university("no-leak-university")
        UniversitySignalWeights.objects.create(
            university=university, **{f"{name}_score": 5 for name in _ALL_SIGNAL_NAMES}
        )
        self._attach_assessment()
        fit = calculate_university_fit(self.profile, university)
        comparison = fit["profile_evidence"]["benchmark_comparison"]
        self.assertEqual(set(comparison.keys()), {"available", "fit_band", "signals_compared"})

    def test_below_minimum_comparable_signals_reports_limited_data_not_a_band(self):
        from services.university_service.models import UniversitySignalWeights

        university = create_university("sparse-benchmark-university")
        UniversitySignalWeights.objects.create(university=university, profile_evidence_score=5)
        self._attach_assessment()
        fit = calculate_university_fit(self.profile, university)
        comparison = fit["profile_evidence"]["benchmark_comparison"]
        self.assertFalse(comparison["available"])
        self.assertEqual(comparison["reason"], "insufficient_comparable_signals")


_ALL_SIGNAL_NAMES = (
    "profile_evidence",
    "activities",
    "honors_olympiads",
    "research_experience",
    "portfolio",
    "subject_passion",
    "curiosity",
    "originality",
    "leadership",
    "community_impact",
    "research_fit",
    "olympiads",
)


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
