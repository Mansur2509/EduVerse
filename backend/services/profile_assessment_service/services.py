from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from statistics import mean
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from services.ai_gateway_service.exceptions import AIProviderError, AIProviderUnavailable
from services.ai_gateway_service.gemini_client import GeminiProfileAssessmentClient
from services.ai_gateway_service.logging import log_ai_call
from services.application_service.models import ApplicationTrackerItem
from services.essay_service.models import EssayFeedback, EssayWorkspace
from services.university_service.benchmark import resolve_benchmark
from services.university_service.fit_vector import SIGNAL_NAMES
from services.university_service.models import SavedUniversity
from services.user_profile_service.academic_normalization import normalize_profile_academics
from services.user_profile_service.models import (
    Activity,
    EssayDraft,
    Honor,
    Olympiad,
    PortfolioProject,
    Recommender,
    ResearchProject,
    Sport,
    Volunteer,
)
from services.user_profile_service.readiness import calculate_application_readiness
from services.user_profile_service.services import ensure_profile_records

from .deterministic import compute_deterministic_comparisons, compute_deterministic_student_scores
from .models import AIProfileAssessment

logger = logging.getLogger(__name__)

ASSESSMENT_VERSION = "2026-07-profile-v1"
ASSESSMENT_CACHE_DAYS = 365
PROFILE_ASSESSMENT_CATEGORIES = (
    "profile_evidence_score",
    "activities_score",
    "honors_olympiads_score",
    "research_experience_score",
    "portfolio_score",
    "subject_passion_score",
    "curiosity_score",
    "originality_score",
    "leadership_score",
    "community_impact_score",
    "research_fit_score",
    "olympiads_score",
)
# PERFORMANCE-012 PART 4: personal/qualitative-fit rubric, scored by the same
# AI call as the categories above and cached on the same model row. University
# fit (services.university_service) compares these against per-major weight
# profiles entirely deterministically -- this list is the single source of
# truth other modules import rather than re-declaring.
QUALITATIVE_FIT_DIMENSIONS = (
    "academic_readiness",
    "quantitative_readiness",
    "writing_communication",
    "research_orientation",
    "leadership_initiative",
    "service_impact",
    "extracurricular_depth",
    "major_alignment",
    "intellectual_curiosity",
    "resilience_independence",
)
FORBIDDEN_OUTCOME_LANGUAGE_RE = re.compile(
    r"\b(admission\s+chance|admissions\s+chance|chance|probability|odds|"
    r"guarantee(?:d|s)?|acceptance\s+likelihood|admission\s+likelihood)\b",
    re.IGNORECASE,
)
KEYWORD_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,48}$")
DISCLAIMER = (
    "This is a profile-readiness estimate based on saved UniWay profile data. "
    "It is not an admissions decision and does not promise an outcome."
)


class AssessmentValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AssessmentRunResult:
    assessment: AIProfileAssessment | None
    cached: bool
    reason: str
    can_refresh: bool
    next_available_at: Any
    ai_available: bool


def _clean_text(value: Any, *, max_length: int = 500) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return text[:max_length]


def _string_list(values: Any, *, max_items: int = 20, max_length: int = 180) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned = []
    for value in values:
        text = _clean_text(value, max_length=max_length)
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in sorted(value.items())}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    return value


def _age_range(birth_date: date | None) -> str:
    if birth_date is None:
        return "unknown"
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    if age < 14:
        return "under_14"
    if age <= 17:
        return "14_17"
    if age <= 22:
        return "18_22"
    return "23_plus"


def _proof_present(*values: Any) -> bool:
    return any(bool(_clean_text(value, max_length=500)) for value in values)


def _activity_summary(activity: Activity) -> dict:
    role = _clean_text(activity.role, max_length=120).lower()
    category = _clean_text(activity.category, max_length=80).lower()
    return {
        "title": _clean_text(activity.title, max_length=150),
        "role": _clean_text(activity.role, max_length=150),
        "category": _clean_text(activity.category, max_length=100),
        "organization": _clean_text(activity.organization, max_length=150),
        "year": activity.year,
        "hours_per_week": activity.hours_per_week,
        "weeks_per_year": activity.weeks_per_year,
        "scope": activity.scale,
        "impact_numbers": _clean_text(activity.impact_number, max_length=120),
        "leadership_signal": "lead" in role or "founder" in role or "leadership" in category,
        "has_proof_link": _proof_present(activity.proof_link),
        "description": _clean_text(activity.description),
    }


