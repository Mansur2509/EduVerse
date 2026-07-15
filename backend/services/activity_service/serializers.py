from rest_framework import serializers


class UserAnalyticsSerializer(serializers.Serializer):
    profile_completion_percent = serializers.IntegerField()
    roadmap_tasks_completed = serializers.IntegerField()
    roadmap_tasks_total = serializers.IntegerField()
    applications_by_status = serializers.DictField()
    essay_reviews_count = serializers.IntegerField()
    upcoming_deadlines_count = serializers.IntegerField()
    activity_by_type = serializers.DictField()


class AdminAnalyticsSummarySerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    new_users_7d = serializers.IntegerField()
    new_users_30d = serializers.IntegerField()
    active_users_7d = serializers.IntegerField()
    active_users_30d = serializers.IntegerField()
    applications_created_total = serializers.IntegerField()
    universities_shortlisted_total = serializers.IntegerField()
    essay_reviews_requested_total = serializers.IntegerField()
    roadmap_generations_total = serializers.IntegerField()
    event_registrations_total = serializers.IntegerField()
    organizer_events_created_total = serializers.IntegerField()
    retained_users_2plus_actions = serializers.IntegerField()
    onboarding_completion_rate_percent = serializers.FloatField()
