"use client";

import { useCallback, useEffect, useState } from "react";

import type {
  FeedbackPriority,
  FeedbackReport,
  FeedbackStatus,
  FeedbackType
} from "@/entities/feedback";
import { FEEDBACK_PRIORITIES, FEEDBACK_STATUSES } from "@/entities/feedback";
import { getAdminFeedbackListRequest, updateAdminFeedbackRequest } from "@/features/feedback";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { DEFAULT_PAGE_SIZE, PaginationControls } from "@/shared/ui/pagination";

const FEEDBACK_TYPES: FeedbackType[] = ["issue", "idea", "confusing", "data"];

const STATUS_STYLES: Record<FeedbackStatus, string> = {
  new: "border-primary/35 bg-primary/10 text-primary",
  reviewed: "border-accent/35 bg-accent/10 text-accent",
  resolved: "border-success/35 bg-success/10 text-success",
  archived: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

const PRIORITY_STYLES: Record<FeedbackPriority, string> = {
  low: "border-muted-foreground/30 bg-surface text-muted-foreground",
  normal: "border-accent/35 bg-accent/10 text-accent",
  high: "border-warning/35 bg-warning/10 text-warning",
  critical: "border-danger/35 bg-danger/10 text-danger"
};

function badgeClass(base: string) {
  return `inline-flex items-center rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${base}`;
}

export function AdminFeedbackScreen() {
  const { locale, t } = useI18n();
  const [reports, setReports] = useState<FeedbackReport[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const [statusFilter, setStatusFilter] = useState<FeedbackStatus | "">("");
  const [typeFilter, setTypeFilter] = useState<FeedbackType | "">("");
  const [priorityFilter, setPriorityFilter] = useState<FeedbackPriority | "">("");
  const [pageModuleFilter, setPageModuleFilter] = useState("");
  const [appliedFilters, setAppliedFilters] = useState<{
    status: FeedbackStatus | "";
    feedback_type: FeedbackType | "";
    priority: FeedbackPriority | "";
    page_module: string;
  }>({ status: "", feedback_type: "", priority: "", page_module: "" });

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [notesDraft, setNotesDraft] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);
  const [actionErrorId, setActionErrorId] = useState<number | null>(null);

  const loadReports = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getAdminFeedbackListRequest({
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
    setAppliedFilters({
      status: statusFilter,
      feedback_type: typeFilter,
      priority: priorityFilter,
      page_module: pageModuleFilter.trim()
    });
  }

  function resetFilters() {
    setStatusFilter("");
    setTypeFilter("");
    setPriorityFilter("");
    setPageModuleFilter("");
    setCurrentPage(1);
    setAppliedFilters({ status: "", feedback_type: "", priority: "", page_module: "" });
  }

  function toggleExpanded(report: FeedbackReport) {
    if (expandedId === report.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(report.id);
    setNotesDraft(report.admin_notes);
    setActionErrorId(null);
  }

  async function updateReport(report: FeedbackReport, changes: Partial<FeedbackReport>) {
    setSavingId(report.id);
    setActionErrorId(null);
    try {
      const updated = await updateAdminFeedbackRequest(report.id, changes);
      setReports((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch {
      setActionErrorId(report.id);
    } finally {
      setSavingId(null);
    }
  }

  async function saveNotes(report: FeedbackReport) {
    await updateReport(report, { admin_notes: notesDraft });
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / DEFAULT_PAGE_SIZE));
  const hasActiveFilters =
    appliedFilters.status !== "" ||
    appliedFilters.feedback_type !== "" ||
    appliedFilters.priority !== "" ||
    appliedFilters.page_module !== "";

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("adminFeedback.eyebrow")}
        </p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">{t("adminFeedback.title")}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          {t("adminFeedback.description")}
        </p>
      </section>

      <Card>
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">{t("adminFeedback.filters.title")}</h2>
          {hasActiveFilters ? (
            <span className="rounded-sm border border-accent/30 bg-accent/10 px-2 py-0.5 text-[0.68rem] font-medium text-accent">
              {t("adminFeedback.filters.active")}
            </span>
          ) : null}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block">
            <span className="text-xs font-semibold">{t("adminFeedback.filters.status")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setStatusFilter(event.target.value as FeedbackStatus | "")}
              value={statusFilter}
            >
              <option value="">{t("applications.filters.all")}</option>
              {FEEDBACK_STATUSES.map((option) => (
                <option key={option} value={option}>
                  {t(`adminFeedback.status.${option}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("adminFeedback.filters.type")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setTypeFilter(event.target.value as FeedbackType | "")}
              value={typeFilter}
            >
              <option value="">{t("applications.filters.all")}</option>
              {FEEDBACK_TYPES.map((option) => (
                <option key={option} value={option}>
                  {t(`support.type.${option}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("adminFeedback.filters.priority")}</span>
            <select
              className={fieldClassName}
              onChange={(event) => setPriorityFilter(event.target.value as FeedbackPriority | "")}
              value={priorityFilter}
            >
              <option value="">{t("applications.filters.all")}</option>
              {FEEDBACK_PRIORITIES.map((option) => (
                <option key={option} value={option}>
                  {t(`adminFeedback.priority.${option}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("adminFeedback.filters.page")}</span>
            <input
              className={fieldClassName}
              onChange={(event) => setPageModuleFilter(event.target.value)}
              placeholder={t("adminFeedback.filters.pagePlaceholder")}
              value={pageModuleFilter}
            />
          </label>
        </div>
        <div className="mt-3 flex justify-end gap-2 border-t pt-3">
          <Button onClick={resetFilters} size="sm" type="button" variant="ghost">
            {t("adminFeedback.filters.reset")}
          </Button>
          <Button onClick={applyFilters} size="sm" type="button">
            {t("adminFeedback.filters.apply")}
          </Button>
        </div>
      </Card>

      {isLoading ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("adminFeedback.states.loading")}</p>
        </Card>
      ) : hasError ? (
        <Card>
          <p className="text-sm text-danger" role="alert">
            {t("adminFeedback.states.loadError")}
          </p>
          <Button className="mt-4" onClick={() => void loadReports()} type="button">
            {t("essays.actions.retry")}
          </Button>
        </Card>
      ) : reports.length === 0 ? (
        <Card>
          <p className="text-sm text-muted-foreground">
            {hasActiveFilters
              ? t("adminFeedback.states.emptyFilter")
              : t("adminFeedback.states.empty")}
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => (
            <Card key={report.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={badgeClass("border-muted-foreground/30 bg-surface text-muted-foreground")}>
                      {t(`support.type.${report.feedback_type}` as TranslationKey)}
                    </span>
                    <span className={badgeClass(STATUS_STYLES[report.status])}>
                      {t(`adminFeedback.status.${report.status}` as TranslationKey)}
                    </span>
                    <span className={badgeClass(PRIORITY_STYLES[report.priority])}>
                      {t(`adminFeedback.priority.${report.priority}` as TranslationKey)}
                    </span>
                    {report.page_module ? (
                      <span className="text-xs text-muted-foreground">{report.page_module}</span>
                    ) : null}
                  </div>
                  <p className="mt-2 truncate text-sm">{report.message}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatDateTime(report.created_at, locale)}
                    {report.user_email
                      ? ` · ${report.user_email}`
                      : report.contact
                        ? ` · ${report.contact}`
                        : ` · ${t("adminFeedback.anonymous")}`}
                  </p>
                </div>
                <Button
                  onClick={() => toggleExpanded(report)}
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  {expandedId === report.id
                    ? t("adminFeedback.actions.collapse")
                    : t("adminFeedback.actions.view")}
                </Button>
              </div>

              {expandedId === report.id ? (
                <div className="mt-4 space-y-3 border-t pt-4">
                  <p className="whitespace-pre-wrap text-sm leading-6">{report.message}</p>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block">
                      <span className="text-xs font-semibold">{t("adminFeedback.filters.status")}</span>
                      <select
                        className={fieldClassName}
                        disabled={savingId === report.id}
                        onChange={(event) =>
                          void updateReport(report, { status: event.target.value as FeedbackStatus })
                        }
                        value={report.status}
                      >
                        {FEEDBACK_STATUSES.map((option) => (
                          <option key={option} value={option}>
                            {t(`adminFeedback.status.${option}` as TranslationKey)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="block">
                      <span className="text-xs font-semibold">{t("adminFeedback.filters.priority")}</span>
                      <select
                        className={fieldClassName}
                        disabled={savingId === report.id}
                        onChange={(event) =>
                          void updateReport(report, {
                            priority: event.target.value as FeedbackPriority
                          })
                        }
                        value={report.priority}
                      >
                        {FEEDBACK_PRIORITIES.map((option) => (
                          <option key={option} value={option}>
                            {t(`adminFeedback.priority.${option}` as TranslationKey)}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <label className="block">
                    <span className="text-xs font-semibold">{t("adminFeedback.notesLabel")}</span>
                    <textarea
                      className={`${fieldClassName} min-h-20 resize-y py-2 leading-5`}
                      maxLength={2000}
                      onChange={(event) => setNotesDraft(event.target.value)}
                      value={notesDraft}
                    />
                  </label>

                  {actionErrorId === report.id ? (
                    <p className="text-xs text-danger" role="alert">
                      {t("adminFeedback.states.actionError")}
                    </p>
                  ) : null}

                  <div className="flex justify-end gap-2">
                    <Button
                      disabled={savingId === report.id}
                      onClick={() => void saveNotes(report)}
                      size="sm"
                      type="button"
                    >
                      {savingId === report.id
                        ? t("adminFeedback.actions.saving")
                        : t("adminFeedback.actions.saveNotes")}
                    </Button>
                  </div>
                </div>
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
