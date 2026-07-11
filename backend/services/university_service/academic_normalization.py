"""University-side GPA-benchmark normalization and student-vs-benchmark
academic comparison (PERFORMANCE-012 PART 2/3).

The student side is already fully normalized to an internal percentage by
`services.user_profile_service.academic_normalization.normalize_profile_academics`.
The university side previously had no scale information at all --
`University.gpa_average` was compared directly against the student's
normalized 0-4.0 GPA (see `services.university_service.services._assess_academics`),
so a benchmark recorded on a different scale (e.g. 88 meaning 88/100) produced
a wildly wrong "below average" verdict for a strong student. This module
normalizes both sides to the same internal percentage before comparing them,
and never invents a scale it isn't reasonably confident about.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from services.user_profile_service.academic_normalization import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    AcademicNormalizationResult,
)

# Only values at or below 4.0 can be conservatively treated as already being
# on a 4.0 scale when no explicit scale is recorded. Weighted GPAs such as
# 4.17 with a null scale are ambiguous and must not become impossible
# percentages like 104.25%.
_UNLABELED_FOUR_POINT_CEILING = Decimal("4.0")

BENCHMARK_STATUS_MEETS = "meets_benchmark"
BENCHMARK_STATUS_ABOVE = "above_benchmark"
BENCHMARK_STATUS_SLIGHTLY_BELOW = "slightly_below_benchmark"
BENCHMARK_STATUS_BELOW = "below_benchmark"
BENCHMARK_STATUS_UNKNOWN = "unknown"

# Percentage-point bands for the human-readable status, applied to
# (student_percent - benchmark_percent). Deliberately conservative: a small
# gap either way reads as "meets", not "above"/"slightly below", since a
# published GPA benchmark is itself often an admitted-class average, not a
# hard cutoff.
_ABOVE_THRESHOLD = Decimal("3")
_SLIGHTLY_BELOW_THRESHOLD = Decimal("-5")

_CONFIDENCE_RANK = {CONFIDENCE_LOW: 0, CONFIDENCE_MEDIUM: 1, CONFIDENCE_HIGH: 2}


@dataclass(frozen=True)
class UniversityGpaBenchmarkResult:
    original_value: Decimal | None
    original_scale: Decimal | None
    normalized_percentage: Decimal | None
    confidence: str
    note: str


def normalize_university_gpa_benchmark(university) -> UniversityGpaBenchmarkResult:
    """Convert `University.gpa_average` to an internal percentage using its
    `gpa_average_scale` when recorded, or a conservative inference when not.
    Never guesses a scale for a value that could plausibly be several
    different scales -- returns `normalized_percentage=None` instead of a
    confident-looking but wrong comparison.
    """

    raw_value = university.gpa_average
    if raw_value is None:
        return UniversityGpaBenchmarkResult(
            original_value=None,
            original_scale=None,
            normalized_percentage=None,
            confidence=CONFIDENCE_LOW,
            note="University has not published a GPA benchmark.",
        )
    value = Decimal(str(raw_value))

    raw_scale = university.gpa_average_scale
    if raw_scale is not None:
        scale = Decimal(str(raw_scale))
        if scale <= 0 or value < 0 or value > scale:
            return UniversityGpaBenchmarkResult(
                original_value=value,
                original_scale=scale,
                normalized_percentage=None,
                confidence=CONFIDENCE_LOW,
                note="University GPA benchmark is outside its declared scale; comparison is disabled.",
            )
        percentage = (value / scale * Decimal("100")).quantize(Decimal("0.01"))
        return UniversityGpaBenchmarkResult(
            original_value=value,
            original_scale=scale,
            normalized_percentage=percentage,
            confidence=CONFIDENCE_HIGH,
            note="Converted from the university's recorded GPA scale.",
        )

    if 0 <= value <= _UNLABELED_FOUR_POINT_CEILING:
        percentage = (value / Decimal("4") * Decimal("100")).quantize(Decimal("0.01"))
        return UniversityGpaBenchmarkResult(
            original_value=value,
            original_scale=None,
            normalized_percentage=percentage,
            confidence=CONFIDENCE_MEDIUM,
            note="No GPA scale recorded; assumed a 4.0 scale based on the value's range.",
        )

    return UniversityGpaBenchmarkResult(
        original_value=value,
        original_scale=None,
        normalized_percentage=None,
        confidence=CONFIDENCE_LOW,
        note="University GPA benchmark scale is unrecorded and cannot be safely compared.",
    )


def compare_academic_benchmark(
    student: AcademicNormalizationResult,
    university: UniversityGpaBenchmarkResult,
) -> dict:
    """Compare normalized percentages, never raw scale-mismatched numbers.
    Confidence is the weaker of the two sides -- an unknown scale on either
    side must not produce a confident-sounding verdict.
    """

    student_percent = student.normalized_percentage
    benchmark_percent = university.normalized_percentage

    if student_percent is None or benchmark_percent is None:
        return {
            "normalized_student_gpa_percent": _as_float(student_percent),
            "normalized_benchmark_percent": _as_float(benchmark_percent),
            "status": BENCHMARK_STATUS_UNKNOWN,
            "confidence": CONFIDENCE_LOW,
            "benchmark_note": university.note,
        }

    diff = student_percent - benchmark_percent
    if diff >= _ABOVE_THRESHOLD:
        status = BENCHMARK_STATUS_ABOVE
    elif diff >= 0:
        status = BENCHMARK_STATUS_MEETS
    elif diff > _SLIGHTLY_BELOW_THRESHOLD:
        status = BENCHMARK_STATUS_SLIGHTLY_BELOW
    else:
        status = BENCHMARK_STATUS_BELOW

    return {
        "normalized_student_gpa_percent": _as_float(student_percent),
        "normalized_benchmark_percent": _as_float(benchmark_percent),
        "status": status,
        "confidence": _weaker_confidence(student.confidence, university.confidence),
        "benchmark_note": university.note,
    }


def _weaker_confidence(a: str, b: str) -> str:
    return a if _CONFIDENCE_RANK.get(a, 0) <= _CONFIDENCE_RANK.get(b, 0) else b


def _as_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None
