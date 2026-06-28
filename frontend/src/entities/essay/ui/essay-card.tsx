"use client";

import { FileText } from "lucide-react";

import type { EssayWorkspace } from "@/entities/essay";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const STATUS_STYLES: Record<string, string> = {
  not_started: "border-muted-foreground/30 bg-surface text-muted-foreground",
  drafting: "border-accent/35 bg-accent/10 text-accent",
  needs_revision: "border-warning/35 bg-warning/10 text-warning",
  reviewed: "border-accent/35 bg-accent/10 text-accent",
  ready: "border-success/35 bg-success/10 text-success",
  submitted: "border-navy/35 bg-navy/10 text-navy"
};

export function EssayCard({
  essay,
  isSelected,
  onSelect
}: {
  essay: EssayWorkspace;
  isSelected?: boolean;
  onSelect: (essay: EssayWorkspace) => void;
}) {
  const { locale, t } = useI18n();

  return (
    <Card
      className={`flex flex-col gap-2 p-4 ${isSelected ? "border-primary/60" : ""}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-sm border bg-surface px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
          {t(`essays.type.${essay.essay_type}` as TranslationKey)}
        </span>
        <span
          className={`rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${STATUS_STYLES[essay.status]}`}
        >
          {t(`essays.status.${essay.status}` as TranslationKey)}
        </span>
      </div>
      <h3 className="flex items-center gap-2 text-base font-semibold">
        <FileText aria-hidden className="size-4 shrink-0 text-accent" />
        {essay.title}
      </h3>
      {essay.university_name ? (
        <p className="text-xs text-muted-foreground">{essay.university_name}</p>
      ) : null}
      <p className="text-xs text-muted-foreground">
        {essay.word_limit
          ? t("essays.card.wordCountWithLimit", {
              count: essay.word_count,
              limit: essay.word_limit
            })
          : t("essays.card.wordCount", { count: essay.word_count })}
      </p>
      {essay.last_reviewed_at ? (
        <p className="text-xs text-muted-foreground">
          {t("essays.card.lastReviewed", { date: formatDate(essay.last_reviewed_at, locale) })}
        </p>
      ) : null}
      <Button
        className="mt-2"
        onClick={() => onSelect(essay)}
        size="sm"
        type="button"
        variant={isSelected ? "secondary" : "primary"}
      >
        {t("essays.card.open")}
      </Button>
    </Card>
  );
}
