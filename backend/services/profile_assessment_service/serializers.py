from rest_framework import serializers

from .models import AIProfileAssessment
from .services import PROFILE_ASSESSMENT_CATEGORIES


class AIProfileAssessmentSerializer(serializers.ModelSerializer):
    category_scores = serializers.SerializerMethodField()

    class Meta:
        model = AIProfileAssessment
        fields = (
            "id",
            "assessment_version",
            "overall_profile_score",
            "category_scores",
            "confidence",
            "public_summary",
            "evidence_used",
            "missing_data",
            "improvement_areas",
            "target_context_used",
            "expires_at",
            "is_stale",
            "created_at",
            "status",
            "benchmark_source",
            "benchmark_sample_size",
            "benchmark_scores",
            "benchmark_academic",
            "deterministic_scores",
            "readiness_scores",
            "overall_readiness_score",
            "next_allowed_refresh_at",
        )

    def get_category_scores(self, obj):
        return {category: getattr(obj, category) for category in PROFILE_ASSESSMENT_CATEGORIES}


class AIProfileAssessmentAdminSerializer(AIProfileAssessmentSerializer):
    class Meta(AIProfileAssessmentSerializer.Meta):
        fields = AIProfileAssessmentSerializer.Meta.fields + (
            "model_provider",
            "model_name",
            "internal_keywords",
            "category_rationales",
            "profile_snapshot_hash",
        )


class AssessmentEnvelopeSerializer(serializers.Serializer):
    assessment = AIProfileAssessmentSerializer(allow_null=True)
    cached = serializers.BooleanField()
    reason = serializers.CharField()
    can_refresh = serializers.BooleanField()
    next_available_at = serializers.DateTimeField(allow_null=True)
    ai_available = serializers.BooleanField()
    disclaimer = serializers.CharField()
