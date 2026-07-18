"use client";

import {
  Archive,
  AlertTriangle,
  CalendarPlus,
  CheckCircle2,
  Clock,
  Layers,
  Send,
  UserCheck,
  Users,
  type LucideIcon
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  ModerationStatusBadge,
  type OrganizerEvent,
  type OrganizerEventAnalytics,
  type PaginatedResponse
} from "@/entities/event";
import {
  archiveOrganizerEventRequest,
  cancelOrganizerEventRequest,
  getOrganizerEventAnalyticsRequest,
  getOrganizerEventsRequest,
  submitOrganizerEventRequest
} from "@/features/organizer-events";
import { StatValue } from "@/entities/university";
import { useI18n } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";
import { formatDateTime } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { DEFAULT_PAGE_SIZE, PaginationControls } from "@/shared/ui/pagination";
import { Reveal } from "@/shared/ui/reveal";

// Icon-chip + top-accent classes for each status tile tone, matching the
// dashboard Core Tools treatment so authenticated surfaces share one visual
// language for "small colored metric card" (Stage 2 goal #1).
const STATUS_TILE_TONE_CLASSES: Record<
  "muted" | "warning" | "success" | "info" | "accent" | "danger",
  { chip: string; topBar: string }
> = {
  muted: { chip: "border-muted-foreground/25 bg-surface text-muted-foreground", topBar: "bg-muted-foreground/40" },
  warning: { chip: "border-warning/30 bg-warning/10 text-warning", topBar: "bg-warning" },
  success: { chip: "border-success/30 bg-success/10 text-success", topBar: "bg-success" },
  info: { chip: "border-info/30 bg-info/10 text-info", topBar: "bg-info" },
  accent: { chip: "border-accent/35 bg-accent/10 text-accent", topBar: "bg-accent" },
  danger: { chip: "border-danger/35 bg-danger/10 text-danger", topBar: "bg-danger" }
};

