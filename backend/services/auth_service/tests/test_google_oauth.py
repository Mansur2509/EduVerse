import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from services.auth_service.google_oauth import (
    GoogleOAuthConfigurationError,
    GoogleOAuthProviderUnavailable,
    require_google_oauth_configuration,
)
from services.auth_service.models import OAuthLoginAttempt, SocialIdentity

User = get_user_model()


OAUTH_SETTINGS = {
    "GOOGLE_CLIENT_ID": "test-client.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "test-server-secret",
    "GOOGLE_REDIRECT_URI": "https://api.test/api/auth/google/callback/",
    "GOOGLE_OAUTH_FRONTEND_URL": "https://frontend.test/login",
    "GOOGLE_OAUTH_ENABLED": True,
    "GOOGLE_OAUTH_ATTEMPT_MAX_AGE_SECONDS": 600,
    "CORS_ALLOWED_ORIGINS": ["https://frontend.test"],
    "CSRF_TRUSTED_ORIGINS": ["https://frontend.test"],
    "ALLOWED_HOSTS": ["api.test", "testserver"],
    "SECURE_COOKIES": False,
}


@override_settings(**OAUTH_SETTINGS)
class GoogleOAuthFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def start_attempt(self):
        response = self.client.get("/api/auth/google/start/")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        parsed = urlparse(response["Location"])
        params = parse_qs(parsed.query)
        self.assertEqual(parsed.netloc, "accounts.google.com")
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertIn("openid email profile", params["scope"])
        cookie = response.cookies["uniway_google_oauth"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        return params["state"][0], params["nonce"][0], cookie.value

    @staticmethod
    def valid_claims(nonce, **overrides):
        claims = {
            "iss": "https://accounts.google.com",
            "aud": OAUTH_SETTINGS["GOOGLE_CLIENT_ID"],
            "sub": "google-subject-123",
            "email": "new.student@example.com",
            "email_verified": True,
            "name": "New Student",
            "nonce": nonce,
            "exp": int(time.time()) + 300,
        }
        claims.update(overrides)
        return claims

    def callback(self, state, claims, *, code="provider-code"):
        with (
            patch(
                "services.auth_service.views.exchange_google_code",
                return_value="signed-provider-id-token",
            ),
            patch(
                "services.auth_service.views.verify_google_id_token",
                return_value=claims,
            ),
        ):
            return self.client.get(
                "/api/auth/google/callback/",
                {"state": state, "code": code},
            )

    def test_start_uses_state_nonce_pkce_and_never_exposes_client_secret(self):
        response = self.client.get("/api/auth/google/start/")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertNotIn(OAUTH_SETTINGS["GOOGLE_CLIENT_SECRET"], response["Location"])
        self.assertEqual(OAuthLoginAttempt.objects.count(), 1)

    def test_valid_google_login_creates_student_and_http_only_session(self):
        state, nonce, _ = self.start_attempt()

        response = self.callback(state, self.valid_claims(nonce))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], "https://frontend.test/login?oauth=success")
        self.assertIn("uniway_refresh", response.cookies)
        self.assertTrue(response.cookies["uniway_refresh"]["httponly"])
        user = User.objects.get(email="new.student@example.com")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertFalse(user.has_usable_password())
        self.assertTrue(
            SocialIdentity.objects.filter(
                user=user,
                provider=SocialIdentity.Provider.GOOGLE,
                subject="google-subject-123",
            ).exists()
        )
        self.assertEqual(user.student_profile.full_name, "New Student")
        self.assertIsNone(user.student_profile.onboarding_completed_at)

    def test_existing_password_student_is_linked_by_verified_email(self):
        existing = User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            password="safe-test-password-123",
        )
        state, nonce, _ = self.start_attempt()

        response = self.callback(
            state,
            self.valid_claims(nonce, email="EXISTING@example.com"),
        )

        self.assertIn("oauth=success", response["Location"])
        self.assertEqual(User.objects.filter(email__iexact="existing@example.com").count(), 1)
        self.assertTrue(existing.has_usable_password())
        self.assertTrue(SocialIdentity.objects.filter(user=existing).exists())

    def test_privileged_account_is_not_auto_linked(self):
        privileged = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="safe-test-password-123",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        state, nonce, _ = self.start_attempt()

        response = self.callback(
            state,
            self.valid_claims(nonce, email="admin@example.com"),
        )

        self.assertIn("oauth=conflict", response["Location"])
        self.assertFalse(SocialIdentity.objects.filter(user=privileged).exists())
        self.assertNotIn("uniway_refresh", response.cookies)

    def test_suspended_account_is_blocked(self):
        suspended = User.objects.create_user(
            username="blocked@example.com",
            email="blocked@example.com",
            password="safe-test-password-123",
            is_active=False,
        )
        state, nonce, _ = self.start_attempt()

        response = self.callback(
            state,
            self.valid_claims(nonce, email="blocked@example.com"),
        )

        self.assertIn("oauth=blocked", response["Location"])
        self.assertFalse(SocialIdentity.objects.filter(user=suspended).exists())

    def test_state_is_single_use(self):
        state, nonce, oauth_cookie = self.start_attempt()
        first = self.callback(state, self.valid_claims(nonce))
        self.assertIn("oauth=success", first["Location"])

        self.client.cookies["uniway_google_oauth"] = oauth_cookie
        second = self.callback(state, self.valid_claims(nonce))

        self.assertIn("oauth=invalid", second["Location"])
        self.assertEqual(User.objects.filter(email="new.student@example.com").count(), 1)

    def test_google_cancellation_consumes_state_without_creating_session(self):
        state, _nonce, _ = self.start_attempt()

        response = self.client.get(
            "/api/auth/google/callback/",
            {"state": state, "error": "access_denied"},
        )

        self.assertIn("oauth=cancelled", response["Location"])
        self.assertNotIn("uniway_refresh", response.cookies)
        self.assertIsNotNone(OAuthLoginAttempt.objects.get().consumed_at)

    def test_invalid_claims_are_rejected(self):
        invalid_variants = (
            {"iss": "https://issuer.example"},
            {"aud": "wrong-client"},
            {"exp": int(time.time()) - 1},
            {"email": None},
            {"email_verified": False},
            {"nonce": "wrong-nonce"},
        )
        for index, override in enumerate(invalid_variants):
            with self.subTest(override=override):
                self.client.cookies.clear()
                state, nonce, _ = self.start_attempt()
                claims = self.valid_claims(
                    nonce,
                    sub=f"invalid-subject-{index}",
                    email=f"invalid-{index}@example.com",
                )
                claims.update(override)
                response = self.callback(state, claims)
                self.assertIn("oauth=invalid", response["Location"])
                self.assertNotIn("uniway_refresh", response.cookies)

    def test_wrong_returned_state_is_rejected_before_provider_exchange(self):
        self.start_attempt()

        with patch("services.auth_service.views.exchange_google_code") as exchange:
            response = self.client.get(
                "/api/auth/google/callback/",
                {"state": "attacker-state", "code": "provider-code"},
            )

        self.assertIn("oauth=invalid", response["Location"])
        exchange.assert_not_called()

    def test_provider_unavailable_returns_generic_failure_without_session(self):
        state, _nonce, _ = self.start_attempt()
        with patch(
            "services.auth_service.views.exchange_google_code",
            side_effect=GoogleOAuthProviderUnavailable,
        ):
            response = self.client.get(
                "/api/auth/google/callback/",
                {"state": state, "code": "provider-code"},
            )

        self.assertEqual(response["Location"], "https://frontend.test/login?oauth=failed")
        self.assertNotIn("uniway_refresh", response.cookies)

    @override_settings(
        DEBUG=False,
        GOOGLE_REDIRECT_URI="https://attacker.example/api/auth/google/callback/",
    )
    def test_backend_callback_host_must_be_allowlisted(self):
        response = self.client.get("/api/auth/google/start/")

        self.assertEqual(response["Location"], "https://frontend.test/login?oauth=unavailable")
        self.assertEqual(OAuthLoginAttempt.objects.count(), 0)

    @override_settings(
        GOOGLE_REDIRECT_URI="https://api.test/api/auth/google/callback/?next=https://attacker.example",
    )
    def test_backend_callback_rejects_query_based_redirect_injection(self):
        response = self.client.get("/api/auth/google/start/")

        self.assertEqual(response["Location"], "https://frontend.test/login?oauth=unavailable")
        self.assertEqual(OAuthLoginAttempt.objects.count(), 0)

    @override_settings(
        GOOGLE_OAUTH_FRONTEND_URL="https://frontend.test/login?next=https://attacker.example",
    )
    def test_frontend_return_url_rejects_query_based_redirect_injection(self):
        # An invalid fixed frontend URL cannot safely receive even the generic
        # configuration error, so validate the guard without following it.
        with self.assertRaises(GoogleOAuthConfigurationError):
            require_google_oauth_configuration()


@override_settings(
    GOOGLE_OAUTH_ENABLED=False,
    GOOGLE_OAUTH_FRONTEND_URL="https://frontend.test/login",
    CORS_ALLOWED_ORIGINS=["https://frontend.test"],
)
class GoogleOAuthDisabledTests(APITestCase):
    def test_missing_credentials_return_to_fixed_frontend_without_open_redirect(self):
        response = self.client.get(
            "/api/auth/google/start/",
            {"next": "https://attacker.example/capture"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response["Location"], "https://frontend.test/login?oauth=unavailable")
        self.assertNotIn("attacker.example", response["Location"])

    def test_config_endpoint_reports_disabled_without_requiring_auth(self):
        response = self.client.get("/api/auth/config/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"google_oauth_enabled": False})


@override_settings(**OAUTH_SETTINGS)
class GoogleOAuthConfigEnabledTests(APITestCase):
    def test_config_endpoint_reports_enabled(self):
        response = self.client.get("/api/auth/config/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"google_oauth_enabled": True})
