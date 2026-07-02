"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import type { EventRegistration, EventRegistrationStatus } from "@/entities/event";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const MAX_CHIPS_PER_DAY = 3;

const STATUS_ACCENTS: Record<EventRegistrationStatus, string> = {
  registered: "border-l-2 border-primary",
  waitlisted: "border-l-2 border-warning",
  attended: "border-l-2 border-success",
  cancelled: "border-l-2 border-border opacity-60"
};

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function addMonths(date: Date, amount: number) {
  return new Date(date.getFullYear(), date.getMonth() + amount, 1);
}

function toDateKey(date: Date) {
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function MyEventsCalendar({ registrations }: { registrations: EventRegistration[] }) {
  const { t, locale } = useI18n();
  const [monthCursor, setMonthCursor] = useState(() => startOfMonth(new Date()));

  const eventsByDay = useMemo(() => {
    const map = new Map<string, EventRegistration[]>();
    for (const registration of registrations) {
      const key = toDateKey(new Date(registration.event.start_at));
      const bucket = map.get(key) ?? [];
      bucket.push(registration);
      map.set(key, bucket);
    }
    for (const bucket of map.values()) {
      bucket.sort((a, b) => a.event.start_at.localeCompare(b.event.start_at));
    }
    return map;
  }, [registrations]);

  const weeks = useMemo(() => {
    const mondayOffset = (monthCursor.getDay() + 6) % 7;
    const gridStart = new Date(monthCursor);
    gridStart.setDate(monthCursor.getDate() - mondayOffset);
    const rows: Date[][] = [];
    for (let row = 0; row < 6; row += 1) {
      const week: Date[] = [];
      for (let column = 0; column < 7; column += 1) {
        const cell = new Date(gridStart);
        cell.setDate(gridStart.getDate() + row * 7 + column);
        week.push(cell);
      }
      if (row >= 4 && week.every((day) => day.getMonth() !== monthCursor.getMonth())) {
        break;
      }
      rows.push(week);
    }
    return rows;
  }, [monthCursor]);

  const monthLabel = new Intl.DateTimeFormat(locale, {
    month: "long",
    year: "numeric"
  }).format(monthCursor);
  const weekdayFormatter = new Intl.DateTimeFormat(locale, { weekday: "short" });
  const timeFormatter = new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit"
  });
  const dayFormatter = new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "long"
  });
  const todayKey = toDateKey(new Date());

  const monthDaysWithEvents = useMemo(
    () =>
      weeks
        .flat()
        .filter(
          (day) =>
            day.getMonth() === monthCursor.getMonth() && eventsByDay.has(toDateKey(day))
        ),
    [weeks, monthCursor, eventsByDay]
  );

  const statusLabel = (status: EventRegistrationStatus) =>
    t(`events.registration.status.${status}` as TranslationKey);

  const renderChip = (registration: EventRegistration, options?: { showStatus?: boolean }) => (
    <Link
      className={`block bg-surface px-2 py-1 text-xs leading-4 hover:bg-muted ${STATUS_ACCENTS[registration.status]}`}
      href={`/events/${registration.event.slug}`}
      key={registration.id}
      title={`${registration.event.title} — ${statusLabel(registration.status)}`}
    >
      <span className="font-semibold text-foreground">
        {timeFormatter.format(new Date(registration.event.start_at))}
      </span>{" "}
      <span className="text-muted-foreground">{registration.event.title}</span>
      {options?.showStatus ? (
        <span className="ml-1 text-muted-foreground">· {statusLabel(registration.status)}</span>
      ) : null}
    </Link>
  );

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold capitalize">{monthLabel}</h2>
        <div className="flex items-center gap-2">
          <Button
            aria-label={t("events.calendar.previousMonth")}
            onClick={() => setMonthCursor((current) => addMonths(current, -1))}
            type="button"
            variant="ghost"
          >
            <ChevronLeft aria-hidden className="size-4" />
          </Button>
          <Button
            onClick={() => setMonthCursor(startOfMonth(new Date()))}
            type="button"
            variant="ghost"
          >
            {t("events.calendar.today")}
          </Button>
          <Button
            aria-label={t("events.calendar.nextMonth")}
            onClick={() => setMonthCursor((current) => addMonths(current, 1))}
            type="button"
            variant="ghost"
          >
            <ChevronRight aria-hidden className="size-4" />
          </Button>
        </div>
      </div>

      {/* Month grid for sm+ viewports. */}
      <div aria-label={t("events.calendar.gridLabel")} className="mt-5 hidden sm:block" role="grid">
        <div className="grid grid-cols-7 border-b text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
          {weeks[0]?.map((day) => (
            <div className="px-2 py-2" key={toDateKey(day)} role="columnheader">
              {weekdayFormatter.format(day)}
            </div>
          ))}
        </div>
        {weeks.map((week) => (
          <div className="grid grid-cols-7" key={toDateKey(week[0])} role="row">
            {week.map((day) => {
              const key = toDateKey(day);
              const inMonth = day.getMonth() === monthCursor.getMonth();
              const dayEvents = eventsByDay.get(key) ?? [];
              const hiddenCount = dayEvents.length - MAX_CHIPS_PER_DAY;
              return (
                <div
                  className={`min-h-24 border-b border-r p-1.5 first:border-l ${
                    inMonth ? "bg-card" : "bg-muted/40"
                  }`}
                  key={key}
                  role="gridcell"
                >
                  <p
                    className={`text-xs font-semibold ${
                      key === todayKey
                        ? "inline-block bg-primary px-1.5 py-0.5 text-primary-foreground"
                        : inMonth
                          ? "text-foreground"
                          : "text-muted-foreground"
                    }`}
                  >
                    {day.getDate()}
                  </p>
                  {inMonth && dayEvents.length > 0 ? (
                    <div className="mt-1 space-y-1">
                      {dayEvents.slice(0, MAX_CHIPS_PER_DAY).map((registration) =>
                        renderChip(registration)
                      )}
                      {hiddenCount > 0 ? (
                        <p className="px-2 text-xs text-muted-foreground">
                          {t("events.calendar.more", { count: hiddenCount })}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Compact agenda for narrow viewports where a 7-column grid cannot fit. */}
      <div className="mt-5 space-y-4 sm:hidden">
        {monthDaysWithEvents.map((day) => (
          <div key={toDateKey(day)}>
            <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
              {dayFormatter.format(day)}
            </p>
            <div className="mt-1.5 space-y-1">
              {(eventsByDay.get(toDateKey(day)) ?? []).map((registration) =>
                renderChip(registration, { showStatus: true })
              )}
            </div>
          </div>
        ))}
      </div>

      {monthDaysWithEvents.length === 0 ? (
        <p className="mt-5 text-sm text-muted-foreground">
          {t("events.calendar.emptyMonth")}
        </p>
      ) : null}
    </Card>
  );
}
