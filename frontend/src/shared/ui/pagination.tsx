"use client";

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import type { ReactNode } from "react";

import { useI18n } from "@/shared/i18n";

import { Button } from "./button";
import { SkeletonCards, SkeletonRows } from "./skeleton";

export const DEFAULT_PAGE_SIZE = 21;

export type PaginationControlsProps = {
  currentPage: number;
  totalPages: number;
  totalCount?: number;
  pageSize?: number;
  itemsOnPage?: number;
  onPageChange?: (page: number) => void;
  onPrevious?: () => void;
  onNext?: () => void;
  onPageSelect?: (page: number) => void;
  isLoading?: boolean;
  disabled?: boolean;
};

export function PaginationControls({
  currentPage,
  totalPages,
  totalCount,
  pageSize = DEFAULT_PAGE_SIZE,
  itemsOnPage,
  onPageChange,
  onPrevious,
  onNext,
  onPageSelect,
  isLoading = false,
  disabled = false
}: PaginationControlsProps) {
  const { t } = useI18n();
  const safeTotalPages = Math.max(totalPages, 1);
  const safeCurrentPage = Math.min(Math.max(currentPage, 1), safeTotalPages);
  const pages = getVisiblePages(safeCurrentPage, safeTotalPages);
  const selectPage = onPageChange ?? onPageSelect;
  const canMovePrevious = Boolean(onPrevious || selectPage);
  const canMoveNext = Boolean(onNext || selectPage);
  const canGoPrevious = safeCurrentPage > 1 && canMovePrevious && !disabled && !isLoading;
  const canGoNext = safeCurrentPage < safeTotalPages && canMoveNext && !disabled && !isLoading;
  const goToPage = (page: number) => {
    const nextPage = Math.min(Math.max(page, 1), safeTotalPages);
    selectPage?.(nextPage);
  };
  const handlePrevious = onPrevious ?? (() => goToPage(safeCurrentPage - 1));
  const handleNext = onNext ?? (() => goToPage(safeCurrentPage + 1));

  return (
    <nav
      aria-label={t("pagination.navigation")}
      className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="space-y-1">
        <p className="text-sm font-semibold text-muted-foreground">
          {t("pagination.pageOf", {
            page: safeCurrentPage,
            total: safeTotalPages
          })}
        </p>
        {typeof totalCount === "number" ? (
          <PaginationSummary
            currentPage={safeCurrentPage}
            itemsOnPage={itemsOnPage ?? pageSize}
            itemsPerPage={pageSize}
            totalCount={totalCount}
          />
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {selectPage && safeTotalPages > 1 ? (
          <Button
            aria-label={t("pagination.firstPage")}
            disabled={!canGoPrevious}
            onClick={() => goToPage(1)}
            size="sm"
            type="button"
            variant="ghost"
          >
            <ChevronsLeft aria-hidden className="size-3.5 sm:mr-1.5" />
            <span className="hidden sm:inline">{t("pagination.firstPage")}</span>
          </Button>
        ) : null}
        <Button
          disabled={!canGoPrevious}
          onClick={handlePrevious}
          size="sm"
          type="button"
          variant="secondary"
        >
          <ChevronLeft aria-hidden className="mr-1.5 size-3.5" />
          {t("pagination.previous")}
        </Button>
        {selectPage && safeTotalPages <= 7 ? (
          <div className="flex flex-wrap gap-1">
            {pages.map((page) => (
              <Button
                aria-label={t("pagination.goToPage", { page })}
                disabled={disabled || isLoading}
                key={page}
                onClick={() => goToPage(page)}
                size="sm"
                type="button"
                variant={page === safeCurrentPage ? "primary" : "ghost"}
              >
                {page}
              </Button>
            ))}
          </div>
        ) : null}
        <Button
          disabled={!canGoNext}
          onClick={handleNext}
          size="sm"
          type="button"
          variant="secondary"
        >
          {t("pagination.next")}
          <ChevronRight aria-hidden className="ml-1.5 size-3.5" />
        </Button>
        {selectPage && safeTotalPages > 1 ? (
          <Button
            aria-label={t("pagination.lastPage")}
            disabled={!canGoNext}
            onClick={() => goToPage(safeTotalPages)}
            size="sm"
            type="button"
            variant="ghost"
          >
            <span className="hidden sm:inline">{t("pagination.lastPage")}</span>
            <ChevronsRight aria-hidden className="size-3.5 sm:ml-1.5" />
          </Button>
        ) : null}
      </div>
    </nav>
  );
}

export type PaginatedGridProps<Item> = {
  items: Item[];
  renderItem: (item: Item) => ReactNode;
  getItemKey?: (item: Item, index: number) => string | number;
  columnsDesktop?: number;
  rowsDesktop?: number;
  pageSize?: number;
  itemsPerPage?: number;
  totalCount?: number;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
  emptyState?: ReactNode;
  loadingState?: ReactNode;
  className?: string;
};

export function PaginatedGrid<Item>({
  items,
  renderItem,
  getItemKey,
  columnsDesktop = 3,
  rowsDesktop = 7,
  pageSize,
  itemsPerPage,
  totalCount,
  currentPage,
  totalPages,
  onPageChange,
  isLoading = false,
  emptyState,
  loadingState,
  className = ""
}: PaginatedGridProps<Item>) {
  const { t } = useI18n();
  const resolvedPageSize = pageSize ?? itemsPerPage ?? columnsDesktop * rowsDesktop;
  const count = totalCount ?? items.length;

  if (isLoading && loadingState) {
    return <>{loadingState}</>;
  }

  if (!isLoading && items.length === 0) {
    return <>{emptyState ?? <DefaultEmptyState />}</>;
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {totalPages <= 1 ? (
        <PaginationSummary
          currentPage={currentPage}
          itemsOnPage={items.length}
          itemsPerPage={resolvedPageSize}
          totalCount={count}
        />
      ) : null}
      <section
        aria-label={t("pagination.items")}
        className={`grid gap-5 ${getGridColumnClass(columnsDesktop)}`}
      >
        {isLoading && items.length === 0 ? (
          <SkeletonCards count={Math.min(resolvedPageSize, 6)} />
        ) : (
          items.map((item, index) => (
            <div key={getItemKey?.(item, index) ?? index}>{renderItem(item)}</div>
          ))
        )}
      </section>
      {totalPages > 1 ? (
        <PaginationControls
          currentPage={currentPage}
          disabled={isLoading}
          itemsOnPage={items.length}
          isLoading={isLoading}
          onPageChange={onPageChange}
          pageSize={resolvedPageSize}
          totalCount={count}
          totalPages={totalPages}
        />
      ) : null}
    </div>
  );
}

export type PaginatedListProps<Item> = Omit<
  PaginatedGridProps<Item>,
  "columnsDesktop" | "rowsDesktop"
>;

export function PaginatedList<Item>({
  items,
  renderItem,
  getItemKey,
  pageSize,
  itemsPerPage,
  totalCount,
  currentPage,
  totalPages,
  onPageChange,
  isLoading = false,
  emptyState,
  loadingState,
  className = ""
}: PaginatedListProps<Item>) {
  const resolvedPageSize = pageSize ?? itemsPerPage ?? DEFAULT_PAGE_SIZE;
  const count = totalCount ?? items.length;

  if (isLoading && loadingState) {
    return <>{loadingState}</>;
  }

  if (!isLoading && items.length === 0) {
    return <>{emptyState ?? <DefaultEmptyState />}</>;
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {totalPages <= 1 ? (
        <PaginationSummary
          currentPage={currentPage}
          itemsOnPage={items.length}
          itemsPerPage={resolvedPageSize}
          totalCount={count}
        />
      ) : null}
      <div className="space-y-3">
        {isLoading && items.length === 0 ? (
          <SkeletonRows count={Math.min(resolvedPageSize, 6)} />
        ) : (
          items.map((item, index) => (
            <div key={getItemKey?.(item, index) ?? index}>{renderItem(item)}</div>
          ))
        )}
      </div>
      {totalPages > 1 ? (
        <PaginationControls
          currentPage={currentPage}
          disabled={isLoading}
          itemsOnPage={items.length}
          isLoading={isLoading}
          onPageChange={onPageChange}
          pageSize={resolvedPageSize}
          totalCount={count}
          totalPages={totalPages}
        />
      ) : null}
    </div>
  );
}

function PaginationSummary({
  currentPage,
  itemsOnPage,
  itemsPerPage,
  totalCount
}: {
  currentPage: number;
  itemsOnPage: number;
  itemsPerPage: number;
  totalCount: number;
}) {
  const { t } = useI18n();
  if (totalCount <= 0) return null;

  const start = (currentPage - 1) * itemsPerPage + 1;
  const end = Math.min(start + Math.max(itemsOnPage, 1) - 1, totalCount);

  return (
    <p className="text-sm font-semibold text-muted-foreground">
      {t("pagination.showingRange", {
        start,
        end,
        total: totalCount
      })}
    </p>
  );
}

function DefaultEmptyState() {
  const { t } = useI18n();
  return (
    <div className="rounded-sm border bg-card p-5">
      <h2 className="text-lg font-semibold">{t("pagination.noResults")}</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {t("pagination.tryChangingFilters")}
      </p>
    </div>
  );
}

function getVisiblePages(currentPage: number, totalPages: number) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_item, index) => index + 1);
  }
  const start = Math.max(1, Math.min(currentPage - 3, totalPages - 6));
  return Array.from({ length: 7 }, (_item, index) => start + index);
}

function getGridColumnClass(columnsDesktop: number) {
  if (columnsDesktop <= 1) return "md:grid-cols-1";
  if (columnsDesktop === 2) return "md:grid-cols-2";
  if (columnsDesktop === 4) return "md:grid-cols-2 xl:grid-cols-4";
  return "md:grid-cols-2 xl:grid-cols-3";
}
