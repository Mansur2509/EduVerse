"use client";

import { Archive, ExternalLink, History, ShieldCheck, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  type EventModerationLog,
  type OrganizerEvent,
  type PaginatedResponse
} from "@/entities/event";
import {
  approveEventRequest,
  archiveModeratedEventRequest,
  getEventModerationLogsRequest,
  getPendingEventsRequest,
  rejectEventRequest
} from "@/features/organizer-events";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { DEFAULT_PAGE_SIZE, PaginationControls } from "@/shared/ui/pagination";

export function EventModerationScreen() {
  const { locale, t } = useI18n();
  const [events, setEvents] = useState<OrganizerEvent[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [logs, setLogs] = useState<Record<string, EventModerationLog[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [actionSlug, setActionSlug] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadEvents = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response: PaginatedResponse<OrganizerEvent> =
        await getPendingEventsRequest({ page: currentPage, page_size: DEFAULT_PAGE_SIZE });
      setEvents(response.results);
      setTotalCount(response.count);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  async function runAction(
    event: OrganizerEvent,
    action: "approve" | "reject" | "archive"
  ) {
    const reason = reasons[event.slug]?.trim() ?? "";
    if (action === "reject" && !reason) {
      setActionError(event.slug);
      return;
    }
    const confirmationKey =
      action === "approve"
        ? "moderation.confirm.approve"
        : action === "reject"
          ? "moderation.confirm.reject"
          : "moderation.confirm.archive";
    if (!window.confirm(t(confirmationKey as TranslationKey))) {
      return;
    }

    setActionSlug(event.slug);
    setActionError(null);
    try {
      if (action === "approve") {
        await approveEventRequest(event.slug);
      } else if (action === "reject") {
        await rejectEventRequest(event.slug, reason);
      } else {
        await archiveModeratedEventRequest(event.slug);
      }
      await loadEvents();
    } catch {
      setActionError(event.slug);
    } finally {
      setActionSlug(null);
    }
  }

  async function toggleLogs(event: OrganizerEvent) {
    if (logs[event.slug]) {
      setLogs((current) => {
        const next = { ...current };
        delete next[event.slug];
        return next;
      });
      return;
    }
    setActionSlug(event.slug);
    try {
      const response = await getEventModerationLogsRequest(event.slug);
      setLogs((current) => ({ ...current, [event.slug]: response }));
    } catch {
      setActionError(event.slug);
    } finally {
      setActionSlug(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / DEFAULT_PAGE_SIZE));
  const pageStart = totalCount ? (currentPage - 1) * DEFAULT_PAGE_SIZE + 1 : 0;
  const pageEnd = Math.min(pageStart + Math.max(events.length, 1) - 1, totalCount);

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("moderation.eyebrow")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold sm:text-5xl">
          {t("moderation.title")}
        </h1>
        <p className="mt-4 max-w-3xl leading-7 text-muted-foreground">
          {t("moderation.description")}
        </p>
      </section>

      {isLoading ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("moderation.loading")}</p>
        </Card>
      ) : hasError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("moderation.loadError")}
          </p>
          <Button className="mt-4" onClick={() => void loadEvents()} type="button">
            {t("events.actions.retry")}
          </Button>
        </Card>
      ) : events.length === 0 ? (
        <Card>
          <h2 className="text-xl font-semibold">{t("moderation.emptyTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("moderation.emptyDescription")}
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
          <section aria-label={t("moderation.results")} className="space-y-5">
            {events.map((event) => (
              <Card key={event.id}>
              <div className="grid gap-6 xl:grid-cols-[1fr_22rem]">
                <div>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>{event.category.name}</span>
                    <span aria-hidden>·</span>
                    <span>{formatDateTime(event.updated_at, locale)}</span>
                  </div>
                  <h2 className="mt-3 text-2xl font-semibold">{event.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {event.short_description}
                  </p>
                  <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="text-xs text-muted-foreground">
                        {t("events.fields.organizer")}
                      </dt>
                      <dd className="mt-1 font-medium">
                        {event.organizer_name} · {event.organizer_email}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">
                        {t("events.fields.start")}
                      </dt>
                      <dd className="mt-1 font-medium">
                        {formatDateTime(event.start_at, locale)}
                      </dd>
                    </div>
                  </dl>
                  <a
                    className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-primary-hover hover:underline"
                    href={event.source.source_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {t("events.actions.officialSource")}
                    <ExternalLink aria-hidden className="size-4" />
                  </a>
                </div>

                <div className="space-y-4 rounded-sm border bg-elevated/45 p-4">
                  <label className="block">
                    <span className="text-sm font-semibold">
                      {t("moderation.rejectReason")}
                    </span>
                    <textarea
                      className={`${fieldClassName} min-h-24 py-3`}
                      onChange={(inputEvent) =>
                        setReasons((current) => ({
                          ...current,
                          [event.slug]: inputEvent.target.value
                        }))
                      }
                      placeholder={t("moderation.rejectReasonPlaceholder")}
                      value={reasons[event.slug] ?? ""}
                    />
                  </label>
                  {actionError === event.slug ? (
                    <p className="text-sm text-danger" role="alert">
                      {t("moderation.actionError")}
                    </p>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={actionSlug === event.slug}
                      onClick={() => void runAction(event, "approve")}
                      type="button"
                    >
                      <ShieldCheck aria-hidden className="mr-2 size-4" />
                      {t("moderation.approve")}
                    </Button>
                    <Button
                      className="text-danger"
                      disabled={actionSlug === event.slug}
                      onClick={() => void runAction(event, "reject")}
                      type="button"
                      variant="secondary"
                    >
                      <XCircle aria-hidden className="mr-2 size-4" />
                      {t("moderation.reject")}
                    </Button>
                    <Button
                      disabled={actionSlug === event.slug}
                      onClick={() => void runAction(event, "archive")}
                      type="button"
                      variant="ghost"
                    >
                      <Archive aria-hidden className="mr-2 size-4" />
                      {t("moderation.archive")}
                    </Button>
                    <Button
                      disabled={actionSlug === event.slug}
                      onClick={() => void toggleLogs(event)}
                      type="button"
                      variant="ghost"
                    >
                      <History aria-hidden className="mr-2 size-4" />
                      {t("moderation.logs")}
                    </Button>
                    <Button
                      disabled={actionSlug === event.slug || !(reasons[event.slug] ?? "").trim()}
                      onClick={() =>
                        setReasons((current) => ({ ...current, [event.slug]: "" }))
                      }
                      type="button"
                      variant="ghost"
                    >
                      {t("moderation.clearReason")}
                    </Button>
                  </div>
                </div>
              </div>

              {logs[event.slug] ? (
                <div className="mt-6 border-t pt-5">
                  <h3 className="font-semibold">{t("moderation.logTitle")}</h3>
                  {logs[event.slug].length === 0 ? (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {t("moderation.noLogs")}
                    </p>
                  ) : (
                    <ul className="mt-3 space-y-3">
                      {logs[event.slug].map((log) => (
                        <li className="rounded-lg border bg-surface p-3 text-sm" key={log.id}>
                          <p className="font-semibold">
                            {t(
                              `organizer.status.${log.previous_status}` as TranslationKey
                            )}{" "}
                            →{" "}
                            {t(`organizer.status.${log.new_status}` as TranslationKey)}
                          </p>
                          <p className="mt-1 text-muted-foreground">
                            {log.note || t("moderation.noNote")}
                          </p>
                          <p className="mt-2 text-xs text-muted-foreground">
                            {log.moderator_email} ·{" "}
                            {formatDateTime(log.created_at, locale)}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : null}
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
