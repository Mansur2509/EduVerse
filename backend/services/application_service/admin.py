from django.contrib import admin

from .models import ApplicationMilestone, ApplicationTrackerItem


class ApplicationMilestoneInline(admin.TabularInline):
    model = ApplicationMilestone
    extra = 0
    fields = ("title", "category", "due_date", "status")


@admin.register(ApplicationTrackerItem)
class ApplicationTrackerItemAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "status", "priority", "deadline")
    list_filter = ("status", "priority", "application_round")
    search_fields = ("user__email", "university__name")
    inlines = [ApplicationMilestoneInline]


admin.site.register(ApplicationMilestone)