def _honor_summary(honor: Honor) -> dict:
    return {
        "title": _clean_text(honor.title, max_length=150),
        "level": _clean_text(honor.level, max_length=100),
        "organization": _clean_text(honor.issuing_organization, max_length=150),
        "result_or_rank": _clean_text(honor.result_rank, max_length=100),
        "year": honor.year,
        "has_proof_link": _proof_present(honor.proof_link),
        "description": _clean_text(honor.description),
    }


def _olympiad_summary(olympiad: Olympiad) -> dict:
    return {
        "name": _clean_text(olympiad.name, max_length=150),
        "subject": _clean_text(olympiad.subject, max_length=100),
        "level": _clean_text(olympiad.level, max_length=100),
        "result_or_rank": _clean_text(olympiad.result or olympiad.rank_percentile, max_length=120),
        "year": olympiad.year,
        "has_proof_link": _proof_present(olympiad.proof_link),
        "description": _clean_text(olympiad.description),
    }


def _research_summary(project: ResearchProject) -> dict:
    return {
        "title": _clean_text(project.title, max_length=150),
        "topic_or_field": _clean_text(project.field, max_length=150),
        "research_question": _clean_text(project.research_question),
        "methodology": _clean_text(project.methods_used, max_length=150),
        "sample_or_scope": _clean_text(project.sample_size, max_length=100),
        "regions": _clean_text(project.countries_region, max_length=150),
        "stage": project.current_stage,
        "publication_status": _clean_text(project.publication_status, max_length=100),
        "has_proof_link": _proof_present(project.manuscript_link),
        "description": _clean_text(project.description),
    }


def _portfolio_summary(project: PortfolioProject) -> dict:
    return {
        "title": _clean_text(project.title, max_length=150),
        "category": _clean_text(project.project_type, max_length=100),
        "tech_stack_or_field": _clean_text(project.tech_stack, max_length=150),
        "users_or_impact": _clean_text(project.users_impact, max_length=150),
        "status": _clean_text(project.status, max_length=100),
        "has_proof_link": _proof_present(project.link),
        "description": _clean_text(project.description),
    }


def _volunteer_summary(volunteer: Volunteer) -> dict:
    return {
        "title": _clean_text(volunteer.title, max_length=150),
        "role": _clean_text(volunteer.role, max_length=150),
        "organization": _clean_text(volunteer.organization, max_length=150),
        "scope": volunteer.scale,
        "hours_per_week": volunteer.hours_per_week,
        "weeks_per_year": volunteer.weeks_per_year,
        "impact": _clean_text(volunteer.impact_number, max_length=120),
        "beneficiaries": _clean_text(volunteer.beneficiaries, max_length=150),
        "has_proof_link": _proof_present(volunteer.proof_link),
        "description": _clean_text(volunteer.description),
    }


def _sports_summary(sport: Sport) -> dict:
    return {
        "sport": _clean_text(sport.sport_name, max_length=150),
        "level": _clean_text(sport.level, max_length=100),
        "years_active": _clean_text(sport.years_trained, max_length=100),
        "achievement": _clean_text(sport.peak_result, max_length=150),
        "competition": _clean_text(sport.competition_name, max_length=150),
        "has_proof_link": _proof_present(sport.proof_link),
        "description": _clean_text(sport.description),
    }


def _essay_readiness_summary(user) -> dict:
    profile_drafts = list(EssayDraft.objects.filter(user=user))
    workspaces = list(EssayWorkspace.objects.filter(user=user).select_related("university", "application"))
    verified_prompt_count = sum(
        1
        for workspace in workspaces
        if workspace.prompt_verification_status == EssayWorkspace.VerificationStatus.VERIFIED
    )
    feedback_scores = list(
        EssayFeedback.objects.filter(essay__user=user)
        .exclude(prompt_fit_score__isnull=True)
        .values_list("prompt_fit_score", flat=True)
    )
    return {
        "profile_draft_count": len(profile_drafts),
        "workspace_count": len(workspaces),
        "draft_statuses": sorted(
            {
                draft.status
                for draft in profile_drafts
            }
            | {workspace.status for workspace in workspaces}
        ),
        "linked_university_count": sum(1 for workspace in workspaces if workspace.university_id),
        "linked_application_count": sum(1 for workspace in workspaces if workspace.application_id),
        "verified_prompt_count": verified_prompt_count,
        "average_prompt_fit_score": (
            round(sum(feedback_scores) / len(feedback_scores), 1) if feedback_scores else None
        ),
        "missing_prompt_count": sum(
            1
            for workspace in workspaces
            if workspace.prompt_verification_status == EssayWorkspace.VerificationStatus.MISSING
        ),
    }


