"""Pure gap-comparison skeleton for the system-only profile-scoring vector.

No UI, no persistence, no AI call -- a plain function the future fit/
readiness engine can call once it's ready to use
`UniversitySignalWeights`. Never expresses results as an admission chance,
probability, or guarantee: only descriptive alignment bands.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SIGNAL_NAMES = (
    "profile_evidence",
    "activities",
    "honors_olympiads",
    "research_experience",
    "portfolio",
    "subject_passion",
    "curiosity",
    "originality",
    "leadership",
    "community_impact",
    "research_fit",
    "olympiads",
)

SEVERITY_MEETS_OR_EXCEEDS = "meets_or_exceeds"
SEVERITY_MINOR_GAP = "minor_gap"
SEVERITY_IMPORTANT_GAP = "important_gap"
SEVERITY_SIGNIFICANT_GAP = "significant_gap"
SEVERITY_INSUFFICIENT_DATA = "insufficient_data"

FIT_BAND_STRONG = "strong_alignment"
FIT_BAND_GOOD = "good_alignment"
FIT_BAND_MODERATE = "moderate_alignment"
FIT_BAND_STRETCH = "stretch_alignment"
FIT_BAND_HIGH_STRETCH = "high_stretch_alignment"


@dataclass
class SignalGap:
    signal: str
    student_score: int | None
    university_weight: int | None
    gap: int | None
    severity: str


@dataclass
class FitVectorComparison:
    per_signal: list[SignalGap] = field(default_factory=list)
    counts_by_severity: dict[str, int] = field(default_factory=dict)
    total_gap_score: int = 0
    fit_band: str = FIT_BAND_STRONG
    signals_compared: int = 0
    signals_missing_data: int = 0


def _classify_gap(gap: int) -> str:
    if gap <= 0:
        return SEVERITY_MEETS_OR_EXCEEDS
    if gap == 1:
        return SEVERITY_MINOR_GAP
    if gap == 2:
        return SEVERITY_IMPORTANT_GAP
    return SEVERITY_SIGNIFICANT_GAP


def _determine_fit_band(counts: dict[str, int]) -> str:
    """Band the overall alignment from the count of important/significant
    gaps among the signals that were actually comparable. Intentionally
    ladder-shaped and conservative: even one severe gap (>=3 points) is
    enough to move out of "strong", and two or more moves out of
    "moderate" -- there is no probability or chance implied by any band,
    only a description of how many rubric signals the student currently
    falls short on.
    """

    significant = counts.get(SEVERITY_SIGNIFICANT_GAP, 0)
    important = counts.get(SEVERITY_IMPORTANT_GAP, 0)

    if significant == 0 and important == 0:
        return FIT_BAND_STRONG
    if significant == 0 and important <= 2:
        return FIT_BAND_GOOD
    if significant <= 1:
        return FIT_BAND_MODERATE
    if significant == 2:
        return FIT_BAND_STRETCH
    return FIT_BAND_HIGH_STRETCH


def compare_student_vector_to_university_weights(
    student_vector: dict[str, int | None],
    university_weights: dict[str, int | None],
) -> FitVectorComparison:
    """Compare a 12-signal student vector (0-10 each) against a university's
    published signal weights (0-10 each, any of which may be null/unset).

    A signal missing on either side is reported as `insufficient_data` and
    excluded from `total_gap_score` and the fit-band calculation -- it is
    never assumed to be 0, since that would invent a gap that isn't backed
    by any real data.

    `fit_band` is only meaningful when `signals_compared > 0`; callers must
    check that before displaying or acting on the band.
    """

    per_signal: list[SignalGap] = []
    counts = {
        SEVERITY_MEETS_OR_EXCEEDS: 0,
        SEVERITY_MINOR_GAP: 0,
        SEVERITY_IMPORTANT_GAP: 0,
        SEVERITY_SIGNIFICANT_GAP: 0,
        SEVERITY_INSUFFICIENT_DATA: 0,
    }
    total_gap_score = 0

    for signal in SIGNAL_NAMES:
        student_score = student_vector.get(signal)
        university_weight = university_weights.get(signal)
        if student_score is None or university_weight is None:
            per_signal.append(
                SignalGap(signal, student_score, university_weight, None, SEVERITY_INSUFFICIENT_DATA)
            )
            counts[SEVERITY_INSUFFICIENT_DATA] += 1
            continue

        gap = university_weight - student_score
        severity = _classify_gap(gap)
        per_signal.append(SignalGap(signal, student_score, university_weight, gap, severity))
        counts[severity] += 1
        total_gap_score += gap

    signals_compared = len(SIGNAL_NAMES) - counts[SEVERITY_INSUFFICIENT_DATA]
    return FitVectorComparison(
        per_signal=per_signal,
        counts_by_severity=counts,
        total_gap_score=total_gap_score,
        fit_band=_determine_fit_band(counts),
        signals_compared=signals_compared,
        signals_missing_data=counts[SEVERITY_INSUFFICIENT_DATA],
    )
