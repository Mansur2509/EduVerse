from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

SCALE_4 = "4_0"
SCALE_5 = "5_0"
SCALE_PERCENTAGE = "percentage_100"
SCALE_IB = "ib_45"
SCALE_A_LEVEL = "a_level"
SCALE_AP_HEAVY = "ap_heavy"
SCALE_UZBEKISTAN_5 = "uzbekistan_5"
SCALE_KAZAKHSTAN_LOCAL = "kazakhstan_local"
SCALE_KYRGYZSTAN_LOCAL = "kyrgyzstan_local"
SCALE_TAJIKISTAN_LOCAL = "tajikistan_local"
SCALE_CUSTOM_UNKNOWN = "custom_unknown"

FOUR_POINT_SCALES = {SCALE_4}
FIVE_POINT_SCALES = {
    SCALE_5,
    SCALE_UZBEKISTAN_5,
    SCALE_KAZAKHSTAN_LOCAL,
    SCALE_KYRGYZSTAN_LOCAL,
    SCALE_TAJIKISTAN_LOCAL,
}

ROUNDING = Decimal("0.01")


@dataclass(frozen=True)
class AcademicNormalizationResult:
    original_gpa_value: Decimal | None
    original_gpa_scale: Decimal | None
    original_gpa_scale_type: str
    normalized_gpa_4: Decimal | None
    normalized_percentage: Decimal | None
    confidence: str
    note: str


def _decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _round(value: Decimal) -> Decimal:
    return value.quantize(ROUNDING, rounding=ROUND_HALF_UP)


def infer_gpa_scale_type(
    value,
    scale,
    explicit_scale_type: str | None = None,
) -> str:
    if explicit_scale_type and explicit_scale_type != SCALE_CUSTOM_UNKNOWN:
        return explicit_scale_type

    decimal_scale = _decimal(scale)
    if decimal_scale is None:
        return SCALE_CUSTOM_UNKNOWN
    if decimal_scale == Decimal("4"):
        return SCALE_4
    if decimal_scale == Decimal("5"):
        return SCALE_5
    if decimal_scale == Decimal("100"):
        return SCALE_PERCENTAGE
    if decimal_scale == Decimal("45"):
        return SCALE_IB
    return SCALE_CUSTOM_UNKNOWN


def _percentage_to_gpa_4(percentage: Decimal) -> Decimal:
    bands = (
        (Decimal("97"), Decimal("4.00")),
        (Decimal("93"), Decimal("3.80")),
        (Decimal("90"), Decimal("3.60")),
        (Decimal("87"), Decimal("3.40")),
        (Decimal("83"), Decimal("3.20")),
        (Decimal("80"), Decimal("3.00")),
        (Decimal("77"), Decimal("2.70")),
        (Decimal("73"), Decimal("2.30")),
        (Decimal("70"), Decimal("2.00")),
        (Decimal("67"), Decimal("1.70")),
        (Decimal("65"), Decimal("1.30")),
        (Decimal("60"), Decimal("1.00")),
    )
    for minimum, gpa in bands:
        if percentage >= minimum:
            return gpa
    return Decimal("0.70")


def _ib_to_gpa_4(points: Decimal) -> Decimal:
    bands = (
        (Decimal("42"), Decimal("4.00")),
        (Decimal("39"), Decimal("3.80")),
        (Decimal("36"), Decimal("3.60")),
        (Decimal("33"), Decimal("3.30")),
        (Decimal("30"), Decimal("3.00")),
        (Decimal("27"), Decimal("2.70")),
        (Decimal("24"), Decimal("2.30")),
    )
    for minimum, gpa in bands:
        if points >= minimum:
            return gpa
    return Decimal("2.00")


