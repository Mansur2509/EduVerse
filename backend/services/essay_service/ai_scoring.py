from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from services.ai_gateway_service.essay_scoring_client import GeminiEssayScoringClient
from services.ai_gateway_service.exceptions import AIProviderError
from services.subscription_service.models import Plan, Subscription, UsageLog

from .models import AIEssayScoreReport, EssayWorkspace

logger = logging.getLogger(__name__)

RUBRIC_VERSION = "essay_numeric_v1"

MAX_SUGGESTIONS = 3
MAX_SUGGESTION_WORDS = 20
MIN_VERBATIM_MATCH_LEN = 40

# Matched case-insensitively against every AI-authored string field. Negation
# disclaimers ("not an admissions decision or guarantee") are never checked
# against this list because `disclaimers` is always replaced with the fixed
# REQUIRED_DISCLAIMERS below, not taken from the model's own output.
FORBIDDEN_PHRASES = (
    "probability",
    "chance of admission",
    "admission chance",
    "odds of",
    "guarantee",
    "guaranteed",
    "will get in",
    "will be accepted",
    "you will get",
)

REQUIRED_DISCLAIMERS = [
    "This is an automated essay-readiness estimate, not an admissions decision or guarantee.",
    "Scores are based only on the essay text and verified EduVerse context available.",
    "AI/paraphrase style signal is not proof of AI use.",
    "For important submissions, verify requirements yourself and ideally review with a qualified human reviewer.",
]

ESSAY_SCORING_SYSTEM_PROMPT = (
    "You are EduVerse Essay Scoring Engine, acting as a strict admissions essay "
    "evaluator with professional admissions-review standards. Evaluate only the "
    "provided essay and verified context. Do not use outside knowledge. Do not "
    "invent university requirements. Do not invent student facts. Do not write, "
    "rewrite, or paraphrase the essay. Do not provide admission probability, "
    "odds, chance, or guarantee. Return only valid JSON matching the requested "
    "schema. Score the essay against the rubric: prompt fit, structure, "
    "specificity/evidence, authenticity, language clarity, word-limit "
    "discipline, and school/program alignment only when verified school/"
    "program data exists. Do not provide admissions outcome promises. "
    "Suggestions must be approximate, high-level, and max 20 words each. If "
    "official prompt or school data is missing, lower confidence and state "
    "the limitation."
)

ALLOWED_TOP_LEVEL_KEYS = {
    "overall_essay_readiness",
    "confidence",
    "subscores",
    "ai_paraphrase_style_signal",
    "generic_language_signal",
    "unsupported_claims_signal",
    "strength_flags",
    "risk_flags",
    "approximate_suggestions",
    "source_warnings",
}
ALLOWED_SUBSCORE_KEYS = {
    "prompt_fit",
    "structure",
    "specificity_evidence",
    "authenticity",
    "language_clarity",
    "word_limit_discipline",
    "school_program_alignment",
}
DISALLOWED_GENERATION_KEYS = {
    "generated_essay",
    "rewritten_essay",
    "rewritten_text",
    "rewritten_paragraph",
    "paragraph_rewrite",
    "new_draft",
    "full_essay",
}


class EssayScoringValidationError(Exception):
    """Raised when the AI response fails strict schema/content validation."""


