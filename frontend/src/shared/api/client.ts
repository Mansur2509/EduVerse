import { env } from "@/shared/config/env";
import {
  authStorage,
  notifyAuthInvalid,
  type AuthTokens
} from "@/shared/lib/auth-storage";

// The backend runs on Render's free tier, which spins the service down after a
// period of inactivity. The first request after a spin-down is a "cold start"
// and can take ~60-90s while the container boots. Without a timeout a cold
// start would leave the browser's fetch pending indefinitely, which is what
// produced the "infinite spinner that never resolves" bug. We cap every
// request at REQUEST_TIMEOUT_MS: long enough to let a cold start finish, but
// bounded so a genuinely unreachable backend surfaces a clear, retryable error
// instead of hanging forever.
export const REQUEST_TIMEOUT_MS = 60_000;

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
    | "applications";
  retryOnUnauthorized?: boolean;
  timeoutMs?: number;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly data: unknown,
    // True when the request never got a response: it either timed out (likely a
    // Render cold start) or the network/backend was unreachable. Screens use
    // this to show a "the server may be waking up" message instead of a generic
    // failure, since this case is usually transient and resolves on retry.
    public readonly isNetworkError = false
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
  console.info("[eduverse-api]", {
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
      `EduVerse API returned ${contentType || "an unknown content type"} instead of JSON.`,
      response.status,
      {
        contentType,
        body: text.slice(0, 500)
      }
    );
  }

  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(text) as unknown;
    } catch {
      throw new ApiError(
        "EduVerse API returned invalid JSON.",
        response.status,
        {
          contentType,
          body: text.slice(0, 500)
        }
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
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        "The request took too long. The server may be waking up — please try again.",
        0,
        null,
        true
      );
    }
    throw new ApiError(
      "The service is unreachable. Please check your connection and try again.",
      0,
      null,
      true
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
                    : env.apiBaseUrl;
  const init: RequestInit = {
    ...requestOptions,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
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

  const data = await parseResponse(response);
  logApiDiagnostic(url, response.status, data);
  if (!response.ok) {
    if (response.status === 401 && auth) {
      authStorage.clear();
      notifyAuthInvalid();
    }
    throw new ApiError(
      getErrorMessage(data, `EduVerse API request failed with status ${response.status}.`),
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
    `EduVerse API payload mismatch for ${endpointName}: expected an array or a paginated results object.`,
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
