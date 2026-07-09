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
    categories: list[dict[str, object]]
    strengths: list[str]
    improvements: list[str]
    reasons: list[str]
    next_actions: list[str]
    cap_reason: str
    comparison_status: str
    compared_universities: list[str]
    official_sources: list[dict[str, str]]
    # PROTOCOL-008 PART 6: the same 6 categories, enriched with the exact
    # per-section shape the readiness widget needs (main_strength/main_risk/
    # missing_items/next_action) plus any section-specific cap reasons.
    # Additive -- `categories` above is untouched for existing callers.
    sections: list[dict[str, object]]


LEVELS = {
    1: "incomplete",
    2: "developing",
    3: "solid",
    4: "strong",
    5: "excellent",
}

READINESS_CATEGORY_KEYS = (
    "academic_readiness",
    "testing_readiness",
    "activities_leadership",
    "honors_competitions",
    "research_portfolio",
    "application_execution",
)


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


CAP_EVIDENCE_KEYS = (
    "activities",
    "honors",
    "research",
    "portfolio",
    "recommenders",
    "essays",
)


def _rounded_mean(values: list[int]) -> int:
    return max(1, min(5, round(mean(values))))


def _build_readiness_categories(components: dict[str, int]) -> list[dict[str, object]]:
    category_inputs = {
        "academic_readiness": ("profile", "academics", "timeline"),
        "testing_readiness": ("exams",),
        "activities_leadership": ("activities", "leadership", "volunteering"),
        "honors_competitions": ("honors", "olympiads"),
        "research_portfolio": ("research", "portfolio"),
        "application_execution": ("essays", "recommenders", "timeline"),
    }
    categories = []
    for key in READINESS_CATEGORY_KEYS:
        source_keys = category_inputs[key]
        scores = [components[source_key] for source_key in source_keys]
        score = _rounded_mean(scores)
        missing_sources = [
            source_key for source_key in source_keys if components[source_key] <= 1
        ]
        categories.append(
            {
                "key": key,
                "score": score,
                "source_keys": list(source_keys),
                "missing_sources": missing_sources,
                "status": LEVELS[score],
            }
        )
    return categories


def _readiness_cap(components: dict[str, int], completion_percentage: int) -> tuple[int, str]:
    missing_evidence = [key for key in CAP_EVIDENCE_KEYS if components[key] <= 1]
    if completion_percentage < 50:
        return 2, "foundation_incomplete"
    if len(missing_evidence) >= 4:
        return 2, "evidence_incomplete"
    if len(missing_evidence) >= 3:
        return 3, "evidence_limited"
    return 5, ""


def _readiness_reasons(
    categories: list[dict[str, object]],
    components: dict[str, int],
    cap_reason: str,
) -> list[str]:
    reasons: list[str] = []
    if cap_reason:
        reasons.append(cap_reason)
    if components["academics"] >= 4 and cap_reason in {"evidence_incomplete", "evidence_limited"}:
        reasons.append("academically_promising_evidence_incomplete")
    if components["exams"] <= 2:
        reasons.append("testing_data_limited")
    if components["essays"] <= 2 or components["recommenders"] <= 2:
        reasons.append("application_execution_limited")
    if not reasons:
        strongest = max(categories, key=lambda item: int(item["score"]))
        reasons.append(f"{strongest['key']}_strongest")
    return reasons[:4]


def _readiness_next_actions(categories: list[dict[str, object]]) -> list[str]:
    sorted_categories = sorted(categories, key=lambda item: int(item["score"]))
    return [str(item["key"]) for item in sorted_categories[:3]]


def _build_readiness_sections(
    categories: list[dict[str, object]], components: dict[str, int]
) -> list[dict[str, object]]:
    """PROTOCOL-008 PART 6's exact per-section shape: main_strength/
    main_risk/missing_items/next_action, derived from the same sub-component
    scores `categories` already summarizes -- never a second, independently
    invented score.
    """

    sections = []
    for category in categories:
        source_keys = [str(key) for key in category["source_keys"]]
        sub_scores = {key: components[key] for key in source_keys}
        strongest = max(sub_scores, key=lambda key: sub_scores[key]) if sub_scores else None
        weakest = min(sub_scores, key=lambda key: sub_scores[key]) if sub_scores else None
        missing_items = [key for key in source_keys if components[key] <= 1]
        sections.append(
            {
                "key": category["key"],
                "score": category["score"],
                "status": category["status"],
                "main_strength": strongest if strongest and sub_scores[strongest] >= 3 else None,
                "main_risk": weakest if weakest and sub_scores[weakest] <= 2 else None,
                "missing_items": missing_items,
                "next_action": f"improve_{missing_items[0]}" if missing_items else f"maintain_{category['key']}",
                "cap_reasons": category.get("cap_reasons", []),
            }
        )
    return sections


