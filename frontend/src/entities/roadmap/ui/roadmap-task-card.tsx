"use client";

import { Archive, Check, ChevronDown, ExternalLink, Pencil, SkipForward, Trash2 } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import type { RoadmapTask } from "@/entities/roadmap";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { HelpTooltip } from "@/shared/ui/help-tooltip";

const PRIORITY_STYLES: Record<string, string> = {
  low: "border-muted-foreground/30 bg-surface text-muted-foreground",
  medium: "border-accent/35 bg-accent/10 text-accent",
  high: "border-warning/35 bg-warning/10 text-warning",
  urgent: "border-danger/35 bg-danger/10 text-danger"
};

export function RoadmapTaskCard({
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
  onDelete?: (task: RoadmapTask) => void;
  onDismiss?: (task: RoadmapTask) => void;
  isPending?: boolean;
}) {
  const { locale, t } = useI18n();
  const [detailsOpen, setDetailsOpen] = useState(false);
  const isDone = task.status === "completed" || task.status === "skipped";
  const daysRemaining = useMemo(() => {
    if (!task.due_date) return null;
    const due = new Date(`${task.due_date}T00:00:00`);
    const today = new Date(new Date().toDateString());
    return Math.ceil((due.getTime() - today.getTime()) / 86_400_000);
  }, [task.due_date]);
  const whereToDoIt = task.source_url
    ? t("roadmap.task.where.source")
    : task.linked_university_name
      ? task.linked_university_name
      : task.linked_event_title
        ? task.linked_event_title
        : task.linked_profile_section
          ? t("roadmap.task.where.profile")
          : t("roadmap.task.where.default");
  const verificationStatus = task.source_url
    ? t("roadmap.task.verification.sourceAvailable")
    : task.source_type === "planning_window"
      ? t("roadmap.task.verification.planningOnly")
      : t("roadmap.task.verification.verifyOfficial");

  return (
    <Card className="flex h-full flex-col gap-2 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
          {t(`roadmap.category.${task.category}` as TranslationKey)}
        </span>
        <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
          {t(`roadmap.task.kind.${task.task_kind}` as TranslationKey)}
        </span>
        <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
          {t(`roadmap.source.${task.source_type}` as TranslationKey)}
        </span>
        <span
          className={`inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${PRIORITY_STYLES[task.priority]}`}
        >
          {t(`roadmap.priority.${task.priority}` as TranslationKey)}
          <HelpTooltip label={t("help.roadmapPriority")} />
        </span>
        {task.status === "completed" ? (
          <span className="rounded-sm border border-success/35 bg-success/10 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-success">
            {t("roadmap.status.completed")}
          </span>
        ) : null}
        {task.status === "skipped" ? (
          <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
            {t("roadmap.status.skipped")}
          </span>
        ) : null}
      </div>

      <h3 className="text-base font-semibold">{task.title}</h3>
      {task.description ? (
        <p className="text-sm leading-5 text-muted-foreground">{task.description}</p>
      ) : null}

      <dl className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {task.due_date ? (
          <div>
            <dt className="inline font-semibold">{t("roadmap.task.due")}: </dt>
            <dd className="inline">{formatDate(task.due_date, locale)}</dd>
          </div>
        ) : null}
        {daysRemaining !== null ? (
          <div>
            <dt className="inline font-semibold">{t("roadmap.task.daysRemaining")}: </dt>
            <dd className="inline">
              {daysRemaining >= 0
                ? t("roadmap.task.daysRemainingValue", { days: daysRemaining })
                : t("roadmap.task.overdueValue", { days: Math.abs(daysRemaining) })}
            </dd>
          </div>
        ) : null}
        {task.linked_university_name ? (
          <div>
            <dt className="inline font-semibold">{t("roadmap.task.university")}: </dt>
            <dd className="inline">
              {task.linked_university_slug ? (
                <Link
                  className="text-primary-hover hover:underline"
                  href={`/universities/${task.linked_university_slug}`}
                >
                  {task.linked_university_name}
                </Link>
              ) : (
                task.linked_university_name
              )}
            </dd>
          </div>
        ) : null}
        {task.linked_application_university_name ? (
          <div>
            <dt className="inline font-semibold">{t("roadmap.task.application")}: </dt>
            <dd className="inline">{task.linked_application_university_name}</dd>
          </div>
        ) : null}
        {task.linked_event_title ? (
          <div>
            <dt className="inline font-semibold">{t("roadmap.task.event")}: </dt>
            <dd className="inline">{task.linked_event_title}</dd>
          </div>
        ) : null}
      </dl>

      <button
        className="mt-1 flex items-center justify-between border-t pt-2 text-left text-xs font-semibold text-primary-hover"
        onClick={() => setDetailsOpen((current) => !current)}
        type="button"
      >
        <span>{t("roadmap.task.details")}</span>
        <ChevronDown
          aria-hidden
          className={`size-3.5 shrink-0 transition-transform ${detailsOpen ? "rotate-180" : ""}`}
        />
      </button>

      {detailsOpen ? (
        <div className="grid gap-2 text-xs leading-5 text-muted-foreground">
          <p>
            <span className="font-semibold text-foreground">{t("roadmap.task.whatThisMeans")}: </span>
            {task.description || t("roadmap.task.whatFallback")}
          </p>
          <p>
            <span className="font-semibold text-foreground">{t("roadmap.task.whyThisMatters")}: </span>
            {task.generated_reason || task.evidence_note || t("roadmap.task.whyFallback")}
          </p>
          <p>
            <span className="font-semibold text-foreground">{t("roadmap.task.whereToDoIt")}: </span>
            {whereToDoIt}
          </p>
          <p>
            <span className="font-semibold text-foreground">{t("roadmap.task.verificationStatus")}: </span>
            {verificationStatus}
          </p>
          {task.evidence_note ? (
            <p>
              <span className="font-semibold text-foreground">{t("roadmap.task.evidence")}: </span>
              {task.evidence_note}
            </p>
          ) : null}
          {task.source_url ? (
            <a
              className="inline-flex items-center gap-1 font-semibold text-primary-hover hover:underline"
              href={task.source_url}
              rel="noreferrer"
              target="_blank"
            >
              {t("roadmap.task.source")}
              <ExternalLink aria-hidden className="size-3" />
            </a>
          ) : null}
        </div>
      ) : null}

      <div className="mt-auto flex flex-wrap gap-2 pt-2">
        {!isDone ? (
          <Button disabled={isPending} onClick={() => onComplete(task)} size="sm" type="button">
            <Check aria-hidden className="mr-1.5 size-3.5" />
            {t("roadmap.actions.complete")}
          </Button>
        ) : null}
        {!isDone ? (
          <Button
            disabled={isPending}
            onClick={() => onSkip(task)}
            size="sm"
            type="button"
            variant="ghost"
          >
            <SkipForward aria-hidden className="mr-1.5 size-3.5" />
            {t("roadmap.actions.skip")}
          </Button>
        ) : null}
        <Button disabled={isPending} onClick={() => onEdit(task)} size="sm" type="button" variant="secondary">
          <Pencil aria-hidden className="mr-1.5 size-3.5" />
          {t("roadmap.actions.edit")}
        </Button>
        {task.task_kind === "manual" && onDelete ? (
          <Button disabled={isPending} onClick={() => onDelete(task)} size="sm" type="button" variant="ghost">
            <Trash2 aria-hidden className="mr-1.5 size-3.5" />
            {t("roadmap.actions.delete")}
          </Button>
        ) : null}
        {task.task_kind === "generated" && onDismiss && task.status !== "skipped" ? (
          <Button disabled={isPending} onClick={() => onDismiss(task)} size="sm" type="button" variant="ghost">
            <Archive aria-hidden className="mr-1.5 size-3.5" />
            {t("roadmap.actions.dismiss")}
          </Button>
        ) : null}
      </div>
    </Card>
  );
}
