"use client";

import { GraduationCap } from "lucide-react";

import type { ApplicationTrackerItem } from "@/entities/application";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const PRIORITY_STYLES: Record<string, string> = {
  low: "border-muted-foreground/30 bg-surface text-muted-foreground",
  medium: "border-accent/35 bg-accent/10 text-accent",
  high: "border-warning/35 bg-warning/10 text-warning",
  dream: "border-danger/35 bg-danger/10 text-danger"
};

export function ApplicationCard({
  application,
  isSelected,
  onSelect
}: {
  application: ApplicationTrackerItem;
  isSelected?: boolean;
  onSelect: (application: ApplicationTrackerItem) => void;
}) {
  const { locale, t } = useI18n();
  const incompleteCount = [
    application.essays_status !== "submitted" && application.essays_status !== "ready",
    application.recommendations_status !== "submitted" &&
      application.recommendations_status !== "received",
    application.documents_status !== "submitted" && application.documents_status !== "ready"
  ].filter(Boolean).length;

  return (
    <Card className={`flex flex-col gap-2 p-4 ${isSelected ? "border-primary/60" : ""}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${PRIORITY_STYLES[application.priority]}`}
        >
          {t(`applications.priority.${application.priority}` as TranslationKey)}
        </span>
        <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
          {t(`applications.round.${application.application_round}` as TranslationKey)}
        </span>
      </div>
      <h3 className="flex items-center gap-2 text-base font-semibold">
        <GraduationCap aria-hidden className="size-4 shrink-0 text-accent" />
        {application.university_name}
      </h3>
      {application.deadline ? (
        <p className="text-xs text-muted-foreground">
          {t("applications.card.deadline", { date: formatDate(application.deadline, locale) })}
        </p>
      ) : (
        <p className="text-xs italic text-muted-foreground">
          {t("applications.card.noDeadline")}
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        {t("applications.card.incompleteRequirements", { count: incompleteCount })}
      </p>
      <Button
        className="mt-2"
        onClick={() => onSelect(application)}
        size="sm"
        type="button"
        variant={isSelected ? "secondary" : "primary"}
      >
        {t("applications.card.open")}
      </Button>
    </Card>
  );
}
