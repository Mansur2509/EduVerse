from django.urls import path

from .views import (
    AuthConfigView,
    AuthTokenRefreshView,
    CurrentUserView,
    GoogleOAuthCallbackView,
    GoogleOAuthStartView,
    LoginView,
    LogoutView,
    RegisterView,
)

app_name = "auth"

urlpatterns = [
    path("config/", AuthConfigView.as_view(), name="config"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("token/refresh/", AuthTokenRefreshView.as_view(), name="token-refresh"),
    path("google/start/", GoogleOAuthStartView.as_view(), name="google-start"),
    path("google/callback/", GoogleOAuthCallbackView.as_view(), name="google-callback"),
]
