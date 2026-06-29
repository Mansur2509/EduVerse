"use client";

import { Plus } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  APPLICATION_BOARD_COLUMNS,
  ApplicationCard,
  DECISION_STATUSES,
  type ApplicationStatus,
  type ApplicationTrackerItem,
  type DocumentsStatus,
  type FinancialAidStatus,
  type RecommendationsStatus,
  type TestScoresStatus
} from "@/entities/application";
import type { RoadmapTask } from "@/entities/roadmap";
import type { SuggestedItem } from "@/entities/suggestion";
import type { SavedUniversity } from "@/entities/university";
import {
  createApplicationMilestoneRequest,
  createApplicationRequest,
  deleteApplicationRequest,
  getApplicationsRequest,
  updateApplicationMilestoneRequest,
  updateApplicationRequest
} from "@/features/applications";
import { ApplicationForm, type ApplicationFormValues } from "@/features/applications/ui/application-form";
import { MilestoneForm } from "@/features/applications/ui/milestone-form";
import { getRoadmapTasksRequest } from "@/features/roadmap";
import {
  addSuggestionToRoadmapRequest,
  dismissSuggestionRequest,
  generateSuggestionsRequest,
  getSuggestionsRequest,
  SuggestionPanel
} from "@/features/suggestions";
import { getShortlistRequest } from "@/features/universities";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { LoadingNotice } from "@/shared/ui/loading-notice";

const ESSAYS_STATUSES = ["not_started", "drafting", "needs_revision", "ready", "submitted"];
const RECOMMENDATIONS_STATUSES: RecommendationsStatus[] = [
  "not_started",
  "requested",
  "received",
  "submitted"
];
const TEST_SCORES_STATUSES: TestScoresStatus[] = ["not_required", "planned", "ready", "sent"];
const DOCUMENTS_STATUSES: DocumentsStatus[] = ["not_started", "collecting", "ready", "submitted"];
const FINANCIAL_AID_STATUSES: FinancialAidStatus[] = [
  "not_applying",
  "researching",
  "preparing",
  "submitted"
];
const ALL_STATUSES: ApplicationStatus[] = [...APPLICATION_BOARD_COLUMNS, ...DECISION_STATUSES];

