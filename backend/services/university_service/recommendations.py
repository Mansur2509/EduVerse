from __future__ import annotations

import re
from datetime import date

from services.application_service.models import ApplicationTrackerItem

from .deadline_normalization import normalize_university_deadline
from .major_matching import match_programs_to_profile, subject_ranking_context
from .models import SavedUniversity, University
from .program_display import format_program_display_names
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

# Category quotas for the balanced 20-25 list (PART 8). "competitive" from the
# fit engine folds into "reach" at the recommendation layer -- the underlying
# per-university fit endpoint is untouched, this bucketing is display-only.
CATEGORY_QUOTAS = {
    "dream": 5,
    "reach": 7,
    "target": 8,
    "safety": 6,
}
CATEGORY_ORDER_FOR_LIST = ("dream", "reach", "target", "safety")

CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}

# Program-fit clusters (PART 7). Broad, deliberately conservative keyword
# groups used only to find *related* programs when no exact major match
# exists -- never to invent programs a university does not offer.
PROGRAM_CLUSTERS: dict[str, dict[str, tuple[str, ...]]] = {
    "computer_science_engineering": {
        "major_keywords": (
            "computer science",
            "software",
            "engineering",
            "electrical",
            "mechanical",
            "civil engineering",
            "robotics",
        ),
        "program_keywords": (
            "computer science",
            "software",
            "engineering",
            "electrical",
            "mechanical",
            "civil",
            "robotics",
            "information technology",
        ),
    },
    "data_ai": {
        "major_keywords": ("data science", "artificial intelligence", "machine learning", "data analytics"),
        "program_keywords": ("data science", "artificial intelligence", "machine learning", "analytics", "statistics"),
    },
    "business_finance_economics": {
        "major_keywords": ("business", "finance", "economics", "accounting", "management"),
        "program_keywords": ("business", "finance", "economics", "accounting", "management", "commerce"),
    },
    "politics_law_ir": {
        "major_keywords": ("political science", "law", "international relations", "public policy", "government"),
        "program_keywords": ("political science", "law", "international relations", "public policy", "government"),
    },
    "biology_premed_public_health": {
        "major_keywords": ("biology", "pre-med", "medicine", "public health", "biomedical"),
        "program_keywords": ("biology", "medicine", "public health", "biomedical", "health science"),
    },
    "psychology_neuroscience": {
        "major_keywords": ("psychology", "neuroscience", "cognitive science"),
        "program_keywords": ("psychology", "neuroscience", "cognitive science"),
    },
    "social_sciences": {
        "major_keywords": ("sociology", "anthropology", "social science"),
        "program_keywords": ("sociology", "anthropology", "social science"),
    },
    "humanities": {
        "major_keywords": ("history", "literature", "philosophy", "linguistics", "classics"),
        "program_keywords": ("history", "literature", "philosophy", "linguistics", "classics"),
    },
    "arts_design": {
        "major_keywords": ("art", "design", "fine arts", "architecture", "film", "music"),
        "program_keywords": ("art", "design", "fine arts", "architecture", "film", "music"),
    },
    "education": {
        "major_keywords": ("education", "teaching", "pedagogy"),
        "program_keywords": ("education", "teaching", "pedagogy"),
    },
    "environmental_studies": {
        "major_keywords": ("environmental", "sustainability", "earth science", "climate"),
        "program_keywords": ("environmental", "sustainability", "earth science", "climate"),
    },
}

# Round labels recognized in raw deadline/requirement text. Order matters:
# "ed ii" must be checked before the bare "ed" pattern.
ROUND_PATTERNS = (
    ("REA", r"\brea\b"),
    ("ED II", r"\bed\s*ii\b"),
    ("ED", r"\bed\b"),
    ("EA", r"\bea\b"),
    ("RD", r"\brd\b"),
    ("UCAS", r"\bucas\b"),
    ("ROLLING", r"\brolling\b"),
)


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


def _user_majors(profile) -> list[str]:
    return [
        str(value).strip().lower()
        for value in (profile.intended_majors or ([profile.intended_major] if profile.intended_major else []))
        if str(value).strip()
    ]


def _clusters_for_majors(majors: list[str]) -> list[str]:
    matches = []
    for cluster_name, config in PROGRAM_CLUSTERS.items():
        if any(keyword in major for major in majors for keyword in config["major_keywords"]):
            matches.append(cluster_name)
    return matches


