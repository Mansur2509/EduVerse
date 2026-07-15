from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from services.application_service.models import ApplicationTrackerItem
from services.application_service.timeline import build_application_timeline, urgency_for_days
from services.essay_service.models import EssayWorkspace
from services.exam_content_service.models import OfficialExamDate
from services.roadmap_service.models import RoadmapPlan, RoadmapTask
from services.university_service.models import (
    University,
    UniversityFieldVerification,
)
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


class UrgencyThresholdTests(SimpleTestCase):
    def test_urgency_buckets(self):
        self.assertEqual(urgency_for_days(None), "unknown")
        self.assertEqual(urgency_for_days(-1), "overdue")
        self.assertEqual(urgency_for_days(0), "critical")
        self.assertEqual(urgency_for_days(7), "critical")
        self.assertEqual(urgency_for_days(8), "urgent")
        self.assertEqual(urgency_for_days(14), "urgent")
        self.assertEqual(urgency_for_days(15), "soon")
        self.assertEqual(urgency_for_days(30), "soon")
        self.assertEqual(urgency_for_days(31), "upcoming")
        self.assertEqual(urgency_for_days(90), "upcoming")
        self.assertEqual(urgency_for_days(91), "far")


def _create_university(slug="timeline-university", **overrides):
    defaults = {
        "name": "Timeline University",
        "country": "Demoland",
        "city": "Sample City",
        "official_website": f"https://example.com/{slug}",
        "admissions_url": f"https://example.com/{slug}/admissions",
        "is_published": True,
    }
    defaults.update(overrides)
    return University.objects.create(slug=slug, **defaults)


class ApplicationTimelineApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="timeline-user", email="timeline@test.com", password="testpass123"
        )
        self.client.force_authenticate(self.user)

    def _create_application(self, university, **overrides):
        return ApplicationTrackerItem.objects.create(
            user=self.user, university=university, **overrides
        )

    def _timeline(self, application):
        response = self.client.get(f"/api/applications/{application.id}/timeline/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_missing_deadline_is_reported_not_invented(self):
        university = _create_university()
        application = self._create_application(university)
        data = self._timeline(application)
        application_deadline = next(d for d in data["deadlines"] if d["kind"] == "application")
        self.assertIsNone(application_deadline["date"])
        self.assertEqual(application_deadline["confidence"], "missing")
        self.assertEqual(data["suggested_dates"], [])

    def test_user_provided_deadline_is_labelled(self):
        university = _create_university()
        application = self._create_application(
            university, deadline=date.today() + timedelta(days=60)
        )
        data = self._timeline(application)
        application_deadline = next(d for d in data["deadlines"] if d["kind"] == "application")
        self.assertEqual(application_deadline["confidence"], "user_provided")

    def test_imported_university_deadline_without_verification_is_partial(self):
        university = _create_university(
            application_deadline=date.today() + timedelta(days=60)
        )
        application = self._create_application(university)
        data = self._timeline(application)
        application_deadline = next(d for d in data["deadlines"] if d["kind"] == "application")
        self.assertEqual(application_deadline["confidence"], "partial")

    def test_verified_university_deadline_is_verified(self):
        university = _create_university(
            application_deadline=date.today() + timedelta(days=60)
        )
        UniversityFieldVerification.objects.create(
            university=university,
            field_name="application_deadline",
            status="verified",
            source_url="https://example.com/official",
            last_verified_date=date.today(),
        )
        application = self._create_application(university)
        data = self._timeline(application)
        application_deadline = next(d for d in data["deadlines"] if d["kind"] == "application")
        self.assertEqual(application_deadline["confidence"], "verified")

    def test_university_deadline_uses_profile_graduation_cycle(self):
        university = _create_university(application_deadline=date(2025, 11, 1))
        application = self._create_application(university)
        profile, _ = ensure_profile_records(self.user)
        profile.expected_graduation_year = 2027
        profile.save(update_fields=["expected_graduation_year"])

        data = build_application_timeline(application, profile, today=date(2026, 7, 1))
        application_deadline = next(d for d in data["deadlines"] if d["kind"] == "application")

        self.assertEqual(application_deadline["date"], "2026-11-01")
        self.assertEqual(application_deadline["source_date"], "2025-11-01")
        self.assertEqual(application_deadline["normalized_year"], 2026)
        self.assertEqual(application_deadline["cycle_label"], "2026-2027")
        self.assertEqual(application_deadline["days_remaining"], 123)
        self.assertTrue(data["suggested_dates"])

    def test_missing_graduation_year_does_not_use_source_year_for_planning(self):
        university = _create_university(application_deadline=date(2025, 11, 1))
        application = self._create_application(university)
        profile, _ = ensure_profile_records(self.user)
        profile.expected_graduation_year = None
        profile.save(update_fields=["expected_graduation_year"])

        data = build_application_timeline(application, profile, today=date(2026, 7, 1))
        application_deadline = next(d for d in data["deadlines"] if d["kind"] == "application")

        self.assertIsNone(application_deadline["date"])
        self.assertEqual(application_deadline["source_date"], "2025-11-01")
        self.assertIsNone(application_deadline["days_remaining"])
        self.assertEqual(application_deadline["urgency"], "unknown")
        self.assertEqual(data["suggested_dates"], [])

    def test_far_away_deadline_does_not_create_urgent_work(self):
        university = _create_university()
        application = self._create_application(
            university, deadline=date.today() + timedelta(days=300)
        )
        data = self._timeline(application)
        application_deadline = next(d for d in data["deadlines"] if d["kind"] == "application")
        self.assertEqual(application_deadline["urgency"], "far")
        suggested_types = {item["type"] for item in data["suggested_dates"]}
        self.assertNotIn("final_review", suggested_types)
        self.assertFalse(
            any(item["urgency"] in {"urgent", "critical"} for item in data["suggested_dates"])
        )

    def test_close_deadline_creates_critical_final_review(self):
        university = _create_university()
        application = self._create_application(
            university, deadline=date.today() + timedelta(days=10)
        )
        data = self._timeline(application)
        application_deadline = next(d for d in data["deadlines"] if d["kind"] == "application")
        self.assertEqual(application_deadline["urgency"], "urgent")
        suggested = {item["type"]: item for item in data["suggested_dates"]}
        self.assertIn("final_review", suggested)
        self.assertEqual(suggested["final_review"]["urgency"], "critical")
        # No unrealistic long-term work when the deadline is imminent.
        self.assertNotIn("exam_registration", suggested)
        self.assertNotIn("essay_start", suggested)

    def test_linked_essays_appear(self):
        university = _create_university()
        application = self._create_application(university)
        EssayWorkspace.objects.create(
            user=self.user,
            university=university,
            application=application,
            title="Why this school",
            essay_type=EssayWorkspace.EssayType.WHY_SCHOOL,
            word_limit=650,
            draft_text="one two three",
        )
        data = self._timeline(application)
        self.assertEqual(len(data["linked_essays"]), 1)
        self.assertEqual(data["linked_essays"][0]["word_count"], 3)

    def test_essay_sharing_university_but_not_linked_to_application_is_excluded(self):
        # A university-matched essay that was never explicitly linked (via the
        # `application` FK) must not appear as "linked" -- otherwise the
        # unlink action in the UI would have no visible effect.
        university = _create_university()
        EssayWorkspace.objects.create(
            user=self.user,
            university=university,
            title="Why this school",
            essay_type=EssayWorkspace.EssayType.WHY_SCHOOL,
            word_limit=650,
            draft_text="one two three",
        )
        application = self._create_application(university)
        data = self._timeline(application)
        self.assertEqual(data["linked_essays"], [])

    def test_linked_essays_query_count_does_not_grow_with_essay_count(self):
        # _linked_essays() is a single filtered queryset with word_count
        # computed from an already-loaded field -- guards against a future
        # change reintroducing a per-essay query.
        university = _create_university()
        application = self._create_application(university)
        for index in range(2):
            EssayWorkspace.objects.create(
                user=self.user,
                university=university,
                application=application,
                title=f"Essay {index}",
                essay_type=EssayWorkspace.EssayType.WHY_SCHOOL,
                draft_text="one two three",
            )

        with CaptureQueriesContext(connection) as few:
            self._timeline(application)

        for index in range(2, 8):
            EssayWorkspace.objects.create(
                user=self.user,
                university=university,
                application=application,
                title=f"Essay {index}",
                essay_type=EssayWorkspace.EssayType.WHY_SCHOOL,
                draft_text="one two three",
            )

        with CaptureQueriesContext(connection) as many:
            self._timeline(application)

        self.assertEqual(
            len(few),
            len(many),
            "Timeline query count grew with linked-essay count -- check for a new N+1.",
        )

    def test_linked_exams_report_sat_gap_severity(self):
        university = _create_university(sat_p75=1510)
        application = self._create_application(university)
        profile, _ = ensure_profile_records(self.user)
        profile.test_scores = {"sat": 1220}
        profile.save(update_fields=["test_scores"])
        data = self._timeline(application)
        sat = next(entry for entry in data["linked_exams"] if entry["exam"] == "SAT")
        self.assertEqual(sat["current_score"], 1220)
        self.assertEqual(sat["threshold"], 1510)
        self.assertEqual(sat["severity"], "significant_gap")

    def test_toefl_links_to_official_ets_site_when_planned(self):
        university = _create_university()
        application = self._create_application(university)
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {"toefl": {"planned_retake": True}}
        profile.save(update_fields=["exam_plans"])
        data = self._timeline(application)
        toefl = next(entry for entry in data["linked_exams"] if entry["exam"] == "TOEFL")
        self.assertEqual(toefl["source_url"], "https://www.ets.org/toefl")

    def test_ielts_falls_back_to_official_site_without_university_source(self):
        university = _create_university(
            ielts_minimum="6.5", admissions_url="", official_website=""
        )
        application = self._create_application(university)
        data = self._timeline(application)
        ielts = next(entry for entry in data["linked_exams"] if entry["exam"] == "IELTS")
        self.assertEqual(ielts["source_url"], "https://www.ielts.org")

    def test_exam_after_deadline_is_flagged(self):
        university = _create_university(sat_p75=1510)
        application = self._create_application(
            university, deadline=date.today() + timedelta(days=10)
        )
        profile, _ = ensure_profile_records(self.user)
        profile.exam_plans = {"sat": {"planned_retake": True}}
        profile.save(update_fields=["exam_plans"])
        OfficialExamDate.objects.create(
            exam_type=OfficialExamDate.ExamType.SAT,
            name="Late SAT",
            test_date=date.today() + timedelta(days=30),
            registration_deadline=date.today() + timedelta(days=15),
            late_registration_deadline=date.today() + timedelta(days=18),
            late_test_date=date.today() + timedelta(days=45),
            late_test_time="12 p.m. local time",
            academic_year="2026-2027",
            source_url="https://satsuite.collegeboard.org/dates",
            last_verified_date=date.today(),
            verification_status=OfficialExamDate.VerificationStatus.PARTIAL,
        )
        data = self._timeline(application)
        sat = next(entry for entry in data["linked_exams"] if entry["exam"] == "SAT")
        self.assertFalse(sat["scores_arrive_before_deadline"])
        self.assertEqual(
            sat["late_registration_deadline"],
            (date.today() + timedelta(days=18)).isoformat(),
        )
        self.assertEqual(sat["late_test_time"], "12 p.m. local time")

    def test_milestone_and_roadmap_task_appear_as_events(self):
        university = _create_university()
        application = self._create_application(university)
        application.milestones.create(
            title="Draft personal statement",
            category="essays",
            due_date=date.today() + timedelta(days=20),
        )
        plan = RoadmapPlan.objects.create(user=self.user, title="Roadmap")
        RoadmapTask.objects.create(
            user=self.user,
            plan=plan,
            title="Submit application",
            category=RoadmapTask.Category.DEADLINES,
            due_date=date.today() + timedelta(days=25),
            dedup_key="manual:timeline",
            linked_application=application,
            linked_university=university,
        )
        data = self._timeline(application)
        event_types = {event["type"] for event in data["events"]}
        self.assertIn("custom_milestone", event_types)
        self.assertIn("roadmap_task", event_types)

    def test_timeline_is_self_only(self):
        university = _create_university()
        application = self._create_application(university)
        other = User.objects.create_user(
            username="intruder", email="intruder@test.com", password="testpass123"
        )
        self.client.force_authenticate(other)
        response = self.client.get(f"/api/applications/{application.id}/timeline/")
        self.assertEqual(response.status_code, 404)


class MilestoneFieldsApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="milestone-user", email="milestone@test.com", password="testpass123"
        )
        self.client.force_authenticate(self.user)
        self.university = _create_university()

    def test_milestone_priority_and_notes_persist(self):
        application = ApplicationTrackerItem.objects.create(
            user=self.user, university=self.university
        )
        response = self.client.post(
            f"/api/applications/{application.id}/milestones/",
            {
                "title": "Recommendation request",
                "category": "recommendations",
                "priority": "high",
                "notes": "Ask Ms. Rivera by email.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["priority"], "high")
        self.assertEqual(response.data["notes"], "Ask Ms. Rivera by email.")

        listing = self.client.get(f"/api/applications/{application.id}/milestones/")
        self.assertEqual(listing.data[0]["priority"], "high")
