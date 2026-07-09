"use client";

import { CalendarClock } from "lucide-react";

import type { ProfileStrategy, StrategyEvent } from "@/entities/profile";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Card } from "@/shared/ui/card";

const URGENCY_TONE: Record<string, string> = {
  overdue: "border-danger/45 bg-danger/10 text-danger",
  critical: "border-danger/45 bg-danger/10 text-danger",
  urgent: "border-warning/45 bg-warning/10 text-warning",
  soon: "border-warning/35 bg-warning/10 text-warning",
  upcoming: "border-accent/35 bg-accent/10 text-accent",
  far: "border-muted-foreground/30 bg-surface text-muted-foreground",
  unknown: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

function upcomingEvents(strategy: ProfileStrategy, limit: number): StrategyEvent[] {
  return [
    ...strategy.overdue,
    ...strategy.next_7_days,
    ...strategy.next_30_days,
    ...strategy.next_90_days
  ].slice(0, limit);
}

export function StrategyPanel({
  strategy,
  isLoading = false,
  loadError = false,
  limit = 4
}: {
  strategy: ProfileStrategy | null;
  isLoading?: boolean;
  loadError?: boolean;
  limit?: number;
}) {
  const { locale, t } = useI18n();
  const events = strategy ? upcomingEvents(strategy, limit) : [];

  return (
    <Card className="p-4">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
        {t("profileStrategy.title")}
      </p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{t("profileStrategy.description")}</p>

      {loadError ? (
        <p className="mt-3 text-xs text-warning" role="alert">
          {t("profileStrategy.loadError")}
        </p>
      ) : isLoading || !strategy ? (
        <p className="mt-3 text-xs text-muted-foreground">{t("profileStrategy.loading")}</p>
      ) : !strategy.has_tracked_applications ? (
        <p className="mt-3 text-xs text-muted-foreground">{t("profileStrategy.noApplications")}</p>
      ) : (
        <>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-sm border bg-surface p-2">
              <p className="text-base font-bold text-foreground">{strategy.next_7_days.length}</p>
              <p className="text-[0.65rem] text-muted-foreground">{t("profileStrategy.bucket.next7Days")}</p>
            </div>
            <div className="rounded-sm border bg-surface p-2">
              <p className="text-base font-bold text-foreground">{strategy.next_30_days.length}</p>
              <p className="text-[0.65rem] text-muted-foreground">{t("profileStrategy.bucket.next30Days")}</p>
            </div>
            <div className="rounded-sm border bg-surface p-2">
              <p className="text-base font-bold text-foreground">{strategy.next_90_days.length}</p>
              <p className="text-[0.65rem] text-muted-foreground">{t("profileStrategy.bucket.next90Days")}</p>
            </div>
          </div>

          {!strategy.has_verified_deadlines ? (
            <p className="mt-2 text-[0.68rem] text-warning">{t("profileStrategy.deadlineNotVerified")}</p>
          ) : null}

          {events.length === 0 ? (
            <p className="mt-3 text-xs text-muted-foreground">{t("profileStrategy.noUpcomingItems")}</p>
          ) : (
            <ul className="mt-3 space-y-1.5">
              {events.map((event, index) => (
                <li
                  className="flex items-center justify-between gap-2 text-xs"
                  key={`${event.type}-${event.university ?? ""}-${index}`}
                >
                  <span className="flex min-w-0 items-center gap-1.5">
                    <CalendarClock aria-hidden className="size-3 shrink-0 text-accent" />
                    <span className="truncate">
                      {t(`applications.eventType.${event.type}` as TranslationKey)}
                      {event.university ? ` — ${event.university}` : ""}
                    </span>
                  </span>
                  <span
                    className={`shrink-0 rounded-sm border px-1.5 py-0.5 text-[0.62rem] font-bold uppercase ${
                      URGENCY_TONE[event.urgency] ?? URGENCY_TONE.unknown
                    }`}
                  >
                    {event.date ? formatDate(event.date, locale) : t("applications.confidence.missing")}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {strategy.essay_plan.essays_missing || strategy.recommendation_letter_plan.recommendation_letters_missing ? (
            <div className="mt-3 space-y-1 border-t pt-2 text-xs text-muted-foreground">
              {strategy.essay_plan.essays_missing ? (
                <p>{t(`profileRecommendations.action.${strategy.essay_plan.next_action}` as TranslationKey)}</p>
              ) : null}
              {strategy.recommendation_letter_plan.recommendation_letters_missing ? (
                <p>
                  {t(
                    `profileRecommendations.action.${strategy.recommendation_letter_plan.next_action}` as TranslationKey
                  )}
                </p>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </Card>
  );
}
