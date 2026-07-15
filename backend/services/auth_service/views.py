from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from common.demo_accounts import CANONICAL_STUDENT_DEMO_EMAIL
from services.activity_service.models import AnalyticsEvent
from services.activity_service.services import track_event

from .cookies import clear_refresh_cookie, refresh_token_from_request, set_refresh_cookie
from .google_oauth import (
    GoogleOAuthError,
    build_google_authorization_url,
    consume_google_oauth_attempt,
    create_google_oauth_attempt,
    exchange_google_code,
    get_or_link_google_user,
    load_google_oauth_attempt,
    oauth_frontend_redirect,
    validate_google_claims,
    verify_google_id_token,
)
from .serializers import (
    ActiveUserTokenRefreshSerializer,
    CurrentUserSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    token_pair_for_user,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        track_event(user=user, event_type=AnalyticsEvent.EventType.USER_REGISTERED)
        tokens = token_pair_for_user(user)
        response = Response(
            {
                "access": tokens["access"],
                "user": CurrentUserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )
        set_refresh_cookie(response, tokens["refresh"])
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if user.email.lower() == CANONICAL_STUDENT_DEMO_EMAIL.lower():
            track_event(user=user, event_type=AnalyticsEvent.EventType.DEMO_LOGIN_USED)
        tokens = token_pair_for_user(user)
        response = Response(
            {
                "access": tokens["access"],
                "user": CurrentUserSerializer(user).data,
            }
        )
        set_refresh_cookie(response, tokens["refresh"])
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response


class AuthConfigView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED})


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)

    def patch(self, request):
        serializer = CurrentUserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(CurrentUserSerializer(user).data)


class AuthTokenRefreshView(TokenRefreshView):
    serializer_class = ActiveUserTokenRefreshSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_refresh"

    def post(self, request, *args, **kwargs):
        refresh_token = refresh_token_from_request(request)
        if not refresh_token:
            raise AuthenticationFailed("Invalid or expired refresh token.")

        serializer = self.get_serializer(data={"refresh": refresh_token})
        serializer.is_valid(raise_exception=True)
        response_data = dict(serializer.validated_data)
        rotated_refresh = response_data.pop("refresh", refresh_token)
        response = Response(response_data, status=status.HTTP_200_OK)
        set_refresh_cookie(response, rotated_refresh)
        return response


def _clear_google_oauth_cookie(response) -> None:
    response.delete_cookie(
        settings.GOOGLE_OAUTH_STATE_COOKIE_NAME,
        path="/api/auth/google/",
        samesite="Lax",
    )


class GoogleOAuthStartView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_oauth"

    def get(self, request):
        try:
            attempt, cookie_payload = create_google_oauth_attempt()
            response = HttpResponseRedirect(build_google_authorization_url(attempt))
            response.set_cookie(
                settings.GOOGLE_OAUTH_STATE_COOKIE_NAME,
                cookie_payload,
                max_age=settings.GOOGLE_OAUTH_ATTEMPT_MAX_AGE_SECONDS,
                httponly=True,
                secure=settings.SECURE_COOKIES,
                samesite="Lax",
                path="/api/auth/google/",
            )
            return response
        except GoogleOAuthError as error:
            return HttpResponseRedirect(oauth_frontend_redirect(error.code))


class GoogleOAuthCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_oauth"

    def get(self, request):
        try:
            attempt = load_google_oauth_attempt(
                request.COOKIES.get(settings.GOOGLE_OAUTH_STATE_COOKIE_NAME),
                str(request.query_params.get("state", "")),
            )
            consume_google_oauth_attempt(attempt)
            if request.query_params.get("error"):
                response = HttpResponseRedirect(oauth_frontend_redirect("cancelled"))
            else:
                provider_id_token = exchange_google_code(
                    str(request.query_params.get("code", "")), attempt.code_verifier
                )
                claims = verify_google_id_token(provider_id_token)
                identity_data = validate_google_claims(claims, attempt.nonce)
                user = get_or_link_google_user(identity_data)
                tokens = token_pair_for_user(user)
                response = HttpResponseRedirect(oauth_frontend_redirect("success"))
                set_refresh_cookie(response, tokens["refresh"])
        except GoogleOAuthError as error:
            response = HttpResponseRedirect(oauth_frontend_redirect(error.code))
        _clear_google_oauth_cookie(response)
        return response
