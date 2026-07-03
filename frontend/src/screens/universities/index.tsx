"use client";

import { Scale, Search, Star } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  UniversityCard,
  type UniversityDetails,
  type UniversityFilterOptions,
  type UniversityFilters
} from "@/entities/university";
import {
  getUniversitiesRequest,
  addToShortlistRequest,
  removeFromShortlistRequest,
  getUniversityFilterOptionsRequest
} from "@/features/universities";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { HelpTooltip } from "@/shared/ui/help-tooltip";
import { LoadingNotice } from "@/shared/ui/loading-notice";
import { DEFAULT_PAGE_SIZE, PaginatedGrid } from "@/shared/ui/pagination";

const emptyFilters: UniversityFilters = {
  search: "",
  country: "",
  city: "",
  institution_type: "",
  scholarship_available: "",
  verification_status: "",
  include_demo: "",
  ordering: "",
  ielts_minimum__lte: "",
  sat_average__gte: "",
  sat_average__lte: "",
  gpa_average__lte: "",
  currency_conversion_confidence: "",
  cost_status: undefined,
  major_cluster: "",
  program_search: "",
  subject_area: "",
  ranking_source: "",
  subject_rank_min: "",
  subject_rank_max: "",
  has_subject_ranking: "",
  portfolio_required: "",
  research_heavy: "",
  stem_heavy: "",
  interdisciplinary: "",
  source_confidence: "",
  global_rank_min: "",
  global_rank_max: "",
  qs_ranking_min: "",
  qs_ranking_max: "",
  the_rank_min: "",
  the_rank_max: "",
  national_rank_min: "",
  national_rank_max: ""
};

const MAX_COMPARE = 4;
const MIN_COMPARE = 2;
const MAX_SUGGESTIONS = 6;

