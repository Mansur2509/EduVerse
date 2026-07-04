"use client";

import { ExternalLink } from "lucide-react";

import type { ApplicationReadiness } from "@/entities/profile";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Card } from "@/shared/ui/card";

export function ReadinessCard({
  readiness,
  compact = false
}: {
  readiness: ApplicationReadiness;
  compact?: boolean;
}) {
  const { t } = useI18n();

  const componentLabel = (component: string) =>
    t(`admissions.component.${component}` as TranslationKey);
  const categories = readiness.categories?.length
    ? readiness.categories
    : Object.entries(readiness.score_components).map(([key, score]) => ({
        key,
        score,
        source_keys: [],
        missing_sources: [],
        status: readiness.level
      }));

  return (
    <Card>
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-hover">
            {t("admissions.readiness.title")}
          </p>
          <h2 className="mt-2 text-2xl font-semibold">
            {t(
              `admissions.readiness.level.${readiness.level}` as TranslationKey
            )}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {t("admissions.readiness.description")}
          </p>
        </div>
        <div className="shrink-0 rounded-sm border bg-surface px-4 py-3 text-right">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t("admissions.readiness.scoreLabel")}
          </p>
          <p className="text-2xl font-semibold">{readiness.stars}/5</p>
          {readiness.cap_reason ? (
            <p className="mt-1 max-w-44 text-xs leading-5 text-warning">
              {t(`admissions.readiness.cap.${readiness.cap_reason}` as TranslationKey)}
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map((category) => (
          <div className="border bg-surface p-3" key={category.key}>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="font-semibold">{componentLabel(category.key)}</span>
              <span className="text-accent">{category.score}/5</span>
            </div>
            <div className="mt-2 h-1.5 bg-muted">
              <div
                className="h-full bg-primary"
                style={{ width: `${category.score * 20}%` }}
              />
            </div>
            {category.missing_sources.length > 0 ? (
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                {t("admissions.readiness.missingSources", {
                  sources: category.missing_sources.map(componentLabel).join(", ")
                })}
              </p>
            ) : null}
          </div>
        ))}
      </div>

      {!compact ? (
        <div className="mt-6 grid gap-5 md:grid-cols-2">
          <div>
            <h3 className="text-lg font-semibold">
              {t("admissions.readiness.why")}
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {(readiness.reasons.length
                ? readiness.reasons.map((reason) =>
                    t(`admissions.readiness.reason.${reason}` as TranslationKey)
                  )
                : [t("admissions.readiness.noReasons")]
              ).map((item) => (
                <li className="border-l-2 border-success pl-3" key={item}>
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-semibold">
              {t("admissions.readiness.nextActions")}
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {(readiness.next_actions.length
                ? readiness.next_actions.map((component) =>
                    t(`admissions.readiness.action.${component}` as TranslationKey)
                  )
                : [t("admissions.readiness.noImprovements")]
              ).map((item) => (
                <li className="border-l-2 border-warning pl-3" key={item}>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      <div className="mt-6 border border-warning/30 bg-warning/10 p-4 text-xs leading-5 text-warning">
        <p>
          {readiness.comparison_status === "published_ranges"
            ? t("admissions.readiness.published")
            : t("admissions.readiness.officialNeeded")}
        </p>
        <p className="mt-2">{t("admissions.readiness.disclaimer")}</p>
      </div>

      {readiness.official_sources.length ? (
        <div className="mt-5">
          <h3 className="text-sm font-semibold">
            {t("admissions.readiness.sources")}
          </h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {readiness.official_sources.map((source) => (
              <a
                className="inline-flex items-center gap-2 border bg-surface px-3 py-2 text-xs font-semibold text-primary-hover hover:underline"
                href={source.url}
                key={`${source.university}-${source.url}`}
                rel="noreferrer"
                target="_blank"
              >
                {source.university}: {source.title}
                <ExternalLink aria-hidden className="size-3" />
              </a>
            ))}
          </div>
        </div>
      ) : null}
    </Card>
  );
}
