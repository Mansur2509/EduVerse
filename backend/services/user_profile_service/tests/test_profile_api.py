from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from services.user_profile_service.models import StudentProfile, UserPreference

User = get_user_model()


class ProfileApiTests(APITestCase):
    complete_onboarding_payload = {
        "full_name": "Student Example",
        "birth_date": "2008-04-12",
        "country": "Uzbekistan",
        "city": "Tashkent",
        "school_or_university": "Example Academic School",
        "grade": "11",
        "education_status": "school_student",
        "expected_graduation_year": 2027,
        "gpa": "4.50",
        "gpa_scale": "5.00",
        "intended_degree": "bachelor",
        "target_countries": ["United States"],
        "target_universities": [],
        "university_unsure": True,
        "intended_majors": ["Computer Science"],
        "major_unsure": False,
        "scholarship_need": "yes",
        "interested_classes": ["Mathematics"],
        "preparation_needs": ["SAT preparation"],
        "exam_plans": {
            "taken": [],
            "planned": [
                {
                    "name": "SAT",
                    "date": "2027-03-13",
                    "target_score": "1450",
                }
            ],
        },
        "activities": {
            "extracurriculars": ["Coding club"],
            "honors": [],
            "sports": [],
            "olympiads": [],
            "research_projects": [],
            "mun_debate": [],
            "volunteering": [],
            "leadership": [],
            "work_internships": [],
        },
        "essay_status": "not_yet",
        "essay_stage": "planning",
        "support_priorities": ["University research"],
        "onboarding_sections": [
            "identity",
            "academic",
            "exams",
            "activities",
            "support",
        ],
    }

    def setUp(self):
        self.user = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.STUDENT,
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            full_name="Student Example",
        )
        self.preferences = UserPreference.objects.create(user=self.user)
        self.other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="Strong-Development-Password-842!",
            role=User.Role.ORGANIZER,
        )
        self.other_profile = StudentProfile.objects.create(
            user=self.other_user,
            full_name="Other User",
            country="Other country",
        )
        UserPreference.objects.create(user=self.other_user)

    def test_authenticated_user_can_view_only_own_profile(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("profile:me"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["full_name"], self.profile.full_name)
        self.assertEqual(response.data["exam_plans"], {"taken": [], "planned": []})
        self.assertNotEqual(response.data["id"], self.other_user.id)

    def test_authenticated_user_can_update_allowed_fields(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("profile:me"),
            {
                "birth_date": "2008-04-12",
                "country": "Uzbekistan",
                "city": "Tashkent",
                "school_or_university": "Example Academic School",
                "grade": "11",
                "education_status": "school_student",
                "intended_degree": "bachelor",
                "target_countries": ["United States", "Germany"],
                "intended_majors": ["Computer Science", "Economics"],
                "interests": ["Research", "Debate"],
                "languages": ["Uzbek", "English", "Russian"],
                "test_scores": {
                    "sat": 1450,
                    "ielts": 7.5,
                    "ap": ["Calculus BC: 5"],
                },
                "telegram_username": "student_example",
                "phone": "+998 90 123 45 67",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.profile.refresh_from_db()
        self.preferences.refresh_from_db()
        self.other_profile.refresh_from_db()
        self.assertEqual(self.profile.country, "Uzbekistan")
        self.assertEqual(self.profile.intended_majors, ["Computer Science", "Economics"])
        self.assertEqual(self.profile.intended_major, "Computer Science")
        self.assertEqual(self.profile.test_scores["sat"], 1450)
        self.assertEqual(self.profile.telegram_username, "@student_example")
        self.assertEqual(self.preferences.interests, ["Research", "Debate"])
        self.assertEqual(self.other_profile.country, "Other country")

    def test_profile_allows_normal_detail_in_onboarding_lists(self):
        self.client.force_authenticate(self.user)
        detailed_activity = (
            "Founded a weekly behavioral finance reading group, coordinated peer "
            "presentations, and documented how students applied statistics concepts "
            "to budgeting and university planning decisions."
        )
        support_priority = (
            "I need help turning a broad interest in finance, machine learning, "
            "and psychology into a realistic university list with sourced deadlines."
        )

        response = self.client.patch(
            reverse("profile:me"),
            {
                "activities": {"research_projects": [detailed_activity]},
                "support_priorities": [support_priority],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.activities["research_projects"],
            [detailed_activity],
        )
        self.assertEqual(response.data["support_priorities"], [support_priority])

    def test_profile_rejects_spam_length_on_onboarding_list_items(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("profile:me"),
            {"activities": {"honors": ["x" * 501]}},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("activities", response.data)

    def test_role_cannot_be_changed_through_profile_endpoint(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("profile:me"),
            {
                "role": User.Role.ADMIN,
                "full_name": "Still a Student",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.STUDENT)
        self.assertEqual(response.data["role"], User.Role.STUDENT)

    def test_anonymous_user_cannot_access_profile_or_completion(self):
        profile_response = self.client.get(reverse("profile:me"))
        completion_response = self.client.get(reverse("profile:completion"))

        self.assertEqual(profile_response.status_code, 401)
        self.assertEqual(completion_response.status_code, 401)

    def test_profile_completion_reports_missing_and_completed_fields(self):
        self.client.force_authenticate(self.user)

        initial_response = self.client.get(reverse("profile:completion"))
        self.assertEqual(initial_response.status_code, 200)
        self.assertGreater(initial_response.data["percentage"], 0)
        self.assertIn("country", initial_response.data["missing_fields"])

        self.client.patch(
            reverse("profile:me"),
            self.complete_onboarding_payload,
            format="json",
        )
        completed_response = self.client.get(reverse("profile:completion"))

        self.assertEqual(completed_response.status_code, 200)
        self.assertEqual(completed_response.data["percentage"], 100)
        self.assertEqual(completed_response.data["missing_fields"], [])
        self.assertEqual(completed_response.data["missing_sections"], [])
        self.assertTrue(completed_response.data["can_complete"])
        self.assertFalse(completed_response.data["is_complete"])

        finish_response = self.client.post(reverse("profile:complete-onboarding"))
        self.assertEqual(finish_response.status_code, 200)
        self.assertTrue(finish_response.data["is_complete"])
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.onboarding_completed_at)

    def test_onboarding_cannot_finish_with_missing_required_data(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("profile:complete-onboarding"))

        self.assertEqual(response.status_code, 400)
        self.assertIn("country", response.data["missing_fields"])
        self.assertIn("identity", response.data["missing_sections"])

    def test_profile_validates_gpa_graduation_year_and_exam_date(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("profile:me"),
            {
                "gpa": "5.00",
                "gpa_scale": "4.00",
                "expected_graduation_year": 2099,
                "exam_plans": {
                    "taken": [],
                    "planned": [{"name": "SAT", "date": "2020-01-01", "target_score": "1500"}],
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("expected_graduation_year", response.data)
        self.assertIn("exam_plans", response.data)

        gpa_response = self.client.patch(
            reverse("profile:me"),
            {"gpa": "5.00", "gpa_scale": "4.00"},
            format="json",
        )
        self.assertEqual(gpa_response.status_code, 400)
        self.assertIn("gpa", gpa_response.data)

    def test_readiness_returns_stars_without_outcome_estimate(self):
        self.client.force_authenticate(self.user)
        self.client.patch(
            reverse("profile:me"),
            self.complete_onboarding_payload,
            format="json",
        )

        response = self.client.get(reverse("profile:readiness"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.data["stars"], range(1, 6))
        self.assertIn(
            response.data["level"],
            ("foundation", "developing", "competitive", "strong", "outstanding"),
        )
        self.assertEqual(response.data["comparison_status"], "official_data_needed")
        self.assertNotIn("admissions_outcome_estimate", response.data)

    def test_invalid_profile_values_are_rejected(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("profile:me"),
            {
                "birth_date": "2099-01-01",
                "test_scores": {"sat": 2000},
                "telegram_username": "@bad!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("birth_date", response.data)
        self.assertIn("test_scores", response.data)
        self.assertIn("telegram_username", response.data)
