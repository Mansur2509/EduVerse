from rest_framework import serializers

from .models import (
    SavedUniversity,
    University,
    UniversityDataSource,
    UniversityProgram,
    UniversityRequirement,
    UniversityScholarship,
)


class UniversityDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityDataSource
        fields = "__all__"


class UniversityProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityProgram
        exclude = ("university",)


class UniversityRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityRequirement
        exclude = ("university",)


class UniversityScholarshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityScholarship
        exclude = ("university",)


class UniversitySerializer(serializers.ModelSerializer):
    programs = UniversityProgramSerializer(many=True, read_only=True)
    requirements = UniversityRequirementSerializer(many=True, read_only=True)
    scholarships = UniversityScholarshipSerializer(many=True, read_only=True)
    data_sources = UniversityDataSourceSerializer(many=True, read_only=True)
    is_shortlisted = serializers.SerializerMethodField()

    class Meta:
        model = University
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def get_is_shortlisted(self, obj) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        saved_ids = self.context.get("saved_university_ids")
        if saved_ids is not None:
            return obj.id in saved_ids
        return SavedUniversity.objects.filter(user=user, university=obj).exists()


class SavedUniversitySerializer(serializers.ModelSerializer):
    university = UniversitySerializer(read_only=True)

    class Meta:
        model = SavedUniversity
        fields = ("id", "university", "created_at")
        read_only_fields = ("id", "university", "created_at")
