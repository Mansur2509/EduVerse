import re
from dataclasses import dataclass
from datetime import date
from statistics import mean

from services.university_service.models import University

from .academic_normalization import normalize_profile_academics
from .models import StudentProfile, UserPreference
from .services import calculate_profile_completion


@dataclass(frozen=True)
class ApplicationReadiness:
    stars: int
    level: str
    score_components: dict[str, int]
    strengths: list[str]
    improvements: list[str]
    comparison_status: str
    compared_universities: list[str]
    official_sources: list[dict[str, str]]


LEVELS = {
    1: "foundation",
    2: "developing",
    3: "competitive",
    4: "strong",
    5: "outstanding",
}


def _number(value):
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _score_gpa(profile):
    normalization = normalize_profile_academics(profile)
    if normalization.normalized_gpa_4 is None:
        return 1
    gpa = float(normalization.normalized_gpa_4)
    if gpa >= 3.8:
        return 5
    if gpa >= 3.5:
        return 4
    if gpa >= 3.1:
        return 3
    if gpa >= 2.7:
        return 2
    return 1


def _score_exams(profile):
    scores = profile.test_scores
    values = []
    sat = _number(scores.get("sat"))
    if sat is not None:
        values.append(5 if sat >= 1500 else 4 if sat >= 1400 else 3 if sat >= 1250 else 2)
    ielts = _number(scores.get("ielts"))
    if ielts is not None:
        values.append(5 if ielts >= 8 else 4 if ielts >= 7 else 3 if ielts >= 6 else 2)
    toefl = _number(scores.get("toefl"))
    if toefl is not None:
        values.append(5 if toefl >= 110 else 4 if toefl >= 100 else 3 if toefl >= 85 else 2)
    act = _number(scores.get("act"))
    if act is not None:
        values.append(5 if act >= 34 else 4 if act >= 31 else 3 if act >= 27 else 2)
    ap = scores.get("ap")
    if isinstance(ap, list) and ap:
        values.append(min(5, 2 + len(ap)))
    if not values:
        return 2 if profile.exam_plans.get("planned") else 1
    return round(mean(values))


def _score_activities(profile):
    activity_counts = [
        len(value)
        for value in profile.activities.values()
        if isinstance(value, list) and value
    ]
    depth = len(activity_counts)
    evidence = sum(activity_counts)
    if depth >= 5 and evidence >= 8:
        return 5
    if depth >= 4 and evidence >= 5:
        return 4
    if depth >= 2 and evidence >= 3:
        return 3
    if depth >= 1:
        return 2
    return 1


def _score_essays(profile):
    stage = profile.essay_stage.lower()
    if profile.essay_status != StudentProfile.EssayStatus.YES:
        return 2
    if any(word in stage for word in ("final", "polish", "complete")):
        return 5
    if any(word in stage for word in ("revision", "second", "review")):
        return 4
    if any(word in stage for word in ("draft", "first")):
        return 3
    return 2


def _score_timeline(profile):
    if profile.expected_graduation_year is None:
        return 1
    years_left = profile.expected_graduation_year - date.today().year
    if years_left >= 2:
        return 5
    if years_left == 1:
        return 4
    if years_left == 0:
        return 3
    return 2


def _published_comparison(profile):
    targets = [value.strip() for value in profile.target_universities if value.strip()]
    if not targets:
        return [], [], []

    universities = (
        University.objects.filter(is_published=True, name__in=targets)
        .prefetch_related("requirements", "data_sources")
        .order_by("name")
    )
    comparisons = []
    sources = []
    names = []
    normalization = normalize_profile_academics(profile)
    profile_values = {
        "gpa": float(normalization.normalized_gpa_4)
        if normalization.normalized_gpa_4 is not None
        else None,
        "sat": _number(profile.test_scores.get("sat")),
        "ielts": _number(profile.test_scores.get("ielts")),
        "toefl": _number(profile.test_scores.get("toefl")),
        "act": _number(profile.test_scores.get("act")),
    }
    for university in universities:
        names.append(university.name)
        for source in university.data_sources.filter(is_official=True):
            sources.append(
                {
                    "title": source.source_title,
                    "url": source.source_url,
                    "university": university.name,
                }
            )
        for requirement in university.requirements.all():
            key = requirement.requirement_type.strip().lower()
            profile_value = next(
                (value for name, value in profile_values.items() if name in key and value is not None),
                None,
            )
            numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", requirement.value)]
            if profile_value is None or not numbers:
                continue
            lower = min(numbers)
            upper = max(numbers)
            comparisons.append(
                5
                if profile_value >= upper
                else 4
                if profile_value >= lower
                else 2
            )
    return comparisons, names, sources


def calculate_application_readiness(
    profile: StudentProfile,
    preferences: UserPreference,
) -> ApplicationReadiness:
    completion = calculate_profile_completion(profile, preferences)
    components = {
        "profile": max(1, min(5, round(completion.percentage / 20))),
        "academics": _score_gpa(profile),
        "exams": _score_exams(profile),
        "activities": _score_activities(profile),
        "essays": _score_essays(profile),
        "timeline": _score_timeline(profile),
    }
    published_scores, compared_universities, sources = _published_comparison(profile)
    if published_scores:
        components["published_ranges"] = round(mean(published_scores))

    stars = max(1, min(5, round(mean(components.values()))))
    strengths = [key for key, value in components.items() if value >= 4]
    improvements = [key for key, value in components.items() if value <= 2]
    return ApplicationReadiness(
        stars=stars,
        level=LEVELS[stars],
        score_components=components,
        strengths=strengths,
        improvements=improvements,
        comparison_status="published_ranges" if published_scores else "official_data_needed",
        compared_universities=compared_universities,
        official_sources=sources[:8],
    )
