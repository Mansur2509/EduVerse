"use client";

import { AlertTriangle, CircleUserRound, Eye, LogOut, RefreshCw, ShieldCheck } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import type { NotificationPreference } from "@/entities/notification";
import { useAuth } from "@/features/auth";
import {
  getNotificationPreferencesRequest,
  updateNotificationPreferencesRequest
} from "@/features/notifications";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { fieldClassName } from "@/shared/ui/field";
import { AppIcon } from "@/shared/ui/icon";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { LanguageSwitcher } from "@/shared/ui/language-switcher";
import { ThemeSelector } from "@/shared/ui/theme-selector";

const PREFERENCE_FIELDS: Array<{
  key: keyof Omit<NotificationPreference, "updated_at">;
  labelKey: TranslationKey;
}> = [
  { key: "deadlines_enabled", labelKey: "notifications.preferences.deadlines" },
  { key: "exams_enabled", labelKey: "notifications.preferences.exams" },
  { key: "roadmap_enabled", labelKey: "notifications.preferences.roadmap" },
  { key: "recommendations_essays_enabled", labelKey: "notifications.preferences.recommendationsEssays" },
  { key: "essay_reviews_enabled", labelKey: "notifications.preferences.essayReviews" },
  { key: "events_enabled", labelKey: "notifications.preferences.events" },
  { key: "organizer_events_enabled", labelKey: "notifications.preferences.organizerEvents" }
];

