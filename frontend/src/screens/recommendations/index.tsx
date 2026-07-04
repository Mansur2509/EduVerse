"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  CostRisk,
  RecommendationCategory,
  RecommendationItem,
  RiskLevel,
  Urgency
} from "@/entities/recommendation";
import { RECOMMENDATION_CATEGORIES } from "@/entities/recommendation";
import { createApplicationRequest } from "@/features/applications";
import { addToShortlistRequest, getRecommendationsRequest } from "@/features/universities";
import { useI18n, type LocaleCode, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { CollapsibleFilterPanel } from "@/shared/ui/collapsible-filter-panel";
import { fieldClassName } from "@/shared/ui/field";
import { HelpTooltip } from "@/shared/ui/help-tooltip";
import { LoadingNotice } from "@/shared/ui/loading-notice";
import { SectionTabs } from "@/shared/ui/section-tabs";

const SORT_OPTIONS = ["best_fit", "deadline_soon", "lowest_cost", "highest_confidence"] as const;
type SortOption = (typeof SORT_OPTIONS)[number];

const CONFIDENCE_RANK: Record<string, number> = { low: 0, medium: 1, high: 2 };
const URGENCY_RANK: Record<Urgency, number> = {
  overdue: 0,
  critical: 1,
  urgent: 2,
  soon: 3,
  upcoming: 4,
  far: 5,
  unknown: 6
};

const CATEGORY_BADGE_STYLES: Record<RecommendationCategory, string> = {
  dream: "border-danger/45 bg-danger/15 text-danger",
  reach: "border-danger/35 bg-danger/10 text-danger",
  target: "border-accent/35 bg-accent/10 text-accent",
  safety: "border-success/35 bg-success/10 text-success"
};

const RISK_BADGE_STYLES: Record<RiskLevel, string> = {
  low: "border-success/35 bg-success/10 text-success",
  moderate: "border-warning/35 bg-warning/10 text-warning",
  high: "border-danger/35 bg-danger/10 text-danger"
};

const COST_RISK_BADGE_STYLES: Record<CostRisk, string> = {
  low: "border-success/35 bg-success/10 text-success",
  moderate: "border-warning/35 bg-warning/10 text-warning",
  high: "border-danger/35 bg-danger/10 text-danger",
  unknown: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

const URGENCY_BADGE_STYLES: Record<Urgency, string> = {
  overdue: "border-danger/45 bg-danger/10 text-danger",
  critical: "border-danger/45 bg-danger/10 text-danger",
  urgent: "border-warning/45 bg-warning/10 text-warning",
  soon: "border-warning/35 bg-warning/10 text-warning",
  upcoming: "border-accent/35 bg-accent/10 text-accent",
  far: "border-muted-foreground/30 bg-surface text-muted-foreground",
  unknown: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

const PROFILE_SIGNAL_HREFS: Record<string, string> = {
  profile_gpa: "/profile#profile-foundation-education",
  profile_sat: "/profile#profile-foundation-tests",
  profile_ielts: "/profile#profile-foundation-tests",
  profile_curriculum: "/profile#profile-foundation-education",
  profile_intended_major: "/profile#profile-foundation-admissions",
  profile_activities: "/profile#profile-section-activities",
  profile_essays: "/profile#profile-section-essays"
};

function profileSignalHref(code: string) {
  return PROFILE_SIGNAL_HREFS[code] ?? "/profile";
}

function badgeClass(base: string) {
  return `inline-flex items-center rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${base}`;
}

function costValue(item: RecommendationItem): number {
  const value = item.estimated_total_cost_usd;
  if (value === null || value === undefined || value === "") return Number.POSITIVE_INFINITY;
  const numeric = typeof value === "number" ? value : Number.parseFloat(value);
  return Number.isFinite(numeric) ? numeric : Number.POSITIVE_INFINITY;
}

function sortItems(items: RecommendationItem[], sortBy: SortOption): RecommendationItem[] {
  const sorted = [...items];
  switch (sortBy) {
    case "deadline_soon":
      sorted.sort((a, b) => URGENCY_RANK[a.urgency] - URGENCY_RANK[b.urgency]);
      break;
    case "lowest_cost":
      sorted.sort((a, b) => costValue(a) - costValue(b));
      break;
    case "highest_confidence":
      sorted.sort((a, b) => CONFIDENCE_RANK[b.confidence] - CONFIDENCE_RANK[a.confidence]);
      break;
    case "best_fit":
    default:
      sorted.sort((a, b) => b.fit_score - a.fit_score);
      break;
  }
  return sorted;
}

export function RecommendationsScreen() {
  const { locale, t } = useI18n();
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [missingPreferences, setMissingPreferences] = useState<string[]>([]);
  const [listSizeLimited, setListSizeLimited] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [actionError, setActionError] = useState(false);
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
  const [pendingSlugs, setPendingSlugs] = useState<Set<string>>(new Set());

  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [countryFilter, setCountryFilter] = useState<string>("all");
  const [costRiskFilter, setCostRiskFilter] = useState<string>("all");
  const [urgencyFilter, setUrgencyFilter] = useState<string>("all");
  const [confidenceFilter, setConfidenceFilter] = useState<string>("all");
  const [internationalOnly, setInternationalOnly] = useState(false);
  const [sortBy, setSortBy] = useState<SortOption>("best_fit");
  const hasActiveFilters =
    categoryFilter !== "all" ||
    countryFilter !== "all" ||
    costRiskFilter !== "all" ||
    urgencyFilter !== "all" ||
    confidenceFilter !== "all" ||
    internationalOnly ||
    sortBy !== "best_fit";
  const activeFilterCount = [
    categoryFilter !== "all",
    countryFilter !== "all",
    costRiskFilter !== "all",
    urgencyFilter !== "all",
    confidenceFilter !== "all",
    internationalOnly,
    sortBy !== "best_fit"
  ].filter(Boolean).length;

  function clearFilters() {
    setCategoryFilter("all");
    setCountryFilter("all");
    setCostRiskFilter("all");
    setUrgencyFilter("all");
    setConfidenceFilter("all");
    setInternationalOnly(false);
    setSortBy("best_fit");
  }

  const load = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getRecommendationsRequest();
      setItems(response.recommendations);
      setMissingPreferences(response.missing_preferences);
      setListSizeLimited(response.list_size_limited);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function updateItem(slug: string, patch: Partial<RecommendationItem>) {
    setItems((current) =>
      current.map((item) => (item.university.slug === slug ? { ...item, ...patch } : item))
    );
  }

  function setPending(slug: string, isPending: boolean) {
    setPendingSlugs((current) => {
      const next = new Set(current);
      if (isPending) next.add(slug);
      else next.delete(slug);
      return next;
    });
  }

  async function handleAddToShortlist(item: RecommendationItem) {
    if (pendingSlugs.has(item.university.slug)) return;
    setActionError(false);
    setPending(item.university.slug, true);
    try {
      await addToShortlistRequest(item.university.slug);
      updateItem(item.university.slug, { is_shortlisted: true });
    } catch {
      setActionError(true);
    } finally {
      setPending(item.university.slug, false);
    }
  }

  async function handleTrackApplication(item: RecommendationItem) {
    if (pendingSlugs.has(item.university.slug)) return;
    setActionError(false);
    setPending(item.university.slug, true);
    try {
      const created = await createApplicationRequest({ university: item.university.id });
      updateItem(item.university.slug, { application_id: created.id });
    } catch {
      setActionError(true);
    } finally {
      setPending(item.university.slug, false);
    }
  }

  const countries = useMemo(
    () => Array.from(new Set(items.map((item) => item.university.country))).sort(),
    [items]
  );
  const missingProfileSignals = useMemo(
    () =>
      Array.from(
        new Set(
          items.flatMap((item) =>
            item.missing_data.filter((code) => String(code).startsWith("profile_"))
          )
        )
      ).slice(0, 5),
    [items]
  );

  const filtered = useMemo(
    () =>
      items.filter((item) => {
        if (categoryFilter !== "all" && item.category !== categoryFilter) return false;
        if (countryFilter !== "all" && item.university.country !== countryFilter) return false;
        if (costRiskFilter !== "all" && item.cost_risk !== costRiskFilter) return false;
        if (urgencyFilter !== "all" && item.urgency !== urgencyFilter) return false;
        if (confidenceFilter !== "all" && item.confidence !== confidenceFilter) return false;
        if (internationalOnly && !item.is_international) return false;
        return true;
      }),
    [items, categoryFilter, countryFilter, costRiskFilter, urgencyFilter, confidenceFilter, internationalOnly]
  );

  const sections = useMemo(() => {
    const grouped = new Map<RecommendationCategory, RecommendationItem[]>();
    RECOMMENDATION_CATEGORIES.forEach((category) => grouped.set(category, []));
    filtered.forEach((item) => grouped.get(item.category)?.push(item));
    grouped.forEach((list, category) => grouped.set(category, sortItems(list, sortBy)));
    return grouped;
  }, [filtered, sortBy]);

  if (isLoading) {
    return <LoadingNotice message={t("recommendations.states.loading")} />;
  }

  if (hasError) {
    return (
      <Card>
        <p className="text-sm text-danger" role="alert">
          {t("recommendations.states.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void load()} type="button">
          {t("recommendations.actions.retry")}
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <SectionTabs
        ariaLabel={t("universities.tabs.ariaLabel")}
        items={[
          { href: "/universities", label: t("universities.tabs.browse") },
          { href: "/recommendations", label: t("universities.tabs.recommendations") },
          { href: "/strategy", label: t("universities.tabs.strategy") }
        ]}
      />

      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("recommendations.eyebrow")}
        </p>
        <h1 className="mt-2 max-w-3xl text-3xl font-semibold sm:text-4xl">
          {t("recommendations.title")}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          {t("recommendations.description")}
        </p>
        {items.length > 0 ? (
          <p className="mt-3 text-xs text-muted-foreground">
            {t("recommendations.summary.total", { count: items.length })}
          </p>
        ) : null}
      </section>

      {missingPreferences.length > 0 ? (
        <Card className="border-warning/35 bg-warning/10">
          <p className="text-sm font-semibold">{t("recommendations.missingProfile.title")}</p>
          <ul className="mt-2 space-y-1 text-sm">
            {missingPreferences.includes("preferred_countries") ? (
              <li>{t("recommendations.missingProfile.countries")}</li>
            ) : null}
            {missingPreferences.includes("intended_major") ? (
              <li>{t("recommendations.missingProfile.major")}</li>
            ) : null}
          </ul>
          <Button asChild className="mt-3" size="sm" variant="ghost">
            <Link href="/profile">{t("recommendations.missingProfile.update")}</Link>
          </Button>
        </Card>
      ) : null}

      {listSizeLimited ? (
        <Card className="border-accent/35 bg-accent/10">
          <p className="text-sm">{t("recommendations.listLimited")}</p>
        </Card>
      ) : null}

      <Card className="border-accent/25 bg-elevated/35 p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <p className="text-sm font-semibold">{t("recommendations.profileDepth.title")}</p>
            <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
              {t("recommendations.profileDepth.description")}
            </p>
          </div>
          <Button asChild size="sm" variant="secondary">
            <Link href="/profile">{t("recommendations.profileDepth.action")}</Link>
          </Button>
        </div>
        {missingProfileSignals.length > 0 ? (
          <ul className="mt-3 flex flex-wrap gap-2 text-xs">
            {missingProfileSignals.map((code) => (
              <li key={code}>
                <Link
                  className="inline-flex items-center rounded-sm border bg-card px-2 py-1 font-semibold text-muted-foreground hover:text-primary-hover"
                  href={profileSignalHref(code)}
                >
                  {t(`universities.fit.missingFields.${code}` as TranslationKey)}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-xs text-muted-foreground">
            {t("recommendations.profileDepth.complete")}
          </p>
        )}
      </Card>

      {actionError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("recommendations.states.actionError")}
          </p>
        </Card>
      ) : null}

      <CollapsibleFilterPanel
        activeCount={activeFilterCount}
        onClear={clearFilters}
        resultCount={filtered.length}
        storageKey="eduverse.filters.recommendations"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <h2 className="text-sm font-semibold">{t("applications.filters.title")}</h2>
            <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
              {t("applications.filters.autoApply")}
            </span>
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <label className="block">
            <span className="text-xs font-semibold">{t("recommendations.filters.category")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setCategoryFilter(event.target.value)}
              value={categoryFilter}
            >
              <option value="all">{t("applications.filters.all")}</option>
              {RECOMMENDATION_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {t(`universities.fit.category.${category}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("recommendations.filters.country")}</span>
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
          <label className="block">
            <span className="text-xs font-semibold">{t("recommendations.filters.costRisk")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setCostRiskFilter(event.target.value)}
              value={costRiskFilter}
            >
              <option value="all">{t("applications.filters.all")}</option>
              {(["low", "moderate", "high", "unknown"] as const).map((risk) => (
                <option key={risk} value={risk}>
                  {t(`recommendations.costRisk.${risk}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("applications.filters.urgency")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setUrgencyFilter(event.target.value)}
              value={urgencyFilter}
            >
              <option value="all">{t("applications.filters.all")}</option>
              {(["overdue", "critical", "urgent", "soon", "upcoming", "far"] as const).map((level) => (
                <option key={level} value={level}>
                  {t(`applications.urgency.${level}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("recommendations.filters.confidence")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setConfidenceFilter(event.target.value)}
              value={confidenceFilter}
            >
              <option value="all">{t("applications.filters.all")}</option>
              {(["low", "medium", "high"] as const).map((level) => (
                <option key={level} value={level}>
                  {t(`universities.fit.confidence.${level}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="flex items-center gap-2 text-xs font-semibold">
            <input
              checked={internationalOnly}
              onChange={(event) => setInternationalOnly(event.target.checked)}
              type="checkbox"
            />
            {t("recommendations.filters.internationalOnly")}
          </label>
          <label className="flex items-center gap-2 text-xs font-semibold">
            {t("recommendations.sort.label")}
            <select
              className={fieldClassName}
              onChange={(event) => setSortBy(event.target.value as SortOption)}
              value={sortBy}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {t(`recommendations.sort.${option}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="text-xs text-muted-foreground">
          {t("recommendations.filters.resultCount", { count: filtered.length })}
        </p>
      </CollapsibleFilterPanel>

      {filtered.length === 0 ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("recommendations.states.empty")}</p>
          {hasActiveFilters ? (
            <Button className="mt-4" onClick={clearFilters} size="sm" type="button" variant="secondary">
              {t("applications.filters.clear")}
            </Button>
          ) : (
            <Button asChild className="mt-4" size="sm" variant="secondary">
              <Link href="/profile">{t("recommendations.missingProfile.update")}</Link>
            </Button>
          )}
        </Card>
      ) : (
        RECOMMENDATION_CATEGORIES.map((category) => {
          const list = sections.get(category) ?? [];
          if (list.length === 0) return null;
          return (
            <div className="space-y-2" key={category}>
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <span className={badgeClass(CATEGORY_BADGE_STYLES[category])}>
                  {t(`universities.fit.category.${category}` as TranslationKey)}
                </span>
                <span className="text-sm font-normal text-muted-foreground">({list.length})</span>
                <HelpTooltip label={t(`recommendations.help.category.${category}` as TranslationKey)} />
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {list.map((item) => (
                  <RecommendationCard
                    isExpanded={expandedSlug === item.university.slug}
                    isPending={pendingSlugs.has(item.university.slug)}
                    item={item}
                    key={item.university.slug}
                    locale={locale}
                    onAddToShortlist={() => void handleAddToShortlist(item)}
                    onToggleExpand={() =>
                      setExpandedSlug((current) =>
                        current === item.university.slug ? null : item.university.slug
                      )
                    }
                    onTrackApplication={() => void handleTrackApplication(item)}
                    t={t}
                  />
                ))}
              </div>
            </div>
          );
        })
      )}

      <p className="text-xs leading-5 text-muted-foreground">{t("recommendations.disclaimer")}</p>
    </div>
  );
}

function RecommendationCard({
  item,
  isExpanded,
  isPending,
  onToggleExpand,
  onAddToShortlist,
  onTrackApplication,
  locale,
  t
}: {
  item: RecommendationItem;
  isExpanded: boolean;
  isPending: boolean;
  onToggleExpand: () => void;
  onAddToShortlist: () => void;
  onTrackApplication: () => void;
  locale: LocaleCode;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}) {
  const roundLabel = item.application_round.recommended_round;
  const isDeadlineOverdue = item.urgency === "overdue";
  let roundDisplay = roundLabel;
  if (isDeadlineOverdue) {
    roundDisplay = t("recommendations.card.needsUpdatedDeadline");
  } else if (roundLabel === "unknown") {
    roundDisplay = t("applications.deadlines.notVerified");
  }
  return (
    <Card className="flex h-full min-w-0 flex-col gap-2.5 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-base font-semibold">{item.university.name}</p>
          <p className="text-xs text-muted-foreground">
            {item.university.city ? `${item.university.city}, ` : ""}
            {item.university.country}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="flex items-center gap-1 rounded-sm border bg-surface px-2 py-1 text-center text-xs font-bold">
            {item.fit_score}
            <HelpTooltip label={t("recommendations.help.fitScore")} />
          </span>
          {typeof item.conditional_fit_score === "number" ? (
            <span className="flex items-center gap-1 rounded-sm border border-accent/35 bg-accent/10 px-2 py-1 text-center text-xs font-bold text-accent">
              {t("recommendations.card.conditionalScore", {
                score: item.conditional_fit_score
              })}
              <HelpTooltip label={t("recommendations.help.conditionalFit")} />
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        <span className={badgeClass(CATEGORY_BADGE_STYLES[item.category])}>
          {t(`universities.fit.category.${item.category}` as TranslationKey)}
        </span>
        <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
          {t(`universities.fit.confidence.${item.confidence}` as TranslationKey)}
        </span>
        {item.is_international ? (
          <span className="rounded-sm border border-accent/35 bg-accent/10 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-accent">
            {t("recommendations.internationalBadge")}
          </span>
        ) : null}
      </div>

      {item.recommended_programs.length > 0 ? (
        <div className="text-xs">
          <p className="font-semibold text-muted-foreground">
            {t("recommendations.card.programs")}
          </p>
          <ul className="mt-1 space-y-1">
            {item.recommended_programs.slice(0, isExpanded ? undefined : 3).map((program) => (
              <li key={program.name}>
                <span>{program.name}</span>
                <span className="ml-1.5 text-muted-foreground">
                  ({t(`recommendations.programReason.${program.fit_reason_key}` as TranslationKey)})
                </span>
                <span className="ml-1.5 text-muted-foreground">
                  {t("recommendations.card.programFitScore", {
                    score: program.program_fit_score
                  })}
                </span>
                <span className="ml-1.5 text-muted-foreground">
                  {t(`universities.majorCluster.${program.major_cluster}` as TranslationKey)}
                </span>
                {isExpanded && program.subject_ranking ? (
                  <span className="mt-0.5 block text-muted-foreground">
                    {t("recommendations.card.subjectRanking", {
                      subject: program.subject_ranking.subject_area,
                      rank: program.subject_ranking.rank,
                      source: program.subject_ranking.source_name
                    })}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
          {!isExpanded && item.recommended_programs.length > 3 ? (
            <p className="mt-1 text-[0.68rem] font-semibold text-muted-foreground">
              +{item.recommended_programs.length - 3}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          {item.program_data_verified
            ? t("recommendations.card.noProgramMatch")
            : t("recommendations.card.programsNotVerified")}
        </p>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <p className="flex items-center gap-1 font-semibold text-muted-foreground">
            {t("recommendations.card.cost")}
            <HelpTooltip label={t("recommendations.help.costConfidence")} />
          </p>
          <p>
            {item.estimated_total_cost_usd
              ? `$${Number(item.estimated_total_cost_usd).toLocaleString()}`
              : t("universities.notVerifiedYet")}
          </p>
          <span className={badgeClass(COST_RISK_BADGE_STYLES[item.cost_risk])}>
            {t(`recommendations.costRisk.${item.cost_risk}` as TranslationKey)}
          </span>
        </div>
        <div>
          <p className="font-semibold text-muted-foreground">
            {t("recommendations.card.deadline")}
          </p>
          <p>{item.deadline ? formatDate(item.deadline, locale) : t("applications.deadlines.notVerified")}</p>
          <span className={badgeClass(URGENCY_BADGE_STYLES[item.urgency])}>
            {t(`applications.urgency.${item.urgency}` as TranslationKey)}
          </span>
          {isDeadlineOverdue ? (
            <p className="mt-1 text-[0.68rem] font-semibold text-danger">
              {t("recommendations.card.currentCycleUnavailable")}
            </p>
          ) : null}
        </div>
      </div>

      <p className="text-xs">
        {t("recommendations.card.recommendedRound")}:{" "}
        <span className="font-semibold">{roundDisplay}</span>
      </p>

      {item.main_strength ? (
        <p className="text-xs text-success">
          <span className="font-semibold uppercase tracking-wide">
            {t("recommendations.card.mainStrength")}:{" "}
          </span>
          {t(`universities.fit.strengths.${item.main_strength}` as TranslationKey)}
        </p>
      ) : null}
      {item.main_risk ? (
        <p className="text-xs text-warning">
          <span className="font-semibold uppercase tracking-wide">
            {t("recommendations.card.mainRisk")}:{" "}
          </span>
          {t(
            `universities.fit.${
              item.missing_data.includes(item.main_risk as never) ? "missingFields" : "risks"
            }.${item.main_risk}` as TranslationKey
          )}
        </p>
      ) : null}

      <button
        className="text-left text-xs font-semibold text-primary-hover underline"
        onClick={onToggleExpand}
        type="button"
      >
        {isExpanded ? t("recommendations.card.hideDetails") : t("recommendations.card.showDetails")}
      </button>

      {isExpanded ? (
        <div className="space-y-2 rounded-sm border bg-surface p-3 text-xs">
          <div>
            <p className="font-semibold">{t("recommendations.card.whyRecommended")}</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5">
              {item.why_recommended_keys.map((key) => (
                <li key={key}>{t(`recommendations.reason.${key}` as TranslationKey)}</li>
              ))}
            </ul>
          </div>
          <p>
            <span className="font-semibold">{t("recommendations.card.roundReason")}: </span>
            {t(`recommendations.roundReason.${item.application_round.reason_key}` as TranslationKey, {
              round: item.application_round.reason_params.round ?? ""
            })}
          </p>
          <p>
            <span className="font-semibold">{t("recommendations.card.currentFit")}: </span>
            {t("recommendations.card.currentFitScore", { score: item.current_academic_subscore })}
          </p>
          <div className="flex flex-wrap gap-2">
            <span className={badgeClass(RISK_BADGE_STYLES[item.academic_risk])}>
              {t("recommendations.card.academicRisk")}:{" "}
              {t(`recommendations.riskLevel.${item.academic_risk}` as TranslationKey)}
            </span>
            <span className={badgeClass(RISK_BADGE_STYLES[item.profile_risk])}>
              {t("recommendations.card.profileRisk")}:{" "}
              {t(`recommendations.riskLevel.${item.profile_risk}` as TranslationKey)}
            </span>
            <span className={badgeClass(RISK_BADGE_STYLES[item.deadline_risk])}>
              {t("recommendations.card.deadlineRisk")}:{" "}
              {t(`recommendations.riskLevel.${item.deadline_risk}` as TranslationKey)}
            </span>
          </div>
          {item.missing_data.length > 0 ? (
            <div>
              <p className="font-semibold">{t("recommendations.card.missingData")}</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5">
                {item.missing_data.map((code) => (
                  <li key={code}>{t(`universities.fit.missingFields.${code}` as TranslationKey)}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {item.missing_program_data.length > 0 ? (
            <div>
              <p className="font-semibold">{t("recommendations.card.programDataContext")}</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5">
                {item.missing_program_data.map((code) => (
                  <li key={code}>
                    {t(`universities.programMatching.missing.${code}` as TranslationKey)}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {item.subject_ranking_context ? (
            <p>
              <span className="font-semibold">{t("recommendations.card.subjectRankingLabel")}: </span>
              {t("recommendations.card.subjectRanking", {
                subject: item.subject_ranking_context.subject_area,
                rank: item.subject_ranking_context.rank,
                source: item.subject_ranking_context.source_name
              })}
            </p>
          ) : null}
          {item.conditional_notes.length > 0 || typeof item.conditional_fit_score === "number" ? (
            <div>
              <p className="font-semibold">{t("recommendations.card.conditionalFit")}</p>
              {typeof item.conditional_fit_score === "number" ? (
                <p className="mt-1">
                  {t("recommendations.card.conditionalExplanation", {
                    current: item.fit_score,
                    conditional: item.conditional_fit_score,
                    targets: [
                      item.conditional_targets?.sat
                        ? `SAT ${item.conditional_targets.sat}`
                        : null,
                      item.conditional_targets?.ielts
                        ? `IELTS ${item.conditional_targets.ielts}`
                        : null
                    ]
                      .filter(Boolean)
                      .join(", ")
                  })}
                </p>
              ) : null}
              {item.conditional_notes.map((note, index) => (
                <p className="mt-1" key={index}>
                  {note}
                </p>
              ))}
            </div>
          ) : null}
          <p>
            <span className="font-semibold">{t("recommendations.card.nextAction")}: </span>
            {t(`universities.fit.nextActions.${item.next_action}` as TranslationKey)}
          </p>
          <div>
            <p className="font-semibold">{t("recommendations.card.dataContext")}</p>
            <p className="mt-1">
              {t("recommendations.card.deadlineConfidence")}:{" "}
              {t(`applications.confidence.${item.deadline_confidence}` as TranslationKey)}
              <HelpTooltip className="ml-1" label={t("recommendations.help.deadlineConfidence")} />
              {item.deadline_cycle_label
                ? ` · ${t("applications.deadlines.cycleLabel", { cycle: item.deadline_cycle_label })}`
                : ""}
            </p>
            {item.source_notes.length > 0 ? (
              <ul className="mt-1 space-y-1">
                {item.source_notes.slice(0, 3).map((source) => (
                  <li key={`${source.title}-${source.url}`}>
                    <a
                      className="font-semibold text-primary-hover underline"
                      href={source.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      {source.title || source.url}
                    </a>{" "}
                    <span className="text-muted-foreground">
                      {source.is_official
                        ? t("recommendations.card.officialSource")
                        : t("recommendations.card.supportingSource")}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-muted-foreground">
                {t("recommendations.card.noSources")}
              </p>
            )}
          </div>
        </div>
      ) : null}

      <div className="mt-auto flex flex-wrap gap-2 pt-2">
        <Button
          disabled={item.is_shortlisted || isPending}
          onClick={onAddToShortlist}
          size="sm"
          type="button"
          variant={item.is_shortlisted ? "secondary" : "primary"}
        >
          {item.is_shortlisted
            ? t("recommendations.actions.shortlisted")
            : t("recommendations.actions.addToShortlist")}
        </Button>
        <Button
          disabled={item.application_id !== null || isPending}
          onClick={onTrackApplication}
          size="sm"
          type="button"
          variant={item.application_id !== null ? "secondary" : "primary"}
        >
          {item.application_id !== null
            ? t("recommendations.actions.tracking")
            : t("recommendations.actions.trackApplication")}
        </Button>
        <Button asChild size="sm" variant="ghost">
          <Link href={`/universities/${item.university.slug}`}>
            {t("recommendations.actions.viewDetails")}
          </Link>
        </Button>
      </div>
    </Card>
  );
}
