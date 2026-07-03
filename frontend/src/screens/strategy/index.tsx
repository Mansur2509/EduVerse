"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { RecommendationCategory } from "@/entities/recommendation";
import type { ApplicationStrategyResponse, StrategySchool } from "@/entities/strategy";
import { getApplicationStrategyRequest } from "@/features/universities";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { HelpTooltip } from "@/shared/ui/help-tooltip";
import { LoadingNotice } from "@/shared/ui/loading-notice";

const CATEGORY_BADGE_STYLES: Record<RecommendationCategory, string> = {
  dream: "border-danger/45 bg-danger/15 text-danger",
  reach: "border-danger/35 bg-danger/10 text-danger",
  target: "border-accent/35 bg-accent/10 text-accent",
  safety: "border-success/35 bg-success/10 text-success"
};

const ROUND_CONFIDENCE_STYLES: Record<string, string> = {
  verified: "border-success/35 bg-success/10 text-success",
  estimated: "border-warning/35 bg-warning/10 text-warning",
  unverified: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

function badgeClass(base: string) {
  return `inline-flex items-center rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${base}`;
}

type GroupMode = "category" | "round";

export function StrategyScreen() {
  const { t } = useI18n();
  const [data, setData] = useState<ApplicationStrategyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [groupMode, setGroupMode] = useState<GroupMode>("category");
  const [countryFilter, setCountryFilter] = useState("all");

  const load = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getApplicationStrategyRequest();
      setData(response);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const countries = useMemo(() => {
    if (!data) return [];
    return Array.from(new Set(data.schools.map((school) => school.university.country))).sort();
  }, [data]);

  if (isLoading) {
    return <LoadingNotice message={t("strategy.states.loading")} />;
  }

  if (hasError || !data) {
    return (
      <Card className="border-danger/35 bg-danger/10">
        <p className="text-sm text-danger" role="alert">
          {t("strategy.states.loadError")}
        </p>
      </Card>
    );
  }

  const matchesCountry = (school: StrategySchool) =>
    countryFilter === "all" || school.university.country === countryFilter;

  const groups: { key: string; label: string; schools: StrategySchool[] }[] =
    groupMode === "category"
      ? data.category_order.map((category) => ({
          key: category,
          label: t(`universities.fit.category.${category}` as TranslationKey),
          schools: (data.by_category[category] ?? []).filter(matchesCountry)
        }))
      : data.round_bucket_order.map((round) => ({
          key: round,
          label: t(`strategy.round.${round}` as TranslationKey),
          schools: (data.by_round[round] ?? []).filter(matchesCountry)
        }));

  const visibleGroups = groups.filter((group) => group.schools.length > 0);

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          {t("strategy.eyebrow")}
        </p>
        <h1 className="mt-1 text-2xl font-semibold">{t("strategy.title")}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          {t("strategy.description", {
            min: String(data.target_range.minimum),
            max: String(data.target_range.maximum)
          })}
        </p>
      </div>

      {data.data_scarcity ? (
        <Card className="border-warning/35 bg-warning/10">
          <p className="text-sm text-warning">{t("strategy.dataScarcity")}</p>
        </Card>
      ) : null}

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <label className="block">
            <span className="flex items-center gap-1 text-sm font-semibold">
              {t("strategy.groupBy")}
              <HelpTooltip label={t("help.strategyCategory")} />
            </span>
            <select
              className={fieldClassName}
              onChange={(event) => setGroupMode(event.target.value as GroupMode)}
              value={groupMode}
            >
              <option value="category">{t("strategy.groupBy.category")}</option>
              <option value="round">{t("strategy.groupBy.round")}</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t("strategy.filterCountry")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setCountryFilter(event.target.value)}
              value={countryFilter}
            >
              <option value="all">{t("applications.filters.all")}</option>
              {countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      {visibleGroups.length === 0 ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("strategy.states.empty")}</p>
        </Card>
      ) : (
        visibleGroups.map((group) => (
          <Card key={group.key}>
            <h2 className="text-lg font-semibold">
              {group.label}{" "}
              <span className="text-sm font-normal text-muted-foreground">
                ({group.schools.length})
              </span>
            </h2>
            <div className="mt-3 space-y-2">
              {group.schools.map((school) => (
                <div className="rounded-sm border bg-card p-3 text-sm" key={school.university.id}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-semibold">{school.university.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {school.university.city ? `${school.university.city}, ` : ""}
                        {school.university.country}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className={badgeClass(CATEGORY_BADGE_STYLES[school.category])}>
                        {t(`universities.fit.category.${school.category}` as TranslationKey)}
                      </span>
                      <span
                        className={badgeClass(ROUND_CONFIDENCE_STYLES[school.round_confidence])}
                      >
                        {t(`strategy.round.${school.round_bucket}` as TranslationKey)}
                      </span>
                      <HelpTooltip label={t("help.strategyRound")} />
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <span>
                      {t("universities.fit.scoreLabel")}: {school.fit_score}
                    </span>
                    {typeof school.conditional_fit_score === "number" ? (
                      <span>
                        {t("recommendations.card.conditionalFit")}: {school.conditional_fit_score}
                      </span>
                    ) : null}
                    {school.deadline ? (
                      <span>{t(`applications.urgency.${school.urgency}` as TranslationKey)}</span>
                    ) : null}
                    <span>{t(`recommendations.costRisk.${school.cost_risk}` as TranslationKey)}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ))
      )}

      <p className="text-xs italic text-muted-foreground">{data.disclaimer}</p>
    </div>
  );
}
