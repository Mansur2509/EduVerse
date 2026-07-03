from __future__ import annotations

from dataclasses import dataclass

from services.user_profile_service.academic_normalization import normalize_profile_academics
from services.user_profile_service.curriculum_rigor import calculate_curriculum_rigor

from .models import University, UniversityProgram
from .program_display import format_program_display_names
from .services import _optional_evidence_counts, calculate_optional_evidence_fit

CLUSTER_KEYWORDS: dict[str, tuple[str, ...]] = {
    UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA: (
        "computer science",
        "software",
        "artificial intelligence",
        "ai",
        "machine learning",
        "ml",
        "data science",
        "analytics",
        "statistics",
        "informatics",
    ),
    UniversityProgram.MajorCluster.ENGINEERING: (
        "engineering",
        "electrical",
        "mechanical",
        "civil",
        "aerospace",
        "chemical",
        "robotics",
    ),
    UniversityProgram.MajorCluster.BUSINESS_ECONOMICS_FINANCE: (
        "business",
        "finance",
        "economics",
        "econ",
        "accounting",
        "management",
        "commerce",
        "entrepreneurship",
        "behavioral economics",
    ),
    UniversityProgram.MajorCluster.LAW_POLITICS_IR: (
        "law",
        "politics",
        "political science",
        "international relations",
        "ir",
        "government",
        "diplomacy",
    ),
    UniversityProgram.MajorCluster.PUBLIC_POLICY_SOCIAL_IMPACT: (
        "public policy",
        "policy",
        "social impact",
        "public affairs",
        "development",
        "community",
    ),
    UniversityProgram.MajorCluster.MEDICINE_BIOLOGY_HEALTH: (
        "medicine",
        "pre-med",
        "biology",
        "biomedical",
        "health",
        "public health",
        "neuroscience",
    ),
    UniversityProgram.MajorCluster.PSYCHOLOGY_COGNITIVE_SCIENCE: (
        "psychology",
        "cognitive science",
        "behavioral science",
        "neuroscience",
    ),
    UniversityProgram.MajorCluster.SOCIAL_SCIENCES: (
        "sociology",
        "anthropology",
        "social science",
        "behavioral science",
        "international development",
    ),
    UniversityProgram.MajorCluster.HUMANITIES: (
        "history",
        "literature",
        "philosophy",
        "linguistics",
        "classics",
        "languages",
    ),
    UniversityProgram.MajorCluster.DESIGN_ARTS: (
        "art",
        "design",
        "architecture",
        "film",
        "music",
        "media",
        "fine arts",
    ),
    UniversityProgram.MajorCluster.EDUCATION: ("education", "teaching", "pedagogy"),
    UniversityProgram.MajorCluster.ENVIRONMENTAL_SUSTAINABILITY: (
        "environmental",
        "sustainability",
        "climate",
        "earth science",
        "ecology",
    ),
    UniversityProgram.MajorCluster.STEM: (
        "mathematics",
        "math",
        "physics",
        "chemistry",
        "natural sciences",
        "statistics",
    ),
    UniversityProgram.MajorCluster.UNDECIDED_INTERDISCIPLINARY: (
        "undecided",
        "interdisciplinary",
        "liberal arts",
        "open curriculum",
        "exploratory",
    ),
}

CLUSTER_PROGRAM_KEYWORDS = CLUSTER_KEYWORDS


@dataclass(frozen=True)
class MajorInference:
    primary_major_cluster: str | None
    secondary_major_clusters: list[str]
    possible_program_keywords: list[str]
    strong_preparation_signals: list[str]
    weak_preparation_signals: list[str]
    missing_data: list[str]
    confidence: str

    @property
    def clusters(self) -> list[str]:
        values = []
        if self.primary_major_cluster:
            values.append(self.primary_major_cluster)
        values.extend(self.secondary_major_clusters)
        return list(dict.fromkeys(values))


