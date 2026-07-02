"""Normalize a stored official deadline to a student's own admissions cycle.

Universities publish deadlines with a specific year attached (e.g. "November 1,
2025"). The month/day is the real, official part; the year is only valid for
whichever admissions cycle the data was captured during. A student graduating
in a different year needs the cycle-equivalent date, not the stale one.

This module never invents a new month/day and never overwrites the raw stored
field. It only recomputes which year the already-known month/day falls in for
a given expected graduation year, using the standard admissions-cycle rule:
Aug-Dec deadlines belong to the cycle year before graduation, Jan-Jul
deadlines belong to the graduation year itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

CONFIDENCE_NORMALIZED = "normalized"
CONFIDENCE_SOURCE_ONLY = "source_only"
CONFIDENCE_MISSING = "missing"


@dataclass(frozen=True)
class NormalizedDeadline:
    source_date: date | None
    source_month: int | None
    source_day: int | None
    normalized_date: date | None
    normalized_year: int | None
    expected_graduation_year: int | None
    cycle_label: str | None
    confidence: str
    explanation: str
    source_url: str

    @property
    def display_date(self) -> date | None:
        """Best date to use for days-remaining/urgency: normalized, else raw."""
        return self.normalized_date or self.source_date


def _cycle_year_for_month(month: int, expected_graduation_year: int) -> int:
    if month >= 8:
        return expected_graduation_year - 1
    return expected_graduation_year


def normalize_deadline_for_graduation_year(
    source_date: date | None,
    expected_graduation_year: int | None,
    *,
    source_url: str = "",
) -> NormalizedDeadline:
    if source_date is None:
        return NormalizedDeadline(
            source_date=None,
            source_month=None,
            source_day=None,
            normalized_date=None,
            normalized_year=None,
            expected_graduation_year=expected_graduation_year,
            cycle_label=None,
            confidence=CONFIDENCE_MISSING,
            explanation="No deadline is on file yet; this deadline needs verification.",
            source_url=source_url,
        )

    if not expected_graduation_year:
        return NormalizedDeadline(
            source_date=source_date,
            source_month=source_date.month,
            source_day=source_date.day,
            normalized_date=None,
            normalized_year=None,
            expected_graduation_year=None,
            cycle_label=None,
            confidence=CONFIDENCE_SOURCE_ONLY,
            explanation=(
                "Showing the source month and day only. Add your expected "
                "graduation year to see this deadline for your own cycle."
            ),
            source_url=source_url,
        )

    normalized_year = _cycle_year_for_month(source_date.month, expected_graduation_year)
    try:
        normalized_date = source_date.replace(year=normalized_year)
    except ValueError:
        # Feb 29 source date landing on a non-leap normalized year.
        normalized_date = source_date.replace(year=normalized_year, day=28)

    cycle_label = f"{expected_graduation_year - 1}-{expected_graduation_year}"

    return NormalizedDeadline(
        source_date=source_date,
        source_month=source_date.month,
        source_day=source_date.day,
        normalized_date=normalized_date,
        normalized_year=normalized_year,
        expected_graduation_year=expected_graduation_year,
        cycle_label=cycle_label,
        confidence=CONFIDENCE_NORMALIZED,
        explanation=(
            "Month and day are from the official source; the year is adjusted "
            f"to your {expected_graduation_year} graduation cycle."
        ),
        source_url=source_url,
    )


def normalize_university_deadline(university, profile) -> NormalizedDeadline:
    """Convenience wrapper for the common case: a University's stored deadline."""
    return normalize_deadline_for_graduation_year(
        university.application_deadline,
        getattr(profile, "expected_graduation_year", None) if profile else None,
        source_url=university.admissions_url or university.official_website or "",
    )