function SectionHeading({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function SettingsScreen() {
  const { t } = useI18n();
  const { user, updateUser, logout } = useAuth();

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [nameSaveState, setNameSaveState] = useState<"idle" | "saving" | "saved" | "error">(
    "idle"
  );

  useEffect(() => {
    setFullName(user?.full_name ?? "");
  }, [user?.full_name]);

  async function handleSaveName(event: FormEvent) {
    event.preventDefault();
    const trimmed = fullName.trim();
    if (!user || !trimmed || trimmed === user.full_name) return;
    setNameSaveState("saving");
    try {
      await updateUser({ full_name: trimmed });
      setNameSaveState("saved");
    } catch {
      setNameSaveState("error");
    }
  }

  const [preferences, setPreferences] = useState<NotificationPreference | null>(null);
  const [preferencesError, setPreferencesError] = useState(false);
  const [savingPreferenceKey, setSavingPreferenceKey] = useState<string | null>(null);
  const [preferenceActionError, setPreferenceActionError] = useState(false);

  const loadPreferences = useCallback(() => {
    setPreferencesError(false);
    setPreferences(null);
    getNotificationPreferencesRequest()
      .then(setPreferences)
      .catch(() => setPreferencesError(true));
  }, []);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  async function togglePreference(key: keyof Omit<NotificationPreference, "updated_at">) {
    if (!preferences) return;
    setPreferenceActionError(false);
    setSavingPreferenceKey(key);
    const previous = preferences;
    // Optimistic flip is safe here: a single boolean preference has no
    // cascading side effects, so reverting on failure fully undoes it.
    setPreferences({ ...preferences, [key]: !preferences[key] });
    try {
      const updated = await updateNotificationPreferencesRequest({ [key]: !previous[key] });
      setPreferences(updated);
    } catch {
      setPreferences(previous);
      setPreferenceActionError(true);
    } finally {
      setSavingPreferenceKey(null);
    }
  }

  async function handleLogout() {
    await logout();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-hover">
          {t("settings.eyebrow")}
        </p>
        <h1 className="mt-1 text-2xl font-semibold">{t("settings.title")}</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          {t("settings.description")}
        </p>
      </div>

      <Card className="p-4">
        <SectionHeading
          description={t("settings.appearance.description")}
          title={t("settings.appearance.title")}
        />
        <ThemeSelector />
      </Card>

      <Card className="p-4">
        <SectionHeading
          description={t("settings.language.description")}
          title={t("settings.language.title")}
        />
        <LanguageSwitcher />
      </Card>

      <Card className="p-4">
        <SectionHeading
          description={t("settings.notifications.description")}
          title={t("settings.notifications.title")}
        />
        {preferencesError ? (
          <div className="flex items-center justify-between gap-3 rounded-sm border border-danger/35 bg-danger/10 p-3">
            <p className="flex items-center gap-2 text-sm text-danger" role="alert">
              <AppIcon icon={AlertTriangle} />
              {t("settings.notifications.loadError")}
            </p>
            <Button onClick={loadPreferences} size="sm" type="button" variant="ghost">
              <AppIcon className="mr-2" icon={RefreshCw} />
              {t("essays.actions.retry")}
            </Button>
          </div>
        ) : preferences ? (
          <>
            {preferenceActionError ? (
              <p className="mb-3 text-sm text-danger" role="alert">
                {t("settings.notifications.saveError")}
              </p>
            ) : null}
            <div className="grid gap-3 sm:grid-cols-2">
              {PREFERENCE_FIELDS.map(({ key, labelKey }) => (
                <label
                  className="flex items-center justify-between gap-3 rounded-sm border bg-surface px-3 py-2.5"
                  key={key}
                >
                  <span className="text-sm">{t(labelKey)}</span>
                  <input
                    checked={preferences[key]}
                    disabled={savingPreferenceKey === key}
                    onChange={() => void togglePreference(key)}
                    type="checkbox"
                  />
                </label>
              ))}
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">{t("settings.notifications.loading")}</p>
        )}
      </Card>

      <Card className="p-4">
        <SectionHeading
          description={t("settings.account.description")}
          title={t("settings.account.title")}
        />
        <dl className="grid gap-3 sm:grid-cols-2 text-sm">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("settings.account.email")}
            </dt>
            <dd className="mt-0.5">{user?.email}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("settings.account.role")}
            </dt>
            <dd className="mt-0.5">
              {user ? t(`roles.${user.role}` as TranslationKey) : ""}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("settings.account.googleLinked")}
            </dt>
            <dd className="mt-0.5 flex items-center gap-1.5">
              {user?.google_linked ? (
                <>
                  <AppIcon className="text-success" icon={ShieldCheck} size="sm" />
                  {t("settings.account.googleLinkedYes")}
                </>
              ) : (
                t("settings.account.googleLinkedNo")
              )}
            </dd>
          </div>
        </dl>

        <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={(event) => void handleSaveName(event)}>
          <label className="block flex-1 min-w-[12rem] text-sm font-semibold">
            {t("settings.account.displayName")}
            <input
              className={fieldClassName}
              maxLength={180}
              onChange={(event) => {
                setFullName(event.target.value);
                setNameSaveState("idle");
              }}
              value={fullName}
            />
          </label>
          <Button disabled={nameSaveState === "saving"} size="sm" type="submit">
            {nameSaveState === "saving" ? t("settings.account.saving") : t("settings.account.save")}
          </Button>
        </form>
        {nameSaveState === "saved" ? (
          <p className="mt-2 text-xs text-success">{t("settings.account.saveSuccess")}</p>
        ) : null}
        {nameSaveState === "error" ? (
          <p className="mt-2 text-xs text-danger" role="alert">
            {t("settings.account.saveError")}
          </p>
        ) : null}

        <div className="mt-4 border-t pt-4">
          <Button onClick={() => void handleLogout()} size="sm" type="button" variant="secondary">
            <AppIcon className="mr-2" icon={LogOut} />
            {t("navigation.logout")}
          </Button>
        </div>
      </Card>

      <Card className="p-4">
        <SectionHeading
          description={t("settings.privacy.description")}
          title={t("settings.privacy.title")}
        />
        <p className="text-sm leading-6 text-muted-foreground">{t("settings.privacy.dataStored")}</p>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {t("settings.privacy.exportDeletionUnavailable")}
        </p>
      </Card>

      <Card className="p-4">
        <SectionHeading
          description={t("settings.accessibility.description")}
          title={t("settings.accessibility.title")}
        />
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <AppIcon icon={Eye} />
          {t("settings.accessibility.reducedMotion")}
        </p>
      </Card>

      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <AppIcon icon={CircleUserRound} size="xs" />
        {t("settings.footerNote")}
      </p>
    </div>
  );
}
