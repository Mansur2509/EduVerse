from django.contrib import admin

from .models import (
    SavedUniversity,
    University,
    UniversityDataSource,
    UniversityFieldVerification,
    UniversityProgram,
    UniversityRequirement,
    UniversityScholarship,
)


class UniversityDataSourceInline(admin.TabularInline):
    model = UniversityDataSource
    extra = 0


class UniversityFieldVerificationInline(admin.TabularInline):
    model = UniversityFieldVerification
    extra = 0


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
    list_filter = ("country", "institution_type", "is_demo", "is_published")
    search_fields = ("name", "city")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [UniversityFieldVerificationInline, UniversityDataSourceInline]


@admin.register(SavedUniversity)
class SavedUniversityAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "created_at")
    search_fields = ("user__email", "university__name")


admin.site.register(UniversityProgram)
admin.site.register(UniversityRequirement)
admin.site.register(UniversityScholarship)

