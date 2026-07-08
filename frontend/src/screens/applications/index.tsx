"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
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
import type { SavedUniversityLite } from "@/entities/university";
import {
  createApplicationMilestoneRequest,
  createApplicationRequest,
  deleteApplicationRequest,
  getApplicationsRequest,
  updateApplicationMilestoneRequest,
  updateApplicationRequest
} from "@/features/applications";
import { ApplicationForm, type ApplicationFormValues } from "@/features/applications/ui/application-form";
import { ApplicationTimelinePanel } from "@/features/applications/ui/application-timeline";
import { MilestoneForm, type MilestoneFormValues } from "@/features/applications/ui/milestone-form";
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
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { CollapsibleFilterPanel } from "@/shared/ui/collapsible-filter-panel";
import { fieldClassName } from "@/shared/ui/field";
import { HelpTooltip } from "@/shared/ui/help-tooltip";
import { LoadingNotice } from "@/shared/ui/loading-notice";
import { PaginationControls } from "@/shared/ui/pagination";
import { SectionTabs } from "@/shared/ui/section-tabs";
import { UnsavedChangesDialog } from "@/shared/ui/unsaved-changes-dialog";

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

const SORT_OPTIONS = [
  "nearest_deadline",
  "urgency",
  "name",
  "recently_updated",
  "progress"
] as const;
type SortOption = (typeof SORT_OPTIONS)[number];

const ROUND_OPTIONS = [
  "early_decision",
  "early_action",
  "restrictive_early_action",
  "regular_decision",
  "rolling",
  "scholarship",
  "other"
] as const;

// Applications per user are few and lightweight, so load a wide page and let the
// compact filters/sort operate across the whole set rather than one grid page.
const APPLICATIONS_PAGE_SIZE = 100;

type UrgencyLevel = "overdue" | "critical" | "urgent" | "soon" | "upcoming" | "far" | "unknown";

