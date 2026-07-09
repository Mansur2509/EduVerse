"use client";

import {
  AlertTriangle,
  CalendarClock,
  ChevronDown,
  CheckCircle2,
  HelpCircle,
  ListTodo,
  Plus,
  RefreshCw,
  Route
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  bucketForTask,
  RoadmapTaskCard,
  type RoadmapBucket,
  type RoadmapPlan,
  type RoadmapTask
} from "@/entities/roadmap";
import type { SuggestedItem } from "@/entities/suggestion";
import {
  completeRoadmapTaskRequest,
  createRoadmapTaskRequest,
  deleteRoadmapTaskRequest,
  generateRoadmapRequest,
  getRoadmapRequest,
  skipRoadmapTaskRequest,
  updateRoadmapTaskRequest
} from "@/features/roadmap";
import { RoadmapTaskForm, type RoadmapTaskFormValues } from "@/features/roadmap/ui/roadmap-task-form";
import {
  addSuggestionToRoadmapRequest,
  dismissSuggestionRequest,
  generateSuggestionsRequest,
  getSuggestionsRequest,
  SuggestionPanel
} from "@/features/suggestions";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate, formatDateTime } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { CollapsibleFilterPanel } from "@/shared/ui/collapsible-filter-panel";
import { fieldClassName } from "@/shared/ui/field";
import { HelpTooltip } from "@/shared/ui/help-tooltip";
import { DEFAULT_PAGE_SIZE, PaginatedGrid, PaginatedList } from "@/shared/ui/pagination";
import { SkeletonCards, SkeletonRow } from "@/shared/ui/skeleton";

type ActiveBucketFilter = Exclude<RoadmapBucket, "completed"> | "all";
type RoadmapViewMode = "list" | "timeline";
type TaskStatusScope = "active" | "completed" | "skipped" | "all";

const BUCKET_FILTERS: ActiveBucketFilter[] = ["all", "this_week", "this_month", "later"];
const STATUS_SCOPES: TaskStatusScope[] = ["active", "completed", "skipped", "all"];
const ROADMAP_SOURCE_TYPES = [
  "generated",
  "manual",
  "university_deadline",
  "profile_gap",
  "fit_analysis",
  "essay_status",
  "exam_plan",
  "planning_window",
  "event"
] as const;

const emptyFilters = {
  category: "",
  priority: "",
  university: "",
  application: "",
  exam: "",
  dueAfter: "",
  dueBefore: "",
  sourceType: "",
  taskKind: ""
};

