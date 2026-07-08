import { env } from "@/shared/config/env";
import {
  authStorage,
  notifyAuthInvalid,
  type AuthTokens
} from "@/shared/lib/auth-storage";

// The backend runs on Render's free tier, which spins the service down after a
// period of inactivity, so a cold start can take 60-90s. Rather than make every
// button wait that long before showing an error (which reads as "stuck
// forever" even though it would eventually resolve), we cap requests at a
// bounded 15-25s window and surface a clear, retryable "may be waking up"
// error well before the user gives up. The GET auto-retry below (which also
// serves as the wake-up ping) means a cold start typically self-heals within
// a couple of these shorter windows instead of one long silent wait.
export const REQUEST_TIMEOUT_MS = 20_000;

// Session checks (`/auth/me/`) gate the whole app behind a full-screen loader,
// so they get a shorter budget: a slow session check should surface a
// recoverable "offline" screen quickly rather than block every page load.
export const SESSION_CHECK_TIMEOUT_MS = 12_000;

// A failed first request is also what *triggers* the Render wake-up. So for
// safe, idempotent GET reads we automatically retry once on a timeout/network
// error after a short delay: by the retry, the container is usually booting or
// already warm, so the page self-heals through a cold start instead of forcing
// the user to hit "Try again". Non-GET requests are never auto-retried.
const NETWORK_RETRY_DELAY_MS = 2_500;
const MAX_GET_NETWORK_RETRIES = 1;

type ApiOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  auth?: boolean;
  base?:
    | "api"
    | "auth"
    | "profile"
    | "events"
    | "organizer"
    | "moderation"
    | "roadmap"
    | "essays"
    | "applications"
    | "suggestions"
    | "universityImport"
    | "feedback"
    | "adminFeedback";
  retryOnUnauthorized?: boolean;
  timeoutMs?: number;
  responseType?: "json" | "blob";
};

// Classifies *why* a request failed so callers can pick a localized message
// without ever reading `.message` (which only exists for logs/dev diagnostics
// and is never guaranteed to be translated):
//  - "timeout": the request was aborted after the configured timeout window.
//  - "network": fetch rejected before any response came back (offline, DNS,
//    CORS-style failure, or the backend genuinely unreachable).
//  - "http": a response came back with a non-2xx status.
//  - "parse": a response came back but wasn't valid/expected JSON.
export type ApiErrorCode = "timeout" | "network" | "http" | "parse";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly data: unknown,
    // True when the request never got a response: it either timed out (likely a
    // Render cold start) or the network/backend was unreachable. Screens use
    // this to show a "the server may be waking up" message instead of a generic
    // failure, since this case is usually transient and resolves on retry.
    public readonly isNetworkError = false,
    public readonly errorCode: ApiErrorCode = "http"
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let refreshPromise: Promise<AuthTokens | null> | null = null;

export type PaginatedListResponse<Item> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Item[];
};

function getErrorMessage(data: unknown, fallback: string) {
  if (typeof data === "object" && data !== null) {
    const detail = Reflect.get(data, "detail");
    if (typeof detail === "string") {
      return detail;
    }

    const nonFieldErrors = Reflect.get(data, "non_field_errors");
    if (
      Array.isArray(nonFieldErrors) &&
      typeof nonFieldErrors[0] === "string"
    ) {
      return nonFieldErrors[0];
    }
  }
  return fallback;
}

function summarizePayload(data: unknown): string {
  if (data === undefined) return "empty";
  if (data === null) return "null";
  if (Array.isArray(data)) return `array(${data.length})`;
  if (typeof data === "object") {
    const keys = Object.keys(data as Record<string, unknown>).slice(0, 8);
    return `object(${keys.join(",")})`;
  }
  return typeof data;
}

function logApiDiagnostic(url: string, status: number, data: unknown) {
  if (process.env.NODE_ENV === "production") {
    return;
  }
  console.info("[uniway-api]", {
    url,
    status,
    payload: summarizePayload(data)
  });
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const text = await response.text();
  if (!text.trim()) {
    return undefined;
  }

  if (!contentType.includes("application/json")) {
    throw new ApiError(
      `UniWay API returned ${contentType || "an unknown content type"} instead of JSON.`,
      response.status,
      {
        contentType,
        body: text.slice(0, 500)
      },
      false,
      "parse"
    );
  }

  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(text) as unknown;
    } catch {
      throw new ApiError(
        "UniWay API returned invalid JSON.",
        response.status,
        {
          contentType,
          body: text.slice(0, 500)
        },
        false,
        "parse"
      );
    }
  }
  return undefined;
}

/**
 * fetch with a hard timeout. Aborts the request after `timeoutMs` and converts
 * both timeouts and lower-level network failures into a typed ApiError so every
 * caller gets a consistent, retryable error shape instead of a raw TypeError or
 * an indefinite hang.
 */
export async function withTimeout(
  input: string,
  init: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    // These two messages exist only for dev-console logs and as a last-resort
    // fallback; UI code must branch on `errorCode` and render a translated
    // string instead of ever displaying `.message` to the user.
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        "The request took too long. The server may be waking up — please try again.",
        0,
        null,
        true,
        "timeout"
      );
    }
    throw new ApiError(
      "The service is unreachable. Please check your connection and try again.",
      0,
      null,
      true,
      "network"
    );
  } finally {
    clearTimeout(timer);
  }
}

