import re
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .academic_normalization import (
    apply_academic_normalization,
    infer_gpa_scale_type,
    normalize_profile_academics,
)
from .curriculum_rigor import calculate_curriculum_rigor, calculate_major_curriculum_fit
from .models import (
    Activity,
    EssayDraft,
    Honor,
    Olympiad,
    PortfolioProject,
    Recommender,
    ResearchProject,
    Sport,
    StudentProfile,
    Volunteer,
)
from .readiness import calculate_application_readiness
from .services import (
    REQUIRED_ONBOARDING_SECTIONS,
    calculate_profile_completion,
    ensure_profile_records,
)

TELEGRAM_PATTERN = re.compile(r"^@?[A-Za-z0-9_]{5,32}$")
PHONE_PATTERN = re.compile(r"^\+?[0-9 ()-]{7,24}$")
ACTIVITY_KEYS = {
    "extracurriculars",
    "honors",
    "sports",
    "olympiads",
    "research_projects",
    "mun_debate",
    "volunteering",
    "leadership",
    "work_internships",
}
SHORT_LIST_ITEM_MAX_LENGTH = 120
MAJOR_LIST_ITEM_MAX_LENGTH = 150
UNIVERSITY_LIST_ITEM_MAX_LENGTH = 180
PROFILE_LIST_ITEM_MAX_LENGTH = 500
SUPPORT_LIST_ITEM_MAX_LENGTH = 1000


def validate_string_list(
    value,
    *,
    field_name: str,
    max_items: int = 20,
    max_length: int = PROFILE_LIST_ITEM_MAX_LENGTH,
) -> list[str]:
    if not isinstance(value, list):
        raise serializers.ValidationError(f"{field_name} must be a list.")
    if len(value) > max_items:
        raise serializers.ValidationError(f"{field_name} may contain at most {max_items} items.")

    normalized_items = []
    for item in value:
        if not isinstance(item, str):
            raise serializers.ValidationError(f"Every {field_name} item must be text.")
        normalized_item = item.strip()
        if not normalized_item:
            continue
        if len(normalized_item) > max_length:
            raise serializers.ValidationError(
                f"Each {field_name} item must be {max_length} characters or fewer."
            )
        if normalized_item not in normalized_items:
            normalized_items.append(normalized_item)
    return normalized_items


class ProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=180)
    birth_date = serializers.DateField(required=False, allow_null=True)
    country = serializers.CharField(required=False, allow_blank=True, max_length=100)
    city = serializers.CharField(required=False, allow_blank=True, max_length=120)
    school_or_university = serializers.CharField(required=False, allow_blank=True, max_length=240)
    grade = serializers.CharField(required=False, allow_blank=True, max_length=50)
    expected_graduation_year = serializers.IntegerField(required=False, allow_null=True)
    education_status = serializers.CharField(required=False, allow_blank=True, max_length=120)
    gpa = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=5,
        decimal_places=2,
    )
    gpa_scale = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=5,
        decimal_places=2,
    )
    original_gpa_value = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=5,
        decimal_places=2,
    )
    original_gpa_scale = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=5,
        decimal_places=2,
    )
    original_gpa_scale_type = serializers.ChoiceField(
        choices=StudentProfile.GpaScaleType.choices,
        required=False,
    )
    normalized_gpa_4 = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        read_only=True,
    )
    normalized_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )
    curriculum_type = serializers.ChoiceField(
        choices=StudentProfile.CurriculumType.choices,
        required=False,
    )
    curriculum_country = serializers.CharField(required=False, allow_blank=True, max_length=100)
    course_rigor_level = serializers.ChoiceField(
        choices=StudentProfile.CourseRigorLevel.choices,
        required=False,
    )
    ap_courses_count = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=40)
    ib_courses_count = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=40)
    a_level_subjects_count = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=40
    )
    honors_courses_count = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=40
    )
    academic_normalization_confidence = serializers.ChoiceField(
        choices=StudentProfile.NormalizationConfidence.choices,
        read_only=True,
    )
    academic_normalization_note = serializers.CharField(read_only=True)
    intended_degree = serializers.CharField(required=False, allow_blank=True, max_length=120)
    target_countries = serializers.ListField(
        child=serializers.CharField(max_length=120),
        required=False,
    )
    intended_majors = serializers.ListField(
        child=serializers.CharField(max_length=MAJOR_LIST_ITEM_MAX_LENGTH),
        required=False,
    )
    target_universities = serializers.ListField(
        child=serializers.CharField(max_length=180),
        required=False,
    )
    university_unsure = serializers.BooleanField(required=False)
    major_unsure = serializers.BooleanField(required=False)
    scholarship_need = serializers.ChoiceField(
        choices=StudentProfile.ScholarshipNeed.choices,
        required=False,
    )
    annual_budget_amount = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
    )
    annual_budget_currency = serializers.CharField(required=False, allow_blank=True, max_length=10)
    budget_flexibility = serializers.ChoiceField(
        choices=StudentProfile.BudgetFlexibility.choices,
        required=False,
    )
    interests = serializers.ListField(
        child=serializers.CharField(max_length=PROFILE_LIST_ITEM_MAX_LENGTH),
        required=False,
    )
    languages = serializers.ListField(
        child=serializers.CharField(max_length=120),
        required=False,
    )
    test_scores = serializers.JSONField(required=False)
    exam_plans = serializers.JSONField(required=False)
    preparation_needs = serializers.ListField(
        child=serializers.CharField(max_length=PROFILE_LIST_ITEM_MAX_LENGTH),
        required=False,
    )
    activities = serializers.JSONField(required=False)
    essay_status = serializers.ChoiceField(
        choices=StudentProfile.EssayStatus.choices,
        required=False,
    )
    essay_stage = serializers.CharField(required=False, allow_blank=True, max_length=120)
    support_priorities = serializers.ListField(
        child=serializers.CharField(max_length=SUPPORT_LIST_ITEM_MAX_LENGTH),
        required=False,
    )
    interested_classes = serializers.ListField(
        child=serializers.CharField(max_length=UNIVERSITY_LIST_ITEM_MAX_LENGTH),
        required=False,
    )
    ap_interests = serializers.ListField(
        child=serializers.CharField(max_length=UNIVERSITY_LIST_ITEM_MAX_LENGTH),
        required=False,
    )
    career_interests = serializers.ListField(
        child=serializers.CharField(max_length=PROFILE_LIST_ITEM_MAX_LENGTH),
        required=False,
    )
    mun_debate_interest = serializers.BooleanField(required=False)
    research_interest = serializers.BooleanField(required=False)
    finance_literacy_interest = serializers.BooleanField(required=False)
    onboarding_sections = serializers.ListField(
        child=serializers.ChoiceField(choices=REQUIRED_ONBOARDING_SECTIONS),
        required=False,
    )
    onboarding_version = serializers.IntegerField(read_only=True)
    onboarding_completed_at = serializers.DateTimeField(read_only=True)
    telegram_username = serializers.CharField(required=False, allow_blank=True, max_length=33)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        profile = instance
        _, preferences = ensure_profile_records(profile.user)
        exam_plans = profile.exam_plans if isinstance(profile.exam_plans, dict) else {}
        normalization = normalize_profile_academics(profile)
        return {
            "id": profile.user_id,
            "email": profile.user.email,
            "role": profile.user.role,
            "full_name": profile.full_name,
            "birth_date": profile.birth_date,
            "country": profile.country,
            "city": profile.city,
            "school_or_university": profile.school_or_university,
            "grade": profile.grade,
            "expected_graduation_year": profile.expected_graduation_year,
            "education_status": profile.education_status,
            "gpa": profile.gpa,
            "gpa_scale": profile.gpa_scale,
            "original_gpa_value": normalization.original_gpa_value,
            "original_gpa_scale": normalization.original_gpa_scale,
            "original_gpa_scale_type": normalization.original_gpa_scale_type,
            "normalized_gpa_4": normalization.normalized_gpa_4,
            "normalized_percentage": normalization.normalized_percentage,
            "curriculum_type": profile.curriculum_type,
            "curriculum_country": profile.curriculum_country,
            "course_rigor_level": profile.course_rigor_level,
            "ap_courses_count": profile.ap_courses_count,
            "ib_courses_count": profile.ib_courses_count,
            "a_level_subjects_count": profile.a_level_subjects_count,
            "honors_courses_count": profile.honors_courses_count,
            "curriculum_rigor": vars(calculate_curriculum_rigor(profile)),
            "major_curriculum_fit": calculate_major_curriculum_fit(
                profile,
                profile.intended_major or (profile.intended_majors[0] if profile.intended_majors else None),
            ),
            "academic_normalization_confidence": normalization.confidence,
            "academic_normalization_note": normalization.note,
            "intended_degree": profile.intended_degree,
            "target_countries": profile.target_countries,
            "intended_majors": profile.intended_majors,
            "target_universities": profile.target_universities,
            "university_unsure": profile.university_unsure,
            "major_unsure": profile.major_unsure,
            "scholarship_need": profile.scholarship_need,
            "annual_budget_amount": profile.annual_budget_amount,
            "annual_budget_currency": profile.annual_budget_currency,
            "budget_flexibility": profile.budget_flexibility,
            "interests": preferences.interests,
            "languages": profile.languages,
            "test_scores": profile.test_scores,
            "exam_plans": {
                "taken": exam_plans.get("taken", []),
                "planned": exam_plans.get("planned", []),
            },
            "preparation_needs": profile.preparation_needs,
            "activities": profile.activities,
            "essay_status": profile.essay_status,
            "essay_stage": profile.essay_stage,
            "support_priorities": profile.support_priorities,
            "interested_classes": preferences.interested_classes,
            "ap_interests": preferences.ap_interests,
            "career_interests": preferences.career_interests,
            "mun_debate_interest": preferences.mun_debate_interest,
            "research_interest": preferences.research_interest,
            "finance_literacy_interest": preferences.finance_literacy_interest,
            "onboarding_sections": profile.onboarding_sections,
            "onboarding_version": profile.onboarding_version,
            "onboarding_completed_at": profile.onboarding_completed_at,
            "telegram_username": profile.telegram_username,
            "phone": profile.phone,
            "updated_at": profile.updated_at,
        }

    def validate_birth_date(self, value):
        if value is None:
            return value
        if value > date.today():
            raise serializers.ValidationError("Birth date cannot be in the future.")
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 10 or age > 100:
            raise serializers.ValidationError("Birth date is outside the supported range.")
        return value

    def validate_expected_graduation_year(self, value):
        if value is None:
            return value
        current_year = date.today().year
        if value < current_year - 1 or value > current_year + 15:
            raise serializers.ValidationError("Graduation year is outside the supported range.")
        return value

    def validate_target_countries(self, value):
        return validate_string_list(
            value,
            field_name="target countries",
            max_length=SHORT_LIST_ITEM_MAX_LENGTH,
        )

    def validate_intended_majors(self, value):
        return validate_string_list(
            value,
            field_name="intended majors",
            max_length=MAJOR_LIST_ITEM_MAX_LENGTH,
        )

    def validate_target_universities(self, value):
        return validate_string_list(
            value,
            field_name="target universities",
            max_items=30,
            max_length=UNIVERSITY_LIST_ITEM_MAX_LENGTH,
        )

    def validate_interests(self, value):
        return validate_string_list(
            value,
            field_name="interests",
            max_items=30,
            max_length=PROFILE_LIST_ITEM_MAX_LENGTH,
        )

    def validate_languages(self, value):
        return validate_string_list(
            value,
            field_name="languages",
            max_length=SHORT_LIST_ITEM_MAX_LENGTH,
        )

    def validate_test_scores(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Test scores must be an object.")
        if len(value) > 20:
            raise serializers.ValidationError("Test scores may contain at most 20 entries.")

        normalized_scores = {}
        for key, score in value.items():
            if not isinstance(key, str) or not key.strip() or len(key.strip()) > 40:
                raise serializers.ValidationError("Test score names must be short text values.")
            normalized_key = key.strip().lower()
            if isinstance(score, str):
                normalized_score = score.strip()
                if len(normalized_score) > 120:
                    raise serializers.ValidationError("Test score values must be 120 characters or fewer.")
            elif isinstance(score, int | float) and not isinstance(score, bool):
                normalized_score = score
            elif isinstance(score, list):
                normalized_score = validate_string_list(
                    score,
                    field_name=f"{normalized_key} scores",
                    max_items=20,
                    max_length=SHORT_LIST_ITEM_MAX_LENGTH,
                )
            else:
                raise serializers.ValidationError(
                    "Test score values must be text, a number, or a list of text values."
                )
            normalized_scores[normalized_key] = normalized_score

        numeric_ranges = {
            "sat": (400, 1600),
            "ielts": (0, 9),
            "toefl": (0, 120),
        }
        for key, (minimum, maximum) in numeric_ranges.items():
            score = normalized_scores.get(key)
            if isinstance(score, str):
                try:
                    numeric_score = float(score)
                except ValueError as error:
                    raise serializers.ValidationError(
                        {key: f"{key.upper()} score must be numeric."}
                    ) from error
                score = int(numeric_score) if numeric_score.is_integer() else numeric_score
                normalized_scores[key] = score
            if isinstance(score, int | float) and not minimum <= score <= maximum:
                raise serializers.ValidationError(
                    {key: f"{key.upper()} score must be between {minimum} and {maximum}."}
                )
        return normalized_scores

    def validate_exam_plans(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Exam plans must be an object.")
        unknown_keys = set(value) - {"taken", "planned"}
        if unknown_keys:
            raise serializers.ValidationError("Exam plans contain unsupported fields.")

        taken = validate_string_list(
            value.get("taken", []),
            field_name="taken exams",
            max_length=SHORT_LIST_ITEM_MAX_LENGTH,
        )
        planned = value.get("planned", [])
        if not isinstance(planned, list) or len(planned) > 12:
            raise serializers.ValidationError("Planned exams must be a list with at most 12 items.")

        normalized_plans = []
        for plan in planned:
            if not isinstance(plan, dict):
                raise serializers.ValidationError("Every planned exam must be an object.")
            name = str(plan.get("name", "")).strip()
            exam_date = str(plan.get("date", "")).strip()
            target_score = str(plan.get("target_score", "")).strip()
            exam_type = str(plan.get("exam_type", "")).strip().upper()
            planned_retake_month = str(plan.get("planned_retake_month", "")).strip()
            current_score = str(plan.get("current_score", "")).strip()
            test_status = str(plan.get("test_status", "")).strip()
            if not name or len(name) > 80:
                raise serializers.ValidationError("Every planned exam needs a short name.")
            if exam_date:
                try:
                    parsed_date = datetime.strptime(exam_date, "%Y-%m-%d").date()
                except ValueError as error:
                    raise serializers.ValidationError("Exam dates must use YYYY-MM-DD.") from error
                if parsed_date < date.today() or parsed_date.year > date.today().year + 5:
                    raise serializers.ValidationError("Exam date is outside the supported range.")
            if len(target_score) > 40:
                raise serializers.ValidationError("Target scores must be 40 characters or fewer.")
            if exam_type and exam_type not in {"SAT", "AP", "ACT", "IELTS", "TOEFL"}:
                raise serializers.ValidationError("Exam type is not supported.")
            if planned_retake_month:
                try:
                    datetime.strptime(planned_retake_month, "%Y-%m")
                except ValueError as error:
                    raise serializers.ValidationError(
                        "Planned retake month must use YYYY-MM."
                    ) from error
            for field_name, field_value in {
                "current_score": current_score,
                "test_status": test_status,
            }.items():
                if len(field_value) > 80:
                    raise serializers.ValidationError(
                        f"{field_name.replace('_', ' ').title()} must be 80 characters or fewer."
                    )
            normalized_plan = {"name": name, "date": exam_date, "target_score": target_score}
            if exam_type:
                normalized_plan["exam_type"] = exam_type
            if planned_retake_month:
                normalized_plan["planned_retake_month"] = planned_retake_month
            if current_score:
                normalized_plan["current_score"] = current_score
            if test_status:
                normalized_plan["test_status"] = test_status
            if "planned_retake" in plan:
                normalized_plan["planned_retake"] = bool(plan.get("planned_retake"))
            normalized_plans.append(normalized_plan)
        return {"taken": taken, "planned": normalized_plans}

    def validate_preparation_needs(self, value):
        return validate_string_list(
            value,
            field_name="preparation needs",
            max_items=20,
            max_length=PROFILE_LIST_ITEM_MAX_LENGTH,
        )

    def validate_support_priorities(self, value):
        return validate_string_list(
            value,
            field_name="support priorities",
            max_items=20,
            max_length=SUPPORT_LIST_ITEM_MAX_LENGTH,
        )

    def validate_interested_classes(self, value):
        return validate_string_list(
            value,
            field_name="interested classes",
            max_items=30,
            max_length=UNIVERSITY_LIST_ITEM_MAX_LENGTH,
        )

    def validate_ap_interests(self, value):
        return validate_string_list(
            value,
            field_name="AP interests",
            max_items=20,
            max_length=UNIVERSITY_LIST_ITEM_MAX_LENGTH,
        )

    def validate_career_interests(self, value):
        return validate_string_list(
            value,
            field_name="career interests",
            max_items=30,
            max_length=PROFILE_LIST_ITEM_MAX_LENGTH,
        )

    def validate_activities(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Activities must be an object.")
        if set(value) - ACTIVITY_KEYS:
            raise serializers.ValidationError("Activities contain unsupported fields.")
        return {
            key: validate_string_list(
                value.get(key, []),
                field_name=key.replace("_", " "),
                max_items=20,
                max_length=PROFILE_LIST_ITEM_MAX_LENGTH,
            )
            for key in ACTIVITY_KEYS
        }

    def validate_onboarding_sections(self, value):
        return list(dict.fromkeys(value))

    def validate_telegram_username(self, value):
        normalized_value = value.strip()
        if normalized_value and not TELEGRAM_PATTERN.fullmatch(normalized_value):
            raise serializers.ValidationError("Enter a valid Telegram username.")
        if normalized_value and not normalized_value.startswith("@"):
            normalized_value = f"@{normalized_value}"
        return normalized_value

    def validate_phone(self, value):
        normalized_value = value.strip()
        if normalized_value and not PHONE_PATTERN.fullmatch(normalized_value):
            raise serializers.ValidationError("Enter a valid phone number.")
        return normalized_value

    def validate(self, attrs):
        profile = self.instance
        gpa = attrs.get("gpa", profile.gpa if profile else None)
        gpa_scale = attrs.get("gpa_scale", profile.gpa_scale if profile else None)
        original_gpa = attrs.get(
            "original_gpa_value",
            profile.original_gpa_value if profile else None,
        )
        original_scale = attrs.get(
            "original_gpa_scale",
            profile.original_gpa_scale if profile else None,
        )
        if (gpa is None) != (gpa_scale is None):
            raise serializers.ValidationError(
                {"gpa": "GPA and GPA scale must be provided together."}
            )
        if gpa is not None:
            if gpa <= Decimal("0") or gpa_scale <= Decimal("0") or gpa_scale > Decimal("100"):
                raise serializers.ValidationError({"gpa": "GPA values are outside the supported range."})
            if gpa > gpa_scale:
                raise serializers.ValidationError({"gpa": "GPA cannot exceed its scale."})
        if (original_gpa is None) != (original_scale is None):
            raise serializers.ValidationError(
                {"original_gpa_value": "Original GPA value and scale must be provided together."}
            )
        if original_gpa is not None:
            if (
                original_gpa <= Decimal("0")
                or original_scale <= Decimal("0")
                or original_scale > Decimal("100")
            ):
                raise serializers.ValidationError(
                    {"original_gpa_value": "Original GPA values are outside the supported range."}
                )
            if original_gpa > original_scale:
                raise serializers.ValidationError(
                    {"original_gpa_value": "Original GPA cannot exceed its scale."}
                )
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        profile, preferences = ensure_profile_records(instance.user)
        interests = validated_data.pop("interests", None)
        preference_fields = {
            field: validated_data.pop(field)
            for field in (
                "interested_classes",
                "ap_interests",
                "career_interests",
                "mun_debate_interest",
                "research_interest",
                "finance_literacy_interest",
            )
            if field in validated_data
        }
        for field, value in validated_data.items():
            setattr(profile, field, value)

        if "gpa" in validated_data or "gpa_scale" in validated_data:
            profile.original_gpa_value = profile.gpa
            profile.original_gpa_scale = profile.gpa_scale
            if "original_gpa_scale_type" not in validated_data:
                profile.original_gpa_scale_type = infer_gpa_scale_type(
                    profile.gpa,
                    profile.gpa_scale,
                    profile.original_gpa_scale_type,
                )

        if "original_gpa_value" in validated_data or "original_gpa_scale" in validated_data:
            profile.gpa = profile.original_gpa_value
            profile.gpa_scale = profile.original_gpa_scale
            if "original_gpa_scale_type" not in validated_data:
                profile.original_gpa_scale_type = infer_gpa_scale_type(
                    profile.original_gpa_value,
                    profile.original_gpa_scale,
                    profile.original_gpa_scale_type,
                )

        if "intended_majors" in validated_data:
            profile.intended_major = (
                validated_data["intended_majors"][0] if validated_data["intended_majors"] else ""
            )
        if "test_scores" in validated_data:
            sat_score = validated_data["test_scores"].get("sat", "")
            ielts_score = validated_data["test_scores"].get("ielts", "")
            profile.sat_level = str(sat_score) if sat_score != "" else ""
            profile.ielts_level = str(ielts_score) if ielts_score != "" else ""

        apply_academic_normalization(profile)
        profile.save()
        if interests is not None:
            preferences.interests = interests
        for field, value in preference_fields.items():
            setattr(preferences, field, value)
        if interests is not None or preference_fields:
            preferences.save()
        return profile


class ProfileCompletionSerializer(serializers.Serializer):
    percentage = serializers.IntegerField(read_only=True)
    completed_fields = serializers.IntegerField(read_only=True)
    total_fields = serializers.IntegerField(read_only=True)
    missing_fields = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    missing_sections = serializers.ListField(child=serializers.CharField(), read_only=True)
    required_fields = serializers.ListField(child=serializers.CharField(), read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    can_complete = serializers.BooleanField(read_only=True)

    @classmethod
    def for_profile(cls, profile):
        _, preferences = ensure_profile_records(profile.user)
        completion = calculate_profile_completion(profile, preferences)
        return cls(completion)


class ApplicationReadinessSerializer(serializers.Serializer):
    stars = serializers.IntegerField(read_only=True)
    level = serializers.CharField(read_only=True)
    score_components = serializers.DictField(
        child=serializers.IntegerField(),
        read_only=True,
    )
    categories = serializers.ListField(child=serializers.DictField(), read_only=True)
    strengths = serializers.ListField(child=serializers.CharField(), read_only=True)
    improvements = serializers.ListField(child=serializers.CharField(), read_only=True)
    reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    next_actions = serializers.ListField(child=serializers.CharField(), read_only=True)
    cap_reason = serializers.CharField(read_only=True)
    comparison_status = serializers.CharField(read_only=True)
    compared_universities = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    official_sources = serializers.ListField(
        child=serializers.DictField(),
        read_only=True,
    )

    @classmethod
    def for_profile(cls, profile):
        _, preferences = ensure_profile_records(profile.user)
        readiness = calculate_application_readiness(profile, preferences)
        return cls(readiness)


# Legacy router serializer retained for compatibility with `/api/v1/profiles/me/`.
StudentProfileSerializer = ProfileSerializer


# Serializers for structured profile items


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            "id",
            "title",
            "role",
            "organization",
            "category",
            "start_date",
            "end_date",
            "year",
            "hours_per_week",
            "weeks_per_year",
            "scale",
            "impact_number",
            "description",
            "proof_link",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class HonorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Honor
        fields = [
            "id",
            "title",
            "issuing_organization",
            "level",
            "year",
            "result_rank",
            "description",
            "proof_link",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OlympiadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Olympiad
        fields = [
            "id",
            "name",
            "subject",
            "level",
            "year",
            "result",
            "rank_percentile",
            "description",
            "proof_link",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = [
            "id",
            "sport_name",
            "level",
            "years_trained",
            "peak_result",
            "competition_name",
            "description",
            "proof_link",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ResearchProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProject
        fields = [
            "id",
            "title",
            "field",
            "research_question",
            "sample_size",
            "countries_region",
            "methods_used",
            "current_stage",
            "manuscript_link",
            "publication_status",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EssayDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssayDraft
        fields = [
            "id",
            "essay_type",
            "school_program",
            "status",
            "word_limit",
            "draft_status",
            "last_reviewed_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PortfolioProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioProject
        fields = [
            "id",
            "title",
            "project_type",
            "link",
            "tech_stack",
            "users_impact",
            "status",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class VolunteerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volunteer
        fields = [
            "id",
            "title",
            "role",
            "organization",
            "start_date",
            "end_date",
            "hours_per_week",
            "weeks_per_year",
            "scale",
            "impact_number",
            "beneficiaries",
            "description",
            "proof_link",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RecommenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommender
        fields = [
            "id",
            "name",
            "relationship_role",
            "status",
            "requested_date",
            "submitted_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