function AutocompleteInput({
  className = fieldClassName,
  label,
  options,
  placeholder,
  value,
  onChange
}: {
  className?: string;
  label: string;
  options: string[];
  placeholder: string;
  value: string | undefined;
  onChange: (value: string) => void;
}) {
  const { t } = useI18n();
  const [isFocused, setIsFocused] = useState(false);
  const normalizedValue = value ?? "";
  const trimmedValue = normalizedValue.trim();
  // With no text yet, offer the first few options so users can browse the
  // list (e.g. see what countries are available) instead of needing to
  // already know a substring before anything appears.
  const matches = trimmedValue
    ? options
        .filter((option) => option.toLowerCase().includes(trimmedValue.toLowerCase()))
        .slice(0, MAX_SUGGESTIONS)
    : options.slice(0, MAX_SUGGESTIONS);

  return (
    <div className="relative">
      <input
        aria-autocomplete="list"
        aria-label={label}
        className={className}
        onBlur={() => window.setTimeout(() => setIsFocused(false), 100)}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setIsFocused(true)}
        placeholder={placeholder}
        value={normalizedValue}
      />
      {isFocused && options.length > 0 ? (
        <div className="absolute left-0 right-0 top-[calc(100%+0.25rem)] z-20 rounded-sm border bg-card p-1 shadow-card">
          {matches.length > 0 ? (
            matches.map((option) => (
              <button
                className="block w-full rounded-sm px-2 py-1.5 text-left text-sm hover:bg-elevated"
                key={option}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onChange(option);
                  setIsFocused(false);
                }}
                type="button"
              >
                {option}
              </button>
            ))
          ) : (
            <p className="px-2 py-1.5 text-xs text-muted-foreground">
              {t("universities.filters.noSuggestions")}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

export function UniversitiesScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const [filters, setFilters] = useState<UniversityFilters>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<UniversityFilters>(emptyFilters);
  const [universities, setUniversities] = useState<UniversityDetails[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [filterOptions, setFilterOptions] = useState<UniversityFilterOptions | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [shortlistOnly, setShortlistOnly] = useState(false);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [pendingShortlistId, setPendingShortlistId] = useState<number | null>(null);

  const loadUniversities = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getUniversitiesRequest(appliedFilters, {
        page: currentPage,
        page_size: DEFAULT_PAGE_SIZE
      });
      setUniversities(response.results);
      setTotalCount(response.count);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [appliedFilters, currentPage]);

  useEffect(() => {
    void loadUniversities();
  }, [loadUniversities]);

  useEffect(() => {
    getUniversityFilterOptionsRequest()
      .then(setFilterOptions)
      .catch(() => setFilterOptions(null));
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCurrentPage(1);
    setAppliedFilters(filters);
  }

  function clearFilters() {
    setFilters(emptyFilters);
    setAppliedFilters(emptyFilters);
    setCurrentPage(1);
    setShortlistOnly(false);
  }

  function toggleCompare(id: number) {
    setCompareIds((current) => {
      if (current.includes(id)) {
        return current.filter((item) => item !== id);
      }
      if (current.length >= MAX_COMPARE) {
        return current;
      }
      return [...current, id];
    });
  }

  async function toggleShortlist(university: UniversityDetails) {
    setPendingShortlistId(university.id);
    try {
      if (university.is_shortlisted) {
        await removeFromShortlistRequest(university.slug);
      } else {
        await addToShortlistRequest(university.slug);
      }
      setUniversities((current) =>
        current.map((item) =>
          item.id === university.id ? { ...item, is_shortlisted: !item.is_shortlisted } : item
        )
      );
    } catch {
      setHasError(true);
    } finally {
      setPendingShortlistId(null);
    }
  }

  function goToCompare() {
    router.push(`/universities/compare?ids=${compareIds.join(",")}`);
  }

  const visibleUniversities = shortlistOnly
    ? universities.filter((university) => university.is_shortlisted)
    : universities;
  const totalPages = Math.max(1, Math.ceil(totalCount / DEFAULT_PAGE_SIZE));
  const universityNameOptions = filterOptions?.universities.map((item) => item.name) ?? [];

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("universities.list.eyebrow")}
        </p>
        <div className="mt-3 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <h1 className="max-w-3xl text-3xl font-semibold sm:text-5xl">
              {t("universities.list.title")}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
              {t("universities.list.description")}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => setShortlistOnly((current) => !current)}
              type="button"
              variant={shortlistOnly ? "secondary" : "ghost"}
            >
              <Star aria-hidden className="mr-2 size-4" />
              {t("universities.actions.viewShortlist")}
            </Button>
            <Button
              disabled={compareIds.length < MIN_COMPARE}
              onClick={goToCompare}
              type="button"
            >
              <Scale aria-hidden className="mr-2 size-4" />
              {t("universities.actions.compareSelected", { count: compareIds.length })}
            </Button>
          </div>
        </div>
      </section>

      <Card>
        <form className="space-y-5" onSubmit={handleSubmit}>
          <section className="space-y-3">
            <h2 className="text-sm font-semibold">
              {t("universities.filters.group.searchLocation")}
            </h2>
            <div className="grid gap-3 md:grid-cols-3">
              <label className="block">
                <span className="text-sm font-semibold">{t("universities.filters.search")}</span>
                <div className="relative">
                  <Search
                    aria-hidden
                    className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                  />
                  <AutocompleteInput
                    className={`${fieldClassName} pl-10`}
                    label={t("universities.filters.search")}
                    onChange={(value) =>
                      setFilters((current) => ({ ...current, search: value }))
                    }
                    options={universityNameOptions}
                    placeholder={t("universities.filters.searchPlaceholder")}
                    value={filters.search}
                  />
                </div>
              </label>
              <label className="block">
                <span className="text-sm font-semibold">{t("universities.filters.country")}</span>
                <AutocompleteInput
                  label={t("universities.filters.country")}
                  onChange={(value) =>
                    setFilters((current) => ({ ...current, country: value }))
                  }
                  options={filterOptions?.countries ?? []}
                  placeholder={t("universities.filters.countryPlaceholder")}
                  value={filters.country}
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold">{t("universities.filters.city")}</span>
                <AutocompleteInput
                  label={t("universities.filters.city")}
                  onChange={(value) =>
                    setFilters((current) => ({ ...current, city: value }))
                  }
                  options={filterOptions?.cities ?? []}
                  placeholder={t("universities.filters.cityPlaceholder")}
                  value={filters.city}
                />
              </label>
            </div>
          </section>

          <section className="space-y-3 border-t pt-4">
            <h2 className="text-sm font-semibold">
              {t("universities.filters.group.institutionProfile")}
            </h2>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.institutionType")}
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      institution_type: event.target.value
                    }))
                  }
                  value={filters.institution_type}
                >
                  <option value="">{t("universities.filters.all")}</option>
                  <option value="public">{t("universities.institutionType.public")}</option>
                  <option value="private">{t("universities.institutionType.private")}</option>
                </select>
              </label>
            </div>
          </section>

          <section className="space-y-3 border-t pt-4">
            <h2 className="text-sm font-semibold">
              {t("universities.filters.group.academicRequirements")}
            </h2>
            <div className="grid gap-3 md:grid-cols-3">
              <label className="block">
                <span className="inline-flex items-center gap-1.5 text-sm font-semibold">
                  {t("universities.filters.ieltsAtMost")}
                  <HelpTooltip label={t("universities.filters.ieltsAtMostHelp")} />
                </span>
                <input
                  className={fieldClassName}
                  inputMode="decimal"
                  max={9}
                  min={4}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      ielts_minimum__lte: event.target.value
                    }))
                  }
                  step={0.5}
                  type="number"
                  value={filters.ielts_minimum__lte}
                />
              </label>
              <div className="block">
                <span className="inline-flex items-center gap-1.5 text-sm font-semibold">
                  {t("universities.filters.satRange")}
                  <HelpTooltip label={t("universities.filters.satRangeHelp")} />
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    aria-label={t("universities.filters.satFrom")}
                    className={fieldClassName}
                    inputMode="numeric"
                    max={1600}
                    min={400}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        sat_average__gte: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.satFrom")}
                    step={10}
                    type="number"
                    value={filters.sat_average__gte}
                  />
                  <input
                    aria-label={t("universities.filters.satTo")}
                    className={fieldClassName}
                    inputMode="numeric"
                    max={1600}
                    min={400}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        sat_average__lte: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.satTo")}
                    step={10}
                    type="number"
                    value={filters.sat_average__lte}
                  />
                </div>
              </div>
              <label className="block">
                <span className="inline-flex items-center gap-1.5 text-sm font-semibold">
                  {t("universities.filters.gpaAtMost")}
                  <HelpTooltip label={t("universities.filters.gpaAtMostHelp")} />
                </span>
                <input
                  className={fieldClassName}
                  inputMode="decimal"
                  max={4}
                  min={0}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      gpa_average__lte: event.target.value
                    }))
                  }
                  step={0.1}
                  type="number"
                  value={filters.gpa_average__lte}
                />
              </label>
            </div>
          </section>

          <section className="space-y-3 border-t pt-4">
            <h2 className="text-sm font-semibold">
              {t("universities.filters.group.programsMajors")}
            </h2>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.majorCluster")}
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      major_cluster: event.target.value
                    }))
                  }
                  value={filters.major_cluster}
                >
                  <option value="">{t("universities.filters.all")}</option>
                  {(filterOptions?.major_clusters ?? []).map((cluster) => (
                    <option key={cluster} value={cluster}>
                      {t(`universities.majorCluster.${cluster}` as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.programSearch")}
                </span>
                <AutocompleteInput
                  label={t("universities.filters.programSearch")}
                  onChange={(value) =>
                    setFilters((current) => ({ ...current, program_search: value }))
                  }
                  options={filterOptions?.program_names ?? []}
                  placeholder={t("universities.filters.programSearchPlaceholder")}
                  value={filters.program_search}
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.subjectArea")}
                </span>
                <AutocompleteInput
                  label={t("universities.filters.subjectArea")}
                  onChange={(value) =>
                    setFilters((current) => ({ ...current, subject_area: value }))
                  }
                  options={filterOptions?.subject_areas ?? []}
                  placeholder={t("universities.filters.subjectAreaPlaceholder")}
                  value={filters.subject_area}
                />
              </label>
              {(["portfolio_required", "research_heavy", "stem_heavy", "interdisciplinary"] as const).map(
                (key) => (
                  <label
                    className="flex min-h-10 items-center gap-2 rounded-sm border bg-surface px-3 py-2"
                    key={key}
                  >
                    <input
                      checked={filters[key] === "true"}
                      className="size-4 shrink-0"
                      onChange={(event) =>
                        setFilters((current) => ({
                          ...current,
                          [key]: event.target.checked ? "true" : ""
                        }))
                      }
                      type="checkbox"
                    />
                    <span className="text-sm font-semibold">
                      {t(`universities.filters.${key}` as TranslationKey)}
                    </span>
                  </label>
                )
              )}
            </div>
          </section>

          <section className="space-y-3 border-t pt-4">
            <h2 className="text-sm font-semibold">
              {t("universities.filters.group.rankings")}
            </h2>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.rankingSource")}
                </span>
                <AutocompleteInput
                  label={t("universities.filters.rankingSource")}
                  onChange={(value) =>
                    setFilters((current) => ({ ...current, ranking_source: value }))
                  }
                  options={filterOptions?.ranking_sources ?? []}
                  placeholder={t("universities.filters.rankingSourcePlaceholder")}
                  value={filters.ranking_source}
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.hasSubjectRanking")}
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      has_subject_ranking: event.target.value
                    }))
                  }
                  value={filters.has_subject_ranking}
                >
                  <option value="">{t("universities.filters.all")}</option>
                  <option value="true">{t("universities.filters.hasSubjectRankingYes")}</option>
                  <option value="false">{t("universities.filters.hasSubjectRankingNo")}</option>
                </select>
              </label>
              <div className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.subjectRankRange")}
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    aria-label={t("universities.filters.rankFrom")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        subject_rank_min: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankFrom")}
                    type="number"
                    value={filters.subject_rank_min}
                  />
                  <input
                    aria-label={t("universities.filters.rankTo")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        subject_rank_max: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankTo")}
                    type="number"
                    value={filters.subject_rank_max}
                  />
                </div>
              </div>
              <div className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.globalRankRange")}
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    aria-label={t("universities.filters.rankFrom")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        global_rank_min: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankFrom")}
                    type="number"
                    value={filters.global_rank_min}
                  />
                  <input
                    aria-label={t("universities.filters.rankTo")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        global_rank_max: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankTo")}
                    type="number"
                    value={filters.global_rank_max}
                  />
                </div>
              </div>
              <div className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.qsRankRange")}
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    aria-label={t("universities.filters.rankFrom")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        qs_ranking_min: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankFrom")}
                    type="number"
                    value={filters.qs_ranking_min}
                  />
                  <input
                    aria-label={t("universities.filters.rankTo")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        qs_ranking_max: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankTo")}
                    type="number"
                    value={filters.qs_ranking_max}
                  />
                </div>
              </div>
              <div className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.theRankRange")}
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    aria-label={t("universities.filters.rankFrom")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        the_rank_min: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankFrom")}
                    type="number"
                    value={filters.the_rank_min}
                  />
                  <input
                    aria-label={t("universities.filters.rankTo")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        the_rank_max: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankTo")}
                    type="number"
                    value={filters.the_rank_max}
                  />
                </div>
              </div>
              <div className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.nationalRankRange")}
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    aria-label={t("universities.filters.rankFrom")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        national_rank_min: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankFrom")}
                    type="number"
                    value={filters.national_rank_min}
                  />
                  <input
                    aria-label={t("universities.filters.rankTo")}
                    className={fieldClassName}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        national_rank_max: event.target.value
                      }))
                    }
                    placeholder={t("universities.filters.rankTo")}
                    type="number"
                    value={filters.national_rank_max}
                  />
                </div>
              </div>
            </div>
          </section>

          <section className="space-y-3 border-t pt-4">
            <h2 className="text-sm font-semibold">
              {t("universities.filters.group.costScholarships")}
            </h2>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <label className="flex min-h-10 items-center gap-2 rounded-sm border bg-surface px-3 py-2">
                <input
                  checked={filters.scholarship_available === "true"}
                  className="size-4 shrink-0"
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      scholarship_available: event.target.checked ? "true" : ""
                    }))
                  }
                  type="checkbox"
                />
                <span className="text-sm font-semibold">
                  {t("universities.filters.scholarshipAvailable")}
                </span>
              </label>
              <label className="block">
                <span className="flex items-center gap-1 text-sm font-semibold">
                  {t("universities.filters.costStatus")}
                  <HelpTooltip label={t("help.budgetComparison")} />
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      cost_status: event.target.value as UniversityFilters["cost_status"]
                    }))
                  }
                  value={filters.cost_status ?? ""}
                >
                  <option value="">{t("universities.filters.costStatusAny")}</option>
                  <option value="within_budget">{t("universities.cost.budgetStatus.within_budget")}</option>
                  <option value="above_budget">{t("universities.cost.budgetStatus.above_budget")}</option>
                  <option value="needs_aid">{t("universities.cost.budgetStatus.needs_aid")}</option>
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.costConfidence")}
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      currency_conversion_confidence: event.target.value
                    }))
                  }
                  value={filters.currency_conversion_confidence ?? ""}
                >
                  <option value="">{t("universities.filters.costConfidenceAny")}</option>
                  <option value="high">{t("universities.fit.confidence.high")}</option>
                  <option value="medium">{t("universities.fit.confidence.medium")}</option>
                  <option value="low">{t("universities.fit.confidence.low")}</option>
                </select>
              </label>
            </div>
            <p className="text-xs italic text-muted-foreground">
              {t("universities.cost.disclaimer")}
            </p>
          </section>

          <section className="space-y-3 border-t pt-4">
            <h2 className="text-sm font-semibold">
              {t("universities.filters.group.verificationDataQuality")}
            </h2>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.verificationStatus")}
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      verification_status: event.target.value
                    }))
                  }
                  value={filters.verification_status}
                >
                  <option value="">{t("universities.filters.verificationAny")}</option>
                  <option value="verified">{t("universities.filters.verificationVerified")}</option>
                  <option value="partial">{t("universities.filters.verificationPartial")}</option>
                  <option value="estimated">{t("universities.filters.verificationEstimated")}</option>
                </select>
              </label>
              <label className="flex min-h-10 items-center gap-2 rounded-sm border bg-surface px-3 py-2 md:self-end">
                <input
                  checked={filters.include_demo === "true"}
                  className="size-4 shrink-0"
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      include_demo: event.target.checked ? "true" : ""
                    }))
                  }
                  type="checkbox"
                />
                <span className="text-sm font-semibold">
                  {t("universities.filters.includeDemo")}
                </span>
              </label>
              <label className="block">
                <span className="text-sm font-semibold">
                  {t("universities.filters.sourceConfidence")}
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      source_confidence: event.target.value
                    }))
                  }
                  value={filters.source_confidence}
                >
                  <option value="">{t("universities.filters.sourceConfidenceAny")}</option>
                  <option value="verified">{t("universities.verification.status.verified")}</option>
                  <option value="partial">{t("universities.verification.status.partial")}</option>
                  <option value="estimated">{t("universities.verification.status.estimated")}</option>
                </select>
              </label>
            </div>
          </section>

          <section className="space-y-3 border-t pt-4">
            <h2 className="text-sm font-semibold">
              {t("universities.filters.group.sortActions")}
            </h2>
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
              <label className="block">
                <span className="text-sm font-semibold">{t("universities.filters.sort")}</span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({ ...current, ordering: event.target.value }))
                  }
                  value={filters.ordering}
                >
                  <option value="">{t("universities.filters.defaultSort")}</option>
                  <option value="tuition_usd_amount">{t("universities.filters.tuitionUsdLowHigh")}</option>
                  <option value="-tuition_usd_amount">{t("universities.filters.tuitionUsdHighLow")}</option>
                  <option value="total_cost_usd_amount">{t("universities.filters.totalUsdLowHigh")}</option>
                  <option value="-total_cost_usd_amount">{t("universities.filters.totalUsdHighLow")}</option>
                  <option value="qs_ranking">{t("universities.filters.qsHighLow")}</option>
                  <option value="-qs_ranking">{t("universities.filters.qsLowHigh")}</option>
                  <option value="global_rank">{t("universities.filters.globalHighLow")}</option>
                  <option value="-global_rank">{t("universities.filters.globalLowHigh")}</option>
                  <option value="the_rank">{t("universities.filters.theHighLow")}</option>
                  <option value="-the_rank">{t("universities.filters.theLowHigh")}</option>
                  <option value="national_rank">{t("universities.filters.nationalHighLow")}</option>
                  <option value="-national_rank">{t("universities.filters.nationalLowHigh")}</option>
                  <option value="acceptance_rate">{t("universities.filters.mostSelective")}</option>
                  <option value="-acceptance_rate">{t("universities.filters.leastSelective")}</option>
                </select>
              </label>
              <div className="flex flex-wrap gap-3">
                <Button type="submit">{t("universities.actions.applyFilters")}</Button>
                <Button onClick={clearFilters} type="button" variant="ghost">
                  {t("universities.actions.clearFilters")}
                </Button>
              </div>
            </div>
          </section>
        </form>
      </Card>

      {isLoading ? (
        <LoadingNotice message={t("universities.states.loading")} />
      ) : hasError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("universities.states.loadError")}
          </p>
          <Button className="mt-4" onClick={() => void loadUniversities()} type="button">
            {t("universities.actions.retry")}
          </Button>
        </Card>
      ) : visibleUniversities.length === 0 ? (
        <Card>
          <h2 className="text-xl font-semibold">{t("universities.states.emptyTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {shortlistOnly
              ? t("universities.states.emptyShortlist")
              : t("universities.states.emptyDescription")}
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          <p className="text-sm font-semibold text-muted-foreground">
            {t("universities.list.total", {
              count: shortlistOnly ? visibleUniversities.length : totalCount
            })}
          </p>
          <PaginatedGrid
            currentPage={currentPage}
            getItemKey={(university) => university.id}
            items={visibleUniversities}
            onPageChange={setCurrentPage}
            pageSize={DEFAULT_PAGE_SIZE}
            totalCount={shortlistOnly ? visibleUniversities.length : totalCount}
            totalPages={shortlistOnly ? 1 : totalPages}
            renderItem={(university) => (
              <UniversityCard
                canSelectCompare={compareIds.length < MAX_COMPARE}
                isCompareSelected={compareIds.includes(university.id)}
                isShortlistPending={pendingShortlistId === university.id}
                key={university.id}
                onToggleCompare={toggleCompare}
                onToggleShortlist={(item) => void toggleShortlist(item)}
                university={university}
              />
            )}
          />
        </div>
      )}

      <p className="text-xs leading-5 text-muted-foreground">{t("universities.disclaimer")}</p>
    </div>
  );
}
