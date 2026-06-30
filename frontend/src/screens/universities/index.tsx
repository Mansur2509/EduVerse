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
import { LoadingNotice } from "@/shared/ui/loading-notice";
import { DEFAULT_PAGE_SIZE, PaginatedGrid } from "@/shared/ui/pagination";

const emptyFilters: UniversityFilters = {
  search: "",
  country: "",
  institution_type: "",
  scholarship_available: "",
  include_demo: "",
  ordering: ""
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
        <PaginatedGrid
          currentPage={currentPage}
          getItemKey={(university) => university.id}
          items={visibleUniversities}
          onPageChange={setCurrentPage}
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
      )}

      <p className="text-xs leading-5 text-muted-foreground">{t("universities.disclaimer")}</p>
    </div>
  );
}
