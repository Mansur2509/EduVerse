from rest_framework import serializers

from .models import MentorAvailabilitySlot, MentorProfile, MentorshipSession


class PublicMentorProfileSerializer(serializers.ModelSerializer):
    """Never includes email, phone, or any other contact field -- session
    coordination stays in-app by design (see the roadmap doc's explicit
    non-goal: no unsafe off-platform contact exchange)."""

    class Meta:
        model = MentorProfile
        fields = ("id", "bio", "expertise_areas", "languages", "is_accepting_requests")


class MentorAvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorAvailabilitySlot
        fields = ("id", "starts_at", "ends_at", "is_booked")
        read_only_fields = ("id", "is_booked")


class MentorshipSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        fields = ("id", "mentor", "student", "slot", "status", "topic", "requested_at", "responded_at")
        read_only_fields = ("id", "student", "status", "requested_at", "responded_at")


class SessionRequestSerializer(serializers.Serializer):
    mentor_id = serializers.IntegerField()
    topic = serializers.CharField(max_length=200, allow_blank=True, required=False, default="")


class SessionStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            MentorshipSession.Status.ACCEPTED,
            MentorshipSession.Status.DECLINED,
            MentorshipSession.Status.CANCELLED,
            MentorshipSession.Status.COMPLETED,
        ]
    )


class BlockUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
