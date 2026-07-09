from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from services.ai_gateway_service.exceptions import AIProviderError
from services.essay_service.models import EssayWorkspace
from services.profile_assessment_service.models import AIProfileAssessment
from services.profile_assessment_service.services import (
    PROFILE_ASSESSMENT_CATEGORIES,
    build_profile_assessment_input,
    compute_profile_snapshot_hash,
    run_profile_assessment,
    validate_ai_profile_assessment_json,
)
from services.university_service.services import calculate_university_fit
from services.university_service.tests.test_universities import create_university
from services.user_profile_service.models import Activity, ResearchProject
from services.user_profile_service.services import ensure_profile_records

User = get_user_model()


class FakeProfileAssessmentClient:
    provider_name = "fake"
    model_name = "fake-profile-model"

    def __init__(self, output, *, repair_output=None):
        self.output = output
        self.repair_output = repair_output
        self.calls = 0
        self.repair_reasons: list[str] = []

    def generate_profile_assessment(self, input_summary, *, repair_reason=None):
        self.calls += 1
        self.last_input_summary = input_summary
        if repair_reason is not None:
            self.repair_reasons.append(repair_reason)
            if self.repair_output is not None:
                return self.repair_output
        return self.output


class FakeFailingProfileAssessmentClient:
    provider_name = "fake"
    model_name = "fake-profile-model"

    def __init__(self, error: AIProviderError):
        self.error = error

    def generate_profile_assessment(self, input_summary, *, repair_reason=None):
        raise self.error


def valid_ai_output(**overrides):
    category_scores = {category: 6 for category in PROFILE_ASSESSMENT_CATEGORIES}
    category_scores.update(overrides.pop("category_scores", {}))
    output = {
        "overall_profile_score": 62,
        "category_scores": category_scores,
        "confidence": "medium",
        "target_context_used": True,
        "public_summary": "Your saved profile has useful evidence and several areas to strengthen.",
        "evidence_used": ["saved profile", "structured activities"],
        "missing_data": ["more verified proof"],
        "improvement_areas": ["add research details"],
        "internal_keywords": ["research-driven", "leadership-heavy"],
        "category_rationales": {
            category: "Evidence was assessed from saved UniWay profile data."
            for category in PROFILE_ASSESSMENT_CATEGORIES
        },
        "warnings": [],
    }
    output.update(overrides)
    return output


