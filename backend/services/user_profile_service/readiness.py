import re
from dataclasses import dataclass
from datetime import date
from statistics import mean

from services.university_service.models import University

from .academic_normalization import normalize_profile_academics
from .models import EssayDraft, Recommender, StudentProfile, UserPreference
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
    # Structured Activity entries are richer evidence than the legacy
    # free-text lists (onboarding's quick string tags); weight each one like
    # roughly two legacy items so a profile that has moved to the structured
    # form is not scored as if it were empty.
    structured_count = profile.user.profile_activities.count()
    if structured_count:
        depth += 1
        evidence += structured_count * 2
    if depth >= 5 and evidence >= 8:
        return 5
    if depth >= 4 and evidence >= 5:
        return 4
    if depth >= 2 and evidence >= 3:
        return 3
    if depth >= 1:
        return 2
    return 1


NOTABLE_LEVELS = {"international", "national", "regional"}
LEADERSHIP_ROLE_KEYWORDS = (
    "president",
    "captain",
    "founder",
    "chair",
    "head",
    "lead",
    "director",
    "vice president",
    "vp",
)


def _score_entries(entries: list, *, level_field: str | None = None) -> int:
    """Generic 1-5 evidence-based score for a list of structured profile
    entries. Rewards having multiple entries and at least one at a notable
    scale/level. This is a depth-of-evidence signal only -- never an
    admissions-outcome claim.
    """

    count = len(entries)
    if count == 0:
        return 1
    has_notable = bool(level_field) and any(
        str(getattr(entry, level_field, "") or "").strip().lower() in NOTABLE_LEVELS
        for entry in entries
    )
    if count >= 3 and has_notable:
        return 5
    if count >= 3 or (count >= 1 and has_notable):
        return 4
    if count >= 2:
        return 3
    return 2


def _score_honors(profile):
    return _score_entries(list(profile.user.profile_honors.all()), level_field="level")


def _score_olympiads(profile):
    return _score_entries(list(profile.user.profile_olympiads.all()), level_field="level")


def _score_sports(profile):
    return _score_entries(list(profile.user.profile_sports.all()), level_field="level")


def _score_volunteering(profile):
    return _score_entries(list(profile.user.profile_volunteering.all()), level_field="scale")


def _score_research(profile):
    projects = list(profile.user.profile_research_projects.all())
    count = len(projects)
    if count == 0:
        return 1
    has_notable = any(
        project.current_stage == project.Stage.PUBLISHED
        or str(project.countries_region or "").strip()
        for project in projects
    )
    if count >= 2 and has_notable:
        return 5
    if count >= 1 and has_notable:
        return 4
    if count >= 2:
        return 3
    return 2


def _score_portfolio(profile):
    projects = list(profile.user.profile_portfolio_projects.all())
    count = len(projects)
    if count == 0:
        return 1
    has_link = any(str(project.link or "").strip() for project in projects)
    if count >= 2 and has_link:
        return 5
    if count >= 1 and has_link:
        return 4
    if count >= 2:
        return 3
    return 2


def _score_leadership(profile):
    activities = list(profile.user.profile_activities.all())
    leadership_entries = [
        activity
        for activity in activities
        if "leadership" in str(activity.category or "").strip().lower()
        or any(
            keyword in str(activity.role or "").strip().lower()
            for keyword in LEADERSHIP_ROLE_KEYWORDS
        )
    ]
    return _score_entries(leadership_entries, level_field="scale")


def _score_recommenders(profile):
    recommenders = list(profile.user.profile_recommenders.all())
    if not recommenders:
        return 1
    advanced = sum(
        1
        for recommender in recommenders
        if recommender.status in {Recommender.Status.CONFIRMED, Recommender.Status.SUBMITTED}
    )
    if advanced >= 2:
        return 5
    if advanced >= 1:
        return 4
    if len(recommenders) >= 2:
        return 3
    return 2


def _score_essays(profile):
    essays = list(profile.user.profile_essays.all())
    if essays:
        advanced = sum(
            1
            for essay in essays
            if essay.status in {EssayDraft.Status.REVIEWED, EssayDraft.Status.SUBMITTED}
        )
        if advanced >= 2:
            return 5
        if advanced >= 1:
            return 4
        if len(essays) >= 2:
            return 3
        return 2

    # No structured essay drafts yet -- fall back to the coarse self-reported
    # onboarding fields so existing profiles are not scored as empty.
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


#  Niche achievement categories that many students genuinely do not have
# (not every strong applicant has olympiad results or a research project).
# Their absence must never be averaged in as a weakness -- it only appears
# under `improvements` as an optional next step, and only ever raises the
# overall star average when the student actually has entries.
ENRICHMENT_COMPONENTS = (
    "leadership",
    "honors",
    "olympiads",
    "sports",
    "research",
    "portfolio",
    "volunteering",
    "recommenders",
)


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
        "leadership": _score_leadership(profile),
        "honors": _score_honors(profile),
        "olympiads": _score_olympiads(profile),
        "sports": _score_sports(profile),
        "research": _score_research(profile),
        "portfolio": _score_portfolio(profile),
        "volunteering": _score_volunteering(profile),
        "recommenders": _score_recommenders(profile),
    }
    published_scores, compared_universities, sources = _published_comparison(profile)
    if published_scores:
        components["published_ranges"] = round(mean(published_scores))

    stars_inputs = [
        value
        for key, value in components.items()
        if key not in ENRICHMENT_COMPONENTS or value > 1
    ]
    stars = max(1, min(5, round(mean(stars_inputs))))
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
