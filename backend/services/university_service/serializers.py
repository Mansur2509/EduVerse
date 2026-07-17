from rest_framework import serializers

from common.xlsx_security import validate_xlsx_archive
from services.user_profile_service.models import UserPreference

from .budget import compare_cost_to_budget
from .import_jobs import MAX_IMPORT_UPLOAD_BYTES
from .major_matching import build_program_recommendation_summary
from .models import (
    ExcludedUniversity,
    PinnedUniversity,
    SavedUniversity,
    University,
    UniversityDataSource,
    UniversityFieldVerification,
    UniversityImportJob,
    UniversityModerationRecord,
    UniversityProgram,
    UniversityRequirement,
    UniversityScholarship,
    UniversitySubjectRanking,
)
from .program_display import format_program_display_names


class UniversityDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityDataSource
        fields = "__all__"


class UniversityProgramSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    subject_rankings = serializers.SerializerMethodField()

    class Meta:
        model = UniversityProgram
        fields = (
            "id",
            "name",
            "display_name",
            "major_cluster",
            "degree_level",
            "department_or_school",
            "official_url",
            "source_url",
            "program_requirements_summary",
            "essay_requirements",
            "portfolio_required",
            "research_heavy",
            "stem_heavy",
            "interdisciplinary",
            "source_confidence",
            "last_verified_date",
            "subject_rankings",
        )

    def get_display_name(self, obj) -> str:
        return (format_program_display_names([obj.name]) or [obj.name])[0]

    def get_subject_rankings(self, obj):
        return UniversitySubjectRankingSerializer(obj.subject_rankings.all(), many=True).data


class UniversitySubjectRankingSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source="program.name", read_only=True, default=None)

    class Meta:
        model = UniversitySubjectRanking
        fields = (
            "id",
            "program",
            "program_name",
            "subject_area",
            "major_cluster",
            "rank",
            "source_name",
            "source_url",
            "ranking_year",
            "last_verified_date",
            "confidence",
            "notes",
        )


class UniversityRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityRequirement
        exclude = ("university",)


class UniversityScholarshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityScholarship
        exclude = ("university",)


class UniversityFieldVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityFieldVerification
        fields = ("field_name", "status", "source_url", "last_verified_date", "note")


class UniversityShortlistMixin:
    def get_is_shortlisted(self, obj) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        saved_ids = self.context.get("saved_university_ids")
        if saved_ids is not None:
            return obj.id in saved_ids
        return SavedUniversity.objects.filter(user=user, university=obj).exists()