def _profile_text_values(profile) -> list[str]:
    values: list[str] = []
    values.extend(str(value) for value in (getattr(profile, "intended_majors", []) or []) if value)
    intended_major = getattr(profile, "intended_major", "")
    if intended_major:
        values.append(str(intended_major))
    values.extend(str(value) for value in (getattr(profile, "career_interests", []) or []) if value)
    values.extend(str(value) for value in (getattr(profile, "interests", []) or []) if value)
    values.extend(str(value) for value in (getattr(profile, "interested_classes", []) or []) if value)
    values.extend(str(value) for value in (getattr(profile, "ap_interests", []) or []) if value)
    values.extend(str(value) for value in (getattr(profile, "preparation_needs", []) or []) if value)
    values.extend(str(value) for value in (getattr(profile, "academic_interests", []) or []) if value)

    user = profile.user
    for related_name, fields in (
        ("profile_activities", ("title", "description", "impact")),
        ("profile_research_projects", ("title", "summary", "role")),
        ("profile_portfolio_projects", ("title", "description", "skills_used")),
        ("profile_olympiads", ("name", "subject", "result_rank")),
        ("profile_essays", ("essay_type", "school_program", "status")),
    ):
        manager = getattr(user, related_name, None)
        if manager is None:
            continue
        for item in manager.all()[:20]:
            for field_name in fields:
                value = getattr(item, field_name, "")
                if value:
                    if isinstance(value, list):
                        values.extend(str(entry) for entry in value)
                    else:
                        values.append(str(value))
    return values


def _cluster_scores(text_values: list[str]) -> dict[str, int]:
    text = " ".join(text_values).lower()
    scores: dict[str, int] = {}
    for cluster, keywords in CLUSTER_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score:
            scores[cluster] = score
    return scores


def infer_major_clusters(profile) -> MajorInference:
    cached = getattr(profile, "_major_inference_cache", None)
    if cached is not None:
        return cached
    text_values = _profile_text_values(profile)
    scores = _cluster_scores(text_values)
    ordered = sorted(scores, key=lambda key: (scores[key], key), reverse=True)

    missing_data = []
    if not (getattr(profile, "intended_majors", []) or getattr(profile, "intended_major", "")):
        missing_data.append("intended_major")
    if not text_values:
        missing_data.append("academic_interests")

    counts = _evidence_counts(profile)
    strong = []
    weak = []
    if counts["research"] > 0:
        strong.append("research")
    if counts["portfolio"] > 0:
        strong.append("portfolio")
    if counts["olympiads"] > 0:
        strong.append("olympiads")
    if counts["volunteering"] > 0:
        strong.append("volunteering")
    for key in ("research", "portfolio", "olympiads"):
        if counts[key] == 0:
            weak.append(key)

    possible_keywords = []
    for cluster in ordered[:4]:
        possible_keywords.extend(CLUSTER_PROGRAM_KEYWORDS.get(cluster, ())[:4])

    confidence = "high" if getattr(profile, "intended_majors", []) or getattr(profile, "intended_major", "") else "low"
    if ordered and confidence == "low":
        confidence = "medium"
    if not ordered:
        confidence = "low"

    inference = MajorInference(
        primary_major_cluster=ordered[0] if ordered else None,
        secondary_major_clusters=ordered[1:6],
        possible_program_keywords=list(dict.fromkeys(possible_keywords)),
        strong_preparation_signals=strong,
        weak_preparation_signals=weak,
        missing_data=missing_data,
        confidence=confidence,
    )
    profile._major_inference_cache = inference
    return inference


def _evidence_counts(profile) -> dict[str, int]:
    cached = getattr(profile, "_major_matching_evidence_counts_cache", None)
    if cached is not None:
        return cached
    # Reuse the already-cached, single-query evidence counts computed for the
    # base fit score instead of issuing a second set of per-category .count()
    # queries for the same data (recommendations run this once per candidate
    # university, so a second query set here multiplies query volume for no
    # new information).
    base = _optional_evidence_counts(profile)
    counts = {
        "research": base["research"],
        "portfolio": base["portfolio"],
        "olympiads": base["olympiads"],
        "volunteering": base["volunteering"],
        "activities": base["activities"],
        "essays": base["essays"],
    }
    profile._major_matching_evidence_counts_cache = counts
    return counts


def _program_cluster(program: UniversityProgram, display_name: str) -> str:
    if program.major_cluster:
        return program.major_cluster
    text = f"{program.name} {display_name}".lower()
    for cluster, keywords in CLUSTER_PROGRAM_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return cluster
    return UniversityProgram.MajorCluster.OTHER


def _profile_major_texts(profile) -> list[str]:
    values = [
        str(value).strip().lower()
        for value in (getattr(profile, "intended_majors", []) or [])
        if str(value).strip()
    ]
    intended_major = getattr(profile, "intended_major", "")
    if intended_major:
        values.append(str(intended_major).strip().lower())
    return list(dict.fromkeys(values))