// Mirrors backend services/application_service/timeline.py:urgency_for_days so the
// list-level urgency filter matches the timeline badges exactly.
function urgencyForDeadline(deadline: string | null): UrgencyLevel {
  if (!deadline) return "unknown";
  const parsed = new Date(`${deadline}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return "unknown";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((parsed.getTime() - today.getTime()) / 86_400_000);
  if (days < 0) return "overdue";
  if (days <= 7) return "critical";
  if (days <= 14) return "urgent";
  if (days <= 30) return "soon";
  if (days <= 90) return "upcoming";
  return "far";
}

const URGENCY_RANK: Record<UrgencyLevel, number> = {
  overdue: 0,
  critical: 1,
  urgent: 2,
  soon: 3,
  upcoming: 4,
  far: 5,
  unknown: 6
};

export function ApplicationsScreen() {
  const { locale, t } = useI18n();
  const [applications, setApplications] = useState<ApplicationTrackerItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [suggestions, setSuggestions] = useState<SuggestedItem[]>([]);
  const [suggestionsRequested, setSuggestionsRequested] = useState(false);
  const [isSuggestionsLoading, setIsSuggestionsLoading] = useState(false);
  const [suggestionsLoadError, setSuggestionsLoadError] = useState(false);
  const [shortlist, setShortlist] = useState<SavedUniversityLite[]>([]);
  const [shortlistRequested, setShortlistRequested] = useState(false);
  const [isShortlistLoading, setIsShortlistLoading] = useState(false);
  const [shortlistLoadError, setShortlistLoadError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [actionError, setActionError] = useState(false);
  const [linkedTasks, setLinkedTasks] = useState<RoadmapTask[]>([]);
  const [isRefreshingSuggestions, setIsRefreshingSuggestions] = useState(false);
  const [notesDraft, setNotesDraft] = useState("");
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [roundFilter, setRoundFilter] = useState<string>("all");
  const [urgencyFilter, setUrgencyFilter] = useState<string>("all");
  const [missingDeadlineOnly, setMissingDeadlineOnly] = useState(false);
  const [sortBy, setSortBy] = useState<SortOption>("nearest_deadline");

  const loadApplications = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const applicationsResponse = await getApplicationsRequest({
        page: currentPage,
        page_size: APPLICATIONS_PAGE_SIZE
      });
      setApplications(applicationsResponse.results);
      setTotalCount(applicationsResponse.count);
      setSelectedId((current) =>
        applicationsResponse.results.some((item) => item.id === current) ? current : null
      );
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage]);

  useEffect(() => {
    void loadApplications();
  }, [loadApplications]);

  const loadShortlist = useCallback(async () => {
    if (shortlistRequested && !shortlistLoadError) return;
    setShortlistRequested(true);
    setIsShortlistLoading(true);
    setShortlistLoadError(false);
    try {
      const response = await getShortlistRequest({ lite: true });
      setShortlist(response.results);
    } catch {
      setShortlistLoadError(true);
    } finally {
      setIsShortlistLoading(false);
    }
  }, [shortlistLoadError, shortlistRequested]);

  const loadSuggestions = useCallback(async () => {
    if (suggestionsRequested && !suggestionsLoadError) return;
    setSuggestionsRequested(true);
    setIsSuggestionsLoading(true);
    setSuggestionsLoadError(false);
    try {
      const response = await getSuggestionsRequest();
      setSuggestions(response.results);
    } catch {
      setSuggestionsLoadError(true);
    } finally {
      setIsSuggestionsLoading(false);
    }
  }, [suggestionsLoadError, suggestionsRequested]);

  useEffect(() => {
    if (isFormOpen) {
      void loadShortlist();
    }
  }, [isFormOpen, loadShortlist]);

  const selected = applications.find((item) => item.id === selectedId) ?? null;
  const hasUnsavedNotes = Boolean(selected && notesDraft !== selected.notes);
  const notesGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedNotes
  });

  useEffect(() => {
    setNotesDraft(selected?.notes ?? "");
  }, [selected?.id, selected?.notes]);

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
    setTotalCount((current) => current + 1);
    setCurrentPage(1);
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

  async function handleSaveNotes() {
    if (!selected) return false;
    setIsSavingNotes(true);
    setActionError(false);
    try {
      const updated = await updateApplicationRequest(selected.id, { notes: notesDraft });
      updateInList(updated);
      setNotesDraft(updated.notes);
      return true;
    } catch {
      setActionError(true);
      return false;
    } finally {
      setIsSavingNotes(false);
    }
  }

  function handleDiscardNotes() {
    setNotesDraft(selected?.notes ?? "");
  }

  async function handleDelete(application: ApplicationTrackerItem) {
    setActionError(false);
    try {
      await deleteApplicationRequest(application.id);
      setApplications((current) => current.filter((item) => item.id !== application.id));
      setTotalCount((current) => Math.max(0, current - 1));
      if (selectedId === application.id) setSelectedId(null);
    } catch {
      setActionError(true);
    }
  }

  async function handleAddMilestone(values: MilestoneFormValues) {
    if (!selected) return;
    setActionError(false);
    try {
      const milestone = await createApplicationMilestoneRequest(selected.id, {
        title: values.title,
        category: values.category,
        due_date: values.due_date || null,
        priority: values.priority,
        notes: values.notes
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

  const visibleApplications = useMemo(() => {
    const progressRank = (status: ApplicationStatus) => ALL_STATUSES.indexOf(status);
    const filtered = applications.filter((application) => {
      if (priorityFilter !== "all" && application.priority !== priorityFilter) return false;
      if (roundFilter !== "all" && application.application_round !== roundFilter) return false;
      if (urgencyFilter !== "all" && urgencyForDeadline(application.deadline) !== urgencyFilter) {
        return false;
      }
      if (missingDeadlineOnly && application.deadline) return false;
      return true;
    });
    const sorted = [...filtered];
    sorted.sort((a, b) => {
      switch (sortBy) {
        case "name":
          return a.university_name.localeCompare(b.university_name);
        case "recently_updated":
          return b.updated_at.localeCompare(a.updated_at);
        case "progress":
          return progressRank(b.status) - progressRank(a.status);
        case "urgency":
          return (
            URGENCY_RANK[urgencyForDeadline(a.deadline)] -
            URGENCY_RANK[urgencyForDeadline(b.deadline)]
          );
        case "nearest_deadline":
        default: {
          if (a.deadline && b.deadline) return a.deadline.localeCompare(b.deadline);
          if (a.deadline) return -1;
          if (b.deadline) return 1;
          return 0;
        }
      }
    });
    return sorted;
  }, [applications, priorityFilter, roundFilter, urgencyFilter, missingDeadlineOnly, sortBy]);

  const columns = useMemo(() => {
    const grouped = new Map<string, ApplicationTrackerItem[]>();
    ALL_STATUSES.forEach((status) => grouped.set(status, []));
    visibleApplications.forEach((application) => {
      grouped.get(application.status)?.push(application);
    });
    return grouped;
  }, [visibleApplications]);

  const applicationSuggestions = suggestions.filter((suggestion) => {
    const isApplicationSuggestion =
      suggestion.suggestion_type === "application_deadline" ||
      suggestion.suggestion_type === "document_deadline" ||
      suggestion.suggestion_type === "scholarship_deadline" ||
      suggestion.suggestion_type === "scholarship_type";
    if (!isApplicationSuggestion) return false;
    return selected ? suggestion.linked_application === selected.id : true;
  });
  const totalPages = Math.max(1, Math.ceil(totalCount / APPLICATIONS_PAGE_SIZE));
  const pageStart = totalCount ? (currentPage - 1) * APPLICATIONS_PAGE_SIZE + 1 : 0;
  const pageEnd = Math.min(pageStart + Math.max(applications.length, 1) - 1, totalCount);
  const activeFilterCount = [
    priorityFilter !== "all",
    roundFilter !== "all",
    urgencyFilter !== "all",
    missingDeadlineOnly,
    sortBy !== "nearest_deadline"
  ].filter(Boolean).length;

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
      <SectionTabs
        ariaLabel={t("applications.tabs.ariaLabel")}
        items={[
          { href: "/applications", label: t("applications.tabs.mine") },
          { href: "/strategy", label: t("applications.tabs.strategy") }
        ]}
      />

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
          isShortlistLoading={isShortlistLoading}
          shortlist={shortlist}
          shortlistLoadError={shortlistLoadError}
        />
      ) : null}

      <SuggestionPanel
        defaultOpen={false}
        description={t("applications.suggestions.description")}
        isLoading={isSuggestionsLoading}
        isRefreshing={isRefreshingSuggestions}
        loadError={suggestionsLoadError}
        loadErrorMessage={t("suggestions.states.loadError")}
        onAddToRoadmap={(suggestion) => void handleAddSuggestion(suggestion)}
        onDismiss={(suggestion) => void handleDismissSuggestion(suggestion)}
        onGenerate={() => void handleRefreshSuggestions()}
        onOpen={() => void loadSuggestions()}
        suggestions={applicationSuggestions}
        title={t("applications.suggestions.title")}
      />

      {applications.length === 0 ? (
        <Card>
          <p className="text-sm font-semibold">{t("applications.states.emptyTitle")}</p>
          <p className="mt-2 text-sm text-muted-foreground">{t("applications.states.empty")}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {t("applications.states.emptyAction")}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button asChild size="sm" variant="secondary">
              <Link href="/recommendations">{t("navigation.recommendations")}</Link>
            </Button>
            <Button asChild size="sm" variant="ghost">
              <Link href="/universities">{t("navigation.universities")}</Link>
            </Button>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          <CollapsibleFilterPanel
            activeCount={activeFilterCount}
            onClear={() => {
              setPriorityFilter("all");
              setRoundFilter("all");
              setUrgencyFilter("all");
              setMissingDeadlineOnly(false);
              setSortBy("nearest_deadline");
            }}
            resultCount={visibleApplications.length}
            storageKey="uniway.filters.applications"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <h2 className="text-sm font-semibold">{t("applications.filters.title")}</h2>
                <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
                  {t("applications.filters.autoApply")}
                </span>
              </div>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <label className="block">
                <span className="text-xs font-semibold">{t("applications.detail.priority")}</span>
                <select
                  className={fieldClassName}
                  onChange={(event) => setPriorityFilter(event.target.value)}
                  value={priorityFilter}
                >
                  <option value="all">{t("applications.filters.all")}</option>
                  {(["low", "medium", "high", "dream"] as const).map((priority) => (
                    <option key={priority} value={priority}>
                      {t(`applications.priority.${priority}` as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="flex items-center gap-1 text-xs font-semibold">
                  {t("applications.detail.round")}
                  <HelpTooltip label={t("applications.help.applicationRound")} />
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) => setRoundFilter(event.target.value)}
                  value={roundFilter}
                >
                  <option value="all">{t("applications.filters.all")}</option>
                  {ROUND_OPTIONS.map((round) => (
                    <option key={round} value={round}>
                      {t(`applications.round.${round}` as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="flex items-center gap-1 text-xs font-semibold">
                  {t("applications.filters.urgency")}
                  <HelpTooltip label={t("applications.help.urgency")} />
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) => setUrgencyFilter(event.target.value)}
                  value={urgencyFilter}
                >
                  <option value="all">{t("applications.filters.all")}</option>
                  {(["overdue", "critical", "urgent", "soon", "upcoming", "far"] as const).map(
                    (level) => (
                      <option key={level} value={level}>
                        {t(`applications.urgency.${level}` as TranslationKey)}
                      </option>
                    )
                  )}
                </select>
              </label>
              <label className="block">
                <span className="text-xs font-semibold">{t("applications.sort.label")}</span>
                <select
                  className={fieldClassName}
                  onChange={(event) => setSortBy(event.target.value as SortOption)}
                  value={sortBy}
                >
                  {SORT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {t(`applications.sort.${option}` as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="flex items-center gap-2 text-xs font-semibold">
              <input
                checked={missingDeadlineOnly}
                onChange={(event) => setMissingDeadlineOnly(event.target.checked)}
                type="checkbox"
              />
              {t("applications.filters.missingDeadline")}
            </label>
            <p className="text-xs text-muted-foreground">
              {t("applications.filters.resultCount", { count: visibleApplications.length })}
            </p>
          </CollapsibleFilterPanel>
          <p className="text-sm font-semibold text-muted-foreground">
            {t("pagination.showingRange", {
              start: pageStart,
              end: pageEnd,
              total: totalCount
            })}
          </p>
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
                      onSelect={(item) =>
                        notesGuard.requestLeave(() => setSelectedId(item.id))
                      }
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
          {totalPages > 1 ? (
            <PaginationControls
              currentPage={currentPage}
              onNext={() => setCurrentPage((page) => page + 1)}
              onPageSelect={setCurrentPage}
              onPrevious={() => setCurrentPage((page) => page - 1)}
              totalPages={totalPages}
            />
          ) : null}
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
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => notesGuard.requestLeave(() => setSelectedId(null))}
                size="sm"
                type="button"
                variant="ghost"
              >
                {t("common.actions.close")}
              </Button>
              <Button onClick={() => void handleDelete(selected)} size="sm" type="button" variant="ghost">
                {t("applications.actions.delete")}
              </Button>
            </div>
          </div>

          <section className="rounded-sm border bg-elevated p-4">
            <div className="flex items-center gap-1.5">
              <h3 className="text-base font-semibold">{t("applications.timeline.title")}</h3>
              <HelpTooltip label={t("applications.help.timeline")} />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {t("applications.timeline.description")}
            </p>
            <div className="mt-3">
              <ApplicationTimelinePanel applicationId={selected.id} />
            </div>
          </section>

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
              onChange={(event) => setNotesDraft(event.target.value)}
              rows={3}
              value={notesDraft}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={isSavingNotes || !hasUnsavedNotes}
              onClick={() => void handleSaveNotes()}
              size="sm"
              type="button"
            >
              {isSavingNotes ? t("applications.detail.savingNotes") : t("common.actions.save")}
            </Button>
            <Button
              disabled={isSavingNotes || !hasUnsavedNotes}
              onClick={handleDiscardNotes}
              size="sm"
              type="button"
              variant="ghost"
            >
              {t("common.actions.cancel")}
            </Button>
          </div>
          {!hasUnsavedNotes ? (
            <p className="text-xs text-muted-foreground">
              {t("applications.detail.saveDisabledNoChanges")}
            </p>
          ) : null}

          <div>
            <div className="flex items-center gap-1.5">
              <h3 className="text-sm font-semibold">{t("applications.milestones.title")}</h3>
              <HelpTooltip label={t("applications.milestones.help")} />
            </div>
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
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="rounded-sm border bg-elevated px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
                          {t(`applications.milestoneCategory.${milestone.category}` as TranslationKey)}
                        </span>
                        <span className="rounded-sm border bg-elevated px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
                          {t(`applications.priority.${milestone.priority}` as TranslationKey)}
                        </span>
                      </div>
                      <p className="mt-1 font-semibold">{milestone.title}</p>
                      {milestone.notes ? (
                        <p className="text-xs text-muted-foreground">{milestone.notes}</p>
                      ) : null}
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
              <MilestoneForm onSubmit={handleAddMilestone} />
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
      <UnsavedChangesDialog
        description={t("common.unsaved.description")}
        isSaving={isSavingNotes}
        leaveWithoutSavingLabel={t("common.unsaved.leaveWithoutSaving")}
        onLeaveWithoutSaving={notesGuard.leaveWithoutSaving}
        onSaveAndLeave={handleSaveNotes}
        onStay={notesGuard.stay}
        open={notesGuard.isPromptOpen}
        saveAndLeaveLabel={t("common.unsaved.saveAndLeave")}
        stayLabel={t("common.unsaved.stay")}
        title={t("common.unsaved.title")}
      />
    </div>
  );
}
