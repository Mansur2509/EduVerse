from django.contrib import admin

from .models import SuggestedItem


@admin.register(SuggestedItem)
class SuggestedItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "suggestion_type",
        "priority",
        "source_type",
        "status",
        "updated_at",
    )
    list_filter = ("suggestion_type", "priority", "source_type", "status")
    search_fields = ("title", "description", "evidence_note", "user__email")
