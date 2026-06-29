"use client";

import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
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
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate, formatDateTime } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";

const BUCKETS: RoadmapBucket[] = ["this_week", "this_month", "later", "completed"];
type TaskBucketFilter = RoadmapBucket | "all";

const BUCKET_FILTERS: TaskBucketFilter[] = ["all", ...BUCKETS];

const emptyFilters = { category: "", priority: "", status: "", university: "" };

export function RoadmapScreen() {
  const { locale, t } = useI18n();
  const [plan, setPlan] = useState<RoadmapPlan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [bucket, setBucket] = useState<TaskBucketFilter>("all");
  const [timelineMode, setTimelineMode] = useState(false);
  const [filters, setFilters] = useState(emptyFilters);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<RoadmapTask | null>(null);
  const [pendingTaskId, setPendingTaskId] = useState<number | null>(null);
  const [actionError, setActionError] = useState(false);

  const loadRoadmap = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getRoadmapRequest();
      setPlan(response.plan);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRoadmap();
  }, [loadRoadmap]);

  async function handleGenerate() {
    setIsGenerating(true);
    setActionError(false);
    try {
      const response = await generateRoadmapRequest();
      setPlan(response.plan);
    } catch {
      setActionError(true);
    } finally {
      setIsGenerating(false);
    }
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

  const filteredTasks = useMemo(() => {
    if (!plan) return [];
    return plan.tasks.filter((task) => {
      if (filters.category && task.category !== filters.category) return false;
      if (filters.priority && task.priority !== filters.priority) return false;
      if (filters.status && task.status !== filters.status) return false;
      if (filters.university && task.linked_university_name !== filters.university) return false;
      return true;
    });
  }, [plan, filters]);

  const bucketedTasks = useMemo(
    () =>
      bucket === "all"
        ? filteredTasks
        : filteredTasks.filter((task) => bucketForTask(task, today) === bucket),
    [filteredTasks, bucket, today]
  );

  const timelineTasks = useMemo(
    () =>
      filteredTasks
        .filter((task) => task.status === "todo" || task.status === "in_progress")
        .sort((left, right) => {
          if (!left.due_date && !right.due_date) return 0;
          if (!left.due_date) return 1;
          if (!right.due_date) return -1;
          return left.due_date.localeCompare(right.due_date);
        }),
    [filteredTasks]
  );

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

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">{t("roadmap.states.loading")}</p>
      </Card>
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
          <div className="flex flex-wrap gap-3">
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

          <Card>
            <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
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
                <span className="text-xs font-semibold">{t("roadmap.filters.priority")}</span>
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
                <span className="text-xs font-semibold">{t("roadmap.filters.status")}</span>
                <select
                  className={fieldClassName}
                  onChange={(event) =>
                    setFilters((current) => ({ ...current, status: event.target.value }))
                  }
                  value={filters.status}
                >
                  <option value="">{t("roadmap.filters.all")}</option>
                  {["todo", "in_progress", "completed", "skipped"].map((statusValue) => (
                    <option key={statusValue} value={statusValue}>
                      {t(`roadmap.status.${statusValue}` as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block sm:col-span-2 lg:col-span-1">
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
              <div className="flex items-end">
                <Button
                  onClick={() => setFilters(emptyFilters)}
                  type="button"
                  variant="ghost"
                >
                  {t("roadmap.filters.clear")}
                </Button>
              </div>
            </form>
          </Card>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              {BUCKET_FILTERS.map((value) => (
                <Button
                  key={value}
                  onClick={() => setBucket(value)}
                  size="sm"
                  type="button"
                  variant={bucket === value ? "primary" : "ghost"}
                >
                  {t(`roadmap.bucket.${value}` as TranslationKey)}
                </Button>
              ))}
            </div>
            <Button
              onClick={() => setTimelineMode((current) => !current)}
              size="sm"
              type="button"
              variant={timelineMode ? "secondary" : "ghost"}
            >
              {t("roadmap.actions.timelineMode")}
            </Button>
          </div>

          {timelineMode ? (
            <Card>
              <h2 className="text-sm font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                {t("roadmap.timeline.title")}
              </h2>
              {timelineTasks.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">{t("roadmap.states.emptyFilter")}</p>
              ) : (
                <ol className="mt-3 space-y-2">
                  {timelineTasks.map((task) => (
                    <li className="flex items-center gap-3 border-l-2 border-primary pl-3 text-sm" key={task.id}>
                      <span className="w-24 shrink-0 text-xs text-muted-foreground">
                        {task.due_date ? formatDate(task.due_date, locale) : t("roadmap.timeline.noDate")}
                      </span>
                      <span className="font-semibold">{task.title}</span>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          ) : bucketedTasks.length === 0 ? (
            <Card>
              <p className="text-sm text-muted-foreground">{t("roadmap.states.emptyFilter")}</p>
            </Card>
          ) : (
            <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {bucketedTasks.map((task) => (
                <RoadmapTaskCardWithDelete
                  isPending={pendingTaskId === task.id}
                  key={task.id}
                  onComplete={(item) => void handleComplete(item)}
                  onDelete={(item) => void handleDelete(item)}
                  onEdit={openEditForm}
                  onSkip={(item) => void handleSkip(item)}
                  task={task}
                />
              ))}
            </section>
          )}
        </>
      )}

      <p className="text-xs leading-5 text-muted-foreground">{t("roadmap.disclaimer")}</p>
    </div>
  );
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
  isPending
}: {
  task: RoadmapTask;
  onComplete: (task: RoadmapTask) => void;
  onSkip: (task: RoadmapTask) => void;
  onEdit: (task: RoadmapTask) => void;
  onDelete: (task: RoadmapTask) => void;
  isPending?: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className="space-y-2">
      <RoadmapTaskCard
        isPending={isPending}
        onComplete={onComplete}
        onEdit={onEdit}
        onSkip={onSkip}
        task={task}
      />
      {task.source_type === "manual" ? (
        <Button
          className="text-xs"
          disabled={isPending}
          onClick={() => onDelete(task)}
          size="sm"
          type="button"
          variant="ghost"
        >
          {t("roadmap.actions.delete")}
        </Button>
      ) : null}
    </div>
  );
}
