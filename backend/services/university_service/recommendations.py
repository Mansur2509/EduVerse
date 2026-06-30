from __future__ import annotations

from .models import University
from .services import calculate_university_fit

REGION_COUNTRIES = {
    "us": {"united states", "usa", "u.s.", "u.s.a."},
    "canada": {"canada"},
    "uk": {"united kingdom", "uk", "england", "scotland", "wales"},
    "asia": {
        "singapore",
        "japan",
        "south korea",
        "hong kong",
        "china",
        "kazakhstan",
        "uzbekistan",
    },
}

GLOBAL_MARKERS = {"global", "worldwide", "anywhere", "all", "international"}


def _normalized_targets(profile) -> set[str]:
    return {str(value).strip().lower() for value in profile.target_countries if str(value).strip()}


def _country_matches_preference(country: str, targets: set[str]) -> bool:
    if not targets or targets & GLOBAL_MARKERS:
        return True
    normalized_country = country.strip().lower()
    if normalized_country in targets:
        return True
    for target in targets:
        countries = REGION_COUNTRIES.get(target, set())
        if normalized_country in countries:
            return True
    return False


def _matching_programs(profile, university: University) -> list[str]:
    majors = [
        str(value).strip().lower()
        for value in (profile.intended_majors or ([profile.intended_major] if profile.intended_major else []))
        if str(value).strip()
    ]
    if not majors:
        return []
    matches = []
    for program in university.programs.all():
        name = program.name.lower()
        if any(major in name or name in major for major in majors):
            matches.append(program.name)
    return matches[:5]


def _application_round(university: University) -> str:
    raw = f"{university.deadlines_text} {university.application_requirements}".lower()
    for label in ("rea", "ed ii", "ed", "ea", "rd", "ucas", "rolling", "international"):
        if label in raw:
            return label.upper()
    return "unknown"


def calculate_university_recommendations(profile, preferences=None, *, limit: int = 25) -> dict:
    targets = _normalized_targets(profile)
    queryset = (
        University.objects.filter(is_published=True, is_demo=False)
        .prefetch_related("programs", "scholarships", "data_sources", "field_verifications")
        .order_by("name")
    )
    candidates = [
        university for university in queryset if _country_matches_preference(university.country, targets)
    ]

    recommendations = []
    missing_preferences = []
    if not targets:
        missing_preferences.append("preferred_countries")
    if not (profile.intended_majors or profile.intended_major):
        missing_preferences.append("intended_major")

    for university in candidates:
        fit = calculate_university_fit(profile, university)
        programs = _matching_programs(profile, university)
        cost_context = fit["cost_context"]
        aid_note = (
            "Scholarship or aid signal is available."
            if university.scholarship_available or university.financial_aid_url or university.scholarships.all()
            else "Aid data is not verified yet."
        )
        risk = fit["risks"][0] if fit["risks"] else (
            fit["missing_data"][0] if fit["missing_data"] else "verify_official_sources"
        )
        next_action = fit["next_actions"][0] if fit["next_actions"] else "review_program_requirements"
        recommendations.append(
            {
                "university": {
                    "id": university.id,
                    "name": university.name,
                    "slug": university.slug,
                    "country": university.country,
                    "city": university.city,
                },
                "category": fit["category"],
                "fit_score": fit["fit_score"],
                "confidence": fit["confidence"],
                "recommended_programs": programs,
                "application_round": _application_round(university),
                "estimated_usd_cost": cost_context["total_cost_usd_amount"]
                or cost_context["tuition_usd_amount"],
                "aid_scholarship_note": aid_note,
                "deadline": university.application_deadline,
                "why_recommended": (
                    "Matches your preferred country/region and has a computed fit estimate."
                ),
                "key_risk": risk,
                "next_action": next_action,
                "data_confidence": fit["confidence"],
                "conditional_notes": fit["conditional_notes"],
            }
        )

    recommendations.sort(
        key=lambda item: (
            item["category"] == "safety",
            item["category"] == "target",
            item["fit_score"],
        ),
        reverse=True,
    )
    return {
        "recommendations": recommendations[:limit],
        "missing_preferences": missing_preferences,
        "disclaimer": fit["disclaimer"] if recommendations else (
            "This is a fit estimate based on available profile and university data. "
            "It is not an admissions prediction or guarantee."
        ),
    }
