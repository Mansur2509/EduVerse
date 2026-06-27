from django.contrib import admin

from .models import (
    SavedUniversity,
    University,
    UniversityDataSource,
    UniversityProgram,
    UniversityRequirement,
    UniversityScholarship,
)


class UniversityDataSourceInline(admin.TabularInline):
    model = UniversityDataSource
    extra = 0


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "city",
        "institution_type",
        "is_published",
        "updated_at",
    )
    list_filter = ("country", "institution_type", "is_published")
    search_fields = ("name", "city")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [UniversityDataSourceInline]


@admin.register(SavedUniversity)
class SavedUniversityAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "created_at")
    search_fields = ("user__email", "university__name")


admin.site.register(UniversityProgram)
admin.site.register(UniversityRequirement)
admin.site.register(UniversityScholarship)

