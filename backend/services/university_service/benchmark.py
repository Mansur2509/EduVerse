"""Deterministic benchmark-source fallback chain (HOTFIX-007/PROTOCOL-008
PART 2). Never calls AI -- only arithmetic means over `UniversitySignalWeights`
rows, reusing the existing major-cluster inference and country-preference
matching already built for the recommendation engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .fit_vector import SIGNAL_NAMES
from .major_matching import infer_major_clusters
from .models import University
from .recommendations import _country_matches_preference, _normalized_targets

# Reuse fit_vector's plain signal vocabulary (not the `{signal}_score` Django
# field names) so `resolve_benchmark(...).scores` is directly comparable via
# `compare_student_vector_to_university_weights` without a translation step.
SIGNAL_DIMENSIONS = SIGNAL_NAMES

# Below this count of contributing universities, a tier's average is too thin
# to trust -- fall through to the next, broader tier instead.
MINIMUM_BENCHMARK_SAMPLE_SIZE = 3

BENCHMARK_SOURCE_DREAM_UNIVERSITIES = "dream_universities"
BENCHMARK_SOURCE_MAJOR_COUNTRY_AVERAGE = "major_country_average"
BENCHMARK_SOURCE_COUNTRY_AVERAGE = "country_average"
BENCHMARK_SOURCE_GLOBAL_MAJOR_AVERAGE = "global_major_average"
BENCHMARK_SOURCE_GLOBAL_AVERAGE = "global_average"
BENCHMARK_SOURCE_UNAVAILABLE = "unavailable"


# Raw academic-admission numbers averaged from the same benchmark-tier
# candidates as the 12 signal dimensions, so deterministic comparisons (PART
# 4) have a benchmark GPA/SAT/IELTS to compare a student's own numbers
# against -- not just the 1-10 signal-weight scores.
ACADEMIC_FIELDS = ("gpa_average", "sat_average", "sat_p25", "sat_p75", "ielts_minimum", "ielts_competitive")


@dataclass(frozen=True)
class BenchmarkResult:
    source: str
    sample_size: int
    scores: dict[str, int]
    academic: dict[str, float]


def _valid_score(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 1 <= value <= 10:
        return value
    return None


def _numeric(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _average_signal_weights(universities: list[University]) -> tuple[dict[str, int], int]:
    """Arithmetic mean per dimension, ignoring null/invalid values per
    dimension rather than treating them as zero. `sample_size` counts
    universities that contributed at least one usable dimension.
    """

    per_dimension: dict[str, list[int]] = {dimension: [] for dimension in SIGNAL_DIMENSIONS}
    contributing_ids: set[int] = set()
    for university in universities:
        weights = getattr(university, "signal_weights", None)
        if weights is None:
            continue
        contributed = False
        for dimension in SIGNAL_DIMENSIONS:
            value = _valid_score(getattr(weights, f"{dimension}_score", None))
            if value is not None:
                per_dimension[dimension].append(value)
                contributed = True
        if contributed:
            contributing_ids.add(university.id)

    scores = {
        dimension: round(mean(values)) for dimension, values in per_dimension.items() if values
    }
    return scores, len(contributing_ids)


def _average_academic_requirements(universities: list[University]) -> dict[str, float]:
    """Arithmetic mean of each raw admission number, ignoring null values
    per-field rather than treating them as zero."""

    per_field: dict[str, list[float]] = {field: [] for field in ACADEMIC_FIELDS}
    for university in universities:
        for field in ACADEMIC_FIELDS:
            value = _numeric(getattr(university, field, None))
            if value is not None:
                per_field[field].append(value)
    return {field: round(mean(values), 2) for field, values in per_field.items() if values}


def _clusters_for_profile(profile) -> list[str]:
    inference = infer_major_clusters(profile)
    clusters = []
    if inference.primary_major_cluster:
        clusters.append(inference.primary_major_cluster)
    clusters.extend(inference.secondary_major_clusters)
    return clusters


def _dream_university_candidates(profile) -> list[University]:
    targets = [str(value).strip() for value in profile.target_universities if str(value).strip()]
    if not targets:
        return []
    return list(
        University.objects.filter(is_published=True, name__in=targets).select_related(
            "signal_weights"
        )
    )


def _major_country_candidates(profile) -> list[University]:
    clusters = _clusters_for_profile(profile)
    targets = _normalized_targets(profile)
    if not clusters or not targets:
        return []
    queryset = (
        University.objects.filter(
            is_published=True, is_demo=False, programs__major_cluster__in=clusters
        )
        .select_related("signal_weights")
        .distinct()
    )
    return [
        university for university in queryset if _country_matches_preference(university.country, targets)
    ]


def _country_candidates(profile) -> list[University]:
    targets = _normalized_targets(profile)
    if not targets:
        return []
    queryset = University.objects.filter(is_published=True, is_demo=False).select_related(
        "signal_weights"
    )
    return [
        university for university in queryset if _country_matches_preference(university.country, targets)
    ]


def _global_major_candidates(profile) -> list[University]:
    clusters = _clusters_for_profile(profile)
    if not clusters:
        return []
    return list(
        University.objects.filter(
            is_published=True, is_demo=False, programs__major_cluster__in=clusters
        )
        .select_related("signal_weights")
        .distinct()
    )


def _global_candidates() -> list[University]:
    return list(
        University.objects.filter(is_published=True, is_demo=False).select_related("signal_weights")
    )


def resolve_benchmark(profile) -> BenchmarkResult:
    """Benchmark-source fallback chain: dream_universities ->
    major_country_average -> country_average -> global_major_average ->
    global_average. Falls through when a tier has fewer than
    `MINIMUM_BENCHMARK_SAMPLE_SIZE` universities with usable signal-weight
    data. Never invents a benchmark -- if nothing in the catalog has
    published signal weights at all, returns `BENCHMARK_SOURCE_UNAVAILABLE`
    with empty scores rather than a fabricated average.
    """

    tiers = (
        (BENCHMARK_SOURCE_DREAM_UNIVERSITIES, _dream_university_candidates),
        (BENCHMARK_SOURCE_MAJOR_COUNTRY_AVERAGE, _major_country_candidates),
        (BENCHMARK_SOURCE_COUNTRY_AVERAGE, _country_candidates),
        (BENCHMARK_SOURCE_GLOBAL_MAJOR_AVERAGE, _global_major_candidates),
    )
    for source, candidate_fn in tiers:
        candidates = candidate_fn(profile)
        scores, sample_size = _average_signal_weights(candidates)
        if sample_size >= MINIMUM_BENCHMARK_SAMPLE_SIZE:
            return BenchmarkResult(
                source=source,
                sample_size=sample_size,
                scores=scores,
                academic=_average_academic_requirements(candidates),
            )

    global_candidates = _global_candidates()
    scores, sample_size = _average_signal_weights(global_candidates)
    if sample_size > 0:
        return BenchmarkResult(
            source=BENCHMARK_SOURCE_GLOBAL_AVERAGE,
            sample_size=sample_size,
            scores=scores,
            academic=_average_academic_requirements(global_candidates),
        )
    return BenchmarkResult(source=BENCHMARK_SOURCE_UNAVAILABLE, sample_size=0, scores={}, academic={})
