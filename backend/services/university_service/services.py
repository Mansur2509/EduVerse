from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.user_profile_service.academic_normalization import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    normalize_profile_academics,
)

from .currency import normalize_university_costs
from .deadline_normalization import normalize_university_deadline
from .models import University

CATEGORY_ORDER = ("reach", "competitive", "target", "safety")
FIT_DISCLAIMER = (
    "This is a fit estimate based on available profile and university data. "
    "It is not an admissions prediction or guarantee."
)

GPA_SIGNIFICANT_DIFF = Decimal("0.30")
SAT_SIGNIFICANT_DIFF = 100

STATUS_ON_TRACK = "on_track"
STATUS_NEAR_TARGET = "near_target"
STATUS_MODERATE_GAP = "moderate_gap"
STATUS_SUBSTANTIAL_GAP = "substantial_gap"
STATUS_SIGNIFICANT_GAP = "significant_gap"
STATUS_NOT_ENOUGH_DATA = "not_enough_data"

SAT_GAP_PENALTIES = {
    STATUS_NEAR_TARGET: 6,
    STATUS_MODERATE_GAP: 12,
    STATUS_SUBSTANTIAL_GAP: 18,
    STATUS_SIGNIFICANT_GAP: 28,
}
IELTS_COMPETITIVE_GAP_PENALTIES = {
    STATUS_NEAR_TARGET: 4,
    STATUS_MODERATE_GAP: 8,
    STATUS_SUBSTANTIAL_GAP: 12,
    STATUS_SIGNIFICANT_GAP: 16,
}
IELTS_MINIMUM_GAP_PENALTIES = {
    STATUS_NEAR_TARGET: 16,
    STATUS_MODERATE_GAP: 22,
    STATUS_SUBSTANTIAL_GAP: 26,
    STATUS_SIGNIFICANT_GAP: 30,
}


def normalize_gpa_to_4(gpa, gpa_scale) -> float | None:
    """Legacy helper retained for callers; prefer normalize_profile_academics."""

    if gpa is None or gpa_scale is None:
        return None
    try:
        scale = float(gpa_scale)
    except (TypeError, ValueError):
        return None
    if scale <= 0:
        return None
    return float(gpa) / scale * 4.0


