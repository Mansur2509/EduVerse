"use client";

import Link from "next/link";
import {
  Archive,
  BellRing,
  BookOpenCheck,
  CalendarCheck,
  CalendarClock,
  Check,
  CheckCheck,
  ExternalLink,
  FileText,
  Inbox,
  ListChecks,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  type LucideIcon
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import type {
  Notification,
  NotificationPreference,
  NotificationStatus,
  NotificationType
} from "@/entities/notification";
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
import { EmptyState } from "@/shared/ui/empty-state";
import { AppIcon } from "@/shared/ui/icon";
import { LoadingNotice } from "@/shared/ui/loading-notice";
import { DEFAULT_PAGE_SIZE, PaginatedList } from "@/shared/ui/pagination";

const STATUS_FILTERS: Array<NotificationStatus | "all"> = ["all", "unread", "read", "archived"];

const PRIORITY_STYLES: Record<Notification["priority"], string> = {
  low: "border-muted-foreground/30 bg-surface text-muted-foreground",
  normal: "border-accent/35 bg-accent/10 text-accent",
  high: "border-warning/35 bg-warning/10 text-warning",
  urgent: "border-danger/35 bg-danger/10 text-danger"
};

const PRIORITY_ICON_CHIP_STYLES: Record<Notification["priority"], string> = {
  low: "border-muted-foreground/30 bg-surface text-muted-foreground",
  normal: "border-accent/35 bg-accent/10 text-accent",
  high: "border-warning/35 bg-warning/10 text-warning",
  urgent: "border-danger/35 bg-danger/10 text-danger"
};

// Full literal class strings (not dynamically concatenated) so Tailwind's
// static analyzer can actually find and keep them in the production build.
const PRIORITY_HOVER_STYLES: Record<Notification["priority"], string> = {
  low: "hover:border-muted-foreground/45",
  normal: "hover:border-accent/45",
  high: "hover:border-warning/45",
  urgent: "hover:border-danger/45"
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

const NOTIFICATION_ICONS: Record<NotificationType, LucideIcon> = {
  deadline_upcoming: CalendarClock,
  exam_date_upcoming: BookOpenCheck,
  roadmap_task_due_soon: ListChecks,
  recommendation_missing: Sparkles,
  essay_missing: FileText,
  essay_review_completed: FileText,
  event_registration_confirmed: CalendarCheck,
  event_starting_soon: CalendarClock,
  organizer_event_approved: ShieldCheck,
  organizer_event_rejected: ShieldCheck
};

export function NotificationsScreen() {
  const { locale, t } = useI18n();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [statusFilter, setStatusFilter] = useState<NotificationStatus | "all">("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const [actionError, setActionError] = useState(false);

  const [preferences, setPreferences] = useState<NotificationPreference | null>(null);
  const [preferencesError, setPreferencesError] = useState(false);
  const [savingPreferenceKey, setSavingPreferenceKey] = useState<string | null>(null);
  const [preferenceActionError, setPreferenceActionError] = useState(false);

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
    setCurrentPage(1);
  }, [loadNotifications]);

  const loadPreferences = useCallback(() => {
    setPreferencesError(false);
    getNotificationPreferencesRequest()
      .then(setPreferences)
      .catch(() => setPreferencesError(true));
  }, []);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  const updateStatus = async (notification: Notification, nextStatus: NotificationStatus) => {
    setActionError(false);
    try {
      const updated = await updateNotificationStatusRequest(notification.id, nextStatus);
      setNotifications((current) =>
        statusFilter === "all"
          ? current.map((item) => (item.id === updated.id ? updated : item))
          : current.filter((item) => item.id !== updated.id)
      );
    } catch {
      setActionError(true);
    }
  };

  const handleMarkAllRead = async () => {
    setActionError(false);
    try {
      await markAllNotificationsReadRequest();
      // Patch local state instead of refetching the whole list -- the mutation
      // is fully predictable (every unread item becomes read), so there's
      // nothing a fresh GET would tell us that we don't already know.
      setNotifications((current) =>
        statusFilter === "unread"
          ? []
          : current.map((item) => (item.status === "unread" ? { ...item, status: "read" } : item))
      );
    } catch {
      setActionError(true);
    }
  };

  const togglePreference = async (key: keyof Omit<NotificationPreference, "updated_at">) => {
    if (!preferences) return;
    setPreferenceActionError(false);
    setSavingPreferenceKey(key);
    const previous = preferences;
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
  };

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <div className="flex items-center gap-2 text-primary-hover">
          <AppIcon icon={BellRing} size="md" />
          <p className="text-eyebrow">
            {t("notifications.page.eyebrow")}
          </p>
        </div>
        <h1 className="text-display mt-2">{t("notifications.page.title")}</h1>
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
              <AppIcon className="mr-2" icon={CheckCheck} />
              {t("notifications.page.markAllRead")}
            </Button>
          ) : null}
        </div>

        {actionError ? (
          <p className="mb-3 flex items-center gap-2 text-sm text-danger" role="alert">
            <AppIcon icon={TriangleAlert} />
            {t("notifications.page.actionError")}
          </p>
        ) : null}

        {isLoading && notifications.length === 0 ? (
          <LoadingNotice message={t("notifications.page.loading")} />
        ) : hasError ? (
          <Card>
            <p className="flex items-center gap-2 text-sm text-danger" role="alert">
              <AppIcon icon={TriangleAlert} />
              {t("notifications.page.loadError")}
            </p>
            <Button className="mt-4" onClick={() => void loadNotifications()} type="button">
              <AppIcon className="mr-2" icon={RefreshCw} />
              {t("essays.actions.retry")}
            </Button>
          </Card>
        ) : (
          <PaginatedList
            currentPage={currentPage}
            emptyState={
              <EmptyState description={t("notifications.page.empty")} icon={Inbox} title={t("notifications.page.title")} />
            }
            getItemKey={(notification) => notification.id}
            items={notifications.slice(
              (currentPage - 1) * DEFAULT_PAGE_SIZE,
              currentPage * DEFAULT_PAGE_SIZE
            )}
            onPageChange={setCurrentPage}
            pageSize={DEFAULT_PAGE_SIZE}
            totalCount={notifications.length}
            totalPages={Math.max(1, Math.ceil(notifications.length / DEFAULT_PAGE_SIZE))}
            renderItem={(notification) => (
              <Card className={PRIORITY_HOVER_STYLES[notification.priority]} interactive>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`grid size-8 shrink-0 place-items-center rounded-sm border ${PRIORITY_ICON_CHIP_STYLES[notification.priority]}`}
                      >
                        <AppIcon icon={NOTIFICATION_ICONS[notification.notification_type]} />
                      </span>
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
                        <Link href={notification.action_url}>
                          <AppIcon className="mr-2" icon={ExternalLink} />
                          {t("notifications.page.open")}
                        </Link>
                      </Button>
                    ) : null}
                    {notification.status !== "read" ? (
                      <Button
                        onClick={() => void updateStatus(notification, "read")}
                        size="sm"
                        type="button"
                        variant="ghost"
                      >
                        <AppIcon className="mr-2" icon={Check} />
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
                        <AppIcon className="mr-2" icon={Archive} />
                        {t("notifications.page.archive")}
                      </Button>
                    ) : null}
                  </div>
                </div>
              </Card>
            )}
          />
        )}
      </section>

      <section>
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <AppIcon icon={Settings2} size="md" />
          {t("notifications.preferences.title")}
        </h2>
        <Card className="p-4">
          {preferencesError ? (
            <div className="flex items-center justify-between gap-3 rounded-sm border border-danger/35 bg-danger/10 p-3">
              <p className="flex items-center gap-2 text-sm text-danger" role="alert">
                <AppIcon icon={TriangleAlert} />
                {t("notifications.preferences.loadError")}
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
                  {t("notifications.preferences.saveError")}
                </p>
              ) : null}
              <div className="grid gap-3 sm:grid-cols-2">
                {PREFERENCE_FIELDS.map(({ key, labelKey }) => (
                  <label
                    className="flex items-center justify-between gap-3 rounded-sm border bg-surface px-3 py-2.5 transition-colors hover:border-accent/40 hover:bg-elevated"
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
            <p className="text-sm text-muted-foreground">{t("notifications.preferences.loading")}</p>
          )}
        </Card>
      </section>
    </div>
  );
}