export function ApplicationsScreen() {
  const { locale, t } = useI18n();
  const [applications, setApplications] = useState<ApplicationTrackerItem[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestedItem[]>([]);
  const [shortlist, setShortlist] = useState<SavedUniversity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [actionError, setActionError] = useState(false);
  const [linkedTasks, setLinkedTasks] = useState<RoadmapTask[]>([]);
  const [isRefreshingSuggestions, setIsRefreshingSuggestions] = useState(false);

  const loadApplications = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const [applicationsResponse, shortlistResponse, suggestionsResponse] = await Promise.allSettled([
        getApplicationsRequest(),
        getShortlistRequest(),
        getSuggestionsRequest()
      ]);
      if (applicationsResponse.status === "rejected") {
        setHasError(true);
        return;
      }
      setApplications(applicationsResponse.value.results);
      setShortlist(shortlistResponse.status === "fulfilled" ? shortlistResponse.value.results : []);
      setSuggestions(suggestionsResponse.status === "fulfilled" ? suggestionsResponse.value.results : []);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadApplications();
  }, [loadApplications]);

  const selected = applications.find((item) => item.id === selectedId) ?? null;

  useEffect(() => {
    if (!selected) {
      setLinkedTasks([]);
      return;
    }
    getRoadmapTasksRequest({ linked_university: String(selected.university) })
      .then((response) => setLinkedTasks(response.results))
      .catch(() => setLinkedTasks([]));
  }, [selected]);

  function updateInList(updated: ApplicationTrackerItem) {
    setApplications((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }

  async function handleCreate(values: ApplicationFormValues) {
    const created = await createApplicationRequest({
      university: values.university ?? undefined,
      application_round: values.application_round,
      deadline: values.deadline || null
    });
    setApplications((current) => [created, ...current]);
    setSelectedId(created.id);
    setIsFormOpen(false);
  }

  async function handlePatch(field: string, value: string) {
    if (!selected) return;
    setActionError(false);
    try {
      const updated = await updateApplicationRequest(selected.id, { [field]: value });
      updateInList(updated);
    } catch {
      setActionError(true);
    }
  }

  async function handleNotesChange(notes: string) {
    if (!selected) return;
    try {
      const updated = await updateApplicationRequest(selected.id, { notes });
      updateInList(updated);
    } catch {
      setActionError(true);
    }
  }

  async function handleDelete(application: ApplicationTrackerItem) {
    setActionError(false);
    try {
      await deleteApplicationRequest(application.id);
      setApplications((current) => current.filter((item) => item.id !== application.id));
      if (selectedId === application.id) setSelectedId(null);
    } catch {
      setActionError(true);
    }
  }

  async function handleAddMilestone(values: { title: string; category: string; due_date: string }) {
    if (!selected) return;
    setActionError(false);
    try {
      const milestone = await createApplicationMilestoneRequest(selected.id, {
        title: values.title,
        category: values.category as never,
        due_date: values.due_date || null
      });
      updateInList({ ...selected, milestones: [...selected.milestones, milestone] });
    } catch {
      setActionError(true);
    }
  }

  async function handleMilestoneStatus(milestoneId: number, status: string) {
    if (!selected) return;
    setActionError(false);
    try {
      await updateApplicationMilestoneRequest(milestoneId, { status });
      updateInList({
        ...selected,
        milestones: selected.milestones.map((item) =>
          item.id === milestoneId ? { ...item, status: status as never } : item
        )
      });
    } catch {
      setActionError(true);
    }
  }

  async function handleRefreshSuggestions() {
    setIsRefreshingSuggestions(true);
    setActionError(false);
    try {
      const response = await generateSuggestionsRequest();
      setSuggestions(response.suggestions);
    } catch {
      setActionError(true);
    } finally {
      setIsRefreshingSuggestions(false);
    }
  }

  async function handleAddSuggestion(suggestion: SuggestedItem) {
    setActionError(false);
    try {
      await addSuggestionToRoadmapRequest(suggestion.id);
      setSuggestions((current) => current.filter((item) => item.id !== suggestion.id));
      if (selected) {
        const response = await getRoadmapTasksRequest({ linked_university: String(selected.university) });
        setLinkedTasks(response.results);
      }
    } catch {
      setActionError(true);
    }
  }

  async function handleDismissSuggestion(suggestion: SuggestedItem) {
    setActionError(false);
    try {
      await dismissSuggestionRequest(suggestion.id);
      setSuggestions((current) => current.filter((item) => item.id !== suggestion.id));
    } catch {
      setActionError(true);
    }
  }

  const columns = useMemo(() => {
    const grouped = new Map<string, ApplicationTrackerItem[]>();
    ALL_STATUSES.forEach((status) => grouped.set(status, []));
    applications.forEach((application) => {
      grouped.get(application.status)?.push(application);
    });
    return grouped;
  }, [applications]);

  const applicationSuggestions = suggestions.filter((suggestion) => {
    const isApplicationSuggestion =
      suggestion.suggestion_type === "application_deadline" ||
      suggestion.suggestion_type === "document_deadline" ||
      suggestion.suggestion_type === "scholarship_deadline" ||
      suggestion.suggestion_type === "scholarship_type";
    if (!isApplicationSuggestion) return false;
    return selected ? suggestion.linked_application === selected.id : true;
  });

  if (isLoading) {
    return <LoadingNotice message={t("applications.states.loading")} />;
  }

  if (hasError) {
    return (
      <Card>
        <p className="text-sm text-danger" role="alert">
          {t("applications.states.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void loadApplications()} type="button">
          {t("applications.actions.retry")}
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
              {t("applications.list.eyebrow")}
            </p>
            <h1 className="mt-2 max-w-3xl text-3xl font-semibold sm:text-4xl">
              {t("applications.list.title")}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              {t("applications.list.description")}
            </p>
          </div>
          <Button onClick={() => setIsFormOpen(true)} type="button">
            <Plus aria-hidden className="mr-2 size-4" />
            {t("applications.actions.newApplication")}
          </Button>
        </div>
      </section>

      {actionError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("applications.states.actionError")}
          </p>
        </Card>
      ) : null}

      {isFormOpen ? (
        <ApplicationForm
          onCancel={() => setIsFormOpen(false)}
          onSubmit={handleCreate}
          shortlist={shortlist}
        />
      ) : null}

      <SuggestionPanel
        description={t("applications.suggestions.description")}
        isRefreshing={isRefreshingSuggestions}
        onAddToRoadmap={(suggestion) => void handleAddSuggestion(suggestion)}
        onDismiss={(suggestion) => void handleDismissSuggestion(suggestion)}
        onGenerate={() => void handleRefreshSuggestions()}
        suggestions={applicationSuggestions}
        title={t("applications.suggestions.title")}
      />

      {applications.length === 0 ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("applications.states.empty")}</p>
        </Card>
      ) : (
        <div className="grid gap-3 overflow-x-auto pb-2 lg:grid-cols-7">
          {[...APPLICATION_BOARD_COLUMNS, "decisions"].map((column) => (
            <div className="min-w-[14rem] space-y-2" key={column}>
              <h2 className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                {column === "decisions"
                  ? t("applications.column.decisions")
                  : t(`applications.status.${column}` as TranslationKey)}
              </h2>
              <div className="space-y-2">
                {(column === "decisions"
                  ? DECISION_STATUSES.flatMap((status) => columns.get(status) ?? [])
                  : columns.get(column) ?? []
                ).map((application) => (
                  <ApplicationCard
                    application={application}
                    isSelected={application.id === selectedId}
                    key={application.id}
                    onSelect={(item) => setSelectedId(item.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected ? (
        <Card className="space-y-4 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">{selected.university_name}</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {selected.deadline
                  ? t("applications.detail.deadline", {
                      date: formatDate(selected.deadline, locale)
                    })
                  : t("applications.detail.deadlineNotVerified")}
              </p>
            </div>
            <Button onClick={() => void handleDelete(selected)} size="sm" type="button" variant="ghost">
              {t("applications.actions.delete")}
            </Button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <label className="block">
              <span className="text-xs font-semibold">{t("applications.detail.status")}</span>
              <select
                className={fieldClassName}
                onChange={(event) => void handlePatch("status", event.target.value)}
                value={selected.status}
              >
                {ALL_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`applications.status.${status}` as TranslationKey)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold">{t("applications.detail.priority")}</span>
              <select
                className={fieldClassName}
                onChange={(event) => void handlePatch("priority", event.target.value)}
                value={selected.priority}
              >
                {(["low", "medium", "high", "dream"] as const).map((priority) => (
                  <option key={priority} value={priority}>
                    {t(`applications.priority.${priority}` as TranslationKey)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold">{t("applications.detail.essaysStatus")}</span>
              <select
                className={fieldClassName}
                onChange={(event) => void handlePatch("essays_status", event.target.value)}
                value={selected.essays_status}
              >
                {ESSAYS_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`applications.essaysStatus.${status}` as TranslationKey)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold">
                {t("applications.detail.recommendationsStatus")}
              </span>
              <select
                className={fieldClassName}
                onChange={(event) => void handlePatch("recommendations_status", event.target.value)}
                value={selected.recommendations_status}
              >
                {RECOMMENDATIONS_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`applications.recommendationsStatus.${status}` as TranslationKey)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold">{t("applications.detail.testScoresStatus")}</span>
              <select
                className={fieldClassName}
                onChange={(event) => void handlePatch("test_scores_status", event.target.value)}
                value={selected.test_scores_status}
              >
                {TEST_SCORES_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`applications.testScoresStatus.${status}` as TranslationKey)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold">{t("applications.detail.documentsStatus")}</span>
              <select
                className={fieldClassName}
                onChange={(event) => void handlePatch("documents_status", event.target.value)}
                value={selected.documents_status}
              >
                {DOCUMENTS_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`applications.documentsStatus.${status}` as TranslationKey)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold">
                {t("applications.detail.financialAidStatus")}
              </span>
              <select
                className={fieldClassName}
                onChange={(event) => void handlePatch("financial_aid_status", event.target.value)}
                value={selected.financial_aid_status}
              >
                {FINANCIAL_AID_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(`applications.financialAidStatus.${status}` as TranslationKey)}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="block">
            <span className="text-xs font-semibold">{t("applications.detail.notes")}</span>
            <textarea
              className={fieldClassName}
              defaultValue={selected.notes}
              onBlur={(event) => void handleNotesChange(event.target.value)}
              rows={3}
            />
          </label>

          <div>
            <h3 className="text-sm font-semibold">{t("applications.milestones.title")}</h3>
            {selected.milestones.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">
                {t("applications.milestones.empty")}
              </p>
            ) : (
              <ul className="mt-2 space-y-2">
                {selected.milestones.map((milestone) => (
                  <li
                    className="flex flex-wrap items-center justify-between gap-3 rounded-sm border bg-surface p-3 text-sm"
                    key={milestone.id}
                  >
                    <div>
                      <span className="rounded-sm border bg-elevated px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
                        {t(`applications.milestoneCategory.${milestone.category}` as TranslationKey)}
                      </span>
                      <p className="mt-1 font-semibold">{milestone.title}</p>
                      {milestone.due_date ? (
                        <p className="text-xs text-muted-foreground">
                          {formatDate(milestone.due_date, locale)}
                        </p>
                      ) : null}
                    </div>
                    {milestone.status === "todo" || milestone.status === "in_progress" ? (
                      <div className="flex gap-2">
                        <Button
                          onClick={() => void handleMilestoneStatus(milestone.id, "completed")}
                          size="sm"
                          type="button"
                        >
                          {t("applications.milestones.complete")}
                        </Button>
                        <Button
                          onClick={() => void handleMilestoneStatus(milestone.id, "skipped")}
                          size="sm"
                          type="button"
                          variant="ghost"
                        >
                          {t("applications.milestones.skip")}
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {t(`applications.milestoneStatus.${milestone.status}` as TranslationKey)}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-3">
              <MilestoneForm onSubmit={(values) => void handleAddMilestone(values)} />
            </div>
          </div>

          {linkedTasks.length > 0 ? (
            <div>
              <h3 className="text-sm font-semibold">{t("applications.detail.linkedRoadmapTasks")}</h3>
              <ul className="mt-2 space-y-1.5 text-sm">
                {linkedTasks.map((task) => (
                  <li className="flex items-center justify-between gap-3 rounded-sm border bg-surface px-3 py-2" key={task.id}>
                    <span>{task.title}</span>
                    {task.due_date ? (
                      <span className="text-xs text-muted-foreground">
                        {formatDate(task.due_date, locale)}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </Card>
      ) : null}

      <p className="text-xs leading-5 text-muted-foreground">{t("applications.disclaimer")}</p>
    </div>
  );
}