def _target_context(user, profile) -> dict:
    saved = list(
        SavedUniversity.objects.filter(user=user)
        .select_related("university")
        .prefetch_related("university__programs")
    )
    applications = list(
        ApplicationTrackerItem.objects.filter(user=user)
        .select_related("university", "target_program")
        .prefetch_related("university__programs")
    )
    targets = _string_list(profile.target_universities, max_items=30)
    saved_names = [item.university.name for item in saved]
    tracked_names = [item.university.name for item in applications]
    universities = []
    seen_ids = set()
    for university in [item.university for item in saved] + [item.university for item in applications]:
        if university.id in seen_ids:
            continue
        seen_ids.add(university.id)
        universities.append(
            {
                "name": university.name,
                "country": university.country,
                "acceptance_rate": university.acceptance_rate,
                "global_rank": university.global_rank,
                "qs_ranking": university.qs_ranking,
                "program_clusters": _string_list(
                    [
                        program.major_cluster
                        for program in university.programs.all()
                        if program.major_cluster
                    ],
                    max_items=12,
                    max_length=80,
                ),
            }
        )
    return {
        "target_universities": targets,
        "shortlisted_universities": saved_names[:25],
        "tracked_applications": [
            {
                "university": item.university.name,
                "status": item.status,
                "priority": item.priority,
                # 022 Phase 10: a round change (e.g. Regular Decision ->
                # Early Decision) shifts deadline/readiness context enough
                # that cached recommendations/strategy/assessment must
                # invalidate on it, same as status/priority already do.
                "application_round": item.application_round,
                "target_program": item.target_program.name if item.target_program else "",
            }
            for item in applications[:25]
        ],
        "university_context": universities[:25],
        "has_target_context": bool(targets or saved_names or tracked_names),
    }