def _number(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def ielts_gap_severity(student_score, benchmark) -> str:
    student = _number(student_score)
    target = _number(benchmark)
    if student is None or target is None:
        return STATUS_NOT_ENOUGH_DATA
    gap = target - student
    if gap <= 0:
        return STATUS_ON_TRACK
    if gap <= 0.5:
        return STATUS_NEAR_TARGET
    if gap <= 1.0:
        return STATUS_MODERATE_GAP
    if gap < 1.5:
        return STATUS_SUBSTANTIAL_GAP
    return STATUS_SIGNIFICANT_GAP


def sat_gap_severity(student_score, benchmark) -> str:
    student = _number(student_score)
    target = _number(benchmark)
    if student is None or target is None:
        return STATUS_NOT_ENOUGH_DATA
    gap = target - student
    if gap <= 0:
        return STATUS_ON_TRACK
    if gap <= 50:
        return STATUS_NEAR_TARGET
    if gap <= 100:
        return STATUS_MODERATE_GAP
    if gap <= 150:
        return STATUS_SUBSTANTIAL_GAP
    return STATUS_SIGNIFICANT_GAP


def best_sat_score(test_scores) -> int | None:
    if not isinstance(test_scores, dict):
        return None
    value = test_scores.get("sat") or test_scores.get("SAT")
    number = _number(value)
    return int(number) if number is not None else None


def best_ielts_score(test_scores) -> float | None:
    if not isinstance(test_scores, dict):
        return None
    return _number(test_scores.get("ielts") or test_scores.get("IELTS"))


def _acceptance_rate_baseline_index(acceptance_rate: float) -> int:
    if acceptance_rate <= 15:
        return 0
    if acceptance_rate <= 35:
        return 1
    if acceptance_rate <= 60:
        return 2
    return 3


def _confidence_from_missing(missing_fields: list[str], normalization_confidence: str) -> str:
    if normalization_confidence == CONFIDENCE_LOW or len(missing_fields) >= 6:
        return CONFIDENCE_LOW
    if normalization_confidence == CONFIDENCE_HIGH and len(missing_fields) <= 2:
        return CONFIDENCE_HIGH
    return CONFIDENCE_MEDIUM


def _planned_exam_notes(profile, deadline: date | None) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    next_actions: list[str] = []
    plans = profile.exam_plans.get("planned", []) if isinstance(profile.exam_plans, dict) else []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        exam_name = str(plan.get("exam_type") or plan.get("name") or "").upper()
        if not any(token in exam_name for token in ("SAT", "AP")):
            continue
        target_score = str(plan.get("target_score") or "").strip()
        note = "Planned retake may improve fit only if the target score is achieved"
        if target_score:
            note = f"{note} ({target_score})"
        exam_date = str(plan.get("date") or "").strip()
        if exam_date and deadline:
            try:
                parsed_date = date.fromisoformat(exam_date)
            except ValueError:
                parsed_date = None
            if parsed_date and parsed_date > deadline:
                notes.append(
                    f"{note}; current planned date is after the application deadline."
                )
                next_actions.append("verify_exam_date_before_deadline")
                continue
        notes.append(f"{note}.")
        next_actions.append("plan_exam_retake")
    return notes, next_actions


def _score_program_fit(profile, university: University, strengths: list[str], missing: list[str]) -> int:
    majors = [
        str(value).strip().lower()
        for value in (profile.intended_majors or ([profile.intended_major] if profile.intended_major else []))
        if str(value).strip()
    ]
    if not majors:
        missing.append("profile_intended_major")
        return 45

    programs = [program.name.lower() for program in university.programs.all()]
    if not programs:
        missing.append("university_programs")
        return 55

    if any(major in program or program in major for major in majors for program in programs):
        strengths.append("major_matches_program")
        return 82
    return 58


def _structured_evidence_count(profile) -> int:
    """Total structured admissions-profile entries (activities, honors,
    olympiads, sports, research, portfolio, volunteering) for this profile's
    user. Callers such as the recommendation engine invoke the surrounding
    fit calculation once per candidate university with the *same* profile
    instance, so the count is cached on that instance to avoid re-querying it
    once per candidate.
    """

    cached = getattr(profile, "_structured_evidence_count_cache", None)
    if cached is not None:
        return cached
    user = profile.user
    count = (
        user.profile_activities.count()
        + user.profile_honors.count()
        + user.profile_olympiads.count()
        + user.profile_sports.count()
        + user.profile_research_projects.count()
        + user.profile_portfolio_projects.count()
        + user.profile_volunteering.count()
    )
    profile._structured_evidence_count_cache = count
    return count


def _score_profile_fit(profile, strengths: list[str], missing: list[str]) -> int:
    activities = profile.activities if isinstance(profile.activities, dict) else {}
    evidence_count = sum(len(value) for value in activities.values() if isinstance(value, list))
    # Structured admissions-profile entries are richer evidence than the
    # legacy free-text lists, so a profile that has moved to the structured
    # form is not scored as if it were empty. Weighted like ~2 legacy items
    # each; this only broadens what counts as evidence, it does not change
    # the thresholds below.
    evidence_count += _structured_evidence_count(profile) * 2
    if evidence_count >= 6:
        strengths.append("profile_depth")
        return 82
    if evidence_count >= 2:
        return 65
    missing.append("profile_activities")
    return 45


def _score_essay_fit(profile, missing: list[str]) -> int:
    if profile.essay_status == profile.EssayStatus.YES:
        return 78
    missing.append("profile_essays")
    return 45


def _score_deadline_fit(
    university: University, risks: list[str], missing: list[str], profile=None
) -> int:
    deadline = normalize_university_deadline(university, profile).normalized_date
    if deadline is None:
        missing.append("university_application_deadline")
        return 52
    days = (deadline - date.today()).days
    if days < 0:
        risks.append("deadline_passed")
        return 20
    if days <= 14:
        risks.append("deadline_close")
        return 38
    if days <= 60:
        return 62
    return 78


def _score_cost_fit(profile, university: University, risks: list[str], missing: list[str]) -> int:
    normalize_university_costs(university)
    if university.tuition_original_amount is not None and university.tuition_usd_amount is None:
        risks.append("cost_conversion_missing")
        missing.append("currency_conversion")
        return 45
    if university.tuition_usd_amount is None and university.total_cost_usd_amount is None:
        missing.append("university_cost")
        return 52
    if profile.scholarship_need == profile.ScholarshipNeed.YES and not (
        university.scholarship_available or university.financial_aid_url or university.scholarships.all()
    ):
        risks.append("aid_data_missing")
        return 50
    return 70


def _fit_score_category(score: int, current_category: str | None, university: University) -> str | None:
    if current_category is None:
        return None

    rate = float(university.acceptance_rate) if university.acceptance_rate is not None else None
    if rate is not None and rate < 5:
        return "reach" if score >= 78 else "dream"
    if rate is not None and rate < 10 and current_category == "safety":
        return "target"
    return current_category


def _source_notes(university: University) -> list[dict]:
    notes = [
        {
            "title": source.source_title,
            "url": source.source_url,
            "is_official": source.is_official,
        }
        for source in university.data_sources.all()
    ]
    if not notes:
        notes = [
            {
                "title": university.name,
                "url": university.official_website,
                "is_official": True,
            }
        ]
    return notes


def _as_int_score(value: float) -> int:
    return max(1, min(100, round(value)))


def _assess_academics(
    profile,
    university: University,
    *,
    student_gpa,
    student_sat,
    student_ielts,
    uni_gpa,
    uni_sat_midpoint,
    strengths: list[str],
    risks: list[str],
    missing_fields: list[str],
    next_actions: list[str],
) -> tuple[float, int, bool, bool]:
    """Score one set of student scores against this university's published data.

    Returns (academic_score, index_shift, compared_any, severe_academic_gap).
    Callers pass throwaway lists when re-running with hypothetical scores so
    that bookkeeping from the hypothetical pass never leaks into the response.
    """
    index_shift = 0
    compared_any = False
    academic_score = 60
    severe_academic_gap = False

    if student_gpa is not None and uni_gpa is not None:
        compared_any = True
        gpa_diff = student_gpa - uni_gpa
        if gpa_diff >= GPA_SIGNIFICANT_DIFF:
            index_shift += 1
            academic_score += 10
            strengths.append("gpa_above_average")
        elif gpa_diff <= -GPA_SIGNIFICANT_DIFF:
            index_shift -= 1
            academic_score -= 18
            risks.append("gpa_below_average")
    elif student_gpa is None:
        academic_score -= 14

    if student_sat is not None:
        if university.sat_p25 and university.sat_p75:
            compared_any = True
            sat_p50 = uni_sat_midpoint or round((university.sat_p25 + university.sat_p75) / 2)
            if student_sat < university.sat_p25:
                severity = sat_gap_severity(student_sat, university.sat_p25)
                index_shift -= 1
                academic_score -= SAT_GAP_PENALTIES.get(severity, 24)
                severe_academic_gap = severity in {
                    STATUS_SUBSTANTIAL_GAP,
                    STATUS_SIGNIFICANT_GAP,
                }
                risks.append("sat_below_p25")
            elif student_sat < sat_p50:
                severity = sat_gap_severity(student_sat, sat_p50)
                academic_score -= min(SAT_GAP_PENALTIES.get(severity, 10), 14)
                risks.append("sat_partial_fit")
            elif student_sat < university.sat_p75:
                academic_score += 7
                strengths.append("sat_competitive")
            else:
                index_shift += 1
                academic_score += 12
                strengths.append("sat_above_p75")
        elif uni_sat_midpoint is not None:
            compared_any = True
            sat_diff = student_sat - uni_sat_midpoint
            if sat_diff >= SAT_SIGNIFICANT_DIFF:
                index_shift += 1
                academic_score += 10
                strengths.append("sat_above_average")
            elif sat_diff < 0:
                severity = sat_gap_severity(student_sat, uni_sat_midpoint)
                if severity in {STATUS_MODERATE_GAP, STATUS_SUBSTANTIAL_GAP, STATUS_SIGNIFICANT_GAP}:
                    index_shift -= 1
                if severity in {STATUS_SUBSTANTIAL_GAP, STATUS_SIGNIFICANT_GAP}:
                    severe_academic_gap = True
                academic_score -= SAT_GAP_PENALTIES.get(severity, 12)
                risks.append("sat_below_average")
    elif uni_sat_midpoint is not None or university.sat_p25 or university.sat_p75:
        academic_score -= 10

    if university.ielts_minimum is not None or university.ielts_competitive is not None:
        if student_ielts is None:
            missing_fields.append("profile_ielts")
            next_actions.append("add_ielts_to_profile")
            academic_score -= 8
        else:
            minimum = float(university.ielts_minimum) if university.ielts_minimum else None
            competitive = (
                float(university.ielts_competitive) if university.ielts_competitive else minimum
            )
            if minimum is not None and student_ielts < minimum:
                severity = ielts_gap_severity(student_ielts, minimum)
                academic_score -= IELTS_MINIMUM_GAP_PENALTIES.get(severity, 28)
                severe_academic_gap = True
                risks.append("ielts_below_minimum")
            elif competitive is not None and student_ielts < competitive:
                severity = ielts_gap_severity(student_ielts, competitive)
                academic_score -= IELTS_COMPETITIVE_GAP_PENALTIES.get(severity, 12)
                risks.append("ielts_below_competitive")
            else:
                academic_score += 7
                strengths.append("ielts_meets_competitive")

    if profile.curriculum_type in {
        profile.CurriculumType.IB,
        profile.CurriculumType.A_LEVEL,
        profile.CurriculumType.AP,
        profile.CurriculumType.ACADEMIC_LYCEUM,
    }:
        strengths.append("curriculum_context_available")
        academic_score += 4
    elif profile.curriculum_type == profile.CurriculumType.UNKNOWN:
        academic_score -= 5

    return academic_score, index_shift, compared_any, severe_academic_gap


def _planned_target_scores(profile) -> dict[str, float]:
    """Parseable target scores from planned exams; used for conditional fit only."""
    targets: dict[str, float] = {}
    plans = profile.exam_plans.get("planned", []) if isinstance(profile.exam_plans, dict) else []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        exam_name = str(plan.get("exam_type") or plan.get("name") or "").upper()
        target = _number(str(plan.get("target_score") or "").replace("+", "").strip())
        if target is None:
            continue
        if "SAT" in exam_name and 400 <= target <= 1600:
            targets["sat"] = max(targets.get("sat", 0), target)
        elif "IELTS" in exam_name and 0 < target <= 9:
            targets["ielts"] = max(targets.get("ielts", 0), target)
    return targets


def calculate_university_fit(profile, university: University) -> dict:
    missing_fields: list[str] = []
    strengths: list[str] = []
    risks: list[str] = []
    next_actions: list[str] = []

    normalization = normalize_profile_academics(profile)
    student_gpa = normalization.normalized_gpa_4
    if student_gpa is None:
        missing_fields.append("profile_gpa")
        next_actions.append("add_gpa_to_profile")
        if normalization.original_gpa_value is not None:
            risks.append("gpa_scale_not_confirmed")

    student_sat = best_sat_score(profile.test_scores)
    if student_sat is None:
        missing_fields.append("profile_sat")
        next_actions.append("add_sat_to_profile")

    student_ielts = best_ielts_score(profile.test_scores)

    if profile.curriculum_type == profile.CurriculumType.UNKNOWN:
        missing_fields.append("profile_curriculum")
        next_actions.append("add_curriculum_context")

    uni_gpa = Decimal(str(university.gpa_average)) if university.gpa_average is not None else None
    if uni_gpa is None:
        missing_fields.append("university_gpa_average")

    uni_sat_midpoint = university.sat_average
    if uni_sat_midpoint is None and university.sat_p25 and university.sat_p75:
        uni_sat_midpoint = round((university.sat_p25 + university.sat_p75) / 2)
    if uni_sat_midpoint is None:
        missing_fields.append("university_sat_average")

    uni_rate = (
        float(university.acceptance_rate) if university.acceptance_rate is not None else None
    )
    if uni_rate is None:
        missing_fields.append("university_acceptance_rate")

    baseline_index = _acceptance_rate_baseline_index(uni_rate) if uni_rate is not None else None

    academic_score, index_shift, compared_any, severe_academic_gap = _assess_academics(
        profile,
        university,
        student_gpa=student_gpa,
        student_sat=student_sat,
        student_ielts=student_ielts,
        uni_gpa=uni_gpa,
        uni_sat_midpoint=uni_sat_midpoint,
        strengths=strengths,
        risks=risks,
        missing_fields=missing_fields,
        next_actions=next_actions,
    )

    conditional_notes, planned_actions = _planned_exam_notes(
        profile,
        normalize_university_deadline(university, profile).normalized_date,
    )
    next_actions.extend(action for action in planned_actions if action not in next_actions)

    category: str | None
    if baseline_index is None and not compared_any:
        category = None
        next_actions.append("verify_university_data")
    else:
        index = baseline_index if baseline_index is not None else 2
        index = max(0, min(3, index + index_shift))
        category = CATEGORY_ORDER[index]
        if uni_rate is None and uni_gpa is None and uni_sat_midpoint is None:
            next_actions.append("verify_university_data")
        elif uni_rate is None or uni_gpa is None or uni_sat_midpoint is None:
            next_actions.append("limited_data_for_category")

    program_score = _score_program_fit(profile, university, strengths, missing_fields)
    profile_score = _score_profile_fit(profile, strengths, missing_fields)
    essay_score = _score_essay_fit(profile, missing_fields)
    deadline_score = _score_deadline_fit(university, risks, missing_fields, profile)
    cost_score = _score_cost_fit(profile, university, risks, missing_fields)

    academic_subscore = _as_int_score(academic_score)
    raw_score = (
        academic_subscore * 0.35
        + program_score * 0.15
        + profile_score * 0.15
        + essay_score * 0.10
        + deadline_score * 0.10
        + cost_score * 0.10
        + (70 if len(missing_fields) <= 3 else 45) * 0.05
    )
    fit_score = _as_int_score(raw_score)
    if severe_academic_gap:
        fit_score = min(fit_score, 55)
    if normalization.confidence == CONFIDENCE_LOW:
        fit_score = min(fit_score, 72)

    # Conditional fit: same estimate re-run with planned retake target scores.
    # Only exposed when it would actually improve on the current estimate, so
    # a planned retake never silently lowers or replaces the current fit.
    conditional_fit_score = None
    conditional_targets: dict[str, float] = {}
    planned_targets = _planned_target_scores(profile)
    conditional_sat = student_sat
    conditional_ielts = student_ielts
    if "sat" in planned_targets and (
        student_sat is None or planned_targets["sat"] > student_sat
    ):
        conditional_sat = int(planned_targets["sat"])
        conditional_targets["sat"] = conditional_sat
    if "ielts" in planned_targets and (
        student_ielts is None or planned_targets["ielts"] > student_ielts
    ):
        conditional_ielts = planned_targets["ielts"]
        conditional_targets["ielts"] = planned_targets["ielts"]
    if conditional_targets:
        scratch_a: list[str] = []
        scratch_b: list[str] = []
        scratch_c: list[str] = []
        scratch_d: list[str] = []
        conditional_academic_raw, _shift, _compared, conditional_severe = _assess_academics(
            profile,
            university,
            student_gpa=student_gpa,
            student_sat=conditional_sat,
            student_ielts=conditional_ielts,
            uni_gpa=uni_gpa,
            uni_sat_midpoint=uni_sat_midpoint,
            strengths=scratch_a,
            risks=scratch_b,
            missing_fields=scratch_c,
            next_actions=scratch_d,
        )
        conditional_raw_score = (
            _as_int_score(conditional_academic_raw) * 0.35
            + program_score * 0.15
            + profile_score * 0.15
            + essay_score * 0.10
            + deadline_score * 0.10
            + cost_score * 0.10
            + (70 if len(missing_fields) <= 3 else 45) * 0.05
        )
        conditional_candidate = _as_int_score(conditional_raw_score)
        if conditional_severe:
            conditional_candidate = min(conditional_candidate, 55)
        if normalization.confidence == CONFIDENCE_LOW:
            conditional_candidate = min(conditional_candidate, 72)
        if conditional_candidate > fit_score:
            conditional_fit_score = conditional_candidate
        else:
            conditional_targets = {}

    category = _fit_score_category(fit_score, category, university)
    confidence = _confidence_from_missing(missing_fields, normalization.confidence)

    missing_fields = list(dict.fromkeys(missing_fields))
    strengths = list(dict.fromkeys(strengths))
    risks = list(dict.fromkeys(risks))
    next_actions = list(dict.fromkeys(next_actions))

    return {
        "fit_score": fit_score,
        "category": category,
        "confidence": confidence,
        "academic_subscore": academic_subscore,
        "program_subscore": program_score,
        "profile_subscore": profile_score,
        "essay_subscore": essay_score,
        "deadline_subscore": deadline_score,
        "cost_subscore": cost_score,
        "strengths": strengths,
        "risks": risks,
        "missing_fields": missing_fields,
        "missing_data": missing_fields,
        "next_actions": next_actions,
        "conditional_notes": conditional_notes,
        "conditional_fit_score": conditional_fit_score,
        "conditional_targets": conditional_targets or None,
        "student_academic_context": {
            "original_gpa_value": normalization.original_gpa_value,
            "original_gpa_scale": normalization.original_gpa_scale,
            "original_gpa_scale_type": normalization.original_gpa_scale_type,
            "normalized_gpa_4": normalization.normalized_gpa_4,
            "normalized_percentage": normalization.normalized_percentage,
            "confidence": normalization.confidence,
            "note": normalization.note,
            "curriculum_type": profile.curriculum_type,
            "curriculum_country": profile.curriculum_country,
        },
        "cost_context": {
            "tuition_original_amount": university.tuition_original_amount
            if university.tuition_original_amount is not None
            else university.tuition_amount,
            "tuition_original_currency": university.tuition_original_currency
            or university.tuition_currency,
            "tuition_usd_amount": university.tuition_usd_amount,
            "total_cost_original_amount": university.total_cost_original_amount,
            "total_cost_original_currency": university.total_cost_original_currency,
            "total_cost_usd_amount": university.total_cost_usd_amount,
            "conversion_rate": university.currency_conversion_rate,
            "conversion_date": university.currency_conversion_date,
            "conversion_source": university.currency_conversion_source,
            "conversion_confidence": university.currency_conversion_confidence,
            "cost_notes": university.cost_notes,
        },
        "source_notes": _source_notes(university),
        "disclaimer": FIT_DISCLAIMER,
    }