export function OrganizerEventsScreen() {
  const { locale, t } = useI18n();
  const [events, setEvents] = useState<OrganizerEvent[]>([]);
  const [analytics, setAnalytics] = useState<OrganizerEventAnalytics | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [actionSlug, setActionSlug] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchEvents = useCallback(async () => {
    const [response, analyticsResponse]: [
      PaginatedResponse<OrganizerEvent>,
      OrganizerEventAnalytics
    ] = await Promise.all([
      getOrganizerEventsRequest({ page: currentPage, page_size: DEFAULT_PAGE_SIZE }),
      getOrganizerEventAnalyticsRequest()
    ]);
    setEvents(response.results);
    setTotalCount(response.count);
    setAnalytics(analyticsResponse);
  }, [currentPage]);

  const loadEvents = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      await fetchEvents();
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [fetchEvents]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  const statusCounts = {
    pending:
      analytics?.pending_count ??
      events.filter((event) => event.status === "pending_review").length,
    published:
      analytics?.published_count ??
      events.filter((event) => event.status === "published").length,
    needsAction:
      analytics !== null
        ? analytics.draft_count + analytics.rejected_count
        : events.filter((event) => ["draft", "rejected"].includes(event.status)).length
  };
  const totalPages = Math.max(1, Math.ceil(totalCount / DEFAULT_PAGE_SIZE));
  const pageStart = totalCount ? (currentPage - 1) * DEFAULT_PAGE_SIZE + 1 : 0;
  const pageEnd = Math.min(pageStart + Math.max(events.length, 1) - 1, totalCount);

  async function runAction(
    event: OrganizerEvent,
    action: "submit" | "cancel" | "archive"
  ) {
    const confirmationKey =
      action === "submit"
        ? "organizer.confirm.submit"
        : action === "cancel"
          ? "organizer.confirm.cancel"
          : "organizer.confirm.archive";
    if (!window.confirm(t(confirmationKey))) {
      return;
    }

    setActionSlug(event.slug);
    setActionError(null);
    try {
      if (action === "submit") {
        await submitOrganizerEventRequest(event.slug);
      } else if (action === "cancel") {
        await cancelOrganizerEventRequest(event.slug);
      } else {
        await archiveOrganizerEventRequest(event.slug);
      }
      // Refresh in place -- the mutation already succeeded, so re-fetching
      // through loadEvents() (which flips isLoading) would blank the whole
      // analytics summary and event grid for a refresh the user didn't ask
      // to see a loader for.
      await fetchEvents();
    } catch {
      setActionError(event.slug);
    } finally {
      setActionSlug(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-eyebrow text-primary-hover">{t("organizer.list.eyebrow")}</p>
        <div className="mt-3 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <h1 className="text-display">{t("organizer.list.title")}</h1>
            <p className="mt-4 max-w-2xl leading-7 text-muted-foreground">
              {t("organizer.list.description")}
            </p>
          </div>
          <Button asChild>
            <Link href="/organizer/events/new">
              <CalendarPlus aria-hidden className="mr-2 size-4" />
              {t("organizer.actions.create")}
            </Link>
          </Button>
        </div>
      </section>

      {!isLoading && !hasError ? (
        <section aria-labelledby="organizer-status-summary">
          <div className="mb-3">
            <h2 className="text-2xl font-semibold" id="organizer-status-summary">
              {t("organizer.statusSummary.title")}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              {t("organizer.statusSummary.guide")}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {(
              [
                {
                  label: t("organizer.statusSummary.total"),
                  value: totalCount,
                  icon: Layers,
                  tone: "muted"
                },
                {
                  label: t("organizer.statusSummary.pending"),
                  value: statusCounts.pending,
                  icon: Clock,
                  tone: "warning"
                },
                {
                  label: t("organizer.statusSummary.published"),
                  value: statusCounts.published,
                  icon: CheckCircle2,
                  tone: "success"
                },
                {
                  label: t("organizer.statusSummary.registrations"),
                  value: analytics?.total_registrations ?? 0,
                  icon: Users,
                  tone: "info"
                },
                {
                  label: t("organizer.statusSummary.checkedIn"),
                  value: analytics?.checked_in_count ?? 0,
                  icon: UserCheck,
                  tone: "info"
                },
                {
                  label: t("organizer.statusSummary.attendanceRate"),
                  value:
                    analytics?.attendance_rate === null || analytics?.attendance_rate === undefined
                      ? t("events.value.notSet")
                      : analytics.attendance_rate,
                  suffix:
                    analytics?.attendance_rate === null || analytics?.attendance_rate === undefined
                      ? undefined
                      : "%",
                  icon: Users,
                  tone: "accent"
                },
                {
                  label: t("organizer.statusSummary.needsAction"),
                  value: statusCounts.needsAction,
                  icon: AlertTriangle,
                  tone: statusCounts.needsAction > 0 ? "danger" : "muted"
                }
              ] as Array<{
                label: string;
                value: string | number;
                suffix?: string;
                icon: LucideIcon;
                tone: keyof typeof STATUS_TILE_TONE_CLASSES;
              }>
            ).map(({ label, value, suffix, icon: TileIcon, tone }, index) => {
              const toneClasses = STATUS_TILE_TONE_CLASSES[tone];
              return (
                <Reveal delayMs={index * 30} key={label}>
                  <Card className="relative overflow-hidden p-4" interactive>
                    <span aria-hidden className={cn("absolute inset-x-0 top-0 h-1", toneClasses.topBar)} />
                    <div className="flex items-center gap-2.5">
                      <span
                        className={cn(
                          "grid size-8 shrink-0 place-items-center rounded-sm border",
                          toneClasses.chip
                        )}
                      >
                        <TileIcon aria-hidden className="size-4" strokeWidth={1.75} />
                      </span>
                      <p className="text-eyebrow text-muted-foreground">{label}</p>
                    </div>
                    <p className="text-feature-heading mt-3 text-accent">
                      <StatValue suffix={suffix} value={value} />
                    </p>
                  </Card>
                </Reveal>
              );
            })}
          </div>
        </section>
      ) : null}

      {!isLoading && !hasError && analytics && analytics.registrations_by_event.length > 0 ? (
        <Card className="p-5">
          <p className="text-eyebrow text-primary-hover">{t("organizer.analytics.title")}</p>
          <p className="mt-1.5 max-w-2xl text-sm leading-6 text-muted-foreground">
            {t("organizer.analytics.description")}
          </p>
          {analytics.capacity_fill_percentage !== null ? (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
                <span>{t("organizer.analytics.capacityFill")}</span>
                <span className="text-accent">{analytics.capacity_fill_percentage}%</span>
              </div>
              <div
                aria-valuemax={100}
                aria-valuemin={0}
                aria-valuenow={Math.round(analytics.capacity_fill_percentage)}
                className="mt-1.5 h-2 overflow-hidden rounded-full bg-elevated"
                role="progressbar"
              >
                <div
                  className="h-full rounded-full bg-accent transition-[width] duration-slow ease-academic"
                  style={{ width: `${Math.min(100, Math.max(0, analytics.capacity_fill_percentage))}%` }}
                />
              </div>
            </div>
          ) : null}
          <ul className="mt-4 divide-y divide-border">
            {analytics.registrations_by_event.slice(0, 5).map((row) => (
              <li className="flex items-center justify-between gap-3 py-2.5 text-sm" key={row.slug}>
                <Link className="truncate font-semibold hover:text-primary-hover" href={`/organizer/events/${row.slug}`}>
                  {row.title}
                </Link>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {t("organizer.analytics.checkedInOf", {
                    checkedIn: row.checked_in_count,
                    registered: row.registration_count
                  })}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {isLoading ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("organizer.states.loading")}</p>
        </Card>
      ) : hasError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("organizer.states.loadError")}
          </p>
          <Button className="mt-4" onClick={() => void loadEvents()} type="button">
            {t("events.actions.retry")}
          </Button>
        </Card>
      ) : events.length === 0 ? (
        <Card>
          <h2 className="text-xl font-semibold">{t("organizer.states.emptyTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("organizer.states.emptyDescription")}
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          <p className="text-sm font-semibold text-muted-foreground">
            {t("pagination.showingRange", {
              start: pageStart,
              end: pageEnd,
              total: totalCount
            })}
          </p>
          <section
            aria-label={t("organizer.list.results")}
            className="grid gap-5 xl:grid-cols-2"
          >
            {events.map((event) => (
              <Card className="relative flex flex-col overflow-hidden" interactive key={event.id}>
              <span
                aria-hidden
                className={cn(
                  "absolute inset-x-0 top-0 h-1",
                  STATUS_TILE_TONE_CLASSES[
                    event.status === "published"
                      ? "success"
                      : event.status === "pending_review"
                        ? "warning"
                        : event.status === "rejected" || event.status === "cancelled"
                          ? "danger"
                          : "muted"
                  ].topBar
                )}
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <ModerationStatusBadge status={event.status} />
                <span className="text-xs text-muted-foreground">
                  {formatDateTime(event.updated_at, locale)}
                </span>
              </div>
              <h2 className="mt-4 text-2xl font-semibold">{event.title}</h2>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">
                {event.short_description}
              </p>
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-muted-foreground">
                    {t("events.fields.start")}
                  </dt>
                  <dd className="mt-1 font-medium">
                    {formatDateTime(event.start_at, locale)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">
                    {t("events.fields.location")}
                  </dt>
                  <dd className="mt-1 font-medium">
                    {[event.location.city, event.location.country]
                      .filter(Boolean)
                      .join(", ")}
                  </dd>
                </div>
              </dl>
              {event.moderation_note ? (
                <p className="mt-5 rounded-lg border border-danger/25 bg-danger/10 p-3 text-sm text-danger">
                  {t("organizer.moderationNote", {
                    reason: event.moderation_note
                  })}
                </p>
              ) : null}
              {actionError === event.slug ? (
                <p className="mt-4 text-sm text-danger" role="alert">
                  {t("organizer.states.actionError")}
                </p>
              ) : null}
              <div className="mt-auto flex flex-wrap gap-2 pt-6">
                {event.can_edit ? (
                  <Button asChild variant="secondary">
                    <Link href={`/organizer/events/${event.slug}`}>
                      {t("organizer.actions.edit")}
                    </Link>
                  </Button>
                ) : null}
                {event.can_submit ? (
                  <Button
                    disabled={actionSlug === event.slug}
                    onClick={() => void runAction(event, "submit")}
                    type="button"
                  >
                    <Send aria-hidden className="mr-2 size-4" />
                    {t("organizer.actions.submit")}
                  </Button>
                ) : null}
                {event.can_view_participants ? (
                  <>
                    <Button asChild variant="secondary">
                      <Link href={`/organizer/events/${event.slug}/participants`}>
                        <Users aria-hidden className="mr-2 size-4" />
                        {t("organizer.actions.participants")}
                      </Link>
                    </Button>
                    <Button
                      className="text-danger"
                      disabled={actionSlug === event.slug}
                      onClick={() => void runAction(event, "cancel")}
                      type="button"
                      variant="ghost"
                    >
                      {t("organizer.actions.cancelEvent")}
                    </Button>
                  </>
                ) : null}
                {["draft", "pending_review", "rejected"].includes(event.status) ? (
                  <Button
                    disabled={actionSlug === event.slug}
                    onClick={() => void runAction(event, "archive")}
                    type="button"
                    variant="ghost"
                  >
                    <Archive aria-hidden className="mr-2 size-4" />
                    {t("organizer.actions.archive")}
                  </Button>
                ) : null}
              </div>
              </Card>
            ))}
          </section>
          {totalPages > 1 ? (
            <PaginationControls
              currentPage={currentPage}
              onNext={() => setCurrentPage((page) => page + 1)}
              onPageSelect={setCurrentPage}
              onPrevious={() => setCurrentPage((page) => page - 1)}
              totalPages={totalPages}
            />
          ) : null}
        </div>
      )}
    </div>
  );
}
