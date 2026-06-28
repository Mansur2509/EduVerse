from django.contrib import admin

from .models import EssayFeedback, EssayRevisionTask, EssayWorkspace


class EssayRevisionTaskInline(admin.TabularInline):
    model = EssayRevisionTask
    extra = 0
    fields = ("title", "category", "status")


@admin.register(EssayWorkspace)
class EssayWorkspaceAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "essay_type", "status", "university", "updated_at")
    list_filter = ("essay_type", "status")
    search_fields = ("title", "user__email")
    inlines = [EssayRevisionTaskInline]


@admin.register(EssayFeedback)
class EssayFeedbackAdmin(admin.ModelAdmin):
    list_display = ("essay", "overall_label", "word_count", "word_limit_status", "created_at")
    list_filter = ("overall_label", "word_limit_status")


admin.site.register(EssayRevisionTask)
