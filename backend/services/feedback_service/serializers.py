from django.contrib.auth import get_user_model
from rest_framework import serializers

from services.essay_service.models import AIEssayScoreReport
from services.event_service.models import Event
from services.university_service.models import University

from .models import FeedbackReport, UserReport

User = get_user_model()


class FeedbackReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackReport
        fields = ("id", "contact", "feedback_type", "page_module", "message", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_message(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()


class FeedbackReportAdminSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True, default=None)

    class Meta:
        model = FeedbackReport
        fields = (
            "id",
            "user",
            "user_email",
            "contact",
            "feedback_type",
            "page_module",
            "message",
            "status",
            "priority",
            "user_agent",
            "admin_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "user_email",
            "contact",
            "feedback_type",
            "page_module",
            "message",
            "user_agent",
            "created_at",
            "updated_at",
        )


class UserReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserReport
        fields = ("id", "target_type", "target_id", "reason", "description", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_reason(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Reason is required.")
        return value.strip()

    def validate(self, attrs):
        target_type = attrs.get("target_type")
        target_id = attrs.get("target_id")
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # "No arbitrary object injection": a report must point at something
        # that genuinely exists and that the reporting student could
        # plausibly have seen (or, for essay_review, actually owns) -- the
        # raw type/id pair from the request body is never trusted unchecked.
        # `other` has no specific backing object, so nothing to check there.
        target_exists = True
        if target_type == UserReport.TargetType.UNIVERSITY:
            target_exists = University.objects.filter(pk=target_id, is_published=True).exists()
        elif target_type == UserReport.TargetType.EVENT:
            target_exists = Event.objects.filter(
                pk=target_id,
                visibility=Event.Visibility.PUBLIC,
                moderation_status=Event.Status.PUBLISHED,
            ).exists()
        elif target_type == UserReport.TargetType.ORGANIZER:
            target_exists = User.objects.filter(pk=target_id, role=User.Role.ORGANIZER).exists()
        elif target_type == UserReport.TargetType.ESSAY_REVIEW:
            target_exists = user is not None and AIEssayScoreReport.objects.filter(
                pk=target_id, user=user
            ).exists()
        elif target_type == UserReport.TargetType.MENTORSHIP_SESSION:
            from services.mentor_service.models import MentorshipSession

            target_exists = user is not None and MentorshipSession.objects.filter(
                pk=target_id, student=user
            ).exists()

        if not target_exists:
            raise serializers.ValidationError({"target_id": "This item could not be found."})

        # Deduplication: don't let repeat submissions pile up for the same
        # target from the same user while an earlier report is still
        # unresolved. A new, separate issue can still be reported once the
        # existing one is resolved or dismissed.
        if user is not None and UserReport.objects.filter(
            reporter=user,
            target_type=target_type,
            target_id=target_id,
            status__in=(UserReport.Status.OPEN, UserReport.Status.REVIEWING),
        ).exists():
            raise serializers.ValidationError(
                "You've already reported this. Our team will review it soon."
            )

        return attrs


class UserReportAdminSerializer(serializers.ModelSerializer):
    reporter_email = serializers.EmailField(source="reporter.email", read_only=True, default=None)

    class Meta:
        model = UserReport
        fields = (
            "id",
            "reporter",
            "reporter_email",
            "target_type",
            "target_id",
            "reason",
            "description",
            "status",
            "resolved_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "reporter",
            "reporter_email",
            "target_type",
            "target_id",
            "reason",
            "description",
            "resolved_at",
            "created_at",
        )
