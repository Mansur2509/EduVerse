from rest_framework import serializers

from .models import ApplicationMilestone, ApplicationTrackerItem


class ApplicationMilestoneSerializer(serializers.ModelSerializer):
    linked_roadmap_task_title = serializers.CharField(
        source="linked_roadmap_task.title", read_only=True, default=None
    )

    class Meta:
        model = ApplicationMilestone
        fields = (
            "id",
            "application",
            "title",
            "category",
            "due_date",
            "status",
            "linked_roadmap_task",
            "linked_roadmap_task_title",
            "source_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "application", "created_at", "updated_at")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value


class ApplicationMilestoneCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationMilestone
        fields = ("title", "category", "due_date", "linked_roadmap_task", "source_url")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value

    def validate_linked_roadmap_task(self, value):
        if value is not None:
            request = self.context.get("request")
            if request is None or value.user_id != request.user.id:
                raise serializers.ValidationError("You can only link your own roadmap tasks.")
        return value


class ApplicationTrackerItemSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)
    university_slug = serializers.CharField(source="university.slug", read_only=True)
    target_program_name = serializers.CharField(
        source="target_program.name", read_only=True, default=None
    )
    milestones = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationTrackerItem
        fields = (
            "id",
            "university",
            "university_name",
            "university_slug",
            "target_program",
            "target_program_name",
            "application_round",
            "status",
            "priority",
            "deadline",
            "financial_aid_deadline",
            "scholarship_deadline",
            "essays_status",
            "recommendations_status",
            "test_scores_status",
            "documents_status",
            "financial_aid_status",
            "notes",
            "milestones",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_milestones(self, obj):
        return ApplicationMilestoneSerializer(obj.milestones.all(), many=True).data