async function refreshTokens(): Promise<AuthTokens | null> {
  const currentTokens = authStorage.get();
  if (!currentTokens) {
    return null;
  }

  let response: Response;
  try {
    response = await withTimeout(
      `${env.authApiBaseUrl}/token/refresh/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: currentTokens.refresh })
      },
      REQUEST_TIMEOUT_MS
    );
  } catch {
    // A timeout/network failure during refresh should not destroy a possibly
    // valid session — let the caller surface a retryable error instead.
    return null;
  }

  if (!response.ok) {
    authStorage.clear();
    notifyAuthInvalid();
    return null;
  }

  const data = (await response.json()) as {
    access: string;
    refresh?: string;
  };
  const tokens = {
    access: data.access,
    refresh: data.refresh ?? currentTokens.refresh
  };
  authStorage.set(tokens);
  return tokens;
}

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const {
    auth = true,
    base = "api",
    retryOnUnauthorized = true,
    timeoutMs = REQUEST_TIMEOUT_MS,
    responseType = "json",
    body,
    ...requestOptions
  } = options;
  const tokens = auth ? authStorage.get() : null;
  const baseUrl =
    base === "auth"
      ? env.authApiBaseUrl
      : base === "profile"
        ? env.profileApiBaseUrl
        : base === "events"
          ? env.eventsApiBaseUrl
          : base === "organizer"
            ? env.organizerApiBaseUrl
            : base === "moderation"
              ? env.eventModerationApiBaseUrl
              : base === "roadmap"
                ? env.roadmapApiBaseUrl
                : base === "essays"
                  ? env.essaysApiBaseUrl
                  : base === "applications"
                    ? env.applicationsApiBaseUrl
                    : base === "suggestions"
                      ? env.suggestionsApiBaseUrl
                      : base === "universityImport"
                        ? env.universityImportApiBaseUrl
                        : base === "feedback"
                          ? env.feedbackApiBaseUrl
                          : base === "adminFeedback"
                            ? env.adminFeedbackApiBaseUrl
                      : env.apiBaseUrl;
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  const init: RequestInit = {
    ...requestOptions,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(tokens ? { Authorization: `Bearer ${tokens.access}` } : {}),
      ...requestOptions.headers
    }
  };
  const method = (requestOptions.method ?? "GET").toUpperCase();
  const maxNetworkRetries = method === "GET" ? MAX_GET_NETWORK_RETRIES : 0;
  const url = `${baseUrl}${path}`;

  let response: Response;
  let networkAttempt = 0;
  for (;;) {
    try {
      response = await withTimeout(url, init, timeoutMs);
      break;
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.isNetworkError &&
        networkAttempt < maxNetworkRetries
      ) {
        networkAttempt += 1;
        await new Promise((resolve) => setTimeout(resolve, NETWORK_RETRY_DELAY_MS));
        continue;
      }
      throw error;
    }
  }

  if (response.status === 401 && auth && retryOnUnauthorized) {
    refreshPromise ??= refreshTokens().finally(() => {
      refreshPromise = null;
    });
    const refreshedTokens = await refreshPromise;
    if (refreshedTokens) {
      return apiRequest<T>(path, {
        ...options,
        retryOnUnauthorized: false
      });
    }
  }

  if (responseType === "blob") {
    if (!response.ok) {
      let errorData: unknown;
      try {
        errorData = await parseResponse(response);
      } catch {
        errorData = undefined;
      }
      throw new ApiError(
        getErrorMessage(
          errorData,
          `UniWay API request failed with status ${response.status}.`
        ),
        response.status,
        errorData
      );
    }
    return (await response.blob()) as T;
  }

  const data = await parseResponse(response);
  logApiDiagnostic(url, response.status, data);
  if (!response.ok) {
    if (response.status === 401 && auth) {
      authStorage.clear();
      notifyAuthInvalid();
    }
    throw new ApiError(
      getErrorMessage(data, `UniWay API request failed with status ${response.status}.`),
      response.status,
      data
    );
  }

  return data as T;
}

export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again."
) {
  if (error instanceof ApiError) {
    if (typeof error.data === "object" && error.data !== null) {
      for (const value of Object.values(error.data)) {
        if (Array.isArray(value) && typeof value[0] === "string") {
          return value[0];
        }
      }
    }
    return error.message;
  }
  return fallback;
}

export function isNetworkError(error: unknown): boolean {
  return error instanceof ApiError && error.isNetworkError;
}

export function isPaginatedResponse<Item>(
  data: unknown
): data is PaginatedListResponse<Item> {
  return (
    typeof data === "object" &&
    data !== null &&
    Array.isArray(Reflect.get(data, "results")) &&
    typeof Reflect.get(data, "count") === "number"
  );
}

export function normalizeListResponse<Item>(
  data: unknown,
  endpointName = "list endpoint"
): Item[] {
  if (Array.isArray(data)) {
    return data as Item[];
  }
  if (isPaginatedResponse<Item>(data)) {
    return data.results;
  }
  throw new ApiError(
    `UniWay API payload mismatch for ${endpointName}: expected an array or a paginated results object.`,
    0,
    data
  );
}

export function normalizePaginatedResponse<Item>(
  data: unknown,
  endpointName = "list endpoint"
): PaginatedListResponse<Item> {
  if (isPaginatedResponse<Item>(data)) {
    return data;
  }
  const results = normalizeListResponse<Item>(data, endpointName);
  return {
    count: results.length,
    next: null,
    previous: null,
    results
  };
}
