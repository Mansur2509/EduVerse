from rest_framework import serializers

from .models import RoadmapPlan, RoadmapTask

MANUAL_EDITABLE_FIELDS = ("title", "description", "category", "priority", "due_date")
GENERATED_EDITABLE_FIELDS = ("title", "description", "due_date", "priority", "status")


class RoadmapTaskSerializer(serializers.ModelSerializer):
    linked_university_name = serializers.CharField(
        source="linked_university.name", read_only=True, default=None
    )
    linked_university_slug = serializers.CharField(
        source="linked_university.slug", read_only=True, default=None
    )
    linked_event_title = serializers.CharField(
        source="linked_event.title", read_only=True, default=None
    )
    linked_event_slug = serializers.CharField(
        source="linked_event.slug", read_only=True, default=None
    )
    linked_application_university_name = serializers.CharField(
        source="linked_application.university.name", read_only=True, default=None
    )
    task_kind = serializers.CharField(read_only=True)
    is_timeline_marker = serializers.BooleanField(read_only=True)

    class Meta:
        model = RoadmapTask
        fields = (
            "id",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "due_date",
            "source_type",
            "linked_university",
            "linked_university_name",
            "linked_university_slug",
            "linked_program",
            "linked_application",
            "linked_application_university_name",
            "linked_event",
            "linked_event_title",
            "linked_event_slug",
            "linked_profile_section",
            "linked_score_dimension",
            "estimated_effort",
            "generated_reason",
            "evidence_note",
            "source_url",
            "task_kind",
            "is_timeline_marker",
            "created_at",
            "updated_at",
            "completed_at",
        )
        read_only_fields = (
            "id",
            "source_type",
            "linked_university",
            "linked_program",
            "linked_application",
            "linked_event",
            "linked_profile_section",
            "linked_score_dimension",
            "estimated_effort",
            "generated_reason",
            "evidence_note",
            "source_url",
            "task_kind",
            "is_timeline_marker",
            "created_at",
            "updated_at",
            "completed_at",
        )

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        if instance is not None and instance.source_type != RoadmapTask.SourceType.MANUAL:
            disallowed = set(attrs) - set(GENERATED_EDITABLE_FIELDS)
            if disallowed:
                raise serializers.ValidationError(
                    {"detail": f"Generated tasks cannot have these fields edited: {sorted(disallowed)}"}
                )
        return attrs


class RoadmapTaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadmapTask
        fields = ("title", "description", "category", "priority", "due_date")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value


class RoadmapPlanSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = RoadmapPlan
        fields = (
            "id",
            "title",
            "cycle_year",
            "target_country",
            "primary_goal",
            "generated_at",
            "last_refreshed_at",
            "summary",
            "readiness_snapshot",
            "active",
            "tasks",
        )
        read_only_fields = fields

    def get_tasks(self, obj):
        tasks = (
            obj.tasks.select_related(
                "linked_university",
                "linked_application__university",
                "linked_event",
            )
            .order_by("status", "due_date", "-priority", "created_at")
        )
        return RoadmapTaskSerializer(tasks, many=True, context=self.context).data
