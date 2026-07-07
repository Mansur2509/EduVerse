"""Purpose-scoped internal context retrieval for backend workflows.

This module does NOT call any AI provider. It only assembles a small,
purpose-relevant slice of a university's guidance/context layer (and, for
`profile_improvement`, its public "what evidence they value" notes) so a
future workflow (essay review, fit analysis, recommendation prep, profile
improvement) never has to read the whole `UniversityGuidanceContext` row
blindly. The system-only scoring vector (`UniversitySignalWeights`) is never
included here -- it belongs to `compare_student_vector_to_university_weights`
only, never to a text/prompt context.
"""

from __future__ import annotations

from .models import University, UniversityGuidanceContext

VALID_PURPOSES = (
    "essay_review",
    "why_us_review",
    "fit_analysis",
    "recommendation_prep",
    "profile_improvement",
)

# Which UniversityGuidanceContext fields are relevant for each purpose. Kept
# intentionally narrow per purpose -- a caller building an essay-review
# prompt has no legitimate reason to see `recommendation_letters`, for
# example.
_GUIDANCE_FIELDS_BY_PURPOSE: dict[str, tuple[str, ...]] = {
    "essay_review": (
        "official_admissions_messaging",
        "student_life_page_signals",
        "essay_themes",
        "personality_traits_mentioned",
        "academic_interests_mentioned",
        "institutional_values",
        # Style/theme reference only. Any workflow consuming this must treat
        # it as a pattern to learn from, never text to copy or adapt into the
        # student's own essay -- doing so would be ghostwriting, which is
        # forbidden.
        "sample_admitted_essays",
    ),
    "fit_analysis": (
        "what_they_look_for",
        "preferred_student_profile",
        "who_they_seek",
        "student_traits_mentioned",
        "academic_interests_mentioned",
        "institutional_values",
    ),
    "recommendation_prep": (
        "recommendation_letters",
        "what_they_look_for",
        "student_traits_mentioned",
    ),
    "profile_improvement": (
        "research_leadership_themes",
    ),
}
_GUIDANCE_FIELDS_BY_PURPOSE["why_us_review"] = _GUIDANCE_FIELDS_BY_PURPOSE["essay_review"]

# Public University fields also relevant to `profile_improvement` (what kind
# of evidence this university values in activities/research/portfolio).
_PUBLIC_FIELDS_BY_PURPOSE: dict[str, tuple[str, ...]] = {
    "profile_improvement": (
        "profile_evidence_notes",
        "activities_notes",
        "honors_olympiads_notes",
        "research_experience_notes",
        "portfolio_notes",
    ),
}


def get_university_ai_context(university_id: int, purpose: str) -> dict:
    """Return only the guidance/context fields relevant to `purpose`.

    Never includes `UniversitySignalWeights` (system-only) or any guidance
    field outside the requested purpose's whitelist. Returns an empty
    `fields` dict (not an error) when the university has no guidance context
    row yet -- callers should treat that as "no verified guidance available",
    never invent a substitute.
    """

    if purpose not in VALID_PURPOSES:
        raise ValueError(f"Unknown purpose '{purpose}'. Expected one of: {', '.join(VALID_PURPOSES)}")

    try:
        university = University.objects.get(id=university_id)
    except University.DoesNotExist:
        return {"university_id": university_id, "purpose": purpose, "found": False, "fields": {}}

    fields: dict[str, str] = {}

    for attr in _PUBLIC_FIELDS_BY_PURPOSE.get(purpose, ()):
        value = getattr(university, attr, "")
        if value:
            fields[attr] = value

    try:
        guidance = university.guidance_context
    except UniversityGuidanceContext.DoesNotExist:
        guidance = None

    if guidance is not None:
        for attr in _GUIDANCE_FIELDS_BY_PURPOSE.get(purpose, ()):
            value = getattr(guidance, attr, "")
            if value:
                fields[attr] = value

    return {
        "university_id": university.id,
        "university_name": university.name,
        "purpose": purpose,
        "found": True,
        "fields": fields,
    }