def build_profile_assessment_input(user) -> dict:
    profile, preferences = ensure_profile_records(user)
    normalization = normalize_profile_academics(profile)
    target_context = _target_context(user, profile)
    summary = {
        "assessment_version": ASSESSMENT_VERSION,
        "basic_context": {
            "age_range": _age_range(profile.birth_date),
            "country": _clean_text(profile.country, max_length=100),
            "city": _clean_text(profile.city, max_length=120),
            "school_context_present": bool(profile.school_or_university.strip()),
            "education_status": _clean_text(profile.education_status, max_length=120),
            "grade": _clean_text(profile.grade, max_length=50),
            "expected_graduation_year": profile.expected_graduation_year,
            "target_degree": _clean_text(profile.intended_degree, max_length=120),
            "target_countries": _string_list(profile.target_countries),
            "intended_majors": _string_list(
                profile.intended_majors or ([profile.intended_major] if profile.intended_major else [])
            ),
            "career_interests": _string_list(preferences.career_interests),
            "academic_interests": _string_list(preferences.interests),
            "major_unsure": profile.major_unsure,
            "university_unsure": profile.university_unsure,
        },
        "academic_context": {
            "gpa_raw_value": profile.original_gpa_value or profile.gpa,
            "gpa_scale": profile.original_gpa_scale or profile.gpa_scale,
            "normalized_gpa_4": normalization.normalized_gpa_4,
            "normalized_percentage": normalization.normalized_percentage,
            "normalization_confidence": normalization.confidence,
            "curriculum_type": profile.curriculum_type,
            "curriculum_country": _clean_text(profile.curriculum_country, max_length=100),
            "course_rigor_level": profile.course_rigor_level,
            "ap_courses_count": profile.ap_courses_count,
            "ib_courses_count": profile.ib_courses_count,
            "a_level_subjects_count": profile.a_level_subjects_count,
            "honors_courses_count": profile.honors_courses_count,
            "test_scores": _json_safe(profile.test_scores if isinstance(profile.test_scores, dict) else {}),
            "exam_plans": _json_safe(profile.exam_plans if isinstance(profile.exam_plans, dict) else {}),
        },
        "activities": [
            _activity_summary(activity)
            for activity in Activity.objects.filter(user=user).order_by("-created_at")[:30]
        ],
        "legacy_activity_signals": {
            key: _string_list(value, max_items=12)
            for key, value in (profile.activities or {}).items()
            if isinstance(value, list)
        },
        "honors": [
            _honor_summary(honor)
            for honor in Honor.objects.filter(user=user).order_by("-created_at")[:25]
        ],
        "olympiads": [
            _olympiad_summary(olympiad)
            for olympiad in Olympiad.objects.filter(user=user).order_by("-created_at")[:25]
        ],
        "research": [
            _research_summary(project)
            for project in ResearchProject.objects.filter(user=user).order_by("-created_at")[:20]
        ],
        "portfolio": [
            _portfolio_summary(project)
            for project in PortfolioProject.objects.filter(user=user).order_by("-created_at")[:20]
        ],
        "volunteering": [
            _volunteer_summary(volunteer)
            for volunteer in Volunteer.objects.filter(user=user).order_by("-created_at")[:20]
        ],
        "sports": [
            _sports_summary(sport)
            for sport in Sport.objects.filter(user=user).order_by("-created_at")[:20]
        ],
        "recommenders": [
            {
                "relationship_role": _clean_text(recommender.relationship_role, max_length=150),
                "status": recommender.status,
                "notes_present": bool(recommender.notes.strip()),
            }
            for recommender in Recommender.objects.filter(user=user).order_by("-created_at")[:12]
        ],
        "essays": _essay_readiness_summary(user),
        "budget_context": {
            "annual_budget_amount": profile.annual_budget_amount,
            "annual_budget_currency": _clean_text(profile.annual_budget_currency, max_length=10),
            "needs_financial_aid": profile.scholarship_need,
            "budget_flexibility": profile.budget_flexibility,
            "budget_unknown": profile.annual_budget_amount is None,
        },
        "target_context": target_context,
        "privacy_notes": [
            "No password, payment data, phone, Telegram username, email, or raw essay text is included.",
            "Proof links are represented as presence booleans, not sent as URLs.",
        ],
    }
    return _json_safe(summary)