export function RoadmapScreen() {
  const { locale, t } = useI18n();
  const [plan, setPlan] = useState<RoadmapPlan | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestedItem[]>([]);
  const [suggestionsRequested, setSuggestionsRequested] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [bucket, setBucket] = useState<ActiveBucketFilter>("all");
  const [viewMode, setViewMode] = useState<RoadmapViewMode>("list");
  const [statusScope, setStatusScope] = useState<TaskStatusScope>("active");
  const [taskPage, setTaskPage] = useState(1);
  const [filters, setFilters] = useState(emptyFilters);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<RoadmapTask | null>(null);
  const [pendingTaskId, setPendingTaskId] = useState<number | null>(null);
  const [actionError, setActionError] = useState(false);
  const [isRefreshingSuggestions, setIsRefreshingSuggestions] = useState(false);
  const [isSuggestionsLoading, setIsSuggestionsLoading] = useState(false);
  const [suggestionsLoadError, setSuggestionsLoadError] = useState(false);
  const [instructionsOpen, setInstructionsOpen] = useState(true);
  const [completedOpen, setCompletedOpen] = useState(false);

  const loadRoadmap = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const roadmapResponse = await getRoadmapRequest();
      setPlan(roadmapResponse.plan);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadSuggestions = useCallback(async () => {
    if (suggestionsRequested && !suggestionsLoadError) return;
    setSuggestionsRequested(true);
    setIsSuggestionsLoading(true);
    setSuggestionsLoadError(false);
    try {
      const suggestionsResponse = await getSuggestionsRequest();
      setSuggestions(suggestionsResponse.results);
    } catch {
      setSuggestionsLoadError(true);
    } finally {
      setIsSuggestionsLoading(false);
    }
  }, [suggestionsLoadError, suggestionsRequested]);

  useEffect(() => {
    void loadRoadmap();
  }, [loadRoadmap]);

  useEffect(() => {
    if (window.localStorage.getItem("uniway.roadmap.instructions.viewed") === "true") {
      setInstructionsOpen(false);
    }
    const storedView = window.localStorage.getItem("uniway.roadmap.viewMode");
    if (storedView === "list" || storedView === "timeline") {
      setViewMode(storedView);
    }
  }, []);

  function handleViewModeChange(nextMode: RoadmapViewMode) {
    setViewMode(nextMode);
    window.localStorage.setItem("uniway.roadmap.viewMode", nextMode);
  }

  async function handleGenerate() {
    setIsGenerating(true);
    setActionError(false);
    try {
      const response = await generateRoadmapRequest();
      setPlan(response.plan);
      const suggestionResponse = await generateSuggestionsRequest();
      setSuggestions(suggestionResponse.suggestions);
    } catch {
      setActionError(true);
    } finally {
      setIsGenerating(false);
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
      const response = await getRoadmapRequest();
      setPlan(response.plan);
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

  function toggleInstructions() {
    setInstructionsOpen((current) => {
      const next = !current;
      if (!next) {
        window.localStorage.setItem("uniway.roadmap.instructions.viewed", "true");
      }
      return next;
    });
  }

  function updateTaskInPlan(updated: RoadmapTask) {
    setPlan((current) =>
      current
        ? { ...current, tasks: current.tasks.map((task) => (task.id === updated.id ? updated : task)) }
        : current
    );
  }

  async function handleComplete(task: RoadmapTask) {
    setPendingTaskId(task.id);
    setActionError(false);
    try {
      updateTaskInPlan(await completeRoadmapTaskRequest(task.id));
    } catch {
      setActionError(true);
    } finally {
      setPendingTaskId(null);
    }
  }

  async function handleSkip(task: RoadmapTask) {
    if (!window.confirm(t("roadmap.confirm.dismissGenerated"))) {
      return;
    }
    setPendingTaskId(task.id);
    setActionError(false);
    try {
      updateTaskInPlan(await skipRoadmapTaskRequest(task.id));
    } catch {
      setActionError(true);
    } finally {
      setPendingTaskId(null);
    }
  }

  function openCreateForm() {
    setEditingTask(null);
    setIsFormOpen(true);
  }

  function openEditForm(task: RoadmapTask) {
    setEditingTask(task);
    setIsFormOpen(true);
  }

  async function handleFormSubmit(values: RoadmapTaskFormValues) {
    if (editingTask) {
      const isManual = editingTask.source_type === "manual";
      const updated = await updateRoadmapTaskRequest(editingTask.id, {
        title: values.title,
        description: values.description,
        priority: values.priority,
        due_date: values.due_date || null,
        ...(isManual ? { category: values.category } : {})
      });
      updateTaskInPlan(updated);
    } else {
      const created = await createRoadmapTaskRequest({
        title: values.title,
        description: values.description,
        category: values.category,
        priority: values.priority,
        due_date: values.due_date || null
      });
      setPlan((current) => (current ? { ...current, tasks: [...current.tasks, created] } : current));
    }
    setIsFormOpen(false);
    setEditingTask(null);
  }

  async function handleDelete(task: RoadmapTask) {
    const message =
      task.status === "completed"
        ? t("roadmap.confirm.deleteCompleted")
        : t("roadmap.confirm.deleteManual");
    if (!window.confirm(message)) {
      return;
    }
    setPendingTaskId(task.id);
    setActionError(false);
    try {
      await deleteRoadmapTaskRequest(task.id);
      setPlan((current) =>
        current ? { ...current, tasks: current.tasks.filter((item) => item.id !== task.id) } : current
      );
    } catch {
      setActionError(true);
    } finally {
      setPendingTaskId(null);
    }
  }

  const today = useMemo(() => new Date(new Date().toDateString()), []);

  const universityOptions = useMemo(() => {
    if (!plan) return [];
    const names = new Set<string>();
    plan.tasks.forEach((task) => {
      if (task.linked_university_name) names.add(task.linked_university_name);
    });
    return [...names];
  }, [plan]);

  const applicationOptions = useMemo(() => {
    if (!plan) return [];
    const options = new Map<number, string>();
    plan.tasks.forEach((task) => {
      if (task.linked_application) {
        options.set(
          task.linked_application,
          task.linked_application_university_name || task.linked_university_name || String(task.linked_application)
        );
      }
    });
    return [...options.entries()].map(([id, label]) => ({ id, label }));
  }, [plan]);

  const filteredTasks = useMemo(() => {
    if (!plan) return [];
    return plan.tasks.filter((task) => {
      if (filters.category && task.category !== filters.category) return false;
      if (filters.priority && task.priority !== filters.priority) return false;
      if (filters.university && task.linked_university_name !== filters.university) return false;
      if (filters.application && task.linked_application !== Number(filters.application)) return false;
      if (filters.sourceType && task.source_type !== filters.sourceType) return false;
      if (filters.taskKind && task.task_kind !== filters.taskKind) return false;
      if (filters.dueAfter && (!task.due_date || task.due_date < filters.dueAfter)) return false;
      if (filters.dueBefore && (!task.due_date || task.due_date > filters.dueBefore)) return false;
      if (filters.exam) {
        const examNeedle = filters.exam.toLowerCase();
        const examText = `${task.title} ${task.description} ${task.generated_reason} ${task.evidence_note}`.toLowerCase();
        if (task.category !== "exams" || !examText.includes(examNeedle)) return false;
      }
      return true;
    });
  }, [plan, filters]);

  const actionableTasks = useMemo(
    () => filteredTasks.filter((task) => !task.is_timeline_marker),
    [filteredTasks]
  );

  const statusFilteredTasks = useMemo(
    () => actionableTasks.filter((task) => matchesStatusScope(task, statusScope)),
    [actionableTasks, statusScope]
  );

  const bucketedTasks = useMemo(() => {
    const sorted = [...statusFilteredTasks].sort(compareRoadmapTasks(today));
    return bucket === "all" ? sorted : sorted.filter((task) => bucketForTask(task, today) === bucket);
  }, [statusFilteredTasks, bucket, today]);

  const timelineTasks = useMemo(
    () =>
      filteredTasks
        .filter(
          (task) =>
            (task.status === "todo" || task.status === "in_progress") &&
            (task.due_date || task.is_timeline_marker)
        )
        .sort(compareRoadmapTasks(today)),
    [filteredTasks, today]
  );
  const activeTaskList = viewMode === "timeline" ? timelineTasks : bucketedTasks;
  const totalTaskPages = Math.max(1, Math.ceil(activeTaskList.length / DEFAULT_PAGE_SIZE));
  const visibleTimelineTasks = timelineTasks.slice(
    (taskPage - 1) * DEFAULT_PAGE_SIZE,
    taskPage * DEFAULT_PAGE_SIZE
  );
  const visibleBucketedTasks = bucketedTasks.slice(
    (taskPage - 1) * DEFAULT_PAGE_SIZE,
    taskPage * DEFAULT_PAGE_SIZE
  );

  useEffect(() => {
    setTaskPage(1);
  }, [filters, bucket, viewMode, statusScope]);

  useEffect(() => {
    if (taskPage > totalTaskPages) {
      setTaskPage(totalTaskPages);
    }
  }, [taskPage, totalTaskPages]);

  const overview = useMemo(() => {
    const tasks = plan?.tasks ?? [];
    const urgent = tasks.filter((t) => t.priority === "urgent" && t.status === "todo").length;
    const upcoming = tasks.filter((t) => {
      if (!t.due_date || t.status === "completed" || t.status === "skipped") return false;
      const due = new Date(`${t.due_date}T00:00:00`);
      const days = Math.ceil((due.getTime() - today.getTime()) / 86_400_000);
      return days >= 0 && days <= 30;
    }).length;
    const completed = tasks.filter((t) => t.status === "completed").length;
    const profileGaps = tasks.filter(
      (t) => t.source_type === "profile_gap" && t.status === "todo"
    ).length;
    return { total: tasks.length, urgent, upcoming, completed, profileGaps };
  }, [plan, today]);

  const examPlanningTasks = useMemo(
    () =>
      (plan?.tasks ?? [])
        .filter(
          (task) =>
            task.category === "exams" &&
            task.source_type === "planning_window" &&
            task.status !== "completed" &&
            task.status !== "skipped"
        )
        .slice(0, 3),
    [plan]
  );

  const completedTasks = useMemo(
    () =>
      actionableTasks
        .filter((task) => task.status === "completed")
        .sort((left, right) => {
          const leftDate = left.completed_at || left.updated_at;
          const rightDate = right.completed_at || right.updated_at;
          return rightDate.localeCompare(leftDate);
        }),
    [actionableTasks]
  );

  function clearAllFilters() {
    setFilters(emptyFilters);
    setStatusScope("active");
    setBucket("all");
  }
  const activeFilterCount = [
    ...Object.values(filters).map((value) => Boolean(value)),
    statusScope !== "active",
    bucket !== "all"
  ].filter(Boolean).length;

  if (isLoading && !plan) {
    return (
      <div className="space-y-3">
        <SkeletonRow />
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          <SkeletonCards count={6} />
        </div>
      </div>
    );
  }

  if (hasError) {
    return (
      <Card>
        <p className="text-sm text-danger" role="alert">
          {t("roadmap.states.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void loadRoadmap()} type="button">
          {t("roadmap.actions.retry")}
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
              {t("roadmap.list.eyebrow")}
            </p>
            <h1 className="mt-2 max-w-3xl text-3xl font-semibold sm:text-4xl">
              {t("roadmap.list.title")}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              {plan?.summary || t("roadmap.list.description")}
            </p>
            {plan ? (
              <p className="mt-2 text-xs text-muted-foreground">
                {t("roadmap.list.lastGenerated", {
                  date: formatDateTime(plan.last_refreshed_at, locale)
                })}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <RoadmapViewToggle onChange={handleViewModeChange} value={viewMode} />
            <Button disabled={isGenerating} onClick={() => void handleGenerate()} type="button">
              <RefreshCw aria-hidden className="mr-2 size-4" />
              {isGenerating
                ? t("roadmap.actions.generating")
                : plan
                  ? t("roadmap.actions.refresh")
                  : t("roadmap.actions.generate")}
            </Button>
            <Button onClick={openCreateForm} type="button" variant="secondary">
              <Plus aria-hidden className="mr-2 size-4" />
              {t("roadmap.actions.addTask")}
            </Button>
          </div>
        </div>
      </section>

      {actionError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("roadmap.states.actionError")}
          </p>
        </Card>
      ) : null}

      <Card className="p-5">
        <button
          className="flex w-full items-center justify-between gap-3 text-left"
          onClick={toggleInstructions}
          type="button"
        >
          <span className="flex items-center gap-3">
            <HelpCircle aria-hidden className="size-4 shrink-0 text-accent" />
            <span>
              <span className="block text-sm font-semibold">
                {t("roadmap.instructions.title")}
              </span>
              <span className="block text-xs text-muted-foreground">
                {t("roadmap.instructions.summary")}
              </span>
            </span>
          </span>
          <ChevronDown
            aria-hidden
            className={`size-4 shrink-0 transition-transform ${instructionsOpen ? "rotate-180" : ""}`}
          />
        </button>
        {instructionsOpen ? (
          <div className="mt-4 grid gap-3 border-t pt-4 text-xs leading-5 text-muted-foreground md:grid-cols-2">
            <p>{t("roadmap.instructions.generatedFrom")}</p>
            <p>{t("roadmap.instructions.officialVsPlanning")}</p>
            <p>{t("roadmap.instructions.completeSkip")}</p>
            <p>{t("roadmap.instructions.refresh")}</p>
            <p>{t("roadmap.instructions.duplicates")}</p>
            <p>{t("roadmap.instructions.missingData")}</p>
          </div>
        ) : null}
      </Card>

      {plan && plan.readiness_snapshot.missing_data_warnings.length > 0 ? (
        <Card className="border-warning/30 bg-warning/10">
          <div className="flex items-start gap-3">
            <AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0 text-warning" />
            <div>
              <p className="text-sm font-semibold text-warning">
                {t("roadmap.states.missingDataTitle")}
              </p>
              <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                {plan.readiness_snapshot.missing_data_warnings.map((code) => (
                  <li key={code}>{t(`roadmap.warnings.${code}` as TranslationKey)}</li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      ) : null}

      {isFormOpen ? (
        <RoadmapTaskForm
          isSubmitting={false}
          onCancel={() => {
            setIsFormOpen(false);
            setEditingTask(null);
          }}
          onSubmit={handleFormSubmit}
          task={editingTask}
        />
      ) : null}

      {!plan ? (
        <Card>
          <Route aria-hidden className="size-5 text-accent" />
          <h2 className="mt-3 text-xl font-semibold">{t("roadmap.states.emptyTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{t("roadmap.states.emptyDescription")}</p>
          <Button className="mt-4" disabled={isGenerating} onClick={() => void handleGenerate()} type="button">
            {t("roadmap.actions.generate")}
          </Button>
        </Card>
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <OverviewCard icon={ListTodo} label={t("roadmap.overview.total")} value={overview.total} />
            <OverviewCard
              icon={AlertTriangle}
              label={t("roadmap.overview.urgent")}
              value={overview.urgent}
              tone="danger"
            />
            <OverviewCard
              icon={CalendarClock}
              label={t("roadmap.overview.upcoming")}
              value={overview.upcoming}
              tone="warning"
            />
            <OverviewCard
              icon={CheckCircle2}
              label={t("roadmap.overview.completed")}
              value={overview.completed}
              tone="success"
            />
            <OverviewCard
              icon={Route}
              label={t("roadmap.overview.profileGaps")}
              value={overview.profileGaps}
            />
          </section>

          {examPlanningTasks.length > 0 ? (
            <Card className="p-5">
              <div className="flex items-start gap-3">
                <CalendarClock aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                    {t("roadmap.examPlanning.eyebrow")}
                  </p>
                  <h2 className="mt-1 text-lg font-semibold">{t("roadmap.examPlanning.title")}</h2>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {t("roadmap.examPlanning.description")}
                  </p>
                </div>
              </div>
              <ul className="mt-4 grid gap-3 md:grid-cols-3">
                {examPlanningTasks.map((task) => (
                  <li className="rounded-sm border bg-surface p-3 text-sm" key={task.id}>
                    <p className="font-semibold">{task.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {task.due_date
                        ? t("roadmap.examPlanning.window", {
                            date: formatDate(task.due_date, locale)
                          })
                        : t("roadmap.examPlanning.windowMissing")}
                    </p>
                    {task.evidence_note ? (
                      <p className="mt-2 border-t pt-2 text-xs leading-5 text-muted-foreground">
                        {task.evidence_note}
                      </p>
                    ) : null}
                    <p className="mt-2 text-xs font-semibold text-primary-hover">
                      {t("roadmap.examPlanning.kept")}
                    </p>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          <SuggestionPanel
            defaultOpen={false}
            description={t("roadmap.suggestions.description")}
            isLoading={isSuggestionsLoading}
            isRefreshing={isRefreshingSuggestions}
            loadError={suggestionsLoadError}
            loadErrorMessage={t("suggestions.states.loadError")}
            onAddToRoadmap={(suggestion) => void handleAddSuggestion(suggestion)}
            onDismiss={(suggestion) => void handleDismissSuggestion(suggestion)}
            onGenerate={() => void handleRefreshSuggestions()}
            onOpen={() => void loadSuggestions()}
            suggestions={suggestions}
            title={t("roadmap.suggestions.title")}
          />

          <CollapsibleFilterPanel
            activeCount={activeFilterCount}
            onClear={clearAllFilters}
            resultCount={bucketedTasks.length}
            storageKey="uniway.filters.roadmap"
          >
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold">{t("roadmap.filters.title")}</h2>
                <span className="rounded-sm border border-accent/30 bg-accent/10 px-2 py-0.5 text-[0.68rem] font-medium text-accent">
                  {t("roadmap.filters.autoApply")}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {t("roadmap.filters.resultCount", { count: bucketedTasks.length })}
              </span>
            </div>
            <form className="space-y-4">
              <section className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                  {t("roadmap.filters.group.taskType")}
                </h3>
                <div className="grid gap-3 sm:grid-cols-3">
                  <label className="block">
                    <span className="text-xs font-semibold">{t("roadmap.filters.category")}</span>
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        setFilters((current) => ({ ...current, category: event.target.value }))
                      }
                      value={filters.category}
                    >
                      <option value="">{t("roadmap.filters.all")}</option>
                      {[
                        "profile",
                        "exams",
                        "essays",
                        "universities",
                        "scholarships",
                        "activities",
                        "research",
                        "portfolio",
                        "deadlines",
                        "events",
                        "recommendations"
                      ].map((category) => (
                        <option key={category} value={category}>
                          {t(`roadmap.category.${category}` as TranslationKey)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="flex items-center gap-1 text-xs font-semibold">
                      {t("roadmap.filters.priority")}
                      <HelpTooltip label={t("help.roadmapPriority")} />
                    </span>
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        setFilters((current) => ({ ...current, priority: event.target.value }))
                      }
                      value={filters.priority}
                    >
                      <option value="">{t("roadmap.filters.all")}</option>
                      {["low", "medium", "high", "urgent"].map((priority) => (
                        <option key={priority} value={priority}>
                          {t(`roadmap.priority.${priority}` as TranslationKey)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold">{t("roadmap.filters.taskKind")}</span>
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        setFilters((current) => ({ ...current, taskKind: event.target.value }))
                      }
                      value={filters.taskKind}
                    >
                      <option value="">{t("roadmap.filters.all")}</option>
                      <option value="manual">{t("roadmap.task.kind.manual")}</option>
                      <option value="generated">{t("roadmap.task.kind.generated")}</option>
                    </select>
                  </label>
                </div>
              </section>

              <section className="space-y-3 border-t pt-4">
                <h3 className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                  {t("roadmap.filters.group.linkedItems")}
                </h3>
                <div className="grid gap-3 sm:grid-cols-3">
                  <label className="block">
                    <span className="text-xs font-semibold">{t("roadmap.filters.university")}</span>
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        setFilters((current) => ({ ...current, university: event.target.value }))
                      }
                      value={filters.university}
                    >
                      <option value="">{t("roadmap.filters.all")}</option>
                      {universityOptions.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold">{t("roadmap.filters.application")}</span>
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        setFilters((current) => ({ ...current, application: event.target.value }))
                      }
                      value={filters.application}
                    >
                      <option value="">{t("roadmap.filters.all")}</option>
                      {applicationOptions.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold">{t("roadmap.filters.exam")}</span>
                    <input
                      className={fieldClassName}
                      onChange={(event) =>
                        setFilters((current) => ({ ...current, exam: event.target.value }))
                      }
                      placeholder={t("roadmap.filters.examPlaceholder")}
                      value={filters.exam}
                    />
                  </label>
                </div>
              </section>

              <section className="space-y-3 border-t pt-4">
                <h3 className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                  {t("roadmap.filters.group.timingSource")}
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block">
                    <span className="text-xs font-semibold">{t("roadmap.filters.sourceType")}</span>
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        setFilters((current) => ({ ...current, sourceType: event.target.value }))
                      }
                      value={filters.sourceType}
                    >
                      <option value="">{t("roadmap.filters.all")}</option>
                      {ROADMAP_SOURCE_TYPES.map((sourceType) => (
                        <option key={sourceType} value={sourceType}>
                          {t(`roadmap.source.${sourceType}` as TranslationKey)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="block">
                    <span className="text-xs font-semibold">{t("roadmap.filters.dueRange")}</span>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        aria-label={t("roadmap.filters.dueAfter")}
                        className={fieldClassName}
                        onChange={(event) =>
                          setFilters((current) => ({ ...current, dueAfter: event.target.value }))
                        }
                        type="date"
                        value={filters.dueAfter}
                      />
                      <input
                        aria-label={t("roadmap.filters.dueBefore")}
                        className={fieldClassName}
                        onChange={(event) =>
                          setFilters((current) => ({ ...current, dueBefore: event.target.value }))
                        }
                        type="date"
                        value={filters.dueBefore}
                      />
                    </div>
                  </div>
                </div>
              </section>

            </form>
          </CollapsibleFilterPanel>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                {STATUS_SCOPES.map((value) => (
                  <Button
                    key={value}
                    onClick={() => setStatusScope(value)}
                    size="sm"
                    type="button"
                    variant={statusScope === value ? "primary" : "ghost"}
                  >
                    {t(`roadmap.statusScope.${value}` as TranslationKey)}
                  </Button>
                ))}
              </div>
              <RoadmapViewToggle onChange={handleViewModeChange} value={viewMode} />
            </div>
            {viewMode === "list" ? (
              <div className="flex flex-wrap gap-2">
                {BUCKET_FILTERS.map((value) => (
                  <Button
                    key={value}
                    onClick={() => setBucket(value)}
                    size="sm"
                    type="button"
                    variant={bucket === value ? "secondary" : "ghost"}
                  >
                    {t(`roadmap.bucket.${value}` as TranslationKey)}
                  </Button>
                ))}
              </div>
            ) : null}
          </div>

          {viewMode === "timeline" ? (
            <Card>
              <h2 className="text-sm font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                {t("roadmap.timeline.title")}
              </h2>
              {timelineTasks.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">{t("roadmap.states.emptyFilter")}</p>
              ) : (
                <PaginatedList
                  className="mt-3"
                  currentPage={taskPage}
                  getItemKey={(task) => task.id}
                  items={visibleTimelineTasks}
                  onPageChange={setTaskPage}
                  totalCount={timelineTasks.length}
                  totalPages={totalTaskPages}
                  renderItem={(task) => (
                    <div className="flex flex-col gap-1 border-l-2 border-primary pl-3 text-sm sm:flex-row sm:items-center sm:gap-3">
                      <span className="w-24 shrink-0 text-xs text-muted-foreground">
                        {task.due_date ? formatDate(task.due_date, locale) : t("roadmap.timeline.noDate")}
                      </span>
                      <span className="font-semibold">{task.title}</span>
                      <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
                        {task.is_timeline_marker
                          ? t("roadmap.timeline.marker")
                          : t("roadmap.timeline.task")}
                      </span>
                    </div>
                  )}
                />
              )}
            </Card>
          ) : bucketedTasks.length === 0 ? (
            <Card>
              <p className="text-sm text-muted-foreground">{t("roadmap.states.emptyFilter")}</p>
            </Card>
          ) : (
            <PaginatedGrid
              currentPage={taskPage}
              getItemKey={(task) => task.id}
              items={visibleBucketedTasks}
              onPageChange={setTaskPage}
              totalCount={bucketedTasks.length}
              totalPages={totalTaskPages}
              renderItem={(task) => (
                <RoadmapTaskCardWithDelete
                  isPending={pendingTaskId === task.id}
                  onComplete={(item) => void handleComplete(item)}
                  onDelete={(item) => void handleDelete(item)}
                  onDismiss={(item) => void handleSkip(item)}
                  onEdit={openEditForm}
                  onSkip={(item) => void handleSkip(item)}
                  task={task}
                />
              )}
            />
          )}

          {viewMode === "list" && statusScope === "active" && completedTasks.length > 0 ? (
            <Card className="p-5">
              <button
                className="flex w-full items-center justify-between gap-3 text-left"
                onClick={() => setCompletedOpen((current) => !current)}
                type="button"
              >
                <span>
                  <span className="block text-sm font-semibold">
                    {t("roadmap.completed.title", { count: completedTasks.length })}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {t("roadmap.completed.description")}
                  </span>
                </span>
                <ChevronDown
                  aria-hidden
                  className={`size-4 shrink-0 transition-transform ${completedOpen ? "rotate-180" : ""}`}
                />
              </button>
              {completedOpen ? (
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {completedTasks.slice(0, 6).map((task) => (
                    <RoadmapTaskCard
                      isPending={pendingTaskId === task.id}
                      key={task.id}
                      onComplete={(item) => void handleComplete(item)}
                      onDelete={(item) => void handleDelete(item)}
                      onDismiss={(item) => void handleSkip(item)}
                      onEdit={openEditForm}
                      onSkip={(item) => void handleSkip(item)}
                      task={task}
                    />
                  ))}
                </div>
              ) : null}
            </Card>
          ) : null}
        </>
      )}

      <p className="text-xs leading-5 text-muted-foreground">{t("roadmap.disclaimer")}</p>
    </div>
  );
}

function RoadmapViewToggle({
  value,
  onChange
}: {
  value: RoadmapViewMode;
  onChange: (value: RoadmapViewMode) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="rounded-sm border bg-surface p-1" aria-label={t("roadmap.view.switch")}>
      <div className="flex gap-1">
        <Button
          onClick={() => onChange("list")}
          size="sm"
          type="button"
          variant={value === "list" ? "primary" : "ghost"}
        >
          <ListTodo aria-hidden className="mr-1.5 size-3.5" />
          {t("roadmap.view.list")}
        </Button>
        <Button
          onClick={() => onChange("timeline")}
          size="sm"
          type="button"
          variant={value === "timeline" ? "primary" : "ghost"}
        >
          <CalendarClock aria-hidden className="mr-1.5 size-3.5" />
          {t("roadmap.view.timeline")}
        </Button>
      </div>
    </div>
  );
}

function matchesStatusScope(task: RoadmapTask, scope: TaskStatusScope) {
  if (scope === "active") {
    return task.status === "todo" || task.status === "in_progress";
  }
  if (scope === "completed") {
    return task.status === "completed";
  }
  if (scope === "skipped") {
    return task.status === "skipped";
  }
  return true;
}

const PRIORITY_WEIGHT: Record<RoadmapTask["priority"], number> = {
  urgent: 4,
  high: 3,
  medium: 2,
  low: 1
};

function compareRoadmapTasks(today: Date) {
  return (left: RoadmapTask, right: RoadmapTask) => {
    const leftCompleted = left.completed_at || left.updated_at;
    const rightCompleted = right.completed_at || right.updated_at;
    if (left.status === "completed" && right.status === "completed") {
      return rightCompleted.localeCompare(leftCompleted);
    }
    const leftDue = left.due_date ? new Date(`${left.due_date}T00:00:00`).getTime() : null;
    const rightDue = right.due_date ? new Date(`${right.due_date}T00:00:00`).getTime() : null;
    if (leftDue !== null && rightDue !== null && leftDue !== rightDue) {
      return leftDue - rightDue;
    }
    if (leftDue !== null && rightDue === null) return -1;
    if (leftDue === null && rightDue !== null) return 1;
    const priorityDelta = PRIORITY_WEIGHT[right.priority] - PRIORITY_WEIGHT[left.priority];
    if (priorityDelta !== 0) return priorityDelta;
    const leftBucket = bucketForTask(left, today);
    const rightBucket = bucketForTask(right, today);
    if (leftBucket !== rightBucket) {
      const bucketOrder: Record<RoadmapBucket, number> = {
        this_week: 1,
        this_month: 2,
        later: 3,
        completed: 4
      };
      return bucketOrder[leftBucket] - bucketOrder[rightBucket];
    }
    return left.created_at.localeCompare(right.created_at);
  };
}

function OverviewCard({
  icon: Icon,
  label,
  value,
  tone
}: {
  icon: typeof ListTodo;
  label: string;
  value: number;
  tone?: "danger" | "warning" | "success";
}) {
  const toneClass =
    tone === "danger"
      ? "text-danger"
      : tone === "warning"
        ? "text-warning"
        : tone === "success"
          ? "text-success"
          : "text-accent";
  return (
    <Card className="p-4">
      <Icon aria-hidden className={`size-4 ${toneClass}`} />
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </Card>
  );
}

function RoadmapTaskCardWithDelete({
  task,
  onComplete,
  onSkip,
  onEdit,
  onDelete,
  onDismiss,
  isPending
}: {
  task: RoadmapTask;
  onComplete: (task: RoadmapTask) => void;
  onSkip: (task: RoadmapTask) => void;
  onEdit: (task: RoadmapTask) => void;
  onDelete: (task: RoadmapTask) => void;
  onDismiss: (task: RoadmapTask) => void;
  isPending?: boolean;
}) {
  return (
    <RoadmapTaskCard
      isPending={isPending}
      onComplete={onComplete}
      onDelete={onDelete}
      onDismiss={onDismiss}
      onEdit={onEdit}
      onSkip={onSkip}
      task={task}
    />
  );
}