# Below this acceptance rate, a target university is treated as "very
# selective" for the honors/competitions cap rule -- a real, verified
# statistic already on the University record, never invented.
VERY_SELECTIVE_ACCEPTANCE_RATE = 15


def _targets_very_selective(profile: StudentProfile) -> bool:
    targets = [value.strip() for value in profile.target_universities if value.strip()]
    if not targets:
        return False
    return University.objects.filter(
        is_published=True, name__in=targets, acceptance_rate__lt=VERY_SELECTIVE_ACCEPTANCE_RATE
    ).exists()


def _has_no_evidence(profile: StudentProfile, related_name: str) -> bool:
    """Whether the student has zero real evidence rows for this category --
    checked directly against the evidence tables, not the 1-5 component
    score, since several `_score_*` helpers deliberately floor at 2 via a
    legacy self-reported fallback and would never satisfy a `<= 1` check.
    """

    return getattr(profile.user, related_name).count() == 0


def _apply_section_caps(
    profile: StudentProfile,
    categories: list[dict[str, object]],
    *,
    very_selective: bool,
    deterministic_comparisons: dict | None,
) -> list[dict[str, object]]:
    """PROTOCOL-008 PART 6's exact section-level caps -- applied on top of
    the already-computed category scores so one strong sub-score never
    inflates a section where required evidence is missing.
    """

    by_key = {str(category["key"]): category for category in categories}
    for category in categories:
        category.setdefault("cap_reasons", [])

    def _cap(key: str, maximum: int, reason: str) -> None:
        # Record `reason` whenever the triggering condition is true, even if
        # the score was already at or below `maximum` for some other cause --
        # the reason still explains *why* the section can't score higher,
        # which is exactly what a caller needs to show the student.
        category = by_key.get(key)
        if category is None:
            return
        category["cap_reasons"] = [*category["cap_reasons"], reason]
        if int(category["score"]) > maximum:
            category["score"] = maximum
            category["status"] = LEVELS[maximum]

    no_essays = _has_no_evidence(profile, "profile_essays") and profile.essay_status != StudentProfile.EssayStatus.YES
    no_recommenders = _has_no_evidence(profile, "profile_recommenders")
    no_activities = _has_no_evidence(profile, "profile_activities") and not any(
        isinstance(value, list) and value for value in (profile.activities or {}).values()
    )
    no_research = _has_no_evidence(profile, "profile_research_projects")
    no_portfolio = _has_no_evidence(profile, "profile_portfolio_projects")
    no_honors = _has_no_evidence(profile, "profile_honors")
    no_olympiads = _has_no_evidence(profile, "profile_olympiads")

    if no_essays:
        _cap("application_execution", 3, "essays_missing")
    if no_recommenders:
        _cap("application_execution", 3, "recommendation_letters_missing")
    if no_activities:
        for key in READINESS_CATEGORY_KEYS:
            _cap(key, 3, "activities_missing")
    if no_research and no_portfolio:
        _cap("research_portfolio", 2, "research_and_portfolio_missing")
    if very_selective and no_honors and no_olympiads:
        _cap("honors_competitions", 2, "honors_missing_for_selective_target")
    if deterministic_comparisons:
        sat_status = deterministic_comparisons.get("sat", {}).get("status")
        ielts_status = deterministic_comparisons.get("ielts", {}).get("status")
        if sat_status == "below_benchmark" or ielts_status == "below_benchmark":
            _cap("testing_readiness", 3, "testing_below_benchmark")
    return categories


def calculate_application_readiness(
    profile: StudentProfile,
    preferences: UserPreference,
    *,
    deterministic_comparisons: dict | None = None,
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

    categories = _build_readiness_categories(components)
    categories = _apply_section_caps(
        profile,
        categories,
        very_selective=_targets_very_selective(profile),
        deterministic_comparisons=deterministic_comparisons,
    )
    uncapped_stars = _rounded_mean([int(category["score"]) for category in categories])
    max_score, cap_reason = _readiness_cap(components, completion.percentage)
    if components["activities"] <= 1:
        max_score = min(max_score, 3) if max_score else 3
        cap_reason = cap_reason or "activities_missing"
    stars = min(uncapped_stars, max_score)
    strengths = [
        str(category["key"]) for category in categories if int(category["score"]) >= 4
    ]
    improvements = [
        str(category["key"]) for category in categories if int(category["score"]) <= 2
    ]
    reasons = _readiness_reasons(categories, components, cap_reason)
    next_actions = _readiness_next_actions(categories)
    sections = _build_readiness_sections(categories, components)
    return ApplicationReadiness(
        stars=stars,
        level=LEVELS[stars],
        score_components={str(category["key"]): int(category["score"]) for category in categories},
        categories=categories,
        strengths=strengths,
        improvements=improvements,
        reasons=reasons,
        next_actions=next_actions,
        cap_reason=cap_reason,
        comparison_status="published_ranges" if published_scores else "official_data_needed",
        compared_universities=compared_universities,
        official_sources=sources[:8],
        sections=sections,
    )
