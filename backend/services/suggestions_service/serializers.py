from rest_framework import serializers

from .models import SuggestedItem


class SuggestedItemSerializer(serializers.ModelSerializer):
    linked_university_name = serializers.CharField(
        source="linked_university.name",
        read_only=True,
        default=None,
    )
    linked_university_slug = serializers.CharField(
        source="linked_university.slug",
        read_only=True,
        default=None,
    )
    linked_application_university_name = serializers.CharField(
        source="linked_application.university.name",
        read_only=True,
        default=None,
    )
    linked_essay_title = serializers.CharField(
        source="linked_essay.title",
        read_only=True,
        default=None,
    )
    linked_roadmap_task_title = serializers.CharField(
        source="linked_roadmap_task.title",
        read_only=True,
        default=None,
    )

    class Meta:
        model = SuggestedItem
        fields = (
            "id",
            "suggestion_type",
            "title",
            "description",
            "priority",
            "source_type",
            "status",
            "linked_university",
            "linked_university_name",
            "linked_university_slug",
            "linked_application",
            "linked_application_university_name",
            "linked_essay",
            "linked_essay_title",
            "linked_roadmap_task",
            "linked_roadmap_task_title",
            "recommended_start_date",
            "recommended_end_date",
            "official_deadline",
            "word_limit",
            "source_url",
            "evidence_note",
            "created_at",
            "updated_at",
            "dismissed_at",
            "added_to_roadmap_at",
        )
        read_only_fields = fields
