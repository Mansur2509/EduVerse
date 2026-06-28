from .models import University

CATEGORY_ORDER = ("reach", "competitive", "target", "safety")

GPA_SIGNIFICANT_DIFF = 0.3
SAT_SIGNIFICANT_DIFF = 100


def normalize_gpa_to_4(gpa, gpa_scale) -> float | None:
    if gpa is None or gpa_scale is None:
        return None
    try:
        scale = float(gpa_scale)
    except (TypeError, ValueError):
        return None
    if scale <= 0:
        return None
    return float(gpa) / scale * 4.0


def best_sat_score(test_scores) -> int | None:
    if not isinstance(test_scores, dict):
        return None
    value = test_scores.get("sat") or test_scores.get("SAT")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _acceptance_rate_baseline_index(acceptance_rate: float) -> int:
    if acceptance_rate <= 15:
        return 0
    if acceptance_rate <= 35:
        return 1
    if acceptance_rate <= 60:
        return 2
    return 3


def calculate_university_fit(profile, university: University) -> dict:
    missing_fields: list[str] = []
    strengths: list[str] = []
    risks: list[str] = []
    next_actions: list[str] = []

    student_gpa = normalize_gpa_to_4(profile.gpa, profile.gpa_scale)
    if student_gpa is None:
        missing_fields.append("profile_gpa")
        next_actions.append("add_gpa_to_profile")

    student_sat = best_sat_score(profile.test_scores)
    if student_sat is None:
        missing_fields.append("profile_sat")
        next_actions.append("add_sat_to_profile")

    uni_gpa = float(university.gpa_average) if university.gpa_average is not None else None
    if uni_gpa is None:
        missing_fields.append("university_gpa_average")

    uni_sat = university.sat_average
    if uni_sat is None:
        missing_fields.append("university_sat_average")

    uni_rate = (
        float(university.acceptance_rate) if university.acceptance_rate is not None else None
    )
    if uni_rate is None:
        missing_fields.append("university_acceptance_rate")

    baseline_index = _acceptance_rate_baseline_index(uni_rate) if uni_rate is not None else None

    index_shift = 0
    compared_any = False

    if student_gpa is not None and uni_gpa is not None:
        compared_any = True
        gpa_diff = round(student_gpa - uni_gpa, 4)
        if gpa_diff >= GPA_SIGNIFICANT_DIFF:
            index_shift += 1
            strengths.append("gpa_above_average")
        elif gpa_diff <= -GPA_SIGNIFICANT_DIFF:
            index_shift -= 1
            risks.append("gpa_below_average")

    if student_sat is not None and uni_sat is not None:
        compared_any = True
        sat_diff = student_sat - uni_sat
        if sat_diff >= SAT_SIGNIFICANT_DIFF:
            index_shift += 1
            strengths.append("sat_above_average")
        elif sat_diff <= -SAT_SIGNIFICANT_DIFF:
            index_shift -= 1
            risks.append("sat_below_average")

    category: str | None
    if baseline_index is None and not compared_any:
        category = None
        next_actions.append("verify_university_data")
    else:
        index = baseline_index if baseline_index is not None else 2
        index = max(0, min(3, index + index_shift))
        category = CATEGORY_ORDER[index]
        if uni_rate is None and uni_gpa is None and uni_sat is None:
            next_actions.append("verify_university_data")
        elif uni_rate is None or uni_gpa is None or uni_sat is None:
            # A category was assigned from whatever verified university stat
            # is available, but at least one other stat is still unverified.
            # Flag this explicitly so the UI never presents a partial-data
            # category as a fully-confident classification.
            next_actions.append("limited_data_for_category")

    source_notes = [
        {
            "title": source.source_title,
            "url": source.source_url,
            "is_official": source.is_official,
        }
        for source in university.data_sources.all()
    ]
    if not source_notes:
        source_notes = [
            {
                "title": university.name,
                "url": university.official_website,
                "is_official": True,
            }
        ]

    return {
        "category": category,
        "strengths": strengths,
        "risks": risks,
        "missing_fields": missing_fields,
        "next_actions": next_actions,
        "source_notes": source_notes,
    }
