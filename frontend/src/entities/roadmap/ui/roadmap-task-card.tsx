"use client";

import { Check, ExternalLink, Pencil, SkipForward } from "lucide-react";
import Link from "next/link";

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
  isPending
}: {
  task: RoadmapTask;
  onComplete: (task: RoadmapTask) => void;
  onSkip: (task: RoadmapTask) => void;
  onEdit: (task: RoadmapTask) => void;
  isPending?: boolean;
}) {
  const { locale, t } = useI18n();
  const isDone = task.status === "completed" || task.status === "skipped";

  return (
    <Card className="flex flex-col gap-2 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
          {t(`roadmap.category.${task.category}` as TranslationKey)}
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
        {task.linked_event_title ? (
          <div>
            <dt className="inline font-semibold">{t("roadmap.task.event")}: </dt>
            <dd className="inline">{task.linked_event_title}</dd>
          </div>
        ) : null}
      </dl>

      {task.generated_reason ? (
        <p className="border-t pt-2 text-xs leading-5 text-muted-foreground">
          <span className="font-semibold">{t("roadmap.task.reason")}: </span>
          {task.generated_reason}
        </p>
      ) : null}
      {task.evidence_note ? (
        <p className="text-xs leading-5 text-muted-foreground">
          <span className="font-semibold">{t("roadmap.task.evidence")}: </span>
          {task.evidence_note}
        </p>
      ) : null}
      {task.source_url ? (
        <a
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary-hover hover:underline"
          href={task.source_url}
          rel="noreferrer"
          target="_blank"
        >
          {t("roadmap.task.source")}
          <ExternalLink aria-hidden className="size-3" />
        </a>
      ) : null}

      <div className="mt-2 flex flex-wrap gap-2">
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
      </div>
    </Card>
  );
}
