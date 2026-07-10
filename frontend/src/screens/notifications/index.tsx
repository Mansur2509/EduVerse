"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import type { Notification, NotificationPreference, NotificationStatus } from "@/entities/notification";
import {
  getNotificationPreferencesRequest,
  getNotificationsRequest,
  markAllNotificationsReadRequest,
  updateNotificationPreferencesRequest,
  updateNotificationStatusRequest
} from "@/features/notifications";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const STATUS_FILTERS: Array<NotificationStatus | "all"> = ["all", "unread", "read", "archived"];

const PRIORITY_STYLES: Record<Notification["priority"], string> = {
  low: "border-muted-foreground/30 bg-surface text-muted-foreground",
  normal: "border-accent/35 bg-accent/10 text-accent",
  high: "border-warning/35 bg-warning/10 text-warning",
  urgent: "border-danger/35 bg-danger/10 text-danger"
};

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

export function NotificationsScreen() {
  const { locale, t } = useI18n();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [statusFilter, setStatusFilter] = useState<NotificationStatus | "all">("all");
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const [preferences, setPreferences] = useState<NotificationPreference | null>(null);
  const [isSavingPreference, setIsSavingPreference] = useState(false);

  const loadNotifications = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getNotificationsRequest(
        statusFilter === "all" ? {} : { status: statusFilter }
      );
      setNotifications(response.results);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    getNotificationPreferencesRequest()
      .then(setPreferences)
      .catch(() => undefined);
  }, []);

  const updateStatus = async (notification: Notification, nextStatus: NotificationStatus) => {
    const updated = await updateNotificationStatusRequest(notification.id, nextStatus);
    setNotifications((current) =>
      statusFilter === "all"
        ? current.map((item) => (item.id === updated.id ? updated : item))
        : current.filter((item) => item.id !== updated.id)
    );
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsReadRequest();
    void loadNotifications();
  };

  const togglePreference = async (key: keyof Omit<NotificationPreference, "updated_at">) => {
    if (!preferences) return;
    setIsSavingPreference(true);
    try {
      const updated = await updateNotificationPreferencesRequest({ [key]: !preferences[key] });
      setPreferences(updated);
    } finally {
      setIsSavingPreference(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("notifications.page.eyebrow")}
        </p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">{t("notifications.page.title")}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          {t("notifications.page.description")}
        </p>
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((filter) => (
              <Button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                size="sm"
                type="button"
                variant={statusFilter === filter ? "primary" : "secondary"}
              >
                {t(`notifications.statusFilter.${filter}` as TranslationKey)}
              </Button>
            ))}
          </div>
          {statusFilter !== "archived" && notifications.some((item) => item.status === "unread") ? (
            <Button onClick={() => void handleMarkAllRead()} size="sm" type="button" variant="ghost">
              {t("notifications.page.markAllRead")}
            </Button>
          ) : null}
        </div>

        {isLoading ? (
          <Card>
            <p className="text-sm text-muted-foreground">{t("notifications.page.loading")}</p>
          </Card>
        ) : hasError ? (
          <Card>
            <p className="text-sm text-danger" role="alert">
              {t("notifications.page.loadError")}
            </p>
            <Button className="mt-4" onClick={() => void loadNotifications()} type="button">
              {t("essays.actions.retry")}
            </Button>
          </Card>
        ) : notifications.length === 0 ? (
          <Card>
            <p className="text-sm text-muted-foreground">{t("notifications.page.empty")}</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {notifications.map((notification) => (
              <Card key={notification.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${PRIORITY_STYLES[notification.priority]}`}
                      >
                        {t(`notifications.priority.${notification.priority}` as TranslationKey)}
                      </span>
                      {notification.status === "unread" ? (
                        <Badge className="text-[0.65rem]">{t("notifications.statusFilter.unread")}</Badge>
                      ) : null}
                    </div>
                    <p className="mt-2 font-semibold">{notification.title}</p>
                    {notification.message ? (
                      <p className="mt-1 text-sm text-muted-foreground">{notification.message}</p>
                    ) : null}
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDateTime(notification.created_at, locale)}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    {notification.action_url ? (
                      <Button asChild size="sm" variant="secondary">
                        <Link href={notification.action_url}>{t("notifications.page.open")}</Link>
                      </Button>
                    ) : null}
                    {notification.status !== "read" ? (
                      <Button
                        onClick={() => void updateStatus(notification, "read")}
                        size="sm"
                        type="button"
                        variant="ghost"
                      >
                        {t("notifications.page.markRead")}
                      </Button>
                    ) : null}
                    {notification.status !== "archived" ? (
                      <Button
                        onClick={() => void updateStatus(notification, "archived")}
                        size="sm"
                        type="button"
                        variant="ghost"
                      >
                        {t("notifications.page.archive")}
                      </Button>
                    ) : null}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">{t("notifications.preferences.title")}</h2>
        <Card className="p-4">
          {preferences ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {PREFERENCE_FIELDS.map(({ key, labelKey }) => (
                <label
                  className="flex items-center justify-between gap-3 rounded-sm border bg-surface px-3 py-2.5"
                  key={key}
                >
                  <span className="text-sm">{t(labelKey)}</span>
                  <input
                    checked={preferences[key]}
                    disabled={isSavingPreference}
                    onChange={() => void togglePreference(key)}
                    type="checkbox"
                  />
                </label>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("notifications.preferences.loading")}</p>
          )}
        </Card>
      </section>
    </div>
  );
}