def _match_programs(profile, university: University) -> tuple[list[dict], bool]:
    """Return (recommended_programs, has_any_program_data)."""

    raw_names = [program.name for program in university.programs.all()]
    if not raw_names:
        return [], False

    display_names = format_program_display_names(raw_names)
    majors = _user_majors(profile)
    if not majors:
        return [], True

    exact = [name for name in display_names if any(major in name.lower() or name.lower() in major for major in majors)]
    if exact:
        return (
            [
                {"name": name, "fit_reason_key": "program_exact_match", "match_type": "exact", "confidence": "high"}
                for name in exact[:4]
            ],
            True,
        )

    clusters = _clusters_for_majors(majors)
    if clusters:
        keywords = {
            keyword
            for cluster_name in clusters
            for keyword in PROGRAM_CLUSTERS[cluster_name]["program_keywords"]
        }
        related = [name for name in display_names if any(keyword in name.lower() for keyword in keywords)]
        if related:
            return (
                [
                    {
                        "name": name,
                        "fit_reason_key": "program_related_match",
                        "match_type": "related",
                        "confidence": "medium",
                    }
                    for name in related[:4]
                ],
                True,
            )

    return [], True


def _risk_level_from_score(score: int) -> str:
    if score >= 70:
        return "low"
    if score >= 50:
        return "moderate"
    return "high"


def _has_aid_signal(university: University) -> bool:
    return bool(
        university.scholarship_available or university.financial_aid_url or university.scholarships.all()
    )


def _cost_risk(profile, university: University) -> str:
    has_cost = university.tuition_usd_amount is not None or university.total_cost_usd_amount is not None
    if not has_cost:
        return "unknown"
    if profile.scholarship_need == profile.ScholarshipNeed.YES and not _has_aid_signal(university):
        return "high"
    if profile.scholarship_need in {profile.ScholarshipNeed.YES, profile.ScholarshipNeed.UNSURE} and not (
        university.scholarship_available
    ):
        return "moderate"
    return "low"


def _deadline_confidence(university: University) -> str:
    if university.application_deadline is None:
        return "missing"
    verification = next(
        (
            record
            for record in university.field_verifications.all()
            if record.field_name == "application_deadline"
        ),
        None,
    )
    if verification and verification.status == "verified":
        return "verified"
    return "partial"


def _urgency_for_days(days: int | None) -> str:
    # Mirrors services/application_service/timeline.py:urgency_for_days. Kept as
    # a local copy to avoid a university_service -> application_service import
    # (application_service already imports university_service, so the reverse
    # import would be circular).
    if days is None:
        return "unknown"
    if days < 0:
        return "overdue"
    if days <= 7:
        return "critical"
    if days <= 14:
        return "urgent"
    if days <= 30:
        return "soon"
    if days <= 90:
        return "upcoming"
    return "far"


def _available_rounds(university: University) -> list[str]:
    text = f"{university.deadlines_text} {university.application_requirements}".lower()
    found = []
    for label, pattern in ROUND_PATTERNS:
        if re.search(pattern, text):
            found.append(label)
    return found


def _application_round_info(university: University, *, essay_ready: bool, exam_ready: bool, days_remaining: int | None) -> dict:
    rounds = _available_rounds(university)
    if days_remaining is not None and days_remaining < 0:
        return {
            "available_rounds": rounds,
            "recommended_round": "unknown",
            "reason_key": "round_deadline_passed",
            "reason_params": {},
        }
    if not rounds:
        return {
            "available_rounds": [],
            "recommended_round": "unknown",
            "reason_key": "round_not_verified",
            "reason_params": {},
        }
    if len(rounds) == 1:
        return {
            "available_rounds": rounds,
            "recommended_round": rounds[0],
            "reason_key": "round_single_available",
            "reason_params": {"round": rounds[0]},
        }

    early_rounds = [label for label in rounds if label in {"REA", "ED", "ED II", "EA"}]
    if days_remaining is not None and days_remaining <= 21 and (not essay_ready or not exam_ready):
        fallback = "RD" if "RD" in rounds else rounds[-1]
        return {
            "available_rounds": rounds,
            "recommended_round": fallback,
            "reason_key": "round_early_too_close",
            "reason_params": {"round": fallback},
        }
    if early_rounds and essay_ready and exam_ready:
        return {
            "available_rounds": rounds,
            "recommended_round": early_rounds[0],
            "reason_key": "round_early_recommended_ready",
            "reason_params": {"round": early_rounds[0]},
        }
    return {
        "available_rounds": rounds,
        "recommended_round": rounds[0],
        "reason_key": "round_multiple_available",
        "reason_params": {"round": rounds[0]},
    }