class UniversityListSerializer(UniversityShortlistMixin, serializers.ModelSerializer):
    """Compact catalog-card payload.

    The detail serializer intentionally exposes nested public profile data, but
    a paginated catalog page only needs summary fields. Keeping this projection
    narrow prevents imported long-text/source records from making `/list` slow.
    """

    is_shortlisted = serializers.SerializerMethodField()
    majors_list = serializers.SerializerMethodField()

    class Meta:
        model = University
        fields = (
            "id",
            "name",
            "slug",
            "country",
            "city",
            "official_website",
            "summary",
            "institution_type",
            "is_published",
            "is_demo",
            "acceptance_rate",
            "gpa_average",
            "sat_average",
            "sat_p25",
            "sat_p50",
            "sat_p75",
            "ielts_minimum",
            "ielts_competitive",
            "test_policy",
            "tuition_amount",
            "tuition_currency",
            "tuition_original_amount",
            "tuition_original_currency",
            "tuition_usd_amount",
            "total_cost_original_amount",
            "total_cost_original_currency",
            "total_cost_usd_amount",
            "currency_conversion_confidence",
            "application_deadline",
            "scholarship_available",
            "qs_ranking",
            "qs_ranking_year",
            "global_rank",
            "the_rank",
            "national_rank",
            "ranking_source",
            "ranking_year",
            "ranking_confidence",
            "majors_list",
            "admissions_cycle_target",
            "is_shortlisted",
            "cover_image_url",
            "cover_image_source_title",
            "cover_image_source_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_majors_list(self, obj) -> list[str]:
        majors = obj.majors_list if isinstance(obj.majors_list, list) else []
        return majors[:8]


class UniversitySerializer(UniversityShortlistMixin, serializers.ModelSerializer):
    programs = UniversityProgramSerializer(many=True, read_only=True)
    program_display_names = serializers.SerializerMethodField()
    subject_rankings = UniversitySubjectRankingSerializer(many=True, read_only=True)
    program_matching = serializers.SerializerMethodField()
    requirements = UniversityRequirementSerializer(many=True, read_only=True)
    scholarships = UniversityScholarshipSerializer(many=True, read_only=True)
    data_sources = UniversityDataSourceSerializer(many=True, read_only=True)
    field_verifications = UniversityFieldVerificationSerializer(many=True, read_only=True)
    is_shortlisted = serializers.SerializerMethodField()
    budget_comparison = serializers.SerializerMethodField()

    class Meta:
        model = University
        # Keep this public/detail contract explicit. Import and AI-context fields
        # intentionally remain server-side even when new model fields are added.
        fields = (
            "id",
            "name",
            "slug",
            "country",
            "city",
            "official_website",
            "summary",
            "institution_type",
            "is_published",
            "is_demo",
            "acceptance_rate",
            "gpa_average",
            "gpa_average_scale",
            "sat_average",
            "sat_p25",
            "sat_p50",
            "sat_p75",
            "ielts_minimum",
            "ielts_competitive",
            "test_policy",
            "standardized_testing_policy_text",
            "tuition_amount",
            "tuition_currency",
            "tuition_original_amount",
            "tuition_original_currency",
            "tuition_usd_amount",
            "total_cost_original_amount",
            "total_cost_original_currency",
            "total_cost_usd_amount",
            "currency_conversion_rate",
            "currency_conversion_date",
            "currency_conversion_source",
            "currency_conversion_confidence",
            "cost_notes",
            "application_deadline",
            "deadlines_text",
            "admissions_cycle_target",
            "scholarship_available",
            "essay_requirements",
            "cover_image_url",
            "cover_image_source_title",
            "cover_image_source_url",
            "application_requirements",
            "ap_recommendations",
            "financial_aid_notes",
            "scholarships_text",
            "need_based_aid_notes",
            "merit_scholarship_notes",
            "other_scholarships_notes",
            "scholarship_links_text",
            "data_quality_notes",
            "qs_ranking",
            "qs_ranking_year",
            "qs_overall_score",
            "global_rank",
            "the_rank",
            "national_rank",
            "ranking_source",
            "ranking_source_url",
            "ranking_year",
            "ranking_last_verified_date",
            "ranking_confidence",
            "national_ranking_source",
            "admissions_url",
            "financial_aid_url",
            "application_portal_url",
            "international_office_url",
            "virtual_info_session_url",
            "admissions_website",
            "majors_list",
            "programs",
            "program_display_names",
            "subject_rankings",
            "program_matching",
            "requirements",
            "scholarships",
            "data_sources",
            "field_verifications",
            "is_shortlisted",
            "budget_comparison",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def get_budget_comparison(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        profile = getattr(user, "student_profile", None)
        if profile is None:
            return None
        return compare_cost_to_budget(obj, profile)

    def get_program_display_names(self, obj) -> list[str]:
        # `.order_by()` builds a new queryset and bypasses Django's
        # prefetch_related cache for `programs`, forcing an extra query per
        # university; sorting the already-fetched list in Python reuses it.
        programs = sorted(obj.programs.all(), key=lambda program: program.id)
        return format_program_display_names(program.name for program in programs)

    def get_program_matching(self, obj):
        if not self.context.get("include_program_matching"):
            return None
        request = self.context.get("request")
        user = getattr(request, "user", None)
        profile = getattr(user, "student_profile", None) if user and user.is_authenticated else None
        if profile is None:
            return None
        return build_program_recommendation_summary(profile, obj)


class SavedUniversitySerializer(serializers.ModelSerializer):
    university = UniversitySerializer(read_only=True)

    class Meta:
        model = SavedUniversity
        fields = ("id", "university", "created_at")
        read_only_fields = ("id", "university", "created_at")


class ShortlistUniversitySummarySerializer(serializers.ModelSerializer):
    """Minimal university fields for dropdown/linking UI -- deliberately skips
    the full `UniversitySerializer`'s nested programs/rankings/requirements/
    scholarships/data_sources, which is expensive to serialize across an
    entire shortlist and unnecessary when the caller only needs a label.
    """

    class Meta:
        model = University
        fields = ("id", "slug", "name", "country", "city")
        read_only_fields = fields


class SavedUniversityLiteSerializer(serializers.ModelSerializer):
    university = ShortlistUniversitySummarySerializer(read_only=True)

    class Meta:
        model = SavedUniversity
        fields = ("id", "university", "created_at")
        read_only_fields = fields


class PinnedUniversitySerializer(serializers.ModelSerializer):
    university = ShortlistUniversitySummarySerializer(read_only=True)

    class Meta:
        model = PinnedUniversity
        fields = ("id", "university", "created_at")
        read_only_fields = fields


class ExcludedUniversitySerializer(serializers.ModelSerializer):
    university = ShortlistUniversitySummarySerializer(read_only=True)

    class Meta:
        model = ExcludedUniversity
        fields = ("id", "university", "created_at")
        read_only_fields = fields


class RecommendationPreferenceSerializer(serializers.ModelSerializer):
    """022 Phase 11: only the recommendation-generation controls on
    UserPreference -- countries/major/budget/aid already live on
    StudentProfile and are edited through the existing profile endpoints,
    not duplicated here.
    """

    class Meta:
        model = UserPreference
        fields = (
            "desired_recommendation_count",
            "category_distribution",
            "preferred_ranking_min",
            "preferred_ranking_max",
            "institution_type_preference",
            "campus_setting_preference",
            "test_optional_preference",
        )

    def validate_category_distribution(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("category_distribution must be an object.")
        allowed_keys = {"dream", "reach", "target", "safety"}
        for key, count in value.items():
            if key not in allowed_keys:
                raise serializers.ValidationError(f"Unknown category: {key}.")
            if not isinstance(count, int) or isinstance(count, bool) or not (0 <= count <= 50):
                raise serializers.ValidationError(f"{key} must be an integer between 0 and 50.")
        return value

    def validate_desired_recommendation_count(self, value):
        if value is not None and not (1 <= value <= 100):
            raise serializers.ValidationError("desired_recommendation_count must be between 1 and 100.")
        return value

    def validate(self, attrs):
        ranking_min = attrs.get("preferred_ranking_min", getattr(self.instance, "preferred_ranking_min", None))
        ranking_max = attrs.get("preferred_ranking_max", getattr(self.instance, "preferred_ranking_max", None))
        if ranking_min is not None and ranking_max is not None and ranking_min > ranking_max:
            raise serializers.ValidationError(
                {"preferred_ranking_min": "preferred_ranking_min must not exceed preferred_ranking_max."}
            )
        return attrs


class UniversityImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, uploaded_file):
        filename = uploaded_file.name or ""
        if not filename.lower().endswith(".xlsx"):
            raise serializers.ValidationError("Only .xlsx files are accepted.")
        if uploaded_file.size and uploaded_file.size > MAX_IMPORT_UPLOAD_BYTES:
            raise serializers.ValidationError("The workbook must be 10 MB or smaller.")
        return validate_xlsx_archive(uploaded_file)


class UniversityImportJobSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = UniversityImportJob
        fields = (
            "id",
            "uploaded_by",
            "uploaded_by_email",
            "status",
            "mode",
            "original_filename",
            "row_count",
            "created_count",
            "updated_count",
            "skipped_count",
            "warning_count",
            "source_url_count",
            "field_verification_count",
            "parsed_deadline_count",
            "parsed_essay_count",
            "questionable_sat_count",
            "processed_count",
            "current_row",
            "current_university",
            "last_heartbeat_at",
            "summary_json",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
        )
        read_only_fields = fields


class UniversityModerationRecordSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True, default=None)
    resolved_by_email = serializers.EmailField(source="resolved_by.email", read_only=True, default=None)

    class Meta:
        model = UniversityModerationRecord
        fields = (
            "id",
            "university",
            "university_name",
            "status",
            "field_name",
            "issue_type",
            "description",
            "created_by",
            "created_by_email",
            "resolved_by",
            "resolved_by_email",
            "resolved_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "university",
            "created_by",
            "resolved_by",
            "resolved_at",
            "created_at",
        )


class UniversityModerationActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=UniversityModerationRecord.Status.choices)
    field_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    issue_type = serializers.ChoiceField(choices=UniversityModerationRecord.IssueType.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="")
