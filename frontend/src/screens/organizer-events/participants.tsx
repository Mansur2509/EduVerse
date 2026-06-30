"use client";

import { Download } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import type {
  OrganizerEvent,
  OrganizerParticipant,
  PaginatedResponse
} from "@/entities/event";
import {
  getOrganizerEventParticipantsRequest,
  getOrganizerEventRequest
} from "@/features/organizer-events";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { DEFAULT_PAGE_SIZE, PaginationControls } from "@/shared/ui/pagination";

export function OrganizerParticipantsScreen({ slug }: { slug: string }) {
  const { locale, t } = useI18n();
  const [event, setEvent] = useState<OrganizerEvent | null>(null);
  const [participants, setParticipants] = useState<OrganizerParticipant[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const [eventResponse, participantResponse] = await Promise.all([
        getOrganizerEventRequest(slug),
        getOrganizerEventParticipantsRequest(slug, {
          page: currentPage,
          page_size: DEFAULT_PAGE_SIZE
        })
      ]);
      setEvent(eventResponse);
      setParticipants(
        (participantResponse as PaginatedResponse<OrganizerParticipant>).results
      );
      setTotalCount((participantResponse as PaginatedResponse<OrganizerParticipant>).count);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [slug, currentPage]);

  useEffect(() => {
    void load();
  }, [load]);

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">
          {t("organizer.participants.loading")}
        </p>
      </Card>
    );
  }

  if (hasError || !event) {
    return (
      <Card className="border-danger/35 bg-danger/10">
        <p className="text-sm text-danger" role="alert">
          {t("organizer.participants.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void load()} type="button">
          {t("events.actions.retry")}
        </Button>
      </Card>
    );
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / DEFAULT_PAGE_SIZE));
  const pageStart = totalCount ? (currentPage - 1) * DEFAULT_PAGE_SIZE + 1 : 0;
  const pageEnd = Math.min(pageStart + Math.max(participants.length, 1) - 1, totalCount);

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("organizer.participants.eyebrow")}
        </p>
        <div className="mt-3 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <h1 className="text-3xl font-semibold sm:text-5xl">{event.title}</h1>
            <p className="mt-4 text-muted-foreground">
              {t("organizer.participants.count", {
                count: totalCount
              })}
            </p>
          </div>
          <Button disabled type="button" variant="secondary">
            <Download aria-hidden className="mr-2 size-4" />
            {t("organizer.actions.exportPlaceholder")}
          </Button>
        </div>
      </section>

      <Card>
        <p className="text-sm leading-6 text-muted-foreground">
          {t("organizer.participants.privacyNotice")}
        </p>
      </Card>

      {participants.length === 0 ? (
        <Card>
          <h2 className="text-xl font-semibold">
            {t("organizer.participants.emptyTitle")}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("organizer.participants.emptyDescription")}
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
          <div className="overflow-hidden rounded-sm border bg-card shadow-card">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[48rem] text-left text-sm">
              <thead className="border-b bg-elevated/65 text-xs uppercase tracking-[0.1em] text-muted-foreground">
                <tr>
                  <th className="px-5 py-4">{t("organizer.participants.name")}</th>
                  <th className="px-5 py-4">{t("auth.email")}</th>
                  <th className="px-5 py-4">{t("profile.telegram")}</th>
                  <th className="px-5 py-4">{t("organizer.participants.status")}</th>
                  <th className="px-5 py-4">{t("organizer.participants.registeredAt")}</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {participants.map((participant) => (
                  <tr key={participant.id}>
                    <td className="px-5 py-4 font-semibold">
                      {participant.full_name || t("events.value.notSet")}
                    </td>
                    <td className="px-5 py-4 text-muted-foreground">
                      {participant.email}
                    </td>
                    <td className="px-5 py-4 text-muted-foreground">
                      {participant.telegram_username || t("events.value.notSet")}
                    </td>
                    <td className="px-5 py-4">
                      {t(
                        `events.registration.status.${participant.status}` as TranslationKey
                      )}
                    </td>
                    <td className="px-5 py-4 text-muted-foreground">
                      {formatDateTime(participant.created_at, locale)}
                    </td>
                  </tr>
                ))}
              </tbody>
              </table>
            </div>
          </div>
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

      <Button asChild variant="ghost">
        <Link href="/organizer/events">{t("organizer.actions.backToList")}</Link>
      </Button>
    </div>
  );
}
