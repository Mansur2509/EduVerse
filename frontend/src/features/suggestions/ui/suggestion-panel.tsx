"use client";

import { CalendarDays, ExternalLink, Plus, RefreshCw, X } from "lucide-react";

import type { SuggestedItem } from "@/entities/suggestion";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const PRIORITY_TONE: Record<SuggestedItem["priority"], string> = {
  low: "border-muted-foreground/30 bg-surface text-muted-foreground",
  medium: "border-accent/35 bg-accent/10 text-accent",
  high: "border-warning/35 bg-warning/10 text-warning",
  urgent: "border-danger/35 bg-danger/10 text-danger"
};

export function SuggestionPanel({
  title,
  description,
  suggestions,
  isLoading = false,
  isRefreshing = false,
  limit = 4,
  onGenerate,
  onAddToRoadmap,
  onDismiss
}: {
  title: string;
  description: string;
  suggestions: SuggestedItem[];
  isLoading?: boolean;
  isRefreshing?: boolean;
  limit?: number;
  onGenerate?: () => void;
  onAddToRoadmap?: (suggestion: SuggestedItem) => void;
  onDismiss?: (suggestion: SuggestedItem) => void;
}) {
  const { locale, t } = useI18n();
  const visible = suggestions.slice(0, limit);

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
            {t("suggestions.eyebrow")}
          </p>
          <h2 className="mt-1 text-lg font-semibold">{title}</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p>
        </div>
        {onGenerate ? (
          <Button
            disabled={isRefreshing}
            onClick={onGenerate}
            size="sm"
            type="button"
            variant="secondary"
          >
            <RefreshCw aria-hidden className="mr-1.5 size-3.5" />
            {isRefreshing ? t("suggestions.actions.refreshing") : t("suggestions.actions.refresh")}
          </Button>
        ) : null}
      </div>

      {isLoading ? (
        <p className="mt-4 text-sm text-muted-foreground">{t("suggestions.states.loading")}</p>
      ) : visible.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">{t("suggestions.states.empty")}</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {visible.map((suggestion) => (
            <li className="rounded-sm border bg-surface p-3 text-sm" key={suggestion.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap gap-2">
                    <span
                      className={`rounded-sm border px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wide ${PRIORITY_TONE[suggestion.priority]}`}
                    >
                      {t(`suggestions.priority.${suggestion.priority}` as TranslationKey)}
                    </span>
                    <Badge className="text-[0.68rem]">
                      {t(`suggestions.source.${suggestion.source_type}` as TranslationKey)}
                    </Badge>
                  </div>
                  <p className="mt-2 font-semibold">{suggestion.title}</p>
                  {suggestion.description ? (
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      {suggestion.description}
                    </p>
                  ) : null}
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                {suggestion.recommended_end_date ? (
                  <span className="inline-flex items-center gap-1.5">
                    <CalendarDays aria-hidden className="size-3.5 text-accent" />
                    {t("suggestions.fields.recommended")}:{" "}
                    {formatDate(suggestion.recommended_end_date, locale)}
                  </span>
                ) : null}
                {suggestion.official_deadline ? (
                  <span>
                    {t("suggestions.fields.official")}:{" "}
                    {formatDate(suggestion.official_deadline, locale)}
                  </span>
                ) : null}
                {suggestion.word_limit ? (
                  <span>
                    {t("suggestions.fields.wordLimit")}: {suggestion.word_limit}
                  </span>
                ) : null}
              </div>

              {suggestion.evidence_note ? (
                <p className="mt-2 border-t pt-2 text-xs leading-5 text-muted-foreground">
                  {suggestion.evidence_note}
                </p>
              ) : null}

              <div className="mt-3 flex flex-wrap gap-2">
                {onAddToRoadmap ? (
                  <Button
                    onClick={() => onAddToRoadmap(suggestion)}
                    size="sm"
                    type="button"
                  >
                    <Plus aria-hidden className="mr-1.5 size-3.5" />
                    {t("suggestions.actions.addToRoadmap")}
                  </Button>
                ) : null}
                {suggestion.source_url ? (
                  <a
                    className="inline-flex min-h-9 items-center gap-1.5 rounded-sm border bg-card px-3 text-xs font-semibold text-primary-hover hover:bg-elevated"
                    href={suggestion.source_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {t("suggestions.actions.source")}
                    <ExternalLink aria-hidden className="size-3.5" />
                  </a>
                ) : null}
                {onDismiss ? (
                  <Button
                    onClick={() => onDismiss(suggestion)}
                    size="sm"
                    type="button"
                    variant="ghost"
                  >
                    <X aria-hidden className="mr-1.5 size-3.5" />
                    {t("suggestions.actions.dismiss")}
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
