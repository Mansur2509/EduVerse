"use client";

import { useCallback, useEffect, useState } from "react";
import { Flag, ShieldCheck, UserCog } from "lucide-react";

import type { ReportStatus, ReportTargetType, UserReport } from "@/entities/admin-moderation";
import { REPORT_STATUSES, REPORT_TARGET_TYPES } from "@/entities/admin-moderation";
import { getAdminReportsRequest, updateAdminReportRequest } from "@/features/admin-moderation";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { CollapsibleFilterPanel } from "@/shared/ui/collapsible-filter-panel";
import { fieldClassName } from "@/shared/ui/field";
import { DEFAULT_PAGE_SIZE, PaginationControls } from "@/shared/ui/pagination";
import { SectionTabs } from "@/shared/ui/section-tabs";

const STATUS_STYLES: Record<ReportStatus, string> = {
  open: "border-warning/35 bg-warning/10 text-warning",
  reviewing: "border-accent/35 bg-accent/10 text-accent",
  resolved: "border-success/35 bg-success/10 text-success",
  dismissed: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

function badgeClass(base: string) {
  return `inline-flex items-center rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${base}`;
}

export function AdminReportsScreen() {
  const { locale, t } = useI18n();
  const [reports, setReports] = useState<UserReport[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [actionErrorId, setActionErrorId] = useState<number | null>(null);

  const [statusFilter, setStatusFilter] = useState<ReportStatus | "">("");
  const [targetTypeFilter, setTargetTypeFilter] = useState<ReportTargetType | "">("");
  const [appliedFilters, setAppliedFilters] = useState<{
    status: ReportStatus | "";
    target_type: ReportTargetType | "";
  }>({ status: "", target_type: "" });

  const loadReports = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getAdminReportsRequest({
        page: currentPage,
        page_size: DEFAULT_PAGE_SIZE,
        ...appliedFilters
      });
      setReports(response.results);
      setTotalCount(response.count);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, appliedFilters]);

  useEffect(() => {
    void loadReports();
  }, [loadReports]);

  function applyFilters() {
    setCurrentPage(1);
    setAppliedFilters({ status: statusFilter, target_type: targetTypeFilter });
  }

  function resetFilters() {
    setStatusFilter("");
    setTargetTypeFilter("");
    setCurrentPage(1);
    setAppliedFilters({ status: "", target_type: "" });
  }

  async function updateStatus(report: UserReport, nextStatus: ReportStatus) {
    setSavingId(report.id);
    setActionErrorId(null);
    try {
      const updated = await updateAdminReportRequest(report.id, { status: nextStatus });
      setReports((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch {
      setActionErrorId(report.id);
    } finally {
      setSavingId(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / DEFAULT_PAGE_SIZE));
  const activeFilterCount = Object.values(appliedFilters).filter(Boolean).length;

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-eyebrow text-primary-hover">
          {t("adminReports.eyebrow")}
        </p>
        <h1 className="text-display mt-2">{t("adminReports.title")}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          {t("adminReports.description")}
        </p>
      </section>

      <SectionTabs
        ariaLabel={t("adminModeration.tabs.ariaLabel")}
        items={[
          {
            href: "/admin/moderation",
            icon: ShieldCheck,
            label: t("adminModeration.tabs.universities")
          },
          { href: "/admin/reports", icon: Flag, label: t("adminModeration.tabs.reports") },
          {
            href: "/admin/organizers",
            icon: UserCog,
            label: t("adminModeration.tabs.organizers")
          }
        ]}
      />

      <CollapsibleFilterPanel
        activeCount={activeFilterCount}
        onClear={resetFilters}
        resultCount={totalCount}
        storageKey="uniway.filters.adminReports"
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-semibold">{t("adminReports.filters.status")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setStatusFilter(event.target.value as ReportStatus | "")}
              value={statusFilter}
            >
              <option value="">{t("applications.filters.all")}</option>
              {REPORT_STATUSES.map((option) => (
                <option key={option} value={option}>
                  {t(`adminReports.status.${option}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("adminReports.filters.targetType")}</span>
            <select
              className={fieldClassName}
              onChange={(event) =>
                setTargetTypeFilter(event.target.value as ReportTargetType | "")
              }
              value={targetTypeFilter}
            >
              <option value="">{t("applications.filters.all")}</option>
              {REPORT_TARGET_TYPES.map((option) => (
                <option key={option} value={option}>
                  {t(`adminReports.targetType.${option}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="mt-3 flex justify-end gap-2 border-t pt-3">
          <Button onClick={applyFilters} size="sm" type="button">
            {t("adminFeedback.filters.apply")}
          </Button>
        </div>
      </CollapsibleFilterPanel>

      {isLoading ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("adminReports.states.loading")}</p>
        </Card>
      ) : hasError ? (
        <Card>
          <p className="text-sm text-danger" role="alert">
            {t("adminReports.states.loadError")}
          </p>
          <Button className="mt-4" onClick={() => void loadReports()} type="button">
            {t("essays.actions.retry")}
          </Button>
        </Card>
      ) : reports.length === 0 ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("adminReports.states.empty")}</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => (
            <Card key={report.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={badgeClass(STATUS_STYLES[report.status])}>
                      {t(`adminReports.status.${report.status}` as TranslationKey)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {t(`adminReports.targetType.${report.target_type}` as TranslationKey)} #
                      {report.target_id}
                    </span>
                  </div>
                  <p className="mt-2 font-semibold">{report.reason}</p>
                  {report.description ? (
                    <p className="mt-1 text-sm text-muted-foreground">{report.description}</p>
                  ) : null}
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatDateTime(report.created_at, locale)}
                    {report.reporter_email ? ` · ${report.reporter_email}` : ""}
                  </p>
                </div>
                <select
                  aria-label={t("adminReports.filters.status")}
                  className={fieldClassName}
                  disabled={savingId === report.id}
                  onChange={(event) =>
                    void updateStatus(report, event.target.value as ReportStatus)
                  }
                  value={report.status}
                >
                  {REPORT_STATUSES.map((option) => (
                    <option key={option} value={option}>
                      {t(`adminReports.status.${option}` as TranslationKey)}
                    </option>
                  ))}
                </select>
              </div>
              {actionErrorId === report.id ? (
                <p className="mt-2 text-xs text-danger" role="alert">
                  {t("adminReports.states.actionError")}
                </p>
              ) : null}
            </Card>
          ))}
          {totalPages > 1 ? (
            <PaginationControls
              currentPage={currentPage}
              itemsOnPage={reports.length}
              onPageChange={setCurrentPage}
              pageSize={DEFAULT_PAGE_SIZE}
              totalCount={totalCount}
              totalPages={totalPages}
            />
          ) : null}
        </div>
      )}
    </div>
  );
}