def _is_international(profile, university: University) -> bool | None:
    home_country = str(profile.country or "").strip().lower()
    if not home_country:
        return None
    return university.country.strip().lower() != home_country


def _why_recommended_keys(*, fit: dict, targets: set[str], programs: list[dict], has_program_data: bool) -> list[str]:
    keys: list[str] = []
    if targets:
        keys.append("region_preference_match")
    else:
        keys.append("region_broad_default")
    if programs:
        keys.append(programs[0]["fit_reason_key"])
    elif not has_program_data:
        keys.append("program_not_verified")
    category = fit["category"]
    if category in {"dream", "reach", "target", "safety"}:
        keys.append(f"category_{category}")
    return keys


def _cap_confidence(confidence: str, cap: str) -> str:
    if CONFIDENCE_RANK.get(confidence, 1) > CONFIDENCE_RANK.get(cap, 1):
        return cap
    return confidence


def _build_recommendation_item(
    *,
    profile,
    university: University,
    targets: set[str],
    confidence_cap: str | None,
    shortlisted_ids: set[int],
    tracked_by_university: dict[int, int],
) -> dict | None:
    fit = calculate_university_fit(profile, university)
    if fit["category"] is None:
        return None

    category = "reach" if fit["category"] == "competitive" else fit["category"]
    program_summary = match_programs_to_profile(profile, university)
    programs = [
        {
            "name": program["display_name"],
            "fit_reason_key": program["fit_reason_key"],
            # "keyword" is renamed "related" for this public shape; "exact" and
            # "cluster" pass through unchanged so match_type stays consistent
            # with fit_reason_key (program_exact_match/program_cluster_match/
            # program_related_match) instead of collapsing a real cluster match
            # into the weaker "related" bucket.
            "match_type": "related" if program["match_type"] == "keyword" else program["match_type"],
            "confidence": program["confidence"],
            "program_fit_score": program["program_fit_score"],
            "major_cluster": program["major_cluster"],
            "subject_ranking": program["subject_ranking"],
        }
        for program in program_summary["recommended_programs"]
    ]
    has_program_data = program_summary["program_data_verified"]
    best_program = program_summary["recommended_programs"][0] if program_summary["recommended_programs"] else None
    inferred_clusters = program_summary["major_inference"].get("clusters", [])
    subject_context = subject_ranking_context(university, inferred_clusters)

    essay_ready = profile.essay_status == profile.EssayStatus.YES
    exam_ready = not any(
        risk in fit["risks"] for risk in ("sat_below_p25", "sat_below_average", "ielts_below_minimum")
    )
    normalized_deadline = normalize_university_deadline(university, profile)
    deadline = normalized_deadline.normalized_date
    days_remaining = (deadline - date.today()).days if deadline else None

    confidence = fit["confidence"]
    if confidence_cap:
        confidence = _cap_confidence(confidence, confidence_cap)

    aid_note_key = "aid_signal_available" if _has_aid_signal(university) else "aid_not_verified"
    missing_data = list(fit["missing_data"])[:5]

    return {
        "university": {
            "id": university.id,
            "name": university.name,
            "slug": university.slug,
            "country": university.country,
            "city": university.city,
        },
        "category": category,
        "is_international": _is_international(profile, university),
        "fit_score": fit["fit_score"],
        "confidence": confidence,
        "recommended_programs": programs,
        "matched_programs": programs,
        "program_data_verified": has_program_data,
        "best_program_fit_score": best_program["program_fit_score"] if best_program else None,
        "major_cluster_match": bool(best_program and best_program["major_cluster"] in inferred_clusters),
        "program_fit_confidence": program_summary["confidence"],
        "program_strengths": best_program["preparation_strengths"] if best_program else [],
        "program_gaps": best_program["preparation_gaps"] if best_program else [],
        "subject_ranking_context": subject_context,
        "missing_program_data": program_summary["missing_data"],
        "major_inference": program_summary["major_inference"],
        "application_round": _application_round_info(
            university, essay_ready=essay_ready, exam_ready=exam_ready, days_remaining=days_remaining
        ),
        "deadline": deadline,
        "deadline_confidence": _deadline_confidence(university),
        "deadline_cycle_label": normalized_deadline.cycle_label,
        "days_remaining": days_remaining,
        "urgency": _urgency_for_days(days_remaining),
        "estimated_total_cost_usd": fit["cost_context"]["total_cost_usd_amount"]
        or fit["cost_context"]["tuition_usd_amount"],
        "tuition_usd": fit["cost_context"]["tuition_usd_amount"],
        "aid_scholarship_note_key": aid_note_key,
        "cost_risk": _cost_risk(profile, university),
        "academic_risk": _risk_level_from_score(fit["academic_subscore"]),
        "profile_risk": _risk_level_from_score(fit["profile_subscore"]),
        "deadline_risk": _risk_level_from_score(fit["deadline_subscore"]),
        "main_strength": fit["strengths"][0] if fit["strengths"] else None,
        "main_risk": fit["risks"][0] if fit["risks"] else (missing_data[0] if missing_data else None),
        "why_recommended_keys": _why_recommended_keys(
            fit=fit, targets=targets, programs=programs, has_program_data=has_program_data
        ),
        "next_action": fit["next_actions"][0] if fit["next_actions"] else "verify_official_sources",
        "missing_data": missing_data,
        "current_academic_subscore": fit["academic_subscore"],
        "conditional_notes": fit["conditional_notes"],
        "conditional_fit_score": fit["conditional_fit_score"],
        "conditional_targets": fit["conditional_targets"],
        "source_notes": fit["source_notes"],
        "is_shortlisted": university.id in shortlisted_ids,
        "application_id": tracked_by_university.get(university.id),
    }


