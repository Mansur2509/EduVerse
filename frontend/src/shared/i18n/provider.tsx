"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  defaultLocale,
  isLocaleCode,
  localeMetadata,
  type LocaleCode
} from "./config";
import { dictionaries } from "./dictionaries";
import type { TranslationKey, TranslationValues } from "./types";

const LOCALE_STORAGE_KEY = "uniway.locale";
const LEGACY_LOCALE_STORAGE_KEY = "eduverse.locale";

type I18nContextValue = {
  locale: LocaleCode;
  setLocale: (locale: LocaleCode) => void;
  t: (key: TranslationKey, values?: TranslationValues) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function interpolate(message: string, values?: TranslationValues) {
  if (!values) {
    return message;
  }

  return message.replace(/\{\{(\w+)\}\}/g, (placeholder, key: string) => {
    const value = values[key];
    return value === undefined ? placeholder : String(value);
  });
}

// Resolve a translation, falling back to the key itself when it is missing
// instead of letting `undefined.replace(...)` throw. A render-time throw here
// is especially dangerous because, with no error boundary, it can unmount the
// whole route into a blank page with no feedback. Missing or dynamically-built
// keys must degrade gracefully rather than crash the page.
function resolve(
  dictionary: Record<TranslationKey, string>,
  key: TranslationKey,
  values?: TranslationValues
) {
  const message = dictionary[key];
  if (typeof message !== "string") {
    if (process.env.NODE_ENV !== "production") {
      console.warn(`[i18n] Missing translation key: ${String(key)}`);
    }
    return String(key);
  }
  return interpolate(message, values);
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<LocaleCode>(defaultLocale);

  useEffect(() => {
    const storedLocale =
      window.localStorage.getItem(LOCALE_STORAGE_KEY) ??
      window.localStorage.getItem(LEGACY_LOCALE_STORAGE_KEY);
    if (storedLocale && isLocaleCode(storedLocale)) {
      setLocaleState(storedLocale);
      window.localStorage.setItem(LOCALE_STORAGE_KEY, storedLocale);
      window.localStorage.removeItem(LEGACY_LOCALE_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    const metadata = localeMetadata[locale];
    document.documentElement.lang = locale;
    document.documentElement.dir = metadata.direction;
  }, [locale]);

  const setLocale = useCallback((nextLocale: LocaleCode) => {
    setLocaleState(nextLocale);
    window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale);
    window.localStorage.removeItem(LEGACY_LOCALE_STORAGE_KEY);
  }, []);

  const t = useCallback(
    (key: TranslationKey, values?: TranslationValues) =>
      resolve(dictionaries[locale], key, values),
    [locale]
  );

  const contextValue = useMemo(
    () => ({ locale, setLocale, t }),
    [locale, setLocale, t]
  );

  return (
    <I18nContext.Provider value={contextValue}>{children}</I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider.");
  }
  return context;
}
