"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { useI18n } from "@/shared/i18n";

import { Button } from "./button";

export const DEFAULT_PAGE_SIZE = 21;

export type PaginationControlsProps = {
  currentPage: number;
  totalPages: number;
  onPrevious?: () => void;
  onNext?: () => void;
  onPageSelect?: (page: number) => void;
  isLoading?: boolean;
  disabled?: boolean;
};

export function PaginationControls({
  currentPage,
  totalPages,
  onPrevious,
  onNext,
  onPageSelect,
  isLoading = false,
  disabled = false
}: PaginationControlsProps) {
  const { t } = useI18n();
  const safeTotalPages = Math.max(totalPages, 1);
  const safeCurrentPage = Math.min(Math.max(currentPage, 1), safeTotalPages);
  const canGoPrevious = safeCurrentPage > 1 && !disabled && !isLoading;
  const canGoNext = safeCurrentPage < safeTotalPages && !disabled && !isLoading;
  const pages = getVisiblePages(safeCurrentPage, safeTotalPages);

  return (
    <nav
      aria-label={t("pagination.navigation")}
      className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm font-semibold text-muted-foreground">
        {t("pagination.pageOf", {
          page: safeCurrentPage,
          total: safeTotalPages
        })}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          disabled={!canGoPrevious}
          onClick={onPrevious}
          size="sm"
          type="button"
          variant="secondary"
        >
          <ChevronLeft aria-hidden className="mr-1.5 size-3.5" />
          {t("pagination.previous")}
        </Button>
        {onPageSelect && safeTotalPages <= 7 ? (
          <div className="flex flex-wrap gap-1">
            {pages.map((page) => (
              <Button
                aria-label={t("pagination.goToPage", { page })}
                disabled={disabled || isLoading}
                key={page}
                onClick={() => onPageSelect(page)}
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
          onClick={onNext}
          size="sm"
          type="button"
          variant="secondary"
        >
          {t("pagination.next")}
          <ChevronRight aria-hidden className="ml-1.5 size-3.5" />
        </Button>
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
  itemsPerPage?: number;
  totalCount?: number;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
  emptyState?: ReactNode;
  className?: string;
};

export function PaginatedGrid<Item>({
  items,
  renderItem,
  getItemKey,
  columnsDesktop = 3,
  rowsDesktop = 7,
  itemsPerPage = columnsDesktop * rowsDesktop,
  totalCount,
  currentPage,
  totalPages,
  onPageChange,
  isLoading = false,
  emptyState,
  className = ""
}: PaginatedGridProps<Item>) {
  const { t } = useI18n();
  const count = totalCount ?? items.length;

  if (!isLoading && items.length === 0) {
    return <>{emptyState ?? <DefaultEmptyState />}</>;
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <PaginationSummary
        currentPage={currentPage}
        itemsOnPage={items.length}
        itemsPerPage={itemsPerPage}
        totalCount={count}
      />
      <section
        aria-label={t("pagination.items")}
        className="grid gap-5 md:grid-cols-2 xl:grid-cols-3"
      >
        {items.map((item, index) => (
          <div key={getItemKey?.(item, index) ?? index}>{renderItem(item)}</div>
        ))}
      </section>
      {totalPages > 1 ? (
        <PaginationControls
          currentPage={currentPage}
          disabled={isLoading}
          isLoading={isLoading}
          onNext={() => onPageChange(currentPage + 1)}
          onPageSelect={onPageChange}
          onPrevious={() => onPageChange(currentPage - 1)}
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
  itemsPerPage = DEFAULT_PAGE_SIZE,
  totalCount,
  currentPage,
  totalPages,
  onPageChange,
  isLoading = false,
  emptyState,
  className = ""
}: PaginatedListProps<Item>) {
  const count = totalCount ?? items.length;

  if (!isLoading && items.length === 0) {
    return <>{emptyState ?? <DefaultEmptyState />}</>;
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <PaginationSummary
        currentPage={currentPage}
        itemsOnPage={items.length}
        itemsPerPage={itemsPerPage}
        totalCount={count}
      />
      <div className="space-y-3">
        {items.map((item, index) => (
          <div key={getItemKey?.(item, index) ?? index}>{renderItem(item)}</div>
        ))}
      </div>
      {totalPages > 1 ? (
        <PaginationControls
          currentPage={currentPage}
          disabled={isLoading}
          isLoading={isLoading}
          onNext={() => onPageChange(currentPage + 1)}
          onPageSelect={onPageChange}
          onPrevious={() => onPageChange(currentPage - 1)}
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
