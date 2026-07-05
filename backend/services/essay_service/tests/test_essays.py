from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from services.ai_gateway_service.exceptions import AIProviderError
from services.application_service.models import ApplicationTrackerItem
from services.essay_service.ai_scoring import (
    EssayScoringValidationError,
    build_scoring_payload,
    compute_context_hash,
    compute_essay_text_hash,
    validate_and_normalize_output,
)
from services.essay_service.feedback_engine import generate_feedback
from services.essay_service.models import (
    AIEssayScoreReport,
    EssayFeedback,
    EssayRevisionTask,
    EssayWorkspace,
)
from services.profile_assessment_service.models import AIProfileAssessment
from services.profile_assessment_service.services import compute_profile_snapshot_hash
from services.subscription_service.models import Plan, Subscription
from services.university_service.models import (
    SavedUniversity,
    University,
    UniversityFieldVerification,
    UniversityProgram,
)

User = get_user_model()


def create_university(slug="test-university", **overrides):
    defaults = {
        "name": "Test University",
        "country": "Demoland",
        "city": "Sample City",
        "official_website": f"https://example.com/{slug}",
        "is_published": True,
    }
    defaults.update(overrides)
    return University.objects.create(slug=slug, **defaults)


def valid_ai_score_output(**overrides):
    output = {
        "overall_essay_readiness": 78,
        "confidence": "medium",
        "subscores": {
            "prompt_fit": 20,
            "structure": 16,
            "specificity_evidence": 15,
            "authenticity": 12,
            "language_clarity": 8,
            "word_limit_discipline": 4,
            "school_program_alignment": 4,
        },
        "ai_paraphrase_style_signal": "low",
        "generic_language_signal": "medium",
        "unsupported_claims_signal": "low",
        "strength_flags": ["clear motivation"],
        "risk_flags": ["needs more evidence"],
        "approximate_suggestions": ["Add one specific example of impact."],
        "source_warnings": [],
    }
    for key, value in overrides.items():
        if key == "subscores":
            output["subscores"].update(value)
        else:
            output[key] = value
    return output


class FakeEssayScoringClient:
    def __init__(self, output=None):
        self.output = output or valid_ai_score_output()
        self.calls = 0
        self.prompts = []

    def score_essay(self, *, system_prompt, user_prompt):
        self.calls += 1
        self.prompts.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return self.output


class FakeFailingEssayScoringClient:
    def __init__(self, error: AIProviderError):
        self.error = error

    def score_essay(self, *, system_prompt, user_prompt):
        raise self.error


class FakeFlakyEssayScoringClient:
    """Fails with the given error `fail_times` times, then returns `output`."""

    def __init__(self, error: AIProviderError, *, fail_times: int, output=None):
        self.error = error
        self.fail_times = fail_times
        self.output = output or valid_ai_score_output()
        self.calls = 0

    def score_essay(self, *, system_prompt, user_prompt):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.error
        return self.output


class FakeRacingEssayScoringClient:
    """Simulates a concurrent request winning the race: writes a competing
    AIEssayScoreReport for the same essay/hash pair as a side effect of the
    provider call succeeding, before this call's own result is used."""

    def __init__(self, *, essay, essay_text_hash, context_hash, user, output=None):
        self.essay = essay
        self.essay_text_hash = essay_text_hash
        self.context_hash = context_hash
        self.user = user
        self.output = output or valid_ai_score_output()
        self.calls = 0

    def score_essay(self, *, system_prompt, user_prompt):
        self.calls += 1
        AIEssayScoreReport.objects.create(
            user=self.user,
            essay=self.essay,
            essay_text_hash=self.essay_text_hash,
            context_hash=self.context_hash,
            rubric_version="essay_numeric_v1",
            model_provider="gemini",
            model_name="gemini-flash-latest",
            raw_output_json=self.output,
            **validate_and_normalize_output(self.output, payload=build_scoring_payload(self.essay)),
        )
        return self.output


class EssayFeedbackEngineTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="writer1", email="writer1@test.com", password="testpass123"
        )

    def test_empty_draft_flagged_and_scored_zero(self):
        essay = EssayWorkspace.objects.create(user=self.user, title="My essay", draft_text="")
        result = generate_feedback(essay)
        self.assertIn("empty_draft", result["issues"])
        self.assertEqual(result["structure_score"], 0)
        self.assertEqual(result["overall_label"], EssayFeedback.OverallLabel.WEAK)

    def test_word_limit_too_short(self):
        essay = EssayWorkspace.objects.create(
            user=self.user, title="Short", draft_text="A short draft. " * 5, word_limit=650
        )
        result = generate_feedback(essay)
        self.assertEqual(result["word_limit_status"], EssayFeedback.WordLimitStatus.TOO_SHORT)

    def test_word_limit_too_long(self):
        essay = EssayWorkspace.objects.create(
            user=self.user, title="Long", draft_text="word " * 800, word_limit=650
        )
        result = generate_feedback(essay)
        self.assertEqual(result["word_limit_status"], EssayFeedback.WordLimitStatus.TOO_LONG)

    def test_generic_language_detected(self):
        draft = (
            "Ever since I was young, I have always loved helping people. "
            * 6
        )
        essay = EssayWorkspace.objects.create(user=self.user, title="Generic", draft_text=draft)
        result = generate_feedback(essay)
        self.assertIn("generic_language", result["issues"])

    def test_missing_quantified_impact_detected(self):
        draft = (
            "I worked hard on my community project and met many wonderful people "
            "who taught me valuable lessons about resilience and teamwork. " * 4
        )
        essay = EssayWorkspace.objects.create(user=self.user, title="Vague", draft_text=draft)
        result = generate_feedback(essay)
        self.assertIn("missing_quantified_impact", result["issues"])

    def test_why_school_essay_without_university_name_flagged(self):
        university = create_university()
        draft = (
            "I want to study here because of the strong programs and the community. " * 5
        )
        essay = EssayWorkspace.objects.create(
            user=self.user,
            title="Why school",
            essay_type=EssayWorkspace.EssayType.WHY_SCHOOL,
            university=university,
            draft_text=draft,
        )
        result = generate_feedback(essay)
        self.assertIn("missing_why_this_school", result["issues"])

    def test_why_school_essay_with_university_name_not_flagged(self):
        university = create_university(name="Demo State University")
        draft = (
            "I want to study at Demo State University because of its strong programs "
            "and supportive faculty in my intended field. " * 4
        )
        essay = EssayWorkspace.objects.create(
            user=self.user,
            title="Why school",
            essay_type=EssayWorkspace.EssayType.WHY_SCHOOL,
            university=university,
            draft_text=draft,
        )
        result = generate_feedback(essay)
        self.assertNotIn("missing_why_this_school", result["issues"])

    def test_no_paragraph_breaks_detected_for_long_single_block(self):
        draft = "word " * 200
        essay = EssayWorkspace.objects.create(user=self.user, title="Block", draft_text=draft)
        result = generate_feedback(essay)
        self.assertIn("no_paragraph_breaks", result["issues"])

    def test_feedback_never_includes_a_generated_full_essay(self):
        essay = EssayWorkspace.objects.create(
            user=self.user, title="Check", draft_text="Some draft text without much detail. " * 5
        )
        result = generate_feedback(essay)
        self.assertNotIn("generated_essay", result)
        self.assertNotIn("rewritten_text", result)


class EssayWorkspaceApiTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="writer1", email="writer1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="writer2", email="writer2@test.com", password="testpass123"
        )

    def test_list_requires_authentication(self):
        response = self.client.get("/api/essays/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_and_list_essay(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(
            "/api/essays/",
            {"title": "My Common App essay", "essay_type": "common_app", "draft_text": "Hello"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        essay_id = response.data["id"]

        list_response = self.client.get("/api/essays/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["results"]), 1)
        self.assertEqual(list_response.data["results"][0]["id"], essay_id)

    def test_list_query_count_does_not_grow_with_ai_score_report_count(self):
        self.client.force_authenticate(self.user1)
        essay = EssayWorkspace.objects.create(
            user=self.user1, title="Scored essay", draft_text="Some content here."
        )
        for index in range(8):
            AIEssayScoreReport.objects.create(
                user=self.user1,
                essay=essay,
                essay_text_hash=f"hash-{index}",
                context_hash=f"context-{index}",
                model_name="test-model",
                raw_output_json={"padding": "x" * 500},
                overall_essay_readiness=70,
                prompt_fit=20,
                structure=15,
                specificity_evidence=15,
                authenticity=10,
                language_clarity=8,
                confidence=AIEssayScoreReport.Confidence.MEDIUM,
                word_count=100,
                word_limit_status=AIEssayScoreReport.WordLimitStatus.WITHIN,
                ai_paraphrase_style_signal=AIEssayScoreReport.StyleSignal.LOW,
                generic_language_signal="low",
                unsupported_claims_signal=AIEssayScoreReport.ClaimsSignal.LOW,
            )

        with self.assertNumQueries(4):
            response = self.client.get("/api/essays/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_essays_are_self_only(self):
        self.client.force_authenticate(self.user1)
        self.client.post("/api/essays/", {"title": "Mine", "draft_text": ""}, format="json")

        self.client.force_authenticate(self.user2)
        response = self.client.get("/api/essays/")
        self.assertEqual(response.data["results"], [])

    def test_cannot_access_another_users_essay(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Mine", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]

        self.client.force_authenticate(self.user2)
        response = self.client.get(f"/api/essays/{essay_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_title_is_required(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/essays/", {"title": "  "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_absurd_word_limit_is_rejected(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(
            "/api/essays/",
            {"title": "Limit check", "word_limit": 999999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("word_limit", response.data)

    def test_verified_university_word_limit_auto_fills_when_missing(self):
        university = create_university(
            slug="word-limit-university",
            essay_requirements="Submit one supplemental essay of 250 words.",
        )
        UniversityFieldVerification.objects.create(
            university=university,
            field_name="essay_requirements",
            status=UniversityFieldVerification.Status.VERIFIED,
            source_url="https://example.com/official-essays",
            last_verified_date=date(2026, 7, 1),
        )
        self.client.force_authenticate(self.user1)

        response = self.client.post(
            "/api/essays/",
            {
                "title": "Verified supplement",
                "essay_type": "supplement",
                "university": university.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["word_limit"], 250)
        self.assertEqual(response.data["prompt_verification_status"], "verified")
        self.assertEqual(response.data["prompt_confidence"], "high")
        self.assertEqual(response.data["source_url"], "https://example.com/official-essays")

    def test_unknown_word_limit_remains_unset_and_needs_verification(self):
        university = create_university(slug="unknown-limit-university")
        self.client.force_authenticate(self.user1)

        response = self.client.post(
            "/api/essays/",
            {
                "title": "Unknown supplement",
                "essay_type": "supplement",
                "university": university.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data["word_limit"])
        self.assertEqual(response.data["prompt_verification_status"], "missing")

    def test_generate_feedback_creates_feedback_and_revision_tasks(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]

        response = self.client.post(f"/api/essays/{essay_id}/feedback/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNotNone(response.data["feedback"])
        self.assertTrue(EssayFeedback.objects.filter(essay_id=essay_id).exists())
        self.assertTrue(EssayRevisionTask.objects.filter(essay_id=essay_id).exists())

        essay = EssayWorkspace.objects.get(id=essay_id)
        self.assertEqual(essay.status, EssayWorkspace.Status.NEEDS_REVISION)

    def test_regenerating_feedback_does_not_duplicate_todo_revision_tasks(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]

        self.client.post(f"/api/essays/{essay_id}/feedback/")
        count_after_first = EssayRevisionTask.objects.filter(essay_id=essay_id).count()
        self.client.post(f"/api/essays/{essay_id}/feedback/")
        count_after_second = EssayRevisionTask.objects.filter(essay_id=essay_id).count()
        self.assertEqual(count_after_first, count_after_second)

    def test_manual_revision_task_creation(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": "Some content here."}, format="json"
        )
        essay_id = created.data["id"]

        response = self.client.post(
            f"/api/essays/{essay_id}/revision-tasks/",
            {"title": "Re-read introduction", "description": "", "category": "clarity"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_update_revision_task_status(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]
        task_response = self.client.post(
            f"/api/essays/{essay_id}/revision-tasks/",
            {"title": "Fix something", "category": "clarity"},
            format="json",
        )
        task_id = task_response.data["id"]

        response = self.client.patch(
            f"/api/essays/revision-tasks/{task_id}/", {"status": "completed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "completed")

    def test_cannot_update_another_users_revision_task(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]
        task_response = self.client.post(
            f"/api/essays/{essay_id}/revision-tasks/",
            {"title": "Fix something", "category": "clarity"},
            format="json",
        )
        task_id = task_response.data["id"]

        self.client.force_authenticate(self.user2)
        response = self.client.patch(
            f"/api/essays/revision-tasks/{task_id}/", {"status": "completed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_essay(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]
        response = self.client.delete(f"/api/essays/{essay_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EssayWorkspace.objects.filter(id=essay_id).exists())

    def test_no_ghostwriting_endpoint_exists(self):
        self.client.force_authenticate(self.user1)
        created = self.client.post(
            "/api/essays/", {"title": "Draft", "draft_text": ""}, format="json"
        )
        essay_id = created.data["id"]
        for path in (
            f"/api/essays/{essay_id}/write/",
            f"/api/essays/{essay_id}/generate/",
        ):
            response = self.client.post(path)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generate_suggestions_from_shortlisted_university(self):
        university = create_university(
            slug="essay-source-university",
            name="Essay Source University",
            essay_requirements="Supplemental essay requirements are listed here.",
            admissions_url="https://example.com/admissions",
        )
        UniversityFieldVerification.objects.create(
            university=university,
            field_name="essay_requirements",
            status=UniversityFieldVerification.Status.VERIFIED,
            source_url="https://example.com/admissions/essays",
            last_verified_date=date(2026, 7, 1),
        )
        SavedUniversity.objects.create(user=self.user1, university=university)

        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/essays/generate-suggestions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["created_count"], 2)
        created_titles = {essay["title"] for essay in response.data["essays"]}
        self.assertIn("Common App personal statement", created_titles)
        self.assertIn("Essay Source University: verify supplemental essays", created_titles)

        supplement = EssayWorkspace.objects.get(
            user=self.user1,
            university=university,
            essay_type=EssayWorkspace.EssayType.SUPPLEMENT,
        )
        self.assertEqual(
            supplement.prompt_verification_status,
            EssayWorkspace.VerificationStatus.VERIFIED,
        )
        self.assertEqual(supplement.prompt_confidence, EssayWorkspace.Confidence.HIGH)
        self.assertEqual(supplement.status, EssayWorkspace.Status.SUGGESTED)
        self.assertEqual(supplement.source_url, "https://example.com/admissions/essays")
        self.assertEqual(supplement.draft_text, "")

    def test_generate_suggestions_is_idempotent(self):
        university = create_university(slug="idempotent-university")
        SavedUniversity.objects.create(user=self.user1, university=university)

        self.client.force_authenticate(self.user1)
        first = self.client.post("/api/essays/generate-suggestions/")
        second = self.client.post("/api/essays/generate-suggestions/")

        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(first.data["created_count"], 2)
        self.assertEqual(second.data["created_count"], 0)
        self.assertEqual(second.data["existing_count"], 2)
        self.assertEqual(EssayWorkspace.objects.filter(user=self.user1).count(), 2)

    def test_unverified_prompt_is_labeled_without_inventing_prompt(self):
        university = create_university(slug="missing-prompt-university")
        SavedUniversity.objects.create(user=self.user1, university=university)

        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/essays/generate-suggestions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        supplement = EssayWorkspace.objects.get(
            user=self.user1,
            university=university,
            essay_type=EssayWorkspace.EssayType.SUPPLEMENT,
        )
        self.assertEqual(
            supplement.prompt_verification_status,
            EssayWorkspace.VerificationStatus.MISSING,
        )
        self.assertEqual(supplement.prompt_confidence, EssayWorkspace.Confidence.LOW)
        self.assertIn("Prompt needs verification", supplement.prompt_text)

    def test_generate_suggestions_links_tracked_application(self):
        university = create_university(
            slug="tracked-essay-university",
            name="Tracked Essay University",
        )
        application = ApplicationTrackerItem.objects.create(
            user=self.user1,
            university=university,
            deadline=date(2027, 1, 5),
        )

        self.client.force_authenticate(self.user1)
        response = self.client.post("/api/essays/generate-suggestions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        supplement = EssayWorkspace.objects.get(
            user=self.user1,
            application=application,
            essay_type=EssayWorkspace.EssayType.SUPPLEMENT,
        )
        self.assertEqual(supplement.university, university)
        self.assertEqual(supplement.due_date, date(2027, 1, 5))

    def test_generated_suggestions_remain_self_only(self):
        university = create_university(slug="self-only-suggestion-university")
        SavedUniversity.objects.create(user=self.user1, university=university)

        self.client.force_authenticate(self.user1)
        self.client.post("/api/essays/generate-suggestions/")

        self.client.force_authenticate(self.user2)
        response = self.client.get("/api/essays/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["results"], [])


@override_settings(
    AI_ESSAY_SCORING_ENABLED=True,
    GEMINI_API_KEY="test-gemini-key",
    AI_ESSAY_DAILY_FREE_LIMIT=1,
    AI_ESSAY_BASIC_MONTHLY_LIMIT=1,
    AI_ESSAY_PREMIUM_MONTHLY_LIMIT=1,
    AI_ESSAY_PRO_MONTHLY_LIMIT=1,
)
class AIEssayScoringTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="aiscore1", email="aiscore1@test.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="aiscore2", email="aiscore2@test.com", password="testpass123"
        )

    def _essay(self, user=None, **overrides):
        defaults = {
            "user": user or self.user1,
            "title": "Leadership essay",
            "essay_type": EssayWorkspace.EssayType.SUPPLEMENT,
            "draft_text": "I built a student library project serving 120 students. " * 20,
            "word_limit": 650,
        }
        defaults.update(overrides)
        return EssayWorkspace.objects.create(**defaults)

    def _score_with_client(self, essay, client):
        self.client.force_authenticate(essay.user)
        with patch("services.essay_service.ai_scoring.GeminiEssayScoringClient", return_value=client):
            return self.client.post(f"/api/essays/{essay.id}/score/")

    def test_score_requires_authentication(self):
        essay = self._essay()
        response = self.client.post(f"/api/essays/{essay.id}/score/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_score_another_users_essay(self):
        essay = self._essay(user=self.user1)
        self.client.force_authenticate(self.user2)
        response = self.client.post(f"/api/essays/{essay.id}/score/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(GEMINI_API_KEY="")
    def test_missing_api_key_returns_safe_error_without_report(self):
        essay = self._essay()
        self.client.force_authenticate(self.user1)
        response = self.client.post(f"/api/essays/{essay.id}/score/")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["reason"], "ai_unavailable")
        self.assertIsNone(response.data["score"])
        self.assertFalse(AIEssayScoreReport.objects.exists())

    def test_verified_prompt_context_is_sent_to_ai_payload(self):
        university = create_university(slug="verified-prompt-u", name="Verified Prompt U")
        program = UniversityProgram.objects.create(university=university, name="Computer Science")
        application = ApplicationTrackerItem.objects.create(
            user=self.user1,
            university=university,
            target_program=program,
            application_round=ApplicationTrackerItem.ApplicationRound.REGULAR_DECISION,
        )
        essay = self._essay(
            application=application,
            university=university,
            prompt_text="Explain why Computer Science at Verified Prompt U fits your goals.",
            prompt_verification_status=EssayWorkspace.VerificationStatus.VERIFIED,
            prompt_confidence=EssayWorkspace.Confidence.HIGH,
            source_url="https://example.com/official-prompt",
            last_reviewed_at=timezone.now(),
        )
        client = FakeEssayScoringClient()

        response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        prompt = client.prompts[0]["user_prompt"]
        self.assertIn("Verified Prompt U", prompt)
        self.assertIn("Computer Science", prompt)
        self.assertIn("Explain why Computer Science", prompt)
        self.assertEqual(response.data["score"]["subscores"]["school_program_alignment"], 4)

    def test_cached_profile_keywords_are_included_when_available(self):
        essay = self._essay()
        AIProfileAssessment.objects.create(
            user=self.user1,
            profile_snapshot_hash=compute_profile_snapshot_hash(self.user1),
            overall_profile_score=72,
            profile_evidence_score=7,
            activities_score=6,
            honors_olympiads_score=5,
            research_experience_score=8,
            portfolio_score=7,
            subject_passion_score=8,
            curiosity_score=8,
            originality_score=7,
            leadership_score=7,
            community_impact_score=6,
            research_fit_score=8,
            olympiads_score=4,
            confidence=AIProfileAssessment.Confidence.MEDIUM,
            internal_keywords=["research", "community_impact", "cs_project"],
            category_rationales={},
            expires_at=timezone.now() + timedelta(days=30),
        )

        payload = build_scoring_payload(essay)

        self.assertEqual(payload["profile_keywords"], ["research", "community_impact", "cs_project"])
        self.assertNotIn("email", str(payload).lower())

    def test_missing_prompt_adds_warning_and_nulls_school_alignment(self):
        essay = self._essay(prompt_text="", prompt_verification_status=EssayWorkspace.VerificationStatus.MISSING)
        client = FakeEssayScoringClient(valid_ai_score_output(subscores={"school_program_alignment": 5}))

        response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        score = response.data["score"]
        self.assertIsNone(score["subscores"]["school_program_alignment"])
        self.assertIn("School-specific prompt data is not verified.", score["source_warnings"])

    def test_cache_hit_does_not_call_ai_again_or_consume_quota(self):
        essay = self._essay()
        client = FakeEssayScoringClient()

        first = self._score_with_client(essay, client)
        second = self._score_with_client(essay, client)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(second.data["reason"], "cached")
        self.assertTrue(second.data["cached"])
        self.assertEqual(client.calls, 1)
        self.assertEqual(AIEssayScoreReport.objects.count(), 1)

    @override_settings(AI_ESSAY_DAILY_FREE_LIMIT=2)
    def test_changed_essay_calls_ai_again_when_quota_allows(self):
        essay = self._essay()
        client = FakeEssayScoringClient()

        first = self._score_with_client(essay, client)
        essay.draft_text = essay.draft_text + " A revised ending adds one more concrete detail."
        essay.save(update_fields=["draft_text", "updated_at"])
        second = self._score_with_client(essay, client)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, second.data)
        self.assertEqual(client.calls, 2)
        self.assertEqual(AIEssayScoreReport.objects.count(), 2)

    def test_free_daily_limit_is_enforced_after_changed_essay(self):
        essay = self._essay()
        client = FakeEssayScoringClient()

        first = self._score_with_client(essay, client)
        essay.draft_text = essay.draft_text + " New version."
        essay.save(update_fields=["draft_text", "updated_at"])
        second = self._score_with_client(essay, client)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS, second.data)
        self.assertEqual(second.data["reason"], "quota_exceeded")
        self.assertEqual(client.calls, 1)

    def test_paid_monthly_limit_is_enforced(self):
        Subscription.objects.create(user=self.user1, plan=Plan.STARTER)
        essay = self._essay()
        client = FakeEssayScoringClient()

        first = self._score_with_client(essay, client)
        essay.draft_text = essay.draft_text + " Paid plan revised version."
        essay.save(update_fields=["draft_text", "updated_at"])
        second = self._score_with_client(essay, client)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS, second.data)
        self.assertEqual(second.data["next_available_at"] is not None, True)
        self.assertEqual(client.calls, 1)

    def test_invalid_ai_json_is_rejected_without_quota_consumption(self):
        essay = self._essay()
        client = FakeEssayScoringClient({"overall_essay_readiness": 70})

        response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE, response.data)
        self.assertEqual(response.data["reason"], "validation_failed")
        self.assertEqual(AIEssayScoreReport.objects.count(), 0)

    def test_out_of_range_scores_are_rejected(self):
        essay = self._essay()
        client = FakeEssayScoringClient(valid_ai_score_output(subscores={"prompt_fit": 99}))

        response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE, response.data)
        self.assertEqual(response.data["reason"], "validation_failed")

    def test_suggestions_limits_are_enforced(self):
        payload = build_scoring_payload(self._essay())
        too_many = valid_ai_score_output(
            approximate_suggestions=["one", "two", "three", "four"]
        )
        too_long = valid_ai_score_output(
            approximate_suggestions=[
                "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty one"
            ]
        )

        with self.assertRaises(EssayScoringValidationError):
            validate_and_normalize_output(too_many, payload=payload)
        with self.assertRaises(EssayScoringValidationError):
            validate_and_normalize_output(too_long, payload=payload)

    def test_forbidden_outcome_language_and_rewrite_keys_are_rejected(self):
        payload = build_scoring_payload(self._essay())
        forbidden = valid_ai_score_output(risk_flags=["This improves admission chance."])
        rewrite = valid_ai_score_output(rewritten_text="Here is a replacement paragraph.")

        with self.assertRaises(EssayScoringValidationError):
            validate_and_normalize_output(forbidden, payload=payload)
        with self.assertRaises(EssayScoringValidationError):
            validate_and_normalize_output(rewrite, payload=payload)

    def test_provider_error_logs_sanitized_diagnostics_without_secrets_or_essay_text(self):
        essay = self._essay(draft_text="A very private essay about my grandmother's garden.")
        error = AIProviderError(
            "Gemini essay scoring request failed.",
            status_code=404,
            error_body='{"error": {"code": 404, "message": "models/x is not found", "status": "NOT_FOUND"}}',
            cause_class="HTTPError",
            provider_code=404,
            provider_status="NOT_FOUND",
        )
        client = FakeFailingEssayScoringClient(error)

        with self.assertLogs("services.essay_service.ai_scoring", level="WARNING") as captured:
            response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["reason"], "ai_unavailable")
        log_line = "\n".join(captured.output)
        self.assertIn("feature=essay_scoring", log_line)
        self.assertIn("status=404", log_line)
        self.assertIn("exception=AIProviderError", log_line)
        self.assertIn("cause=HTTPError", log_line)
        self.assertIn("provider_code=404", log_line)
        self.assertIn("provider_status=NOT_FOUND", log_line)
        self.assertIn("NOT_FOUND", log_line)
        self.assertNotIn("grandmother's garden", log_line)
        self.assertNotIn("test-gemini-key", log_line)

    def test_validation_failure_logs_sanitized_message_without_essay_text(self):
        essay = self._essay(draft_text="A very private essay about my grandmother's garden.")
        client = FakeEssayScoringClient({"overall_essay_readiness": 70})

        with self.assertLogs("services.essay_service.ai_scoring", level="WARNING") as captured:
            response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        log_line = "\n".join(captured.output)
        self.assertIn("feature=essay_scoring", log_line)
        self.assertIn("essay_id=", log_line)
        self.assertNotIn("grandmother's garden", log_line)

    def test_transient_provider_error_is_retried_once_and_succeeds(self):
        essay = self._essay()
        error = AIProviderError(
            "Gemini essay scoring request timed out.",
            error_body="timeout while calling Gemini",
            cause_class="TimeoutError",
        )
        client = FakeFlakyEssayScoringClient(error, fail_times=1)

        response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["reason"], "scored")
        self.assertEqual(client.calls, 2)
        self.assertEqual(AIEssayScoreReport.objects.count(), 1)

    def test_transient_provider_error_retried_once_then_fails_cleanly(self):
        essay = self._essay()
        error = AIProviderError(
            "Gemini essay scoring request failed.",
            status_code=503,
            error_body="upstream overloaded",
            cause_class="HTTPError",
        )
        client = FakeFlakyEssayScoringClient(error, fail_times=99)

        with self.assertLogs("services.essay_service.ai_scoring", level="WARNING") as captured:
            response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["reason"], "ai_unavailable")
        # Capped at exactly one retry (two total attempts), never more.
        self.assertEqual(client.calls, 2)
        self.assertEqual(AIEssayScoreReport.objects.count(), 0)
        log_line = "\n".join(captured.output)
        self.assertIn("attempt=1_retrying", log_line)
        self.assertIn("attempt=2_final", log_line)

    def test_non_retryable_provider_error_is_not_retried(self):
        essay = self._essay()
        error = AIProviderError(
            "Gemini essay scoring request failed.",
            status_code=400,
            error_body='{"error": {"code": 400, "status": "INVALID_ARGUMENT"}}',
            cause_class="HTTPError",
            provider_code=400,
            provider_status="INVALID_ARGUMENT",
        )
        client = FakeFlakyEssayScoringClient(error, fail_times=99)

        response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["reason"], "ai_unavailable")
        self.assertEqual(client.calls, 1)

    def test_concurrent_scoring_reuses_winning_report_instead_of_duplicating(self):
        essay = self._essay()
        essay_text_hash = compute_essay_text_hash(essay.draft_text)
        payload = build_scoring_payload(essay)
        context_hash = compute_context_hash(payload, model_name="gemini-flash-latest")
        client = FakeRacingEssayScoringClient(
            essay=essay,
            essay_text_hash=essay_text_hash,
            context_hash=context_hash,
            user=essay.user,
        )

        response = self._score_with_client(essay, client)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["reason"], "cached")
        self.assertTrue(response.data["cached"])
        # Only the racing request's own write exists -- score_essay() did not
        # create a second row for the same essay/hash pair.
        self.assertEqual(AIEssayScoreReport.objects.count(), 1)

    @override_settings(AI_ESSAY_DAILY_FREE_LIMIT=2)
    def test_failed_rescore_does_not_delete_previous_score(self):
        essay = self._essay()
        good_client = FakeEssayScoringClient()
        first = self._score_with_client(essay, good_client)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        report_id = first.data["score"]["id"]

        essay.draft_text = essay.draft_text + " A meaningfully different revised ending."
        essay.save(update_fields=["draft_text", "updated_at"])
        failing_error = AIProviderError(
            "Gemini essay scoring request failed.",
            status_code=500,
            error_body="upstream error",
            cause_class="HTTPError",
        )
        failing_client = FakeFailingEssayScoringClient(failing_error)
        second = self._score_with_client(essay, failing_client)
        self.assertEqual(second.status_code, status.HTTP_503_SERVICE_UNAVAILABLE, second.data)

        # The original report from the first (successful) call must still
        # exist untouched, and the latest-score endpoint must still serve it.
        self.assertTrue(AIEssayScoreReport.objects.filter(id=report_id).exists())
        self.client.force_authenticate(essay.user)
        latest = self.client.get(f"/api/essays/{essay.id}/score/latest/")
        self.assertEqual(latest.status_code, status.HTTP_200_OK)
        self.assertEqual(latest.data["score"]["id"], report_id)

    def test_missing_draft_returns_safe_missing_text_reason(self):
        essay = self._essay(draft_text="")
        self.client.force_authenticate(self.user1)
        response = self.client.post(f"/api/essays/{essay.id}/score/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["reason"], "missing_essay_text")
        self.assertIsNone(response.data["score"])

    def test_score_history_and_latest_are_self_only(self):
        essay = self._essay()
        client = FakeEssayScoringClient()
        response = self._score_with_client(essay, client)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        own_scores = self.client.get(f"/api/essays/{essay.id}/scores/")
        own_latest = self.client.get(f"/api/essays/{essay.id}/score/latest/")
        self.assertEqual(own_scores.status_code, status.HTTP_200_OK, own_scores.data)
        self.assertEqual(len(own_scores.data["results"]), 1)
        self.assertEqual(own_latest.status_code, status.HTTP_200_OK, own_latest.data)
        self.assertIsNotNone(own_latest.data["score"])

        self.client.force_authenticate(self.user2)
        other_scores = self.client.get(f"/api/essays/{essay.id}/scores/")
        other_latest = self.client.get(f"/api/essays/{essay.id}/score/latest/")
        self.assertEqual(other_scores.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(other_latest.status_code, status.HTTP_404_NOT_FOUND)

    def test_raw_essay_hash_changes_when_text_changes(self):
        first = compute_essay_text_hash("Same idea")
        second = compute_essay_text_hash("Same idea with more detail")
        self.assertNotEqual(first, second)