def _numeric_score(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _best_subject_ranking(program: UniversityProgram, university: University, cluster: str) -> dict | None:
    # `university.subject_rankings` (a single prefetch on the base queryset) is a
    # superset of `program.subject_rankings` -- every ranking row carries a
    # `university` FK regardless of whether `program` is also set -- so reading
    # only from the already-fetched `university` here (instead of also prefetching
    # and reading `program.subject_rankings`) avoids a second per-request query
    # while still preferring a ranking tied directly to this program.
    all_rankings = list(university.subject_rankings.all())
    rankings = [ranking for ranking in all_rankings if ranking.program_id == program.id]
    if not rankings:
        rankings = [
            ranking
            for ranking in all_rankings
            if ranking.major_cluster == cluster or ranking.subject_area.lower() in program.name.lower()
        ]
    if not rankings:
        return None
    ranking = sorted(rankings, key=lambda item: item.rank)[0]
    return {
        "subject_area": ranking.subject_area,
        "major_cluster": ranking.major_cluster,
        "rank": ranking.rank,
        "source_name": ranking.source_name,
        "source_url": ranking.source_url,
        "last_verified_date": ranking.last_verified_date,
        "confidence": ranking.confidence,
        "ranking_year": ranking.ranking_year,
    }


def score_program_fit(
    profile,
    program: UniversityProgram,
    university: University | None = None,
    inference: MajorInference | None = None,
) -> dict:
    inference = inference or infer_major_clusters(profile)
    university = university or program.university
    display_name = (format_program_display_names([program.name]) or [program.name])[0]
    cluster = _program_cluster(program, display_name)
    text = f"{program.name} {display_name} {program.program_requirements_summary}".lower()
    major_texts = _profile_major_texts(profile)
    display_text = display_name.lower()
    exact_match = any(major in display_text or display_text in major for major in major_texts)
    cluster_match = cluster in inference.clusters
    keyword_match = any(keyword in text for keyword in inference.possible_program_keywords)

    normalization = normalize_profile_academics(profile)
    curriculum = calculate_curriculum_rigor(profile)
    evidence_counts = _evidence_counts(profile)
    evidence = calculate_optional_evidence_fit(profile, university, display_name)

    academic_score = 45
    if normalization.normalized_gpa_4 is not None:
        academic_score += max(0, min(20, int((float(normalization.normalized_gpa_4) / 4) * 20)))
    sat_score = _numeric_score((profile.test_scores or {}).get("sat") if profile.test_scores else None)
    if sat_score is not None:
        academic_score += max(0, min(10, int((sat_score / 1600) * 10)))
    elif profile.test_scores:
        academic_score += 4
    academic_score += min(15, int(curriculum.rigor_score * 0.15))

    profile_score = 20
    if exact_match:
        profile_score += 25
    if cluster_match:
        profile_score += 20
    if keyword_match:
        profile_score += 10
    profile_score += min(20, evidence["evidence_subscore"] // 5)
    if cluster in {
        UniversityProgram.MajorCluster.STEM,
        UniversityProgram.MajorCluster.ENGINEERING,
        UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
    }:
        profile_score += min(10, evidence_counts["olympiads"] * 5)
    if cluster in {
        UniversityProgram.MajorCluster.PUBLIC_POLICY_SOCIAL_IMPACT,
        UniversityProgram.MajorCluster.LAW_POLITICS_IR,
    }:
        profile_score += min(10, evidence_counts["volunteering"] * 5)
    if program.portfolio_required or cluster == UniversityProgram.MajorCluster.DESIGN_ARTS:
        profile_score += min(10, evidence_counts["portfolio"] * 5)
    if program.research_heavy:
        profile_score += min(10, evidence_counts["research"] * 5)

    essay_score = 45
    if profile.essay_status == profile.EssayStatus.YES:
        essay_score += 25
    if program.essay_requirements:
        essay_score += 10

    requirement_score = 55
    missing_requirements = []
    if program.portfolio_required and evidence_counts["portfolio"] == 0:
        requirement_score -= 20
        missing_requirements.append("portfolio")
    if program.program_requirements_summary:
        requirement_score += 10
    else:
        missing_requirements.append("program_requirements")

    ranking = _best_subject_ranking(program, university, cluster)
    ranking_bonus = 0
    if ranking and ranking["rank"] <= 50 and cluster_match:
        ranking_bonus = 4
    elif ranking and ranking["rank"] <= 100 and cluster_match:
        ranking_bonus = 2

    raw_score = academic_score * 0.45 + profile_score * 0.30 + essay_score * 0.10 + requirement_score * 0.15
    score = max(1, min(100, round(raw_score + ranking_bonus)))

    strengths = []
    gaps = []
    notes = []
    if cluster_match:
        strengths.append("major_cluster_match")
    else:
        gaps.append("major_cluster_not_confirmed")
    if evidence_counts["research"] > 0 and (
        program.research_heavy or cluster in {UniversityProgram.MajorCluster.STEM, UniversityProgram.MajorCluster.SOCIAL_SCIENCES}
    ):
        strengths.append("research_relevant")
    if evidence_counts["portfolio"] > 0 and (
        program.portfolio_required
        or cluster in {
            UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
            UniversityProgram.MajorCluster.DESIGN_ARTS,
        }
    ):
        strengths.append("portfolio_relevant")
    if evidence_counts["olympiads"] > 0 and cluster in {
        UniversityProgram.MajorCluster.STEM,
        UniversityProgram.MajorCluster.ENGINEERING,
        UniversityProgram.MajorCluster.COMPUTER_SCIENCE_AI_DATA,
    }:
        strengths.append("olympiad_relevant")
    if evidence_counts["volunteering"] > 0 and cluster in {
        UniversityProgram.MajorCluster.PUBLIC_POLICY_SOCIAL_IMPACT,
        UniversityProgram.MajorCluster.LAW_POLITICS_IR,
    }:
        strengths.append("volunteering_relevant")
    if not ranking:
        notes.append("subject_ranking_not_available")
    if not program.official_url:
        notes.append("official_program_page_not_verified")

    confidence = "high" if program.source_confidence == "verified" else "medium"
    if not program.major_cluster or not program.program_requirements_summary:
        confidence = "low" if confidence == "medium" else "medium"
    if not inference.primary_major_cluster:
        confidence = "low"

    return {
        "id": program.id,
        "name": program.name,
        "display_name": display_name,
        "major_cluster": cluster,
        "degree_level": program.degree_level,
        "department_or_school": program.department_or_school,
        "official_url": program.official_url,
        "program_fit_score": score,
        "preparation_strengths": strengths,
        "preparation_gaps": gaps,
        "profile_relevance_notes": evidence["program_relevance_notes"],
        "missing_requirements": missing_requirements,
        "confidence": confidence,
        "subject_ranking": ranking,
        "source_confidence": program.source_confidence,
        "last_verified_date": program.last_verified_date,
        "portfolio_required": program.portfolio_required,
        "requirements_available": bool(program.program_requirements_summary),
        "essay_requirements_available": bool(program.essay_requirements),
        "data_notes": notes,
        "match_type": "exact" if exact_match else ("cluster" if cluster_match else ("keyword" if keyword_match else "low_context")),
        "fit_reason_key": "program_exact_match" if exact_match else ("program_cluster_match" if cluster_match else "program_related_match"),
    }


def match_programs_to_profile(profile, university: University, *, limit: int = 4) -> dict:
    inference = infer_major_clusters(profile)
    programs = list(university.programs.all())
    if not programs:
        return {
            "major_inference": inference.__dict__ | {"clusters": inference.clusters},
            "recommended_programs": [],
            "program_data_verified": False,
            "missing_data": ["program_level_data"],
            "confidence": "low",
        }
    scored = [score_program_fit(profile, program, university=university, inference=inference) for program in programs]
    scored.sort(key=lambda item: (item["program_fit_score"], item["confidence"]), reverse=True)
    recommended = [item for item in scored if item["match_type"] != "low_context"]
    missing_data = []
    if not any(item["subject_ranking"] for item in scored):
        missing_data.append("subject_ranking_data")
    if not recommended:
        missing_data.append("profile_major_context")
    return {
        "major_inference": inference.__dict__ | {"clusters": inference.clusters},
        "recommended_programs": recommended[:limit],
        "program_data_verified": True,
        "missing_data": missing_data,
        "confidence": inference.confidence if any(item["major_cluster"] in inference.clusters for item in recommended) else "low",
    }


def subject_ranking_context(university: University, clusters: list[str]) -> dict | None:
    rankings = list(university.subject_rankings.all())
    if clusters:
        matching = [ranking for ranking in rankings if ranking.major_cluster in clusters]
        rankings = matching or rankings
    if not rankings:
        return None
    ranking = sorted(rankings, key=lambda item: item.rank)[0]
    return {
        "subject_area": ranking.subject_area,
        "major_cluster": ranking.major_cluster,
        "rank": ranking.rank,
        "source_name": ranking.source_name,
        "source_url": ranking.source_url,
        "last_verified_date": ranking.last_verified_date,
        "confidence": ranking.confidence,
        "ranking_year": ranking.ranking_year,
    }


def build_program_recommendation_summary(profile, university: University) -> dict:
    return match_programs_to_profile(profile, university)
