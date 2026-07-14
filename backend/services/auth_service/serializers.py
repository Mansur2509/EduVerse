from django.contrib.auth import authenticate, get_user_model, password_validation
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from services.subscription_service.models import Plan, Subscription
from services.user_profile_service.models import StudentProfile, UserPreference

from .cookies import refresh_token_from_request

User = get_user_model()


class ProfileBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = (
            "country",
            "city",
            "grade",
            "education_status",
            "intended_major",
            "scholarship_need",
        )
        extra_kwargs = {
            "country": {"required": False},
            "city": {"required": False},
            "grade": {"required": False},
            "education_status": {"required": False},
            "intended_major": {"required": False},
            "scholarship_need": {"required": False},
        }


class SubscriptionBasicSerializer(serializers.ModelSerializer):
    tier = serializers.CharField(source="plan", read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "tier",
            "period_started_at",
            "ai_message_count",
            "essay_review_count",
            "saved_events_count",
        )


class CurrentUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=180)
    role = serializers.CharField(read_only=True)
    google_linked = serializers.BooleanField(read_only=True)
    profile = ProfileBasicSerializer(required=False)
    subscription = SubscriptionBasicSerializer(read_only=True)

    def to_representation(self, instance):
        profile = StudentProfile.objects.filter(user=instance).first() or StudentProfile(
            user=instance
        )
        subscription = Subscription.objects.filter(user=instance).first() or Subscription(
            user=instance,
            plan=Plan.FREE,
        )
        return {
            "id": instance.id,
            "email": instance.email,
            "full_name": profile.full_name,
            "role": instance.role,
            "google_linked": instance.social_identities.filter(provider="google").exists(),
            "profile": ProfileBasicSerializer(profile).data,
            "subscription": SubscriptionBasicSerializer(subscription).data,
        }

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        profile, _ = StudentProfile.objects.select_for_update().get_or_create(user=instance)
        if "full_name" in validated_data:
            profile.full_name = validated_data["full_name"]
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()
        return instance


def token_pair_for_user(user) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    full_name = serializers.CharField(max_length=180)
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        normalized_email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized_email

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}  # nosec B105
            )
        password_validation.validate_password(attrs["password"])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"]
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=user, full_name=validated_data["full_name"])
        UserPreference.objects.create(user=user)
        Subscription.objects.create(user=user, plan=Plan.FREE)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = User.objects.normalize_email(attrs["email"]).lower()
        user_record = User.objects.filter(email__iexact=email).first()
        user = None
        if user_record is not None:
            user = authenticate(
                request=self.context.get("request"),
                username=user_record.username,
                password=attrs["password"],
            )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, required=False)

    def save(self, **kwargs):
        token_value = refresh_token_from_request(self.context["request"])
        if not token_value:
            return
        try:
            token = RefreshToken(token_value)
            if str(token["user_id"]) != str(self.context["request"].user.pk):
                raise serializers.ValidationError(
                    {"refresh": "Refresh token does not belong to the authenticated user."}
                )
            token.blacklist()
        except TokenError as error:
            raise serializers.ValidationError({"refresh": "Invalid or expired refresh token."}) from error


class ActiveUserTokenRefreshSerializer(TokenRefreshSerializer):
    """Reject refresh for removed/inactive accounts before rotating the token."""

    def validate(self, attrs):
        try:
            refresh = self.token_class(attrs["refresh"])
            user_id = refresh.get(api_settings.USER_ID_CLAIM)
        except (KeyError, TokenError) as error:
            raise AuthenticationFailed("Invalid or expired refresh token.") from error

        if not user_id or not User.objects.filter(
            **{api_settings.USER_ID_FIELD: user_id},
            is_active=True,
        ).exists():
            raise AuthenticationFailed("Invalid or expired refresh token.")

        return super().validate(attrs)
