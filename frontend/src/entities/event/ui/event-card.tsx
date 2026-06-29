"use client";

import { CalendarDays, MapPin, Monitor, Users } from "lucide-react";
import Link from "next/link";

import type { EventDetails } from "@/entities/event";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Card } from "@/shared/ui/card";

function priceLabelKey(event: EventDetails): TranslationKey {
  return `events.price.${event.price_type}` as TranslationKey;
}

function isDemoEvent(event: EventDetails) {
  const marker = [
    event.title,
    event.short_description,
    event.organizer_name,
    event.eligibility,
    event.source?.source_title
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return marker.includes("demo") || marker.includes("fictional");
}

export function EventCard({ event }: { event: EventDetails }) {
  const { locale, t } = useI18n();
  const registrationKey = event.registration_status
    ? (`events.registration.status.${event.registration_status}` as TranslationKey)
    : null;

  return (
    <Card className="flex h-full flex-col transition hover:border-primary/45">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{event.category.name}</Badge>
        <span className="rounded-sm border bg-surface px-2.5 py-1 text-xs font-semibold text-muted-foreground">
          {t(`events.filters.${event.format}` as TranslationKey)}
        </span>
        <span className="rounded-sm border bg-elevated/55 px-2.5 py-1 text-xs text-muted-foreground">
          {t(priceLabelKey(event))}
        </span>
        {isDemoEvent(event) ? (
          <span className="rounded-sm border border-warning/35 bg-warning/10 px-2.5 py-1 text-xs font-semibold text-warning">
            {t("events.demoBadge")}
          </span>
        ) : null}
        {registrationKey ? (
          <span className="rounded-sm border border-success/30 bg-success/10 px-2.5 py-1 text-xs font-semibold text-success">
            {t(registrationKey)}
          </span>
        ) : null}
      </div>

      <h2 className="mt-4 text-2xl font-semibold">
        <Link className="hover:text-primary-hover" href={`/events/${event.slug}`}>
          {event.title}
        </Link>
      </h2>
      <p className="mt-3 flex-1 text-sm leading-6 text-muted-foreground">
        {event.short_description || event.description}
      </p>

      <dl className="mt-5 space-y-3 text-sm">
        <div className="flex items-start gap-3">
          <CalendarDays aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
          <div>
            <dt className="sr-only">{t("events.fields.start")}</dt>
            <dd>{formatDateTime(event.start_at, locale)}</dd>
          </div>
        </div>
        <div className="flex items-start gap-3">
          {event.is_online ? (
            <Monitor aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
          ) : (
            <MapPin aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
          )}
          <div>
            <dt className="sr-only">{t("events.fields.location")}</dt>
            <dd>
              {event.is_online
                ? t("events.location.online")
                : [event.location.city, event.location.country].filter(Boolean).join(", ")}
            </dd>
          </div>
        </div>
        {event.registration_deadline ? (
          <div className="flex items-start gap-3">
            <CalendarDays
              aria-hidden
              className="mt-0.5 size-4 shrink-0 text-warning"
            />
            <div>
              <dt className="text-xs text-muted-foreground">
                {t("events.fields.deadline")}
              </dt>
              <dd>{formatDateTime(event.registration_deadline, locale)}</dd>
            </div>
          </div>
        ) : null}
        <div className="flex items-start gap-3">
          <Users aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
          <div>
            <dt className="text-xs text-muted-foreground">
              {t("events.fields.organizer")}
            </dt>
            <dd>{event.organizer_name}</dd>
          </div>
        </div>
        {event.spots_left !== null ? (
          <div className="flex items-start gap-3">
            <Users aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
            <div>
              <dt className="sr-only">{t("events.fields.capacity")}</dt>
              <dd>{t("events.spotsLeft", { count: event.spots_left })}</dd>
            </div>
          </div>
        ) : null}
      </dl>

      <Link
        className="mt-6 inline-flex min-h-11 items-center justify-center rounded-sm border bg-surface px-4 text-sm font-semibold transition hover:bg-elevated"
        href={`/events/${event.slug}`}
      >
        {t("events.actions.viewDetails")}
      </Link>
    </Card>
  );
}
