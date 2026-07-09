"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EventCard, type EventRegistration } from "@/entities/event";
import { getMyEventRegistrationsRequest } from "@/features/events";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { DEFAULT_PAGE_SIZE, PaginatedGrid } from "@/shared/ui/pagination";
import { SkeletonCards } from "@/shared/ui/skeleton";

import { MyEventsCalendar } from "./my-events-calendar";

type ViewTab = "list" | "calendar";

const CALENDAR_PAGE_SIZE = 200;

export function MyEventsScreen() {
  const { t } = useI18n();
  const [view, setView] = useState<ViewTab>("list");
  const [registrations, setRegistrations] = useState<EventRegistration[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const loadRegistrations = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getMyEventRegistrationsRequest(
        view === "calendar"
          ? { page: 1, page_size: CALENDAR_PAGE_SIZE }
          : { page: currentPage, page_size: DEFAULT_PAGE_SIZE }
      );
      setRegistrations(response.results);
      setTotalCount(response.count);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, view]);

  useEffect(() => {
    void loadRegistrations();
  }, [loadRegistrations]);

  const totalPages = Math.max(1, Math.ceil(totalCount / DEFAULT_PAGE_SIZE));

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("events.my.eyebrow")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold sm:text-5xl">{t("events.my.title")}</h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
          {t("events.my.description")}
        </p>
        <div className="mt-5 flex gap-2" role="tablist">
          {(["list", "calendar"] as const).map((tab) => (
            <Button
              aria-selected={view === tab}
              key={tab}
              onClick={() => setView(tab)}
              role="tab"
              type="button"
              variant={view === tab ? "primary" : "ghost"}
            >
              {t(tab === "list" ? "events.tabs.list" : "events.tabs.calendar")}
            </Button>
          ))}
        </div>
      </section>

      {isLoading && registrations.length === 0 ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          <SkeletonCards count={6} />
        </div>
      ) : hasError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("events.states.myError")}
          </p>
          <Button className="mt-4" onClick={() => void loadRegistrations()} type="button">
            {t("events.actions.retry")}
          </Button>
        </Card>
      ) : registrations.length === 0 ? (
        <Card>
          <h2 className="text-xl font-semibold">{t("events.my.emptyTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("events.my.emptyDescription")}
          </p>
          <Button asChild className="mt-5">
            <Link href="/events">{t("events.actions.exploreEvents")}</Link>
          </Button>
        </Card>
      ) : view === "calendar" ? (
        <MyEventsCalendar registrations={registrations} />
      ) : (
        <PaginatedGrid
          currentPage={currentPage}
          getItemKey={(registration) => registration.id}
          items={registrations}
          onPageChange={setCurrentPage}
          renderItem={(registration) => (
            <div className="space-y-3">
              <EventCard event={registration.event} />
              {registration.ticket ? (
                <Card className="p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                    {t("events.ticket.title")}
                  </p>
                  <p className="mt-2 break-all font-mono text-xs">
                    {registration.ticket.code}
                  </p>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    {t("events.ticket.doNotShare")}
                  </p>
                </Card>
              ) : null}
            </div>
          )}
          totalCount={totalCount}
          totalPages={totalPages}
        />
      )}
    </div>
  );
}
