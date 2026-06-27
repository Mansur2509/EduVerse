import type { LocaleCode } from "@/shared/i18n";

export function formatDateTime(value: string, locale: LocaleCode) {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function formatDate(value: string, locale: LocaleCode) {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium"
  }).format(new Date(value));
}