def normalize_academic_record(
    *,
    original_gpa_value,
    original_gpa_scale,
    original_gpa_scale_type: str | None,
) -> AcademicNormalizationResult:
    value = _decimal(original_gpa_value)
    scale = _decimal(original_gpa_scale)
    scale_type = infer_gpa_scale_type(value, scale, original_gpa_scale_type)

    if value is None or scale is None:
        return AcademicNormalizationResult(
            original_gpa_value=value,
            original_gpa_scale=scale,
            original_gpa_scale_type=scale_type,
            normalized_gpa_4=None,
            normalized_percentage=None,
            confidence=CONFIDENCE_LOW,
            note="GPA value or scale is missing, so EduVerse cannot compare GPA safely.",
        )

    if scale <= 0 or value < 0 or value > scale:
        return AcademicNormalizationResult(
            original_gpa_value=value,
            original_gpa_scale=scale,
            original_gpa_scale_type=scale_type,
            normalized_gpa_4=None,
            normalized_percentage=None,
            confidence=CONFIDENCE_LOW,
            note="GPA value is outside its declared scale; comparison is disabled.",
        )

    percentage = _round(value / scale * Decimal("100"))

    if scale_type in FOUR_POINT_SCALES:
        return AcademicNormalizationResult(
            original_gpa_value=value,
            original_gpa_scale=scale,
            original_gpa_scale_type=scale_type,
            normalized_gpa_4=_round(value),
            normalized_percentage=percentage,
            confidence=CONFIDENCE_HIGH,
            note="GPA is already on a 4.0 scale.",
        )

    if scale_type in FIVE_POINT_SCALES:
        return AcademicNormalizationResult(
            original_gpa_value=value,
            original_gpa_scale=scale,
            original_gpa_scale_type=scale_type,
            normalized_gpa_4=_round(value / scale * Decimal("4")),
            normalized_percentage=percentage,
            confidence=CONFIDENCE_MEDIUM,
            note="Converted proportionally from a 5-point/local scale for comparison only.",
        )

    if scale_type == SCALE_PERCENTAGE:
        return AcademicNormalizationResult(
            original_gpa_value=value,
            original_gpa_scale=scale,
            original_gpa_scale_type=scale_type,
            normalized_gpa_4=_percentage_to_gpa_4(percentage),
            normalized_percentage=percentage,
            confidence=CONFIDENCE_MEDIUM,
            note="Converted conservatively from a 100-point percentage band for comparison only.",
        )

    if scale_type == SCALE_IB:
        return AcademicNormalizationResult(
            original_gpa_value=value,
            original_gpa_scale=scale,
            original_gpa_scale_type=scale_type,
            normalized_gpa_4=_ib_to_gpa_4(value),
            normalized_percentage=percentage,
            confidence=CONFIDENCE_MEDIUM,
            note="Mapped conservatively from IB / 45 bands for comparison only.",
        )

    if scale_type in {SCALE_A_LEVEL, SCALE_AP_HEAVY}:
        return AcademicNormalizationResult(
            original_gpa_value=value,
            original_gpa_scale=scale,
            original_gpa_scale_type=scale_type,
            normalized_gpa_4=None,
            normalized_percentage=percentage,
            confidence=CONFIDENCE_LOW,
            note="This curriculum needs subject-grade context; GPA conversion is not trusted yet.",
        )

    return AcademicNormalizationResult(
        original_gpa_value=value,
        original_gpa_scale=scale,
        original_gpa_scale_type=scale_type,
        normalized_gpa_4=None,
        normalized_percentage=percentage,
        confidence=CONFIDENCE_LOW,
        note="GPA scale is custom or unknown; EduVerse will not compare it as a 4.0 GPA.",
    )


def normalize_profile_academics(profile) -> AcademicNormalizationResult:
    original_value = profile.original_gpa_value
    original_scale = profile.original_gpa_scale
    if original_value is None and getattr(profile, "gpa", None) is not None:
        original_value = profile.gpa
    if original_scale is None and getattr(profile, "gpa_scale", None) is not None:
        original_scale = profile.gpa_scale
    return normalize_academic_record(
        original_gpa_value=original_value,
        original_gpa_scale=original_scale,
        original_gpa_scale_type=profile.original_gpa_scale_type,
    )


def apply_academic_normalization(profile) -> AcademicNormalizationResult:
    result = normalize_profile_academics(profile)
    profile.original_gpa_value = result.original_gpa_value
    profile.original_gpa_scale = result.original_gpa_scale
    profile.original_gpa_scale_type = result.original_gpa_scale_type
    profile.normalized_gpa_4 = result.normalized_gpa_4
    profile.normalized_percentage = result.normalized_percentage
    profile.academic_normalization_confidence = result.confidence
    profile.academic_normalization_note = result.note
    return result
