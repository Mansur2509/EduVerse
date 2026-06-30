export type AuthTokens = {
  access: string;
  refresh: string;
};

const AUTH_STORAGE_KEY = "eduverse.auth.tokens";
export const AUTH_INVALID_EVENT = "eduverse:auth-invalid";

let memoryTokens: AuthTokens | null = null;

function getBrowserStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function removeStoredTokens(storage: Storage | null) {
  try {
    storage?.removeItem(AUTH_STORAGE_KEY);
  } catch {
    // Storage can be unavailable in hardened/incognito browser contexts.
  }
}

export const authStorage = {
  get(): AuthTokens | null {
    const storage = getBrowserStorage();

    let rawValue: string | null = null;
    try {
      rawValue = storage?.getItem(AUTH_STORAGE_KEY) ?? null;
    } catch {
      return memoryTokens;
    }
    if (!rawValue) {
      return memoryTokens;
    }

    try {
      const parsedValue = JSON.parse(rawValue) as Partial<AuthTokens>;
      if (
        typeof parsedValue.access === "string" &&
        typeof parsedValue.refresh === "string"
      ) {
        return {
          access: parsedValue.access,
          refresh: parsedValue.refresh
        };
      }
    } catch {
      // Invalid or manually modified auth state is discarded.
    }

    memoryTokens = null;
    removeStoredTokens(storage);
    return null;
  },

  set(tokens: AuthTokens) {
    memoryTokens = tokens;

    const storage = getBrowserStorage();
    try {
      storage?.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
    } catch {
      // Keep the current tab usable even when persistent storage is blocked.
    }
  },

  clear() {
    memoryTokens = null;
    removeStoredTokens(getBrowserStorage());
  }
};

export function notifyAuthInvalid() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_INVALID_EVENT));
  }
}
