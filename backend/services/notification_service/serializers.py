from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "message",
            "priority",
            "status",
            "action_url",
            "related_entity_type",
            "related_entity_id",
            "scheduled_for",
            "sent_at",
            "created_at",
        )
        read_only_fields = fields


class NotificationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[Notification.Status.READ, Notification.Status.ARCHIVED]
    )


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            "deadlines_enabled",
            "exams_enabled",
            "roadmap_enabled",
            "recommendations_essays_enabled",
            "essay_reviews_enabled",
            "events_enabled",
            "organizer_events_enabled",
            "updated_at",
        )
        read_only_fields = ("updated_at",)