def compute_essay_text_hash(essay_text: str) -> str:
    normalized = (essay_text or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _compute_word_limit_status(word_count: int, word_limit: int | None) -> str:
    if not word_limit:
        return AIEssayScoreReport.WordLimitStatus.UNKNOWN
    if word_count > word_limit:
        return AIEssayScoreReport.WordLimitStatus.OVER
    if word_count < 0.6 * word_limit:
        return AIEssayScoreReport.WordLimitStatus.UNDER
    if word_count >= 0.9 * word_limit:
        return AIEssayScoreReport.WordLimitStatus.NEAR_LIMIT
    return AIEssayScoreReport.WordLimitStatus.WITHIN


def build_scoring_payload(essay: EssayWorkspace) -> dict:
    """Compact, backend-derived context sent to the AI -- never invented."""

    application = essay.application
    university = essay.university or (application.university if application else None)
    program = application.target_program if application else None
    draft_text = essay.draft_text or ""
    word_count = len(draft_text.split())
    prompt_text = (essay.prompt_text or "").strip()

    verified_context_used = bool(
        prompt_text
        and essay.prompt_verification_status == EssayWorkspace.VerificationStatus.VERIFIED
    )
    if not prompt_text or essay.prompt_verification_status == EssayWorkspace.VerificationStatus.MISSING:
        prompt_source_confidence = "missing"
    elif essay.prompt_verification_status == EssayWorkspace.VerificationStatus.VERIFIED:
        prompt_source_confidence = essay.prompt_confidence
    else:
        prompt_source_confidence = "low"

    profile_keywords = []
    try:
        from services.profile_assessment_service.services import get_latest_valid_assessment

        assessment = get_latest_valid_assessment(essay.user)
        if assessment is not None:
            profile_keywords = assessment.internal_keywords[:10]
    except Exception:
        profile_keywords = []

    return {
        "essay_text": draft_text,
        "essay_title": essay.title,
        "essay_type": essay.essay_type,
        "word_count": word_count,
        "word_limit": essay.word_limit,
        "linked_university_name": university.name if university else None,
        "linked_program_name": program.name if program else None,
        "linked_application_round": application.application_round if application else None,
        "official_prompt_text": prompt_text if verified_context_used else None,
        "prompt_source_url": essay.source_url or None,
        "prompt_last_verified_date": (
            essay.last_reviewed_at.date().isoformat()
            if verified_context_used and essay.last_reviewed_at
            else None
        ),
        "prompt_source_confidence": prompt_source_confidence,
        "verified_context_used": verified_context_used,
        "university_id": university.id if university else None,
        "program_id": program.id if program else None,
        "application_id": application.id if application else None,
        "profile_keywords": profile_keywords,
    }


def compute_context_hash(payload: dict, *, model_name: str) -> str:
    # Deliberately excludes `essay_title`: a title-only edit must not bust the
    # cache or consume quota unless the title change also changes one of these
    # (e.g. re-linking to a different application/program).
    material = {
        "official_prompt_text": payload["official_prompt_text"],
        "prompt_source_url": payload["prompt_source_url"],
        "word_limit": payload["word_limit"],
        "university_id": payload["university_id"],
        "program_id": payload["program_id"],
        "application_id": payload["application_id"],
        "profile_keywords": payload["profile_keywords"],
        "rubric_version": RUBRIC_VERSION,
        "model_name": model_name,
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode("utf-8")).hexdigest()


ESSAY_SCORING_JSON_SCHEMA_INSTRUCTIONS = (
    "Return JSON with exactly these top-level keys and nothing else: "
    "overall_essay_readiness (integer 1-100), "
    "confidence (\"low\"|\"medium\"|\"high\"), "
    "subscores (object with exactly: prompt_fit integer 0-25, structure integer 0-20, "
    "specificity_evidence integer 0-20, authenticity integer 0-15, language_clarity "
    "integer 0-10, word_limit_discipline integer 0-5 or null, school_program_alignment "
    "integer 0-5 or null), "
    "ai_paraphrase_style_signal (\"low\"|\"medium\"|\"high\"|\"inconclusive\"), "
    "generic_language_signal (\"low\"|\"medium\"|\"high\"), "
    "unsupported_claims_signal (\"low\"|\"medium\"|\"high\"|\"inconclusive\"), "
    "strength_flags (array of short strings), risk_flags (array of short strings), "
    "approximate_suggestions (array of at most 3 strings, each at most 20 words, "
    "high-level only, never a rewritten sentence or paragraph), "
    "source_warnings (array of short strings). "
    "Do not include word_count, word_limit_status, disclaimers, or any essay text -- "
    "the backend computes those itself."
)

ESSAY_SCORING_JSON_OUTPUT_RULES = (
    "Output format rules: return exactly one JSON object and nothing else. "
    "Do not wrap it in markdown. Do not use ```json code fences. Do not include "
    "any commentary, explanation, or text before or after the JSON object. Use "
    "double quotes for every key and string value. Use null where the schema "
    "allows null. Do not use trailing commas."
)


def build_user_prompt(payload: dict) -> str:
    return (
        "Evaluate this essay using the schema.\n\n"
        f"University:\n{payload['linked_university_name'] or 'Not linked'}\n\n"
        f"Program:\n{payload['linked_program_name'] or 'Not linked'}\n\n"
        f"Application round:\n{payload['linked_application_round'] or 'Not linked'}\n\n"
        f"Essay type:\n{payload['essay_type']}\n\n"
        f"Verified official prompt:\n{payload['official_prompt_text'] or 'null'}\n\n"
        f"Word limit:\n{payload['word_limit'] if payload['word_limit'] is not None else 'null'}\n\n"
        f"Source confidence:\n{payload['prompt_source_confidence']}\n\n"
        f"Last verified:\n{payload['prompt_last_verified_date'] or 'null'}\n\n"
        f"Cached profile keywords:\n{payload['profile_keywords'] or []}\n\n"
        f"Student essay:\n{payload['essay_text']}\n\n"
        f"{ESSAY_SCORING_JSON_SCHEMA_INSTRUCTIONS}\n\n"
        f"{ESSAY_SCORING_JSON_OUTPUT_RULES}"
    )


def _validate_range(value, *, lo: int, hi: int, field: str, allow_null: bool = False):
    if value is None:
        if allow_null:
            return None
        raise EssayScoringValidationError(f"{field} must not be null.")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise EssayScoringValidationError(f"{field} must be numeric.")
    rounded = int(round(value))
    if rounded < lo or rounded > hi:
        raise EssayScoringValidationError(f"{field} out of range: {rounded}")
    return rounded


def _validate_choice(value, *, choices: set[str], field: str) -> str:
    if value not in choices:
        raise EssayScoringValidationError(f"{field} has invalid value: {value!r}")
    return value


def _contains_forbidden_phrase(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in FORBIDDEN_PHRASES)


def _validate_string_list(raw, *, field: str) -> list[str]:
    if not isinstance(raw, list):
        raise EssayScoringValidationError(f"{field} must be a list.")
    cleaned = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise EssayScoringValidationError(f"{field} must contain non-empty strings.")
        if _contains_forbidden_phrase(item):
            raise EssayScoringValidationError(f"{field} used forbidden admissions-outcome wording.")
        cleaned.append(item.strip())
    return cleaned


def _validate_suggestions(raw, *, essay_text: str) -> list[str]:
    if not isinstance(raw, list):
        raise EssayScoringValidationError("approximate_suggestions must be a list.")
    if len(raw) > MAX_SUGGESTIONS:
        raise EssayScoringValidationError("approximate_suggestions exceeds the max item count.")
    normalized_essay = " ".join(essay_text.split()).lower()
    cleaned = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise EssayScoringValidationError("approximate_suggestions must contain non-empty strings.")
        text = item.strip()
        words = text.split()
        if len(words) > MAX_SUGGESTION_WORDS:
            raise EssayScoringValidationError("A suggestion exceeds the 20-word limit.")
        if _contains_forbidden_phrase(text):
            raise EssayScoringValidationError("A suggestion used forbidden admissions-outcome wording.")
        normalized_suggestion = " ".join(words).lower()
        if len(normalized_suggestion) >= MIN_VERBATIM_MATCH_LEN and normalized_suggestion in normalized_essay:
            raise EssayScoringValidationError("A suggestion reuses essay text verbatim.")
        cleaned.append(text)
    return cleaned


def validate_and_normalize_output(raw: dict, *, payload: dict) -> dict:
    """Strictly validate the AI's JSON, then replace anything unsafe to trust
    (word count/status, disclaimers, school/program alignment gating) with our
    own ground truth. Raises EssayScoringValidationError on any violation.
    """

    if not isinstance(raw, dict):
        raise EssayScoringValidationError("AI output was not a JSON object.")
    extra_keys = set(raw) - ALLOWED_TOP_LEVEL_KEYS
    if extra_keys:
        if extra_keys & DISALLOWED_GENERATION_KEYS:
            raise EssayScoringValidationError("AI output attempted to include rewritten essay text.")
        raise EssayScoringValidationError(f"AI output had unexpected keys: {sorted(extra_keys)}")

    overall = _validate_range(raw.get("overall_essay_readiness"), lo=1, hi=100, field="overall_essay_readiness")
    confidence = _validate_choice(raw.get("confidence"), choices={"low", "medium", "high"}, field="confidence")

    subscores = raw.get("subscores")
    if not isinstance(subscores, dict):
        raise EssayScoringValidationError("subscores must be an object.")
    extra_subscore_keys = set(subscores) - ALLOWED_SUBSCORE_KEYS
    if extra_subscore_keys:
        raise EssayScoringValidationError(f"subscores had unexpected keys: {sorted(extra_subscore_keys)}")

    prompt_fit = _validate_range(subscores.get("prompt_fit"), lo=0, hi=25, field="prompt_fit")
    structure = _validate_range(subscores.get("structure"), lo=0, hi=20, field="structure")
    specificity_evidence = _validate_range(
        subscores.get("specificity_evidence"), lo=0, hi=20, field="specificity_evidence"
    )
    authenticity = _validate_range(subscores.get("authenticity"), lo=0, hi=15, field="authenticity")
    language_clarity = _validate_range(subscores.get("language_clarity"), lo=0, hi=10, field="language_clarity")
    word_limit_discipline = _validate_range(
        subscores.get("word_limit_discipline"),
        lo=0,
        hi=5,
        field="word_limit_discipline",
        allow_null=payload["word_limit"] is None,
    )
    school_program_alignment = _validate_range(
        subscores.get("school_program_alignment"),
        lo=0,
        hi=5,
        field="school_program_alignment",
        allow_null=True,
    )
    if not payload["verified_context_used"]:
        # Never let the AI self-certify verification -- only our own backend
        # data (prompt_verification_status) may unlock this subscore.
        school_program_alignment = None

    ai_paraphrase_style_signal = _validate_choice(
        raw.get("ai_paraphrase_style_signal"),
        choices={"low", "medium", "high", "inconclusive"},
        field="ai_paraphrase_style_signal",
    )
    generic_language_signal = _validate_choice(
        raw.get("generic_language_signal"), choices={"low", "medium", "high"}, field="generic_language_signal"
    )
    unsupported_claims_signal = _validate_choice(
        raw.get("unsupported_claims_signal"),
        choices={"low", "medium", "high", "inconclusive"},
        field="unsupported_claims_signal",
    )

    strength_flags = _validate_string_list(raw.get("strength_flags", []), field="strength_flags")
    risk_flags = _validate_string_list(raw.get("risk_flags", []), field="risk_flags")
    source_warnings = _validate_string_list(raw.get("source_warnings", []), field="source_warnings")
    approximate_suggestions = _validate_suggestions(
        raw.get("approximate_suggestions", []), essay_text=payload["essay_text"]
    )

    if not payload["verified_context_used"]:
        warning = "School-specific prompt data is not verified."
        if warning not in source_warnings:
            source_warnings = [*source_warnings, warning]

    word_count = payload["word_count"]
    word_limit_status = _compute_word_limit_status(word_count, payload["word_limit"])

    return {
        "overall_essay_readiness": overall,
        "confidence": confidence,
        "verified_context_used": payload["verified_context_used"],
        "prompt_fit": prompt_fit,
        "structure": structure,
        "specificity_evidence": specificity_evidence,
        "authenticity": authenticity,
        "language_clarity": language_clarity,
        "word_limit_discipline": word_limit_discipline,
        "school_program_alignment": school_program_alignment,
        "word_count": word_count,
        "word_limit_status": word_limit_status,
        "ai_paraphrase_style_signal": ai_paraphrase_style_signal,
        "generic_language_signal": generic_language_signal,
        "unsupported_claims_signal": unsupported_claims_signal,
        "strength_flags": strength_flags,
        "risk_flags": risk_flags,
        "approximate_suggestions": approximate_suggestions,
        "source_warnings": source_warnings,
        "disclaimers": list(REQUIRED_DISCLAIMERS),
    }


@dataclass
class QuotaStatus:
    window: str  # "day" | "month"
    limit: int
    used: int
    remaining: int
    next_available_at: datetime | None


def _quota_window_and_limit(user) -> tuple[str, int]:
    role = getattr(user, "role", None)
    if role is not None and str(role) == "admin":
        # Admin/demo accounts get the highest finite tier, never unlimited.
        return "month", settings.AI_ESSAY_PRO_MONTHLY_LIMIT

    subscription, _ = Subscription.objects.get_or_create(user=user, defaults={"plan": Plan.FREE})
    plan = subscription.plan
    if plan == Plan.FREE:
        return "day", settings.AI_ESSAY_DAILY_FREE_LIMIT
    if plan == Plan.STARTER:
        return "month", settings.AI_ESSAY_BASIC_MONTHLY_LIMIT
    if plan == Plan.GROWTH:
        return "month", settings.AI_ESSAY_PREMIUM_MONTHLY_LIMIT
    return "month", settings.AI_ESSAY_PRO_MONTHLY_LIMIT  # Plan.PREMIUM ~ "Pro" tier


def get_quota_status(user) -> QuotaStatus:
    window, limit = _quota_window_and_limit(user)
    now = timezone.now()
    if window == "day":
        window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        reset_at = window_start + timedelta(days=1)
    else:
        window_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        reset_at = (
            window_start.replace(year=window_start.year + 1, month=1)
            if window_start.month == 12
            else window_start.replace(month=window_start.month + 1)
        )
    used = AIEssayScoreReport.objects.filter(user=user, created_at__gte=window_start).count()
    remaining = max(0, limit - used)
    return QuotaStatus(
        window=window,
        limit=limit,
        used=used,
        remaining=remaining,
        next_available_at=None if remaining > 0 else reset_at,
    )


def score_essay(essay: EssayWorkspace, *, user) -> dict:
    """Returns a dict with `reason`, `cached`, `report` (model instance or
    None), `quota_remaining`, and `next_available_at`. Never raises for
    expected failure paths (missing text, quota, AI unavailable, invalid
    output) -- those are all represented as a `reason` string so the view can
    respond safely without leaking internals.
    """

    if essay.user_id != user.id:
        raise PermissionError("You can only score your own essay.")

    draft_text = (essay.draft_text or "").strip()
    if not draft_text:
        return {
            "reason": "missing_essay_text",
            "cached": False,
            "report": None,
            "quota_remaining": None,
            "next_available_at": None,
        }

    payload = build_scoring_payload(essay)
    model_name = settings.AI_ESSAY_MODEL
    essay_text_hash = compute_essay_text_hash(draft_text)
    context_hash = compute_context_hash(payload, model_name=model_name)

    cached_report = (
        AIEssayScoreReport.objects.filter(
            essay=essay, essay_text_hash=essay_text_hash, context_hash=context_hash
        )
        .order_by("-created_at")
        .first()
    )
    if cached_report is not None:
        quota = get_quota_status(user)
        return {
            "reason": "cached",
            "cached": True,
            "report": cached_report,
            "quota_remaining": quota.remaining,
            "next_available_at": None,
        }

    if not settings.AI_ESSAY_SCORING_ENABLED:
        return {
            "reason": "ai_unavailable",
            "cached": False,
            "report": None,
            "quota_remaining": None,
            "next_available_at": None,
        }

    quota = get_quota_status(user)
    if quota.remaining <= 0:
        return {
            "reason": "quota_exceeded",
            "cached": False,
            "report": None,
            "quota_remaining": 0,
            "next_available_at": quota.next_available_at,
        }

    client = GeminiEssayScoringClient()
    user_prompt = build_user_prompt(payload)
    try:
        raw_output = client.score_essay(system_prompt=ESSAY_SCORING_SYSTEM_PROMPT, user_prompt=user_prompt)
    except AIProviderError as error:
        # Never log the essay text, the prompt, or the API key -- only enough
        # structured, sanitized detail (status code, wrapped-exception class,
        # Gemini's own error code/status, message, and truncated provider
        # error body) to diagnose a production failure from Render logs.
        logger.warning(
            "Gemini provider error feature=essay_scoring model=%s status=%s exception=%s cause=%s "
            "provider_code=%s provider_status=%s message=\"%s\" error=\"%s\"",
            model_name,
            getattr(error, "status_code", None),
            type(error).__name__,
            getattr(error, "cause_class", None),
            getattr(error, "provider_code", None),
            getattr(error, "provider_status", None),
            str(error)[:1000],
            getattr(error, "error_body", "")[:1000],
        )
        return {
            "reason": "ai_unavailable",
            "cached": False,
            "report": None,
            "quota_remaining": quota.remaining,
            "next_available_at": None,
        }

    try:
        normalized = validate_and_normalize_output(raw_output, payload=payload)
    except EssayScoringValidationError as error:
        # `error` only ever names a schema field/key or an out-of-range number
        # (see the _validate_* helpers above) -- never raw essay/profile text.
        # Still truncated defensively since one branch echoes back whatever
        # value Gemini put in an enum field.
        logger.warning(
            "Gemini schema validation error feature=essay_scoring model=%s essay_id=%s message=\"%s\"",
            model_name,
            essay.id,
            str(error)[:300],
        )
        return {
            "reason": "validation_failed",
            "cached": False,
            "report": None,
            "quota_remaining": quota.remaining,
            "next_available_at": None,
        }

    application = essay.application
    university = essay.university or (application.university if application else None)
    program = application.target_program if application else None

    report = AIEssayScoreReport.objects.create(
        user=user,
        essay=essay,
        application=application,
        university=university,
        program=program,
        essay_text_hash=essay_text_hash,
        context_hash=context_hash,
        rubric_version=RUBRIC_VERSION,
        model_provider="gemini",
        model_name=model_name,
        raw_output_json=raw_output,
        **normalized,
    )

    UsageLog.objects.create(
        user=user,
        kind=UsageLog.Kind.ESSAY_REVIEW,
        metadata={"model_name": model_name, "cached": False, "essay_id": essay.id},
    )

    quota_after = get_quota_status(user)
    return {
        "reason": "scored",
        "cached": False,
        "report": report,
        "quota_remaining": quota_after.remaining,
        "next_available_at": None,
    }