@override_settings(
    AI_PROFILE_ASSESSMENT_ENABLED=True,
    GEMINI_API_KEY="test-key",
    AI_PROFILE_ASSESSMENT_DAILY_LIMIT=1,
)
class ProfileAssessmentServiceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-assessment",
            email="assessment@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.profile, self.preferences = ensure_profile_records(self.user)
        self.profile.country = "Uzbekistan"
        self.profile.city = "Tashkent"
        self.profile.expected_graduation_year = 2027
        self.profile.gpa = "4.60"
        self.profile.gpa_scale = "5.00"
        self.profile.intended_majors = ["Computer Science"]
        self.profile.target_countries = ["United States"]
        self.profile.test_scores = {"sat": 1420, "ielts": 7.0}
        self.profile.annual_budget_amount = "25000.00"
        self.profile.phone = "+998 90 000 00 00"
        self.profile.telegram_username = "@student_private"
        self.profile.save()

    def test_profile_snapshot_hash_is_stable_without_meaningful_changes(self):
        first = compute_profile_snapshot_hash(self.user)
        second = compute_profile_snapshot_hash(self.user)

        self.assertEqual(first, second)

    def test_profile_snapshot_hash_changes_when_meaningful_profile_data_changes(self):
        original = compute_profile_snapshot_hash(self.user)
        self.profile.intended_majors = ["Economics"]
        self.profile.exam_plans = {
            "taken": [],
            "planned": [{"exam_type": "SAT", "target_score": "1500"}],
        }
        self.profile.annual_budget_amount = "18000.00"
        self.profile.save()
        Activity.objects.create(user=self.user, title="Finance club", role="Founder")

        changed = compute_profile_snapshot_hash(self.user)

        self.assertNotEqual(original, changed)

    def test_profile_input_is_compact_and_excludes_private_contact_and_raw_essays(self):
        EssayWorkspace.objects.create(
            user=self.user,
            title="Why school",
            draft_text="Private essay body that should not be sent.",
            status=EssayWorkspace.Status.DRAFTING,
        )

        summary = build_profile_assessment_input(self.user)
        payload = str(summary)

        self.assertNotIn(self.user.email, payload)
        self.assertNotIn("998 90", payload)
        self.assertNotIn("@student_private", payload)
        self.assertNotIn("Private essay body", payload)
        self.assertEqual(
            summary["privacy_notes"][0],
            "No password, payment data, phone, Telegram username, email, or raw essay text is included.",
        )

    def test_first_assessment_creates_record_and_unchanged_profile_returns_cached(self):
        client = FakeProfileAssessmentClient(valid_ai_output())

        first = run_profile_assessment(self.user, client=client)
        second = run_profile_assessment(self.user, client=client)

        self.assertEqual(first.reason, "no_previous_assessment")
        self.assertIsNotNone(first.assessment)
        self.assertFalse(first.cached)
        self.assertEqual(second.reason, "unchanged_cached")
        self.assertTrue(second.cached)
        self.assertEqual(client.calls, 1)
        self.assertEqual(AIProfileAssessment.objects.filter(user=self.user).count(), 1)

    def test_stored_assessment_caches_benchmark_deterministic_and_readiness_data(self):
        client = FakeProfileAssessmentClient(valid_ai_output())

        result = run_profile_assessment(self.user, client=client)

        assessment = result.assessment
        self.assertIn(
            assessment.benchmark_source,
            [choice.value for choice in AIProfileAssessment.BenchmarkSource],
        )
        self.assertIsInstance(assessment.benchmark_scores, dict)
        self.assertIsInstance(assessment.benchmark_academic, dict)
        self.assertIn("score_gaps", assessment.deterministic_scores)
        self.assertIn("missing_evidence", assessment.deterministic_scores)
        self.assertIn("sections", assessment.readiness_scores)
        self.assertEqual(len(assessment.readiness_scores["sections"]), 6)
        self.assertTrue(1 <= assessment.overall_readiness_score <= 5)
        self.assertEqual(assessment.status, AIProfileAssessment.Status.OK)
        self.assertIsNotNone(assessment.next_allowed_refresh_at)
        self.assertGreater(assessment.next_allowed_refresh_at, timezone.now())

    def test_changed_profile_within_same_day_hits_daily_limit(self):
        client = FakeProfileAssessmentClient(valid_ai_output())
        run_profile_assessment(self.user, client=client)
        Activity.objects.create(user=self.user, title="New activity")

        result = run_profile_assessment(self.user, client=client)

        self.assertEqual(result.reason, "daily_limit_reached")
        self.assertEqual(client.calls, 1)
        self.assertIsNotNone(result.next_available_at)

    def test_changed_profile_after_twenty_four_hours_can_run(self):
        client = FakeProfileAssessmentClient(valid_ai_output())
        run_profile_assessment(self.user, client=client)
        AIProfileAssessment.objects.filter(user=self.user).update(
            created_at=timezone.now() - timedelta(days=2)
        )
        Activity.objects.create(user=self.user, title="New activity")

        result = run_profile_assessment(self.user, client=client)

        self.assertEqual(result.reason, "profile_changed")
        self.assertEqual(client.calls, 2)
        self.assertEqual(AIProfileAssessment.objects.filter(user=self.user).count(), 2)

    @override_settings(AI_PROFILE_ASSESSMENT_ENABLED=True, GEMINI_API_KEY="")
    def test_missing_gemini_key_returns_safe_unavailable_state(self):
        result = run_profile_assessment(
            self.user,
            client=FakeProfileAssessmentClient(valid_ai_output()),
        )

        self.assertEqual(result.reason, "ai_unavailable")
        self.assertIsNone(result.assessment)
        self.assertFalse(result.ai_available)

    def test_invalid_ai_json_retries_once_then_falls_back_to_deterministic_scores(self):
        client = FakeProfileAssessmentClient({"overall_profile_score": 50})

        result = run_profile_assessment(self.user, client=client)

        self.assertEqual(result.reason, "fallback_used")
        self.assertEqual(client.calls, 2)
        self.assertEqual(len(client.repair_reasons), 1)
        self.assertIn("category_scores", client.repair_reasons[0])
        assessment = AIProfileAssessment.objects.get(user=self.user)
        self.assertEqual(assessment.status, AIProfileAssessment.Status.FALLBACK_USED)
        for category in PROFILE_ASSESSMENT_CATEGORIES:
            self.assertTrue(1 <= getattr(assessment, category) <= 10)

    def test_repair_retry_success_avoids_fallback(self):
        client = FakeProfileAssessmentClient(
            {"overall_profile_score": 50},
            repair_output=valid_ai_output(),
        )

        result = run_profile_assessment(self.user, client=client)

        self.assertEqual(result.reason, "no_previous_assessment")
        self.assertEqual(client.calls, 2)
        assessment = AIProfileAssessment.objects.get(user=self.user)
        self.assertEqual(assessment.status, AIProfileAssessment.Status.OK)

    def test_out_of_range_scores_are_rejected(self):
        output = valid_ai_output(category_scores={"activities_score": 11})

        with self.assertRaises(ValueError):
            validate_ai_profile_assessment_json(output)

    def test_internal_keywords_max_twenty_is_enforced(self):
        output = valid_ai_output(
            internal_keywords=[f"signal-{index}" for index in range(21)]
        )

        with self.assertRaises(ValueError):
            validate_ai_profile_assessment_json(output)

    def test_admissions_probability_wording_is_rejected(self):
        output = valid_ai_output(public_summary="This profile has a strong admission chance.")

        with self.assertRaises(ValueError):
            validate_ai_profile_assessment_json(output)

    def test_profile_with_no_activities_can_store_low_confidence_assessment(self):
        self.user.profile_activities.all().delete()
        output = valid_ai_output(
            confidence="low",
            category_scores={"activities_score": 1, "profile_evidence_score": 2},
            missing_data=["activities", "proof links"],
        )

        result = run_profile_assessment(self.user, client=FakeProfileAssessmentClient(output))

        self.assertEqual(result.reason, "no_previous_assessment")
        self.assertEqual(result.assessment.confidence, "low")
        self.assertEqual(result.assessment.activities_score, 1)

    def test_strong_research_mocked_response_stores_higher_relevant_scores(self):
        ResearchProject.objects.create(
            user=self.user,
            title="Financial anxiety research",
            field="Economics",
            sample_size="530 responses",
            current_stage=ResearchProject.Stage.COMPLETED,
        )
        output = valid_ai_output(
            overall_profile_score=78,
            confidence="high",
            category_scores={
                "research_experience_score": 8,
                "research_fit_score": 8,
                "leadership_score": 7,
                "profile_evidence_score": 8,
            },
        )

        result = run_profile_assessment(self.user, client=FakeProfileAssessmentClient(output))

        self.assertEqual(result.assessment.research_experience_score, 8)
        self.assertEqual(result.assessment.research_fit_score, 8)
        self.assertEqual(result.assessment.confidence, "high")

    def test_fit_engine_reads_cached_assessment_without_ai_call(self):
        output = valid_ai_output(
            category_scores={"profile_evidence_score": 8},
            confidence="high",
        )
        run_profile_assessment(self.user, client=FakeProfileAssessmentClient(output))
        university = create_university("assessment-fit-university")

        fit = calculate_university_fit(self.profile, university)

        self.assertTrue(fit["profile_evidence"]["assessment_context"]["available"])
        self.assertEqual(
            fit["profile_evidence"]["assessment_context"]["source"],
            "cached_profile_assessment",
        )
        self.assertIn(
            "cached_profile_assessment_used",
            fit["profile_evidence"]["program_relevance_notes"],
        )

    def test_provider_error_logs_sanitized_diagnostics_without_secrets_or_profile_text(self):
        error = AIProviderError(
            "Gemini profile assessment request failed.",
            status_code=404,
            error_body='{"error": {"code": 404, "message": "models/x is not found", "status": "NOT_FOUND"}}',
            cause_class="HTTPError",
            provider_code=404,
            provider_status="NOT_FOUND",
        )
        client = FakeFailingProfileAssessmentClient(error)

        with self.assertLogs("services.profile_assessment_service.services", level="WARNING") as captured:
            result = run_profile_assessment(self.user, client=client)

        self.assertEqual(result.reason, "ai_unavailable")
        log_line = "\n".join(captured.output)
        self.assertIn("feature=profile_assessment", log_line)
        self.assertIn("status=404", log_line)
        self.assertIn("exception=AIProviderError", log_line)
        self.assertIn("cause=HTTPError", log_line)
        self.assertIn("provider_code=404", log_line)
        self.assertIn("provider_status=NOT_FOUND", log_line)
        self.assertIn("NOT_FOUND", log_line)
        self.assertNotIn("Tashkent", log_line)
        self.assertNotIn("test-key", log_line)

    def test_validation_failure_logs_sanitized_message_without_profile_text(self):
        client = FakeProfileAssessmentClient({"overall_profile_score": 50})

        with self.assertLogs("services.profile_assessment_service.services", level="WARNING") as captured:
            result = run_profile_assessment(self.user, client=client)

        self.assertEqual(result.reason, "fallback_used")
        log_line = "\n".join(captured.output)
        self.assertIn("feature=profile_assessment", log_line)
        self.assertIn("attempt=1", log_line)
        self.assertIn("attempt=2", log_line)
        self.assertNotIn("Tashkent", log_line)

    def test_successful_assessment_logs_call_summary_without_profile_text(self):
        client = FakeProfileAssessmentClient(valid_ai_output())

        with self.assertLogs("services.profile_assessment_service.services", level="INFO") as captured:
            result = run_profile_assessment(self.user, client=client)

        self.assertIn(result.reason, {"no_previous_assessment", "profile_changed"})
        log_line = "\n".join(captured.output)
        self.assertIn("ai_task_type=profile_assessment", log_line)
        self.assertIn("provider=gemini", log_line)
        self.assertIn(f"status={result.reason}", log_line)
        self.assertIn("cache_hit=False", log_line)
        self.assertIn("duration_ms=", log_line)
        self.assertNotIn("Tashkent", log_line)

    def test_cached_assessment_logs_cache_hit_true(self):
        client = FakeProfileAssessmentClient(valid_ai_output())
        first = run_profile_assessment(self.user, client=client)
        self.assertIn(first.reason, {"no_previous_assessment", "profile_changed"})

        with self.assertLogs("services.profile_assessment_service.services", level="INFO") as captured:
            second = run_profile_assessment(self.user, client=client)

        self.assertEqual(second.reason, "unchanged_cached")
        log_line = "\n".join(captured.output)
        self.assertIn("status=unchanged_cached", log_line)
        self.assertIn("cache_hit=True", log_line)


