"use client";

import { Scale, Search, Star } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { UniversityCard, type UniversityDetails, type UniversityFilters } from "@/entities/university";
import { getUniversitiesRequest, addToShortlistRequest, removeFromShortlistRequest } from "@/features/universities";
import { useI18n } from "@/shared/i18n";
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
  gpa_average__lte: ""
};

const MAX_COMPARE = 4;
const MIN_COMPARE = 2;

export function UniversitiesScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const [filters, setFilters] = useState<UniversityFilters>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<UniversityFilters>(emptyFilters);
  const [universities, setUniversities] = useState<UniversityDetails[]>([]);
  const [totalCount, setTotalCount] = useState(0);
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
        <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" onSubmit={handleSubmit}>
          <label className="block">
            <span className="text-sm font-semibold">{t("universities.filters.search")}</span>
            <div className="relative">
              <Search
                aria-hidden
                className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              />
              <input
                className={`${fieldClassName} pl-10`}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, search: event.target.value }))
                }
                placeholder={t("universities.filters.searchPlaceholder")}
                value={filters.search}
              />
            </div>
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t("universities.filters.country")}</span>
            <input
              className={fieldClassName}
              onChange={(event) =>
                setFilters((current) => ({ ...current, country: event.target.value }))
              }
              placeholder={t("universities.filters.countryPlaceholder")}
              value={filters.country}
            />
          </label>
          <label className="block">
            <span className="text-sm font-semibold">{t("universities.filters.city")}</span>
            <input
              className={fieldClassName}
              onChange={(event) =>
                setFilters((current) => ({ ...current, city: event.target.value }))
              }
              placeholder={t("universities.filters.cityPlaceholder")}
              value={filters.city}
            />
          </label>
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
          <label className="flex items-center gap-2 self-end pb-2.5">
            <input
              checked={filters.scholarship_available === "true"}
              className="size-4"
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
          <label className="flex items-center gap-2 self-end pb-2.5">
            <input
              checked={filters.include_demo === "true"}
              className="size-4"
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
            <div className="flex gap-2">
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
              <option value="acceptance_rate">{t("universities.filters.mostSelective")}</option>
              <option value="-acceptance_rate">{t("universities.filters.leastSelective")}</option>
            </select>
          </label>
          <div className="flex flex-wrap gap-3 md:col-span-2 xl:col-span-3">
            <Button type="submit">{t("universities.actions.applyFilters")}</Button>
            <Button onClick={clearFilters} type="button" variant="ghost">
              {t("universities.actions.clearFilters")}
            </Button>
          </div>
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
