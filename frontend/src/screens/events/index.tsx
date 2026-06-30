"use client";

import { CalendarPlus, Search, ShieldCheck, Tickets } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  EventCard,
  EventMapPreview,
  type EventDetails,
  type EventFilters
} from "@/entities/event";
import { useAuth } from "@/features/auth";
import { getEventsRequest } from "@/features/events";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { LoadingNotice } from "@/shared/ui/loading-notice";
import { DEFAULT_PAGE_SIZE, PaginatedGrid } from "@/shared/ui/pagination";

const emptyFilters: EventFilters = {
  search: "",
  category: "",
  country: "",
  city: "",
  price_type: "",
  format: ""
};

export function EventsScreen() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [filters, setFilters] = useState<EventFilters>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<EventFilters>(emptyFilters);
  const [events, setEvents] = useState<EventDetails[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const loadEvents = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getEventsRequest(appliedFilters, {
        page: currentPage,
        page_size: DEFAULT_PAGE_SIZE
      });
      setEvents(response.results);
      setTotalCount(response.count);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [appliedFilters, currentPage]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCurrentPage(1);
    setAppliedFilters(filters);
  }

  function clearFilters() {
    setFilters(emptyFilters);
    setAppliedFilters(emptyFilters);
    setCurrentPage(1);
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / DEFAULT_PAGE_SIZE));

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("events.list.eyebrow")}
        </p>
        <div className="mt-3 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <h1 className="max-w-3xl text-3xl font-semibold sm:text-5xl">
              {t("events.list.title")}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
              {t("events.list.description")}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild variant="secondary">
              <Link href="/events/my">
                <Tickets aria-hidden className="mr-2 size-4" />
                {t("events.actions.myEvents")}
              </Link>
            </Button>
            {user?.role === "organizer" || user?.role === "admin" ? (
              <>
                <Button asChild variant="secondary">
                  <Link href="/organizer/events">
                    {t("events.actions.manageOrganizer")}
                  </Link>
                </Button>
                <Button asChild>
                  <Link href="/organizer/events/new">
                    <CalendarPlus aria-hidden className="mr-2 size-4" />
                    {t("organizer.actions.create")}
                  </Link>
                </Button>
              </>
            ) : null}
            {user?.role === "admin" ? (
              <Button asChild variant="ghost">
                <Link href="/admin/events/moderation">
                  <ShieldCheck aria-hidden className="mr-2 size-4" />
                  {t("events.actions.moderationQueue")}
                </Link>
              </Button>
            ) : null}
          </div>
        </div>
      </section>

      <Card>
        <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" onSubmit={handleSubmit}>
          <label className="block">
            <span className="text-sm font-semibold">{t("events.filters.search")}</span>
            <div className="relative">
              <Search
                aria-hidden
                className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              />
              <input
                className={`${fieldClassName} pl-10`}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, search: event.target.value }))
                }
                placeholder={t("events.filters.searchPlaceholder")}
                value={filters.search}
              />
            </div>
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t("events.filters.category")}</span>
            <input
              className={fieldClassName}
              onChange={(event) =>
                setFilters((current) => ({ ...current, category: event.target.value }))
              }
              placeholder={t("events.filters.categoryPlaceholder")}
              value={filters.category}
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t("events.filters.country")}</span>
            <input
              className={fieldClassName}
              onChange={(event) =>
                setFilters((current) => ({ ...current, country: event.target.value }))
              }
              placeholder={t("events.filters.countryPlaceholder")}
              value={filters.country}
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t("events.filters.city")}</span>
            <input
              className={fieldClassName}
              onChange={(event) =>
                setFilters((current) => ({ ...current, city: event.target.value }))
              }
              placeholder={t("events.filters.cityPlaceholder")}
              value={filters.city}
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t("events.filters.price")}</span>
            <select
              className={fieldClassName}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  price_type: event.target.value
                }))
              }
              value={filters.price_type}
            >
              <option value="">{t("events.filters.all")}</option>
              <option value="free">{t("events.filters.free")}</option>
              <option value="paid">{t("events.filters.paid")}</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t("events.filters.format")}</span>
            <select
              className={fieldClassName}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  format: event.target.value
                }))
              }
              value={filters.format}
            >
              <option value="">{t("events.filters.all")}</option>
              <option value="online">{t("events.filters.online")}</option>
              <option value="offline">{t("events.filters.offline")}</option>
              <option value="hybrid">{t("events.filters.hybrid")}</option>
            </select>
          </label>
          <div className="flex flex-wrap gap-3 md:col-span-2 xl:col-span-3">
            <Button type="submit">{t("events.actions.applyFilters")}</Button>
            <Button onClick={clearFilters} type="button" variant="ghost">
              {t("events.actions.clearFilters")}
            </Button>
          </div>
        </form>
      </Card>

      {!isLoading && !hasError && events.length ? (
        <EventMapPreview events={events} />
      ) : null}

      {isLoading ? (
        <LoadingNotice message={t("events.states.loading")} />
      ) : hasError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("events.states.loadError")}
          </p>
          <Button className="mt-4" onClick={() => void loadEvents()} type="button">
            {t("events.actions.retry")}
          </Button>
        </Card>
      ) : events.length === 0 ? (
        <Card>
          <h2 className="text-xl font-semibold">{t("events.states.emptyTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("events.states.emptyDescription")}
          </p>
        </Card>
      ) : (
        <PaginatedGrid
          currentPage={currentPage}
          getItemKey={(event) => event.id}
          items={events}
          onPageChange={setCurrentPage}
          renderItem={(event) => <EventCard event={event} />}
          totalCount={totalCount}
          totalPages={totalPages}
        />
      )}

      <p className="text-xs leading-5 text-muted-foreground">{t("events.disclaimer")}</p>
    </div>
  );
}
