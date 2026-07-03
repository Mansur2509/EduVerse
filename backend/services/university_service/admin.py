from django.contrib import admin

from .models import (
    ExchangeRate,
    SavedUniversity,
    University,
    UniversityDataSource,
    UniversityFieldVerification,
    UniversityImportJob,
    UniversityProgram,
    UniversityRequirement,
    UniversityScholarship,
    UniversitySubjectRanking,
)


class UniversityDataSourceInline(admin.TabularInline):
    model = UniversityDataSource
    extra = 0


class UniversityFieldVerificationInline(admin.TabularInline):
    model = UniversityFieldVerification
    extra = 0


class UniversityProgramInline(admin.TabularInline):
    model = UniversityProgram
    extra = 0
    fields = (
        "name",
        "major_cluster",
        "degree_level",
        "department_or_school",
        "official_url",
        "source_confidence",
    )


class UniversitySubjectRankingInline(admin.TabularInline):
    model = UniversitySubjectRanking
    extra = 0
    fields = (
        "subject_area",
        "major_cluster",
        "rank",
        "source_name",
        "ranking_year",
        "confidence",
        "source_url",
        "last_verified_date",
    )


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "city",
        "institution_type",
        "is_demo",
        "is_published",
        "updated_at",
    )
    list_filter = ("country", "institution_type", "ranking_confidence", "is_demo", "is_published")
    search_fields = ("name", "city")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [
        UniversityProgramInline,
        UniversitySubjectRankingInline,
        UniversityFieldVerificationInline,
        UniversityDataSourceInline,
    ]


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("currency_code", "usd_rate", "effective_date", "source", "confidence")
    list_filter = ("currency_code", "confidence", "effective_date")
    search_fields = ("currency_code", "source")


@admin.register(SavedUniversity)
class SavedUniversityAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "created_at")
    search_fields = ("user__email", "university__name")


@admin.register(UniversityImportJob)
class UniversityImportJobAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "mode",
        "status",
        "uploaded_by",
        "row_count",
        "created_count",
        "updated_count",
        "skipped_count",
        "processed_count",
        "created_at",
    )
    list_filter = ("mode", "status", "created_at")
    search_fields = ("original_filename", "uploaded_by__email")
    readonly_fields = (
        "uploaded_by",
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


@admin.register(UniversityProgram)
class UniversityProgramAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "university",
        "major_cluster",
        "degree_level",
        "source_confidence",
    )
    list_filter = (
        "major_cluster",
        "degree_level",
        "portfolio_required",
        "research_heavy",
        "stem_heavy",
        "interdisciplinary",
        "source_confidence",
    )
    search_fields = ("name", "university__name", "department_or_school")


@admin.register(UniversitySubjectRanking)
class UniversitySubjectRankingAdmin(admin.ModelAdmin):
    list_display = (
        "university",
        "subject_area",
        "major_cluster",
        "rank",
        "source_name",
        "ranking_year",
        "confidence",
    )
    list_filter = ("major_cluster", "source_name", "ranking_year", "confidence")
    search_fields = ("university__name", "subject_area", "source_name")


admin.site.register(UniversityRequirement)
admin.site.register(UniversityScholarship)
