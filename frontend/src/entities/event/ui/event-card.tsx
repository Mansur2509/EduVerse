"use client";

import {
  CalendarDays,
  GraduationCap,
  MapPin,
  Mic,
  Monitor,
  PartyPopper,
  ShieldCheck,
  Trophy,
  Users,
  type LucideIcon
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import type { EventDetails } from "@/entities/event";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Card } from "@/shared/ui/card";

function priceLabelKey(event: EventDetails): TranslationKey {
  return `events.price.${event.price_type}` as TranslationKey;
}

// Category-keyed icon + gradient fallback for events without an
// organizer-provided cover image (cover_image_url is real, uploadable data --
// this is only the fallback when that field is empty, never a substitute for
// a real photo). Falls back to a generic calendar glyph for unlisted slugs.
const CATEGORY_VISUALS: Record<string, { icon: LucideIcon; classes: string }> = {
  workshop: { icon: GraduationCap, classes: "from-info to-info/60" },
  fair: { icon: PartyPopper, classes: "from-accent to-accent/60" },
  webinar: { icon: Mic, classes: "from-recommendation to-recommendation/60" },
  competition: { icon: Trophy, classes: "from-warning to-warning/60" },
  info_session: { icon: ShieldCheck, classes: "from-success to-success/60" }
};

function categoryVisual(slug: string) {
  return CATEGORY_VISUALS[slug] ?? { icon: CalendarDays, classes: "from-navy to-navy/70" };
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
  const [coverFailed, setCoverFailed] = useState(false);
  const showCover = Boolean(event.cover_image_url) && !coverFailed;
  const visual = categoryVisual(event.category.slug);

  return (
    <Card
      className="flex h-full flex-col overflow-hidden hover:border-event/45"
      interactive
    >
      <div className="-mx-4 -mt-4 mb-3 h-28 shrink-0 overflow-hidden">
        {showCover ? (
          <Image
            alt=""
            className="size-full object-cover transition-transform duration-slow ease-academic hover:scale-105"
            height={224}
            onError={() => setCoverFailed(true)}
            src={event.cover_image_url}
            unoptimized
            width={640}
          />
        ) : (
          <div
            className={`grid size-full place-items-center bg-gradient-to-br ${visual.classes}`}
          >
            <visual.icon aria-hidden className="size-8 text-navy-foreground/85" strokeWidth={1.5} />
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="event">{event.category.name}</Badge>
        <Badge className="normal-case tracking-normal" tone="muted">
          {t(`events.filters.${event.format}` as TranslationKey)}
        </Badge>
        <Badge className="normal-case tracking-normal" tone="muted">
          {t(priceLabelKey(event))}
        </Badge>
        {isDemoEvent(event) ? <Badge tone="warning">{t("events.demoBadge")}</Badge> : null}
        {registrationKey ? <Badge tone="success">{t(registrationKey)}</Badge> : null}
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
        <div className="flex items-center gap-3">
          <span className="grid size-7 shrink-0 place-items-center rounded-sm border border-event/30 bg-event/10 text-event">
            <CalendarDays aria-hidden className="size-3.5" strokeWidth={1.75} />
          </span>
          <div>
            <dt className="sr-only">{t("events.fields.start")}</dt>
            <dd>{formatDateTime(event.start_at, locale)}</dd>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="grid size-7 shrink-0 place-items-center rounded-sm border border-event/30 bg-event/10 text-event">
            {event.is_online ? (
              <Monitor aria-hidden className="size-3.5" strokeWidth={1.75} />
            ) : (
              <MapPin aria-hidden className="size-3.5" strokeWidth={1.75} />
            )}
          </span>
          <div>
            <dt className="sr-only">{t("events.fields.location")}</dt>
            <dd>
              {event.is_online
                ? t("events.location.online")
                : [event.location?.city, event.location?.country]
                    .filter(Boolean)
                    .join(", ") || t("events.value.notSet")}
            </dd>
          </div>
        </div>
        {event.registration_deadline ? (
          <div className="flex items-center gap-3">
            <span className="grid size-7 shrink-0 place-items-center rounded-sm border border-warning/30 bg-warning/10 text-warning">
              <CalendarDays aria-hidden className="size-3.5" strokeWidth={1.75} />
            </span>
            <div>
              <dt className="text-xs text-muted-foreground">
                {t("events.fields.deadline")}
              </dt>
              <dd>{formatDateTime(event.registration_deadline, locale)}</dd>
            </div>
          </div>
        ) : null}
        <div className="flex items-center gap-3">
          <span className="grid size-7 shrink-0 place-items-center rounded-sm border border-muted-foreground/25 bg-surface text-muted-foreground">
            <Users aria-hidden className="size-3.5" strokeWidth={1.75} />
          </span>
          <div>
            <dt className="text-xs text-muted-foreground">
              {t("events.fields.organizer")}
            </dt>
            <dd>{event.organizer_name}</dd>
          </div>
        </div>
        {event.spots_left !== null ? (
          <div className="flex items-center gap-3">
            <span className="grid size-7 shrink-0 place-items-center rounded-sm border border-muted-foreground/25 bg-surface text-muted-foreground">
              <Users aria-hidden className="size-3.5" strokeWidth={1.75} />
            </span>
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
