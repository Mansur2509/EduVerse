import type {
  AuthResponse,
  CurrentUser,
  LoginInput,
  RegisterInput,
  UpdateCurrentUserInput
} from "@/entities/user";
import { apiRequest, SESSION_CHECK_TIMEOUT_MS } from "@/shared/api/client";
import { env } from "@/shared/config/env";

export function loginRequest(input: LoginInput) {
  return apiRequest<AuthResponse>("/login/", {
    base: "auth",
    auth: false,
    method: "POST",
    body: input
  });
}

export function registerRequest(input: RegisterInput) {
  return apiRequest<AuthResponse>("/register/", {
    base: "auth",
    auth: false,
    method: "POST",
    body: input
  });
}

export function logoutRequest() {
  return apiRequest<void>("/logout/", {
    base: "auth",
    method: "POST",
    body: {}
  });
}

export function getCurrentUserRequest() {
  return apiRequest<CurrentUser>("/me/", { base: "auth", timeoutMs: SESSION_CHECK_TIMEOUT_MS });
}

export function updateCurrentUserRequest(input: UpdateCurrentUserInput) {
  return apiRequest<CurrentUser>("/me/", {
    base: "auth",
    method: "PATCH",
    body: input
  });
}

export function getGoogleOAuthStartUrl() {
  return `${env.authApiBaseUrl}/google/start/`;
}

export function getAuthConfigRequest() {
  return apiRequest<{ google_oauth_enabled: boolean }>("/config/", {
    base: "auth",
    auth: false
  });
}
