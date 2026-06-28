from rest_framework import serializers

from .models import EssayFeedback, EssayRevisionTask, EssayWorkspace


class EssayRevisionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssayRevisionTask
        fields = (
            "id",
            "essay",
            "title",
            "description",
            "category",
            "status",
            "created_at",
            "completed_at",
        )
        read_only_fields = ("id", "essay", "created_at", "completed_at")


class EssayRevisionTaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssayRevisionTask
        fields = ("title", "description", "category")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value


class EssayFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssayFeedback
        fields = (
            "id",
            "overall_label",
            "structure_score",
            "clarity_score",
            "authenticity_score",
            "specificity_score",
            "grammar_score",
            "prompt_fit_score",
            "word_count",
            "word_limit_status",
            "summary",
            "strengths",
            "issues",
            "revision_tasks",
            "created_at",
        )
        read_only_fields = fields


class EssayWorkspaceSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True, default=None)
    university_slug = serializers.CharField(source="university.slug", read_only=True, default=None)
    latest_feedback = serializers.SerializerMethodField()
    revision_tasks = serializers.SerializerMethodField()
    word_count = serializers.SerializerMethodField()

    class Meta:
        model = EssayWorkspace
        fields = (
            "id",
            "title",
            "essay_type",
            "university",
            "university_name",
            "university_slug",
            "prompt_text",
            "word_limit",
            "draft_text",
            "status",
            "source_url",
            "last_reviewed_at",
            "latest_feedback",
            "revision_tasks",
            "word_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "last_reviewed_at", "created_at", "updated_at")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title is required.")
        return value

    def get_latest_feedback(self, obj):
        feedback = obj.feedback_entries.first()
        return EssayFeedbackSerializer(feedback).data if feedback else None

    def get_revision_tasks(self, obj):
        return EssayRevisionTaskSerializer(obj.revision_tasks.all(), many=True).data

    def get_word_count(self, obj):
        return len((obj.draft_text or "").split())
