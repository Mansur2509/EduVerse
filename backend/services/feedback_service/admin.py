from django.contrib import admin

from .models import FeedbackReport


@admin.register(FeedbackReport)
class FeedbackReportAdmin(admin.ModelAdmin):
    list_display = ("id", "feedback_type", "status", "priority", "page_module", "created_at")
    list_filter = ("status", "priority", "feedback_type")
    search_fields = ("message", "contact", "page_module")
    readonly_fields = ("created_at", "updated_at")
