"use client";

import { useCallback, useEffect, useState } from "react";

import type {
  AdminAnalyticsActivity,
  AdminAnalyticsSummary,
  AdminFeatureUsage
} from "@/entities/analytics";
import {
  getAdminAnalyticsActivityRequest,
  getAdminAnalyticsFeatureUsageRequest,
  getAdminAnalyticsSummaryRequest
} from "@/features/analytics";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Card } from "@/shared/ui/card";
import { RetryNotice } from "@/shared/ui/retry-notice";
import { SkeletonCards, SkeletonText } from "@/shared/ui/skeleton";

export function AdminAnalyticsScreen() {
  const { locale, t } = useI18n();
  const [summary, setSummary] = useState<AdminAnalyticsSummary | null>(null);
  const [featureUsage, setFeatureUsage] = useState<AdminFeatureUsage>({});
  const [activity, setActivity] = useState<AdminAnalyticsActivity | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(false);
  const [featureUsageError, setFeatureUsageError] = useState(false);
  const [activityError, setActivityError] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    // One section failing (PERFORMANCE-012 PART 1) must not blank the other
    // two -- each of the 3 admin analytics calls is independent, so
    // Promise.allSettled lets each section render (or offer its own retry)
    // based only on its own outcome instead of Promise.all's all-or-nothing.
    const [summaryResult, featureUsageResult, activityResult] = await Promise.allSettled([
      getAdminAnalyticsSummaryRequest(),
      getAdminAnalyticsFeatureUsageRequest(),
      getAdminAnalyticsActivityRequest()
    ]);
    if (summaryResult.status === "fulfilled") {
      setSummary(summaryResult.value);
      setSummaryError(false);
    } else {
      setSummaryError(true);
    }
    if (featureUsageResult.status === "fulfilled") {
      setFeatureUsage(featureUsageResult.value);
      setFeatureUsageError(false);
    } else {
      setFeatureUsageError(true);
    }
    if (activityResult.status === "fulfilled") {
      setActivity(activityResult.value);
      setActivityError(false);
    } else {
      setActivityError(true);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const summaryTiles: Array<[TranslationKey, string]> = summary
    ? [
        ["adminAnalytics.metric.totalUsers", String(summary.total_users)],
        ["adminAnalytics.metric.newUsers7d", String(summary.new_users_7d)],
        ["adminAnalytics.metric.newUsers30d", String(summary.new_users_30d)],
        ["adminAnalytics.metric.activeUsers7d", String(summary.active_users_7d)],
        ["adminAnalytics.metric.activeUsers30d", String(summary.active_users_30d)],
        ["adminAnalytics.metric.onboardingCompletionRate", `${summary.onboarding_completion_rate_percent}%`],
        ["adminAnalytics.metric.retainedUsers", String(summary.retained_users_2plus_actions)],
        ["adminAnalytics.metric.applicationsCreated", String(summary.applications_created_total)],
        [
          "adminAnalytics.metric.universitiesShortlisted",
          String(summary.universities_shortlisted_total)
        ],
        [
          "adminAnalytics.metric.essayReviewsRequested",
          String(summary.essay_reviews_requested_total)
        ],
        ["adminAnalytics.metric.roadmapGenerations", String(summary.roadmap_generations_total)],
        ["adminAnalytics.metric.eventRegistrations", String(summary.event_registrations_total)],
        [
          "adminAnalytics.metric.organizerEventsCreated",
          String(summary.organizer_events_created_total)
        ]
      ]
    : [];

  const featureUsageEntries = Object.entries(featureUsage).sort(([, a], [, b]) => b - a);
  const maxFeatureUsage = Math.max(1, ...featureUsageEntries.map(([, count]) => count));

  const dailyEntries = Object.entries(activity?.daily_event_counts ?? {}).sort(([a], [b]) =>
    a.localeCompare(b)
  );
  const maxDailyCount = Math.max(1, ...dailyEntries.map(([, count]) => count));

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("adminAnalytics.eyebrow")}
        </p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">{t("adminAnalytics.title")}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          {t("adminAnalytics.description")}
        </p>
      </section>

      {isLoading ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SkeletonCards count={8} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-4">
              <SkeletonText lines={5} />
            </Card>
            <Card className="p-4">
              <SkeletonText lines={5} />
            </Card>
          </div>
        </>
      ) : (
        <>
          <section aria-labelledby="admin-analytics-summary">
            <h2 className="mb-3 text-lg font-semibold" id="admin-analytics-summary">
              {t("adminAnalytics.summary.title")}
            </h2>
            {summaryError ? (
              <RetryNotice message={t("adminAnalytics.states.loadError")} onRetry={() => void load()} />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {summaryTiles.map(([labelKey, value]) => (
                  <Card className="p-4" key={labelKey}>
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                      {t(labelKey)}
                    </p>
                    <p className="mt-2 font-serif text-3xl font-semibold text-accent">{value}</p>
                  </Card>
                ))}
              </div>
            )}
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card className="p-4">
              <h2 className="text-sm font-bold uppercase tracking-[0.12em] text-muted-foreground">
                {t("adminAnalytics.featureUsage.title")}
              </h2>
              {featureUsageError ? (
                <RetryNotice bare message={t("adminAnalytics.states.loadError")} onRetry={() => void load()} />
              ) : featureUsageEntries.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  {t("adminAnalytics.featureUsage.empty")}
                </p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {featureUsageEntries.map(([eventType, count]) => (
                    <li key={eventType}>
                      <div className="flex items-center justify-between gap-2 text-xs">
                        <span className="truncate text-muted-foreground">
                          {t(`analytics.eventType.${eventType}` as TranslationKey)}
                        </span>
                        <span className="shrink-0 font-semibold">{count}</span>
                      </div>
                      <div className="mt-1 h-1.5 w-full rounded-full bg-elevated">
                        <div
                          className="h-1.5 rounded-full bg-accent"
                          style={{ width: `${(count / maxFeatureUsage) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="p-4">
              <h2 className="text-sm font-bold uppercase tracking-[0.12em] text-muted-foreground">
                {t("adminAnalytics.activity.title")}
              </h2>
              {activityError ? (
                <RetryNotice bare message={t("adminAnalytics.states.loadError")} onRetry={() => void load()} />
              ) : dailyEntries.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  {t("adminAnalytics.activity.empty")}
                </p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {dailyEntries.map(([day, count]) => (
                    <li key={day}>
                      <div className="flex items-center justify-between gap-2 text-xs">
                        <span className="text-muted-foreground">{formatDate(day, locale)}</span>
                        <span className="shrink-0 font-semibold">{count}</span>
                      </div>
                      <div className="mt-1 h-1.5 w-full rounded-full bg-elevated">
                        <div
                          className="h-1.5 rounded-full bg-accent"
                          style={{ width: `${(count / maxDailyCount) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