@override_settings(
    AI_PROFILE_ASSESSMENT_ENABLED=True,
    GEMINI_API_KEY="test-key",
    AI_PROFILE_ASSESSMENT_DAILY_LIMIT=1,
)
class ProfileAssessmentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="api-student",
            email="api-student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        ensure_profile_records(self.user)
        self.admin = User.objects.create_user(
            username="api-admin",
            email="api-admin@test.com",
            password="testpass123",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def test_latest_endpoint_returns_safe_empty_state(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/profile/assessment/latest/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["assessment"])
        self.assertEqual(response.data["reason"], "no_previous_assessment")
        self.assertTrue(response.data["ai_available"])

    def test_user_cannot_force_another_users_profile_assessment(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            f"/api/admin/users/{self.admin.id}/profile-assessment/run/"
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_force_reassessment_endpoint_without_cross_user_access(self):
        client = FakeProfileAssessmentClient(valid_ai_output())
        self.client.force_authenticate(self.admin)
        with override_settings(AI_PROFILE_ASSESSMENT_ENABLED=True, GEMINI_API_KEY="test-key"):
            from unittest.mock import patch

            with patch(
                "services.profile_assessment_service.services.get_profile_assessment_client",
                return_value=client,
            ):
                response = self.client.post(
                    f"/api/admin/users/{self.user.id}/profile-assessment/run/"
                )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["reason"], "no_previous_assessment")
        self.assertEqual(response.data["assessment"]["overall_profile_score"], 62)

    def test_run_endpoint_uses_authenticated_user_only(self):
        client = FakeProfileAssessmentClient(valid_ai_output())
        self.client.force_authenticate(self.user)
        from unittest.mock import patch

        with patch(
            "services.profile_assessment_service.services.get_profile_assessment_client",
            return_value=client,
        ):
            response = self.client.post("/api/profile/assessment/run/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["reason"], "no_previous_assessment")
        self.assertEqual(AIProfileAssessment.objects.get().user, self.user)
        self.assertNotIn("internal_keywords", response.data["assessment"])


@override_settings(
    AI_PROFILE_ASSESSMENT_ENABLED=True,
    GEMINI_API_KEY="test-key",
    AI_PROFILE_ASSESSMENT_DAILY_LIMIT=1,
)
class ProtocolEightApiEndpointsTests(APITestCase):
    """PROTOCOL-008 PART 7's additive `/api/v1/` endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="v1-student",
            email="v1-student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        ensure_profile_records(self.user)
        self.client.force_authenticate(self.user)

    def test_v1_me_endpoint_mirrors_legacy_latest_endpoint(self):
        response = self.client.get("/api/v1/profile-assessment/me/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["assessment"])
        self.assertEqual(response.data["reason"], "no_previous_assessment")

    def test_v1_refresh_endpoint_creates_an_assessment(self):
        from unittest.mock import patch

        client = FakeProfileAssessmentClient(valid_ai_output())
        with patch(
            "services.profile_assessment_service.services.get_profile_assessment_client",
            return_value=client,
        ):
            response = self.client.post("/api/v1/profile-assessment/refresh/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(AIProfileAssessment.objects.get().user, self.user)

    def test_recommendations_endpoint_reports_needs_assessment_when_no_cache(self):
        response = self.client.get("/api/v1/recommendations/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["recommendations"], [])
        self.assertTrue(response.data["needs_assessment"])

    def test_recommendations_endpoint_never_calls_ai(self):
        from unittest.mock import patch

        with patch(
            "services.profile_assessment_service.views.get_latest_valid_assessment",
            return_value=None,
        ) as mocked_lookup, patch(
            "services.profile_assessment_service.services.get_profile_assessment_client",
            side_effect=AssertionError("must not call AI on render"),
        ):
            response = self.client.get("/api/v1/recommendations/me/")

        self.assertEqual(response.status_code, 200)
        mocked_lookup.assert_called_once()

    def test_recommendations_endpoint_uses_cached_assessment_once_available(self):
        from unittest.mock import patch

        client = FakeProfileAssessmentClient(valid_ai_output(category_scores={"activities_score": 2}))
        with patch(
            "services.profile_assessment_service.services.get_profile_assessment_client",
            return_value=client,
        ):
            self.client.post("/api/v1/profile-assessment/refresh/")

        response = self.client.get("/api/v1/recommendations/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["needs_assessment"])
        self.assertIsInstance(response.data["recommendations"], list)

    def test_strategy_endpoint_works_before_any_assessment_exists(self):
        response = self.client.get("/api/v1/strategy/me/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["needs_assessment"])
        self.assertFalse(response.data["has_tracked_applications"])
        self.assertIn("university_list_strategy", response.data)

    def test_strategy_endpoint_never_calls_ai(self):
        from unittest.mock import patch

        with patch(
            "services.profile_assessment_service.services.get_profile_assessment_client",
            side_effect=AssertionError("must not call AI on render"),
        ):
            response = self.client.get("/api/v1/strategy/me/")

        self.assertEqual(response.status_code, 200)
