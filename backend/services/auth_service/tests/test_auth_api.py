from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from services.activity_service.models import AnalyticsEvent
from services.auth_service.models import SocialIdentity
from services.subscription_service.models import Plan, Subscription
from services.user_profile_service.models import StudentProfile, UserPreference

User = get_user_model()


class AuthApiTests(APITestCase):
    register_payload = {
        "email": "student@example.com",
        "full_name": "Student Example",
        "password": "Strong-Development-Password-842!",
        "password_confirm": "Strong-Development-Password-842!",
    }

    def setUp(self):
        cache.clear()

    def register(self):
        return self.client.post(reverse("auth:register"), self.register_payload, format="json")

    def test_register_creates_student_profile_subscription_and_tokens(self):
        response = self.register()

        self.assertEqual(response.status_code, 201, response.json())
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        refresh_cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
        self.assertTrue(refresh_cookie["httponly"])
        self.assertEqual(refresh_cookie["path"], settings.AUTH_REFRESH_COOKIE_PATH)
        self.assertEqual(refresh_cookie["samesite"], settings.AUTH_REFRESH_COOKIE_SAMESITE)
        self.assertEqual(response.data["user"]["email"], self.register_payload["email"])
        self.assertEqual(response.data["user"]["role"], User.Role.STUDENT)
        self.assertEqual(response.data["user"]["subscription"]["tier"], Plan.FREE)

        user = User.objects.get(email=self.register_payload["email"])
        self.assertTrue(user.check_password(self.register_payload["password"]))
        self.assertEqual(user.student_profile.full_name, self.register_payload["full_name"])
        self.assertEqual(user.subscription.plan, Plan.FREE)
        self.assertTrue(UserPreference.objects.filter(user=user).exists())

    def test_register_without_organizer_interest_does_not_fire_that_event(self):
        self.register()
        user = User.objects.get(email=self.register_payload["email"])
        self.assertFalse(
            AnalyticsEvent.objects.filter(
                user=user, event_type=AnalyticsEvent.EventType.ORGANIZER_INTEREST_AT_REGISTRATION
            ).exists()
        )

    def test_register_with_organizer_interest_fires_analytics_event_only(self):
        # Deliberately no OrganizerApplication is created here -- registration
        # doesn't collect telegram/description/motivation, so this is a
        # lightweight signal only, not a submission (see RegisterSerializer).
        payload = {**self.register_payload, "wants_organizer_role": True}
        response = self.client.post(reverse("auth:register"), payload, format="json")

        self.assertEqual(response.status_code, 201, response.json())
        user = User.objects.get(email=self.register_payload["email"])
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                user=user, event_type=AnalyticsEvent.EventType.ORGANIZER_INTEREST_AT_REGISTRATION
            ).exists()
        )
        self.assertFalse(user.organizer_applications.exists())

    def test_login_returns_jwt_tokens(self):
        self.register()

        response = self.client.post(
            reverse("auth:login"),
            {
                "email": self.register_payload["email"],
                "password": self.register_payload["password"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.json())
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)
        self.assertEqual(response.data["user"]["full_name"], self.register_payload["full_name"])

    def test_me_requires_authentication_and_returns_related_data(self):
        register_response = self.register()

        anonymous_response = self.client.get(reverse("auth:me"))
        self.assertEqual(anonymous_response.status_code, 401)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {register_response.data['access']}")
        response = self.client.get(reverse("auth:me"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["scholarship_need"], "unsure")
        self.assertEqual(response.data["subscription"]["tier"], Plan.FREE)
        self.assertFalse(response.data["google_linked"])
        self.assertFalse(response.data["product_tour_dismissed"])

    def test_product_tour_dismissal_is_persisted_and_one_way(self):
        register_response = self.register()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {register_response.data['access']}")

        dismiss_response = self.client.patch(
            reverse("auth:me"), {"product_tour_dismissed": True}, format="json"
        )
        self.assertEqual(dismiss_response.status_code, 200, dismiss_response.json())
        self.assertTrue(dismiss_response.data["product_tour_dismissed"])

        me_response = self.client.get(reverse("auth:me"))
        self.assertTrue(me_response.data["product_tour_dismissed"])

        user = User.objects.get(email=self.register_payload["email"])
        first_dismissed_at = user.preferences.product_tour_dismissed_at
        self.assertIsNotNone(first_dismissed_at)

        # Sending false must not clear it -- dismissal is one-way.
        second_response = self.client.patch(
            reverse("auth:me"), {"product_tour_dismissed": False}, format="json"
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertTrue(second_response.data["product_tour_dismissed"])
        user.refresh_from_db()
        self.assertEqual(user.preferences.product_tour_dismissed_at, first_dismissed_at)

    def test_me_reports_google_linked_when_a_social_identity_exists(self):
        register_response = self.register()
        user = User.objects.get(email=self.register_payload["email"])
        SocialIdentity.objects.create(
            user=user,
            provider=SocialIdentity.Provider.GOOGLE,
            subject="google-subject-id",
            email_at_link=user.email,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {register_response.data['access']}")

        response = self.client.get(reverse("auth:me"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["google_linked"])

    def test_me_patch_updates_only_profile_fields(self):
        register_response = self.register()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {register_response.data['access']}")

        response = self.client.patch(
            reverse("auth:me"),
            {
                "full_name": "Updated Student",
                "profile": {
                    "country": "Uzbekistan",
                    "city": "Tashkent",
                    "intended_major": "Computer Science",
                },
                "role": User.Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.data["full_name"], "Updated Student")
        self.assertEqual(response.data["profile"]["country"], "Uzbekistan")
        self.assertEqual(response.data["role"], User.Role.STUDENT)

        user = User.objects.get(email=self.register_payload["email"])
        self.assertEqual(user.role, User.Role.STUDENT)

    def test_logout_blacklists_refresh_token(self):
        register_response = self.register()
        access = register_response.data["access"]
        refresh = register_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

        logout_response = self.client.post(
            reverse("auth:logout"),
            {},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(logout_response.status_code, 204)
        self.assertEqual(logout_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"], 0)

        refresh_response = self.client.post(
            reverse("auth:token-refresh"),
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, 401)

    def test_anonymous_logout_is_rejected(self):
        response = self.client.post(
            reverse("auth:logout"),
            {"refresh": "not-a-token"},
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))

    def test_logout_rejects_another_users_refresh_token(self):
        first_user = User.objects.create_user(
            username="first-logout@example.com",
            email="first-logout@example.com",
            password="Strong-Development-Password-842!",
        )
        second_user = User.objects.create_user(
            username="second-logout@example.com",
            email="second-logout@example.com",
            password="Strong-Development-Password-842!",
        )
        first_token = RefreshToken.for_user(first_user)
        second_token = RefreshToken.for_user(second_user)

        response = self.client.post(
            reverse("auth:logout"),
            {"refresh": str(second_token)},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {first_token.access_token}",
        )

        self.assertEqual(response.status_code, 400)

    def test_refresh_rotates_cookie_without_returning_refresh_token(self):
        register_response = self.register()
        first_refresh = register_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

        response = self.client.post(reverse("auth:token-refresh"), {}, format="json")

        self.assertEqual(response.status_code, 200, response.json())
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        second_refresh = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
        self.assertNotEqual(first_refresh, second_refresh)

        replay_client = APIClient()
        replay_response = replay_client.post(
            reverse("auth:token-refresh"),
            {"refresh": first_refresh},
            format="json",
        )
        self.assertEqual(replay_response.status_code, 401)

    def test_inactive_user_cannot_refresh_or_use_existing_access_token(self):
        register_response = self.register()
        access = register_response.data["access"]
        refresh = register_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
        user = User.objects.get(email=self.register_payload["email"])
        user.is_active = False
        user.save(update_fields=["is_active"])

        refresh_client = APIClient()
        refresh_response = refresh_client.post(
            reverse("auth:token-refresh"),
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, 401)

        me_response = refresh_client.get(
            reverse("auth:me"),
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(me_response.status_code, 401)

    def test_cookie_refresh_rejects_untrusted_browser_origin(self):
        self.register()

        response = self.client.post(
            reverse("auth:token-refresh"),
            {},
            format="json",
            HTTP_ORIGIN="https://attacker.example",
        )

        self.assertEqual(response.status_code, 403)

    def test_refresh_has_dedicated_rate_limit(self):
        cache.clear()
        register_response = self.register()
        refresh = register_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
        client = APIClient()

        with patch.object(
            ScopedRateThrottle,
            "THROTTLE_RATES",
            {"auth_refresh": "2/minute"},
        ):
            first = client.post(
                reverse("auth:token-refresh"),
                {"refresh": refresh},
                format="json",
            )
            rotated_refresh = first.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
            client.cookies.clear()
            second = client.post(
                reverse("auth:token-refresh"),
                {"refresh": rotated_refresh},
                format="json",
            )
            latest_refresh = second.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
            client.cookies.clear()
            third = client.post(
                reverse("auth:token-refresh"),
                {"refresh": latest_refresh},
                format="json",
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 429)

    def test_login_has_dedicated_brute_force_rate_limit(self):
        cache.clear()
        client = APIClient()
        payload = {"email": "missing@example.com", "password": "wrong-password"}

        with patch.object(
            ScopedRateThrottle,
            "THROTTLE_RATES",
            {"auth_login": "2/minute"},
        ):
            first = client.post(reverse("auth:login"), payload, format="json")
            second = client.post(reverse("auth:login"), payload, format="json")
            third = client.post(reverse("auth:login"), payload, format="json")

        self.assertEqual(first.status_code, 400)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(third.status_code, 429)
        self.assertIn("Retry-After", third)

    def test_registration_has_dedicated_rate_limit(self):
        cache.clear()
        client = APIClient()

        with patch.object(
            ScopedRateThrottle,
            "THROTTLE_RATES",
            {"auth_register": "1/minute"},
        ):
            first = client.post(reverse("auth:register"), self.register_payload, format="json")
            second_payload = {**self.register_payload, "email": "second@example.com"}
            second = client.post(reverse("auth:register"), second_payload, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)

    def test_login_error_does_not_reveal_whether_account_exists(self):
        self.register()
        existing = self.client.post(
            reverse("auth:login"),
            {"email": self.register_payload["email"], "password": "wrong-password"},
            format="json",
        )
        missing = self.client.post(
            reverse("auth:login"),
            {"email": "missing@example.com", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(existing.status_code, missing.status_code)
        self.assertEqual(existing.data, missing.data)

    def test_me_uses_read_only_defaults_for_missing_related_records(self):
        user = User.objects.create_user(
            username="legacy@example.com",
            email="legacy@example.com",
            password="Strong-Development-Password-842!",
        )
        self.client.force_authenticate(user)

        response = self.client.get(reverse("auth:me"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["country"], "")
        self.assertEqual(response.data["subscription"]["tier"], Plan.FREE)
        self.assertFalse(StudentProfile.objects.filter(user=user).exists())
        self.assertFalse(Subscription.objects.filter(user=user).exists())