def _bucket_and_balance(items: list[dict]) -> tuple[list[dict], dict]:
    buckets: dict[str, list[dict]] = {category: [] for category in CATEGORY_ORDER_FOR_LIST}
    for item in items:
        buckets.setdefault(item["category"], []).append(item)
    for bucket in buckets.values():
        bucket.sort(key=lambda item: (item["fit_score"], CONFIDENCE_RANK.get(item["confidence"], 1)), reverse=True)

    selected: list[dict] = []
    counts = {"dream": 0, "reach": 0, "target": 0, "safety": 0, "international": 0}
    for category in CATEGORY_ORDER_FOR_LIST:
        quota = CATEGORY_QUOTAS[category]
        chosen = buckets.get(category, [])[:quota]
        selected.extend(chosen)
        counts[category] = len(chosen)
    counts["international"] = sum(1 for item in selected if item["is_international"])
    counts["total"] = len(selected)
    return selected, counts


def calculate_university_recommendations(profile, preferences=None, *, limit: int = 25) -> dict:
    targets = _normalized_targets(profile)
    queryset = (
        University.objects.filter(is_published=True, is_demo=False)
        .prefetch_related(
            "programs",
            "subject_rankings",
            "scholarships",
            "data_sources",
            "field_verifications",
        )
        .order_by("name")
    )
    candidates = [
        university for university in queryset if _country_matches_preference(university.country, targets)
    ]

    missing_preferences = []
    if not targets:
        missing_preferences.append("preferred_countries")
    if not (profile.intended_majors or profile.intended_major):
        missing_preferences.append("intended_major")
    confidence_cap = "medium" if not targets else None

    # Two bulk queries instead of one query per candidate university.
    shortlisted_ids = set(
        SavedUniversity.objects.filter(user_id=profile.user_id).values_list("university_id", flat=True)
    )
    tracked_by_university: dict[int, int] = dict(
        ApplicationTrackerItem.objects.filter(user_id=profile.user_id).values_list("university_id", "id")
    )

    items: list[dict] = []
    excluded_low_data_count = 0
    for university in candidates:
        item = _build_recommendation_item(
            profile=profile,
            university=university,
            targets=targets,
            confidence_cap=confidence_cap,
            shortlisted_ids=shortlisted_ids,
            tracked_by_university=tracked_by_university,
        )
        if item is None:
            excluded_low_data_count += 1
            continue
        items.append(item)

    selected, counts = _bucket_and_balance(items)
    list_size_limited = counts["total"] < min(limit, 20) and counts["total"] == len(items)

    return {
        "recommendations": selected[:limit],
        "counts": counts,
        "missing_preferences": missing_preferences,
        "excluded_low_data_count": excluded_low_data_count,
        "list_size_limited": list_size_limited,
        "disclaimer": (
            "This is a fit estimate based on available profile and university data. "
            "It is not an admissions prediction or guarantee."
        ),
    }
