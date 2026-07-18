"use client";

import { Globe2, MapPin } from "lucide-react";
import Link from "next/link";

import type { EventDetails } from "@/entities/event";
import { useI18n } from "@/shared/i18n";
import { Card } from "@/shared/ui/card";

function mapPosition(value: string | null, minimum: number, maximum: number) {
  if (value === null) return null;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return Math.max(5, Math.min(95, ((numeric - minimum) / (maximum - minimum)) * 90 + 5));
}

export function EventMapPreview({ events }: { events: EventDetails[] }) {
  const { t } = useI18n();
  const mappedEvents = events
    .map((event) => ({
      event,
      left: mapPosition(event.location?.longitude ?? null, -180, 180),
      top: mapPosition(event.location?.latitude ?? null, 90, -90)
    }))
    .filter(
      (item): item is typeof item & { left: number; top: number } =>
        item.left !== null && item.top !== null
    );
  const onlineEvents = events.filter((event) => event.is_online);

  return (
    <Card animate="fade-up" className="overflow-hidden p-0">
      <div className="grid lg:grid-cols-[minmax(0,1fr)_19rem]">
        <div className="relative min-h-[16rem] overflow-hidden bg-navy sm:min-h-[22rem]">
          <div
            aria-hidden
            className="absolute inset-0 bg-[radial-gradient(60%_60%_at_30%_20%,rgba(164,16,52,.18),transparent),radial-gradient(50%_50%_at_85%_85%,rgba(255,255,255,.08),transparent)]"
          />
          <div className="absolute inset-0 opacity-35 [background-image:linear-gradient(rgba(255,255,255,.12)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.12)_1px,transparent_1px)] [background-size:3rem_3rem]" />
          <div className="absolute inset-x-[8%] top-[18%] h-[52%] border border-white/15 bg-white/[0.025] shadow-[0_0_40px_rgba(0,0,0,0.25)_inset] [clip-path:polygon(2%_27%,15%_16%,28%_24%,38%_11%,52%_19%,64%_7%,78%_20%,96%_14%,91%_43%,98%_58%,83%_62%,73%_85%,57%_73%,44%_91%,30%_74%,17%_80%,8%_56%)]" />
          <div className="absolute left-5 top-5 z-10 max-w-md">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">
              {t("events.map.title")}
            </p>
            <p className="mt-2 text-sm leading-6 text-white/70">
              {t("events.map.description")}
            </p>
          </div>
          {mappedEvents.slice(0, 18).map(({ event, left, top }) => (
            <Link
              aria-label={event.title}
              className="group absolute z-10 grid size-11 -translate-x-1/2 -translate-y-1/2 place-items-center"
              href={`/events/${event.slug}`}
              key={event.id}
              style={{ left: `${left}%`, top: `${top}%` }}
            >
              <span className="grid size-7 place-items-center rounded-full border border-white/25 bg-primary-button text-primary-foreground shadow-lg transition-transform duration-normal ease-academic group-hover:scale-125">
                <MapPin aria-hidden className="size-4" />
              </span>
              <span className="pointer-events-none absolute left-1/2 top-9 w-48 -translate-x-1/2 translate-y-1 border border-white/15 bg-navy px-3 py-2 text-xs font-semibold text-white opacity-0 shadow-lg transition-[opacity,transform] duration-fast ease-academic group-hover:translate-y-0 group-hover:opacity-100">
                {event.title}
              </span>
            </Link>
          ))}
          {!mappedEvents.length ? (
            <div className="absolute inset-x-5 bottom-5 border border-white/15 bg-white/5 p-4 text-sm text-white/65">
              {t("events.map.noCoordinates")}
            </div>
          ) : null}
        </div>
        <div className="border-t bg-surface p-5 lg:border-l lg:border-t-0">
          <div className="flex items-center gap-2">
            <Globe2 aria-hidden className="size-4 text-info" />
            <h2 className="text-lg font-semibold">{t("events.filters.online")}</h2>
          </div>
          <div className="mt-4 space-y-3">
            {(onlineEvents.length ? onlineEvents : events).slice(0, 4).map((event) => (
              <Link
                className="block border-l-2 border-primary py-0.5 pl-3 transition-colors duration-fast ease-academic hover:border-accent"
                href={`/events/${event.slug}`}
                key={event.id}
              >
                <p className="text-sm font-semibold">{event.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {event.is_online
                    ? t("events.map.online")
                    : [event.location?.city, event.location?.country]
                        .filter(Boolean)
                        .join(", ") || t("events.value.notSet")}
                </p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}