def compute_profile_snapshot_hash(user) -> str:
    input_summary = build_profile_assessment_input(user)
    payload = json.dumps(input_summary, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_latest_assessment(user) -> AIProfileAssessment | None:
    return AIProfileAssessment.objects.filter(user=user).order_by("-created_at").first()


def get_latest_valid_assessment(user) -> AIProfileAssessment | None:
    latest = get_latest_assessment(user)
    if not latest or latest.is_stale or latest.expires_at <= timezone.now():
        return None

    current_hash = compute_profile_snapshot_hash(user)
    if latest.profile_snapshot_hash == current_hash:
        return latest
    return None


def get_current_assessment_for_profile(profile) -> AIProfileAssessment | None:
    if hasattr(profile, "_current_profile_assessment_cache"):
        return profile._current_profile_assessment_cache
    assessment = get_latest_valid_assessment(profile.user)
    profile._current_profile_assessment_cache = assessment
    return assessment


def profile_assessment_ai_available() -> bool:
    return bool(settings.AI_PROFILE_ASSESSMENT_ENABLED and settings.GEMINI_API_KEY)


def _next_available_at() -> Any:
    now = timezone.now()
    tomorrow = now.date() + timedelta(days=1)
    return timezone.make_aware(
        datetime.combine(tomorrow, datetime.min.time())
    )


def _daily_limit_reached(user) -> bool:
    limit = max(0, settings.AI_PROFILE_ASSESSMENT_DAILY_LIMIT)
    if limit <= 0:
        return True
    now = timezone.now()
    start = timezone.make_aware(datetime.combine(now.date(), datetime.min.time()))
    return AIProfileAssessment.objects.filter(user=user, created_at__gte=start).count() >= limit


QUALITATIVE_FIT_STATUS_FRESH = "fresh"
QUALITATIVE_FIT_STATUS_STALE = "stale"
QUALITATIVE_FIT_STATUS_MISSING = "missing"
QUALITATIVE_FIT_STATUS_PENDING_DAILY_REFRESH = "pending_daily_refresh"
QUALITATIVE_FIT_STATUS_FAILED = "failed"


def qualitative_fit_status(user) -> tuple[str, AIProfileAssessment | None]:
    """Pure read of the cached qualitative-fit dimension scores -- never calls
    AI (PERFORMANCE-012 PART 4/5). University fit reads this to decide whether
    the cached personal-fit scores are usable, stale-but-usable, or missing,
    without a GET ever being able to trigger a fresh AI call. Explicit refresh
    stays exactly `RunProfileAssessmentView`'s existing POST /assessment/run/
    action -- already rate-limited to once per day, already never called on
    render.
    """
    latest = get_latest_assessment(user)
    if latest is None:
        return QUALITATIVE_FIT_STATUS_MISSING, None
    if latest.status == AIProfileAssessment.Status.FALLBACK_USED:
        return QUALITATIVE_FIT_STATUS_FAILED, latest

    current_hash = compute_profile_snapshot_hash(user)
    if latest.profile_snapshot_hash == current_hash and not latest.is_expired:
        return QUALITATIVE_FIT_STATUS_FRESH, latest
    if _daily_limit_reached(user):
        return QUALITATIVE_FIT_STATUS_PENDING_DAILY_REFRESH, latest
    return QUALITATIVE_FIT_STATUS_STALE, latest


def _list_of_strings(value: Any, field_name: str, *, max_items: int = 20) -> list[str]:
    if not isinstance(value, list):
        raise AssessmentValidationError(f"{field_name} must be a list.")
    cleaned = []
    for item in value:
        if not isinstance(item, str):
            raise AssessmentValidationError(f"{field_name} must contain only text.")
        text = item.strip()
        if text:
            cleaned.append(text[:240])
    return cleaned[:max_items]


def _validate_score(value: Any, field_name: str, *, minimum: int = 1, maximum: int = 10) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AssessmentValidationError(f"{field_name} must be an integer.")
    if value < minimum or value > maximum:
        raise AssessmentValidationError(f"{field_name} must be between {minimum} and {maximum}.")
    return value


def _validate_keywords(value: Any) -> list[str]:
    keywords = _list_of_strings(value, "internal_keywords", max_items=21)
    if len(keywords) > 20:
        raise AssessmentValidationError("internal_keywords may contain at most 20 items.")
    normalized = []
    for keyword in keywords:
        safe = keyword.strip().lower().replace(" ", "-")
        if not KEYWORD_RE.fullmatch(safe):
            raise AssessmentValidationError("internal_keywords must be compact lowercase signals.")
        if safe not in normalized:
            normalized.append(safe)
    return normalized


def _validate_qualitative_fit_scores(value: Any) -> dict:
    if not isinstance(value, dict):
        raise AssessmentValidationError("qualitative_fit_scores must be an object.")
    normalized = {}
    for dimension in QUALITATIVE_FIT_DIMENSIONS:
        entry = value.get(dimension)
        if not isinstance(entry, dict):
            raise AssessmentValidationError(f"qualitative_fit_scores.{dimension} must be an object.")
        score = _validate_score(entry.get("score"), f"qualitative_fit_scores.{dimension}.score")
        confidence = entry.get("confidence")
        if confidence not in AIProfileAssessment.Confidence.values:
            raise AssessmentValidationError(
                f"qualitative_fit_scores.{dimension}.confidence must be low, medium, or high."
            )
        evidence = entry.get("evidence")
        if not isinstance(evidence, str):
            raise AssessmentValidationError(f"qualitative_fit_scores.{dimension}.evidence must be text.")
        normalized[dimension] = {
            "score": score,
            "evidence": evidence.strip()[:300],
            "confidence": confidence,
        }
    return normalized


def validate_ai_profile_assessment_json(output: dict) -> dict:
    if not isinstance(output, dict):
        raise AssessmentValidationError("AI assessment output must be an object.")
    if FORBIDDEN_OUTCOME_LANGUAGE_RE.search(json.dumps(output, sort_keys=True)):
        raise AssessmentValidationError("AI assessment output contains outcome-probability wording.")

    category_scores = output.get("category_scores")
    if not isinstance(category_scores, dict):
        raise AssessmentValidationError("category_scores must be an object.")
    normalized_scores = {
        category: _validate_score(category_scores.get(category), category)
        for category in PROFILE_ASSESSMENT_CATEGORIES
    }

    confidence = output.get("confidence")
    if confidence not in AIProfileAssessment.Confidence.values:
        raise AssessmentValidationError("confidence must be low, medium, or high.")

    category_rationales = output.get("category_rationales")
    if not isinstance(category_rationales, dict):
        raise AssessmentValidationError("category_rationales must be an object.")
    normalized_rationales = {}
    for category in PROFILE_ASSESSMENT_CATEGORIES:
        rationale = category_rationales.get(category)
        if not isinstance(rationale, str):
            raise AssessmentValidationError(f"{category} rationale must be text.")
        normalized_rationales[category] = rationale.strip()[:500]

    target_context_used = output.get("target_context_used")
    if not isinstance(target_context_used, bool):
        raise AssessmentValidationError("target_context_used must be boolean.")

    return {
        "overall_profile_score": _validate_score(
            output.get("overall_profile_score"),
            "overall_profile_score",
            maximum=100,
        ),
        "category_scores": normalized_scores,
        "confidence": confidence,
        "target_context_used": target_context_used,
        "public_summary": _clean_text(output.get("public_summary"), max_length=800),
        "evidence_used": _list_of_strings(output.get("evidence_used", []), "evidence_used"),
        "missing_data": _list_of_strings(output.get("missing_data", []), "missing_data"),
        "improvement_areas": _list_of_strings(
            output.get("improvement_areas", []),
            "improvement_areas",
        ),
        "internal_keywords": _validate_keywords(output.get("internal_keywords", [])),
        "category_rationales": normalized_rationales,
        "warnings": _list_of_strings(output.get("warnings", []), "warnings"),
        "qualitative_fit_scores": _validate_qualitative_fit_scores(
            output.get("qualitative_fit_scores", {})
        ),
    }


def get_profile_assessment_client():
    return GeminiProfileAssessmentClient()


@transaction.atomic
def store_profile_assessment(
    user,
    *,
    input_summary: dict,
    output: dict,
    provider_name: str,
    model_name: str,
    status: str = AIProfileAssessment.Status.OK,
) -> AIProfileAssessment:
    normalized = validate_ai_profile_assessment_json(output)
    current_hash = compute_profile_snapshot_hash(user)
    profile, preferences = ensure_profile_records(user)

    # PROTOCOL-008 PART 5: compute the benchmark fallback chain (PART 2),
    # deterministic comparisons (PART 4), and six-section readiness (PART 6)
    # once, at write time, and cache all of it alongside the AI category
    # scores so a page render never has to recompute them or call AI again.
    student_scores = {
        signal: normalized["category_scores"][f"{signal}_score"] for signal in SIGNAL_NAMES
    }
    benchmark = resolve_benchmark(profile)
    deterministic_comparisons = compute_deterministic_comparisons(
        profile, preferences, benchmark=benchmark, student_scores=student_scores
    )
    readiness = calculate_application_readiness(
        profile, preferences, deterministic_comparisons=deterministic_comparisons
    )

    AIProfileAssessment.objects.filter(user=user, is_stale=False).update(is_stale=True)
    return AIProfileAssessment.objects.create(
        user=user,
        profile_snapshot_hash=current_hash,
        assessment_version=ASSESSMENT_VERSION,
        prompt_version=ASSESSMENT_VERSION,
        status=status,
        model_provider=provider_name,
        model_name=model_name,
        raw_input_summary_json=input_summary,
        raw_output_json=output,
        overall_profile_score=normalized["overall_profile_score"],
        confidence=normalized["confidence"],
        public_summary=normalized["public_summary"],
        evidence_used=normalized["evidence_used"],
        missing_data=normalized["missing_data"],
        improvement_areas=normalized["improvement_areas"],
        internal_keywords=normalized["internal_keywords"],
        category_rationales=normalized["category_rationales"],
        target_context_used=normalized["target_context_used"],
        benchmark_source=benchmark.source,
        benchmark_sample_size=benchmark.sample_size,
        benchmark_scores=benchmark.scores,
        benchmark_academic=benchmark.academic,
        deterministic_scores=deterministic_comparisons,
        qualitative_fit_scores=normalized["qualitative_fit_scores"],
        readiness_scores={
            "status": readiness.level,
            "cap_reason": readiness.cap_reason,
            "reasons": readiness.reasons,
            "next_actions": readiness.next_actions,
            "sections": readiness.sections,
        },
        overall_readiness_score=readiness.stars,
        expires_at=timezone.now() + timedelta(days=ASSESSMENT_CACHE_DAYS),
        next_allowed_refresh_at=_next_available_at(),
        **normalized["category_scores"],
    )


def _build_deterministic_fallback_output(profile) -> dict:
    """PROTOCOL-008 PART 3's fallback path: used only when the AI provider's
    output fails schema validation twice in a row (initial attempt + one
    repair retry). Builds a schema-valid synthetic output from real evidence
    counts, so the student still gets a cached, honest assessment instead of
    an outright failure.
    """

    deterministic_scores = compute_deterministic_student_scores(profile)
    category_scores = {f"{signal}_score": deterministic_scores[signal] for signal in SIGNAL_NAMES}
    rationale = "Deterministic fallback score based on profile evidence counts; AI scoring was unavailable."
    fallback_qualitative_entry = {
        "score": 5,
        "evidence": "AI scoring was unavailable; no personal-fit evidence assessed.",
        "confidence": AIProfileAssessment.Confidence.LOW,
    }
    return {
        "overall_profile_score": round(mean(category_scores.values()) * 10),
        "category_scores": category_scores,
        "confidence": AIProfileAssessment.Confidence.LOW,
        "target_context_used": False,
        "public_summary": (
            "This is a deterministic evidence-based estimate. AI scoring could not "
            "produce a valid result, so scores reflect profile evidence counts only."
        ),
        "evidence_used": [],
        "missing_data": [],
        "improvement_areas": [],
        "internal_keywords": [],
        "category_rationales": dict.fromkeys(category_scores, rationale),
        "warnings": ["deterministic_fallback_used"],
        "qualitative_fit_scores": {
            dimension: dict(fallback_qualitative_entry)
            for dimension in QUALITATIVE_FIT_DIMENSIONS
        },
    }


def latest_assessment_envelope(user) -> AssessmentRunResult:
    latest = get_latest_assessment(user)
    current_hash = compute_profile_snapshot_hash(user)
    if latest and latest.profile_snapshot_hash != current_hash and not latest.is_stale:
        latest.is_stale = True
        latest.save(update_fields=["is_stale"])
    unchanged = bool(latest and latest.profile_snapshot_hash == current_hash and not latest.is_expired)
    can_refresh = profile_assessment_ai_available() and (
        latest is None or unchanged is False
    ) and not _daily_limit_reached(user)
    return AssessmentRunResult(
        assessment=latest,
        cached=bool(unchanged and latest and not latest.is_stale),
        reason="latest_assessment" if latest else "no_previous_assessment",
        can_refresh=can_refresh,
        next_available_at=_next_available_at() if latest and not can_refresh else None,
        ai_available=profile_assessment_ai_available(),
    )


def _log_provider_error(assessment_client, error: AIProviderError | AIProviderUnavailable) -> None:
    # Never log the profile input, the prompt, or the API key -- only enough
    # structured, sanitized detail (status code, wrapped-exception class,
    # Gemini's own error code/status, message, and truncated provider error
    # body) to diagnose a production failure from Render logs.
    logger.warning(
        "Gemini provider error feature=profile_assessment model=%s status=%s exception=%s cause=%s "
        "provider_code=%s provider_status=%s message=\"%s\" error=\"%s\"",
        getattr(assessment_client, "model_name", settings.AI_PROFILE_ASSESSMENT_MODEL),
        getattr(error, "status_code", None),
        type(error).__name__,
        getattr(error, "cause_class", None),
        getattr(error, "provider_code", None),
        getattr(error, "provider_status", None),
        str(error)[:1000],
        getattr(error, "error_body", "")[:1000],
    )


def _log_validation_error(assessment_client, error: AssessmentValidationError, *, attempt: int) -> None:
    # `error` only ever names a schema field/key or an out-of-range value
    # (see the _validate_* helpers above) -- never raw profile text. Still
    # truncated defensively since one branch echoes back whatever value the
    # AI put in an enum field.
    logger.warning(
        "Gemini schema validation error feature=profile_assessment model=%s attempt=%s message=\"%s\"",
        getattr(assessment_client, "model_name", settings.AI_PROFILE_ASSESSMENT_MODEL),
        attempt,
        str(error)[:300],
    )


def run_profile_assessment(user, *, force: bool = False, client=None) -> AssessmentRunResult:
    """Times and logs every assessment attempt -- cache hits, provider
    calls, and rejections alike -- with sanitized, aggregate-only fields
    (status, cache_hit, duration_ms), then delegates to
    `_run_profile_assessment_impl` for the actual logic. Never logs profile
    or prompt text.
    """

    started_at = time.monotonic()
    result = _run_profile_assessment_impl(user, force=force, client=client)
    duration_ms = int((time.monotonic() - started_at) * 1000)
    log_ai_call(
        logger,
        task_type="profile_assessment",
        provider="gemini",
        model=settings.AI_PROFILE_ASSESSMENT_MODEL,
        status=result.reason,
        cache_hit=result.cached,
        duration_ms=duration_ms,
        user_id=user.id,
    )
    return result


def _run_profile_assessment_impl(user, *, force: bool = False, client=None) -> AssessmentRunResult:
    latest = get_latest_assessment(user)
    current_hash = compute_profile_snapshot_hash(user)
    if (
        latest
        and latest.profile_snapshot_hash == current_hash
        and not latest.is_stale
        and not latest.is_expired
        and not force
    ):
        return AssessmentRunResult(
            assessment=latest,
            cached=True,
            reason="unchanged_cached",
            can_refresh=False,
            next_available_at=None,
            ai_available=profile_assessment_ai_available(),
        )

    if not profile_assessment_ai_available():
        return AssessmentRunResult(
            assessment=latest,
            cached=False,
            reason="ai_unavailable",
            can_refresh=False,
            next_available_at=None,
            ai_available=False,
        )

    if not force and _daily_limit_reached(user):
        return AssessmentRunResult(
            assessment=latest,
            cached=False,
            reason="daily_limit_reached",
            can_refresh=False,
            next_available_at=_next_available_at(),
            ai_available=True,
        )

    input_summary = build_profile_assessment_input(user)
    assessment_client = client or get_profile_assessment_client()
    profile, _preferences = ensure_profile_records(user)

    used_fallback = False
    try:
        output = assessment_client.generate_profile_assessment(input_summary)
        validate_ai_profile_assessment_json(output)
    except (AIProviderError, AIProviderUnavailable) as error:
        _log_provider_error(assessment_client, error)
        return AssessmentRunResult(
            assessment=latest,
            cached=False,
            reason="ai_unavailable",
            can_refresh=False,
            next_available_at=None,
            ai_available=False,
        )
    except AssessmentValidationError as first_error:
        _log_validation_error(assessment_client, first_error, attempt=1)
        # PROTOCOL-008 PART 3: retry once with a repair prompt before giving
        # up -- most schema misses are a one-off formatting slip the model
        # can correct when told exactly what was wrong.
        try:
            output = assessment_client.generate_profile_assessment(
                input_summary, repair_reason=str(first_error)
            )
            validate_ai_profile_assessment_json(output)
        except (AIProviderError, AIProviderUnavailable) as error:
            _log_provider_error(assessment_client, error)
            return AssessmentRunResult(
                assessment=latest,
                cached=False,
                reason="ai_unavailable",
                can_refresh=False,
                next_available_at=None,
                ai_available=False,
            )
        except AssessmentValidationError as second_error:
            _log_validation_error(assessment_client, second_error, attempt=2)
            logger.warning(
                "Profile assessment deterministic fallback used feature=profile_assessment "
                "model=%s user_id=%s reason=validation_failed_twice",
                getattr(assessment_client, "model_name", settings.AI_PROFILE_ASSESSMENT_MODEL),
                user.id,
            )
            output = _build_deterministic_fallback_output(profile)
            used_fallback = True

    assessment = store_profile_assessment(
        user,
        input_summary=input_summary,
        output=output,
        provider_name=getattr(assessment_client, "provider_name", "unknown"),
        model_name=getattr(assessment_client, "model_name", settings.AI_PROFILE_ASSESSMENT_MODEL),
        status=AIProfileAssessment.Status.FALLBACK_USED if used_fallback else AIProfileAssessment.Status.OK,
    )

    return AssessmentRunResult(
        assessment=assessment,
        cached=False,
        reason=(
            "fallback_used"
            if used_fallback
            else ("no_previous_assessment" if latest is None else "profile_changed")
        ),
        can_refresh=False,
        next_available_at=None,
        ai_available=True,
    )
