"use client";

import {
  CalendarDays,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Layers3,
  Plus,
  RefreshCw,
  X
} from "lucide-react";
import { useMemo, useState } from "react";

import type { SuggestedItem } from "@/entities/suggestion";
import { useI18n, type LocaleCode, type TranslationKey } from "@/shared/i18n";
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

const PRIORITY_RANK: Record<SuggestedItem["priority"], number> = {
  urgent: 4,
  high: 3,
  medium: 2,
  low: 1
};

type SuggestionGroup = {
  key: string;
  title: string;
  items: SuggestedItem[];
  primary: SuggestedItem;
  examLabel: string;
};

export function SuggestionPanel({
  title,
  description,
  suggestions,
  defaultOpen = true,
  isLoading = false,
  isRefreshing = false,
  loadError = false,
  loadErrorMessage,
  onOpen,
  onGenerate,
  onAddToRoadmap,
  onDismiss
}: {
  title: string;
  description: string;
  suggestions: SuggestedItem[];
  defaultOpen?: boolean;
  isLoading?: boolean;
  isRefreshing?: boolean;
  loadError?: boolean;
  loadErrorMessage?: string;
  limit?: number;
  onOpen?: () => void;
  onGenerate?: () => void;
  onAddToRoadmap?: (suggestion: SuggestedItem) => void | Promise<void>;
  onDismiss?: (suggestion: SuggestedItem) => void | Promise<void>;
}) {
  const { locale, t } = useI18n();
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [activeIndex, setActiveIndex] = useState(0);
  const [showAll, setShowAll] = useState(false);
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  const groups = useMemo(() => groupSuggestions(suggestions, t), [suggestions, t]);
  const safeIndex = Math.min(activeIndex, Math.max(groups.length - 1, 0));
  const activeGroup = groups[safeIndex];
  const visibleGroups = showAll ? groups : activeGroup ? [activeGroup] : [];

  function move(delta: number) {
    setActiveIndex((current) => {
      if (groups.length === 0) return 0;
      return (current + delta + groups.length) % groups.length;
    });
  }

  function toggleDetails(groupKey: string) {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  }

  async function handleAdd(item: SuggestedItem, key: string) {
    if (!onAddToRoadmap || pendingKey) return;
    setPendingKey(key);
    try {
      await onAddToRoadmap(item);
    } finally {
      setPendingKey(null);
    }
  }

  async function handleDismiss(items: SuggestedItem[], key: string) {
    if (!onDismiss || pendingKey) return;
    setPendingKey(key);
    try {
      await Promise.all(items.map((item) => onDismiss(item)));
    } finally {
      setPendingKey(null);
    }
  }

  function toggleOpen() {
    setIsOpen((current) => {
      const next = !current;
      if (next) onOpen?.();
      return next;
    });
  }

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
        <div className="flex flex-wrap gap-2">
          <Button onClick={toggleOpen} size="sm" type="button" variant="secondary">
            <ChevronDown
              aria-hidden
              className={`mr-1.5 size-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`}
            />
            {isOpen ? t("suggestions.actions.hidePanel") : t("suggestions.actions.showPanel")}
          </Button>
          {isOpen && onGenerate ? (
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
      </div>

      {!isOpen ? null : loadError ? (
        <p className="mt-4 text-sm text-warning" role="alert">
          {loadErrorMessage || t("suggestions.states.loadError")}
        </p>
      ) : isLoading ? (
        <p className="mt-4 text-sm text-muted-foreground">{t("suggestions.states.loading")}</p>
      ) : groups.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">{t("suggestions.states.empty")}</p>
      ) : (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <Layers3 aria-hidden className="size-3.5 text-accent" />
              <span>
                {t("suggestions.carousel.suggestion")} {t("suggestions.carousel.count", {
                  current: safeIndex + 1,
                  total: groups.length
                })}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {!showAll ? (
                <>
                  <Button
                    disabled={groups.length <= 1}
                    onClick={() => move(-1)}
                    size="sm"
                    type="button"
                    variant="secondary"
                  >
                    <ChevronLeft aria-hidden className="mr-1.5 size-3.5" />
                    {t("suggestions.actions.previous")}
                  </Button>
                  <Button
                    disabled={groups.length <= 1}
                    onClick={() => move(1)}
                    size="sm"
                    type="button"
                    variant="secondary"
                  >
                    {t("suggestions.actions.next")}
                    <ChevronRight aria-hidden className="ml-1.5 size-3.5" />
                  </Button>
                </>
              ) : null}
              <Button
                onClick={() => setShowAll((current) => !current)}
                size="sm"
                type="button"
                variant="ghost"
              >
                {showAll ? t("suggestions.actions.collapse") : t("suggestions.actions.showAll")}
              </Button>
            </div>
          </div>

          {!showAll && groups.length > 1 ? (
            <div aria-hidden className="flex gap-1">
              {groups.map((group, index) => (
                <span
                  className={`h-1.5 rounded-full transition-all ${
                    index === safeIndex ? "w-6 bg-primary" : "w-1.5 bg-border"
                  }`}
                  key={group.key}
                />
              ))}
            </div>
          ) : null}

          <ul className={showAll ? "grid gap-3 md:grid-cols-2 xl:grid-cols-3" : "max-w-xl"}>
            {visibleGroups.map((group) => (
              <SuggestionCard
                group={group}
                isDetailsOpen={openGroups.has(group.key)}
                isPending={pendingKey === group.key}
                key={group.key}
                locale={locale}
                onAdd={(item) => void handleAdd(item, group.key)}
                onDismiss={(items) => void handleDismiss(items, group.key)}
                onToggleDetails={() => toggleDetails(group.key)}
                t={t}
              />
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

function SuggestionCard({
  group,
  isDetailsOpen,
  isPending,
  locale,
  onAdd,
  onDismiss,
  onToggleDetails,
  t
}: {
  group: SuggestionGroup;
  isDetailsOpen: boolean;
  isPending: boolean;
  locale: LocaleCode;
  onAdd: (suggestion: SuggestedItem) => void;
  onDismiss: (suggestions: SuggestedItem[]) => void;
  onToggleDetails: () => void;
  t: ReturnType<typeof useI18n>["t"];
}) {
  const primary = group.primary;
  const suggestedDate =
    primary.recommended_end_date || primary.official_deadline || primary.recommended_start_date;
  const verificationStatus = getVerificationStatus(primary, group.examLabel, t);
  const reason = firstSentence(primary.description || primary.evidence_note);

  return (
    <li className="flex min-h-[18rem] flex-col rounded-sm border bg-surface p-4 text-sm">
      <div className="flex flex-wrap gap-2">
        <span
          className={`rounded-sm border px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wide ${PRIORITY_TONE[primary.priority]}`}
        >
          {t(`suggestions.priority.${primary.priority}` as TranslationKey)}
        </span>
        <Badge className="text-[0.68rem]">
          {t(`suggestions.source.${primary.source_type}` as TranslationKey)}
        </Badge>
        {group.items.length > 1 ? (
          <span className="rounded-sm border bg-card px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wide text-muted-foreground">
            {t("suggestions.group.grouped", { count: group.items.length })}
          </span>
        ) : null}
      </div>

      <p className="mt-3 text-base font-semibold leading-6">{group.title}</p>
      {suggestedDate ? (
        <p className="mt-2 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <CalendarDays aria-hidden className="size-3.5 text-accent" />
          {t("suggestions.fields.recommended")}: {formatDate(suggestedDate, locale)}
        </p>
      ) : null}
      <p className="mt-2 text-xs leading-5 text-muted-foreground">
        {reason || t("suggestions.reason.planningItem")}
      </p>
      <p className="mt-2 text-xs leading-5 text-muted-foreground">
        <span className="font-semibold text-foreground">{t("suggestions.fields.verificationStatus")}: </span>
        {verificationStatus}
      </p>

      <button
        className="mt-3 flex items-center justify-between border-t pt-2 text-left text-xs font-semibold text-primary-hover"
        onClick={onToggleDetails}
        type="button"
      >
        <span>{t("suggestions.actions.details")}</span>
        <ChevronDown
          aria-hidden
          className={`size-3.5 shrink-0 transition-transform ${isDetailsOpen ? "rotate-180" : ""}`}
        />
      </button>

      {isDetailsOpen ? (
        <div className="mt-2 space-y-2 text-xs leading-5 text-muted-foreground">
          {primary.evidence_note ? <p>{primary.evidence_note}</p> : null}
          {group.items.length > 1 ? (
            <ul className="space-y-2">
              {group.items.map((item) => (
                <li className="rounded-sm border bg-card p-2" key={item.id}>
                  <p className="font-semibold text-foreground">{item.title}</p>
                  {item.description ? <p className="mt-1">{firstSentence(item.description)}</p> : null}
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button disabled={isPending} onClick={() => onAdd(item)} size="sm" type="button">
                      <Plus aria-hidden className="mr-1.5 size-3.5" />
                      {t("suggestions.actions.addToRoadmap")}
                    </Button>
                    <Button
                      disabled={isPending}
                      onClick={() => onDismiss([item])}
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      <X aria-hidden className="mr-1.5 size-3.5" />
                      {t("suggestions.actions.dismiss")}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {primary.source_url ? (
            <a
              className="inline-flex items-center gap-1.5 font-semibold text-primary-hover hover:underline"
              href={primary.source_url}
              rel="noreferrer"
              target="_blank"
            >
              {t("suggestions.actions.source")}
              <ExternalLink aria-hidden className="size-3.5" />
            </a>
          ) : null}
        </div>
      ) : null}

      <div className="mt-auto flex flex-wrap gap-2 pt-4">
        <Button disabled={isPending} onClick={() => onAdd(primary)} size="sm" type="button">
          {primary.status === "added_to_roadmap" ? (
            <Check aria-hidden className="mr-1.5 size-3.5" />
          ) : (
            <Plus aria-hidden className="mr-1.5 size-3.5" />
          )}
          {primary.status === "added_to_roadmap"
            ? t("suggestions.actions.added")
            : t("suggestions.actions.addToRoadmap")}
        </Button>
        <Button
          disabled={isPending}
          onClick={() => onDismiss(group.items)}
          size="sm"
          type="button"
          variant="ghost"
        >
          <X aria-hidden className="mr-1.5 size-3.5" />
          {t("suggestions.actions.dismiss")}
        </Button>
      </div>
    </li>
  );
}

function groupSuggestions(
  suggestions: SuggestedItem[],
  t: ReturnType<typeof useI18n>["t"]
): SuggestionGroup[] {
  const grouped = new Map<string, SuggestedItem[]>();
  suggestions.forEach((suggestion) => {
    const key = suggestionGroupKey(suggestion);
    grouped.set(key, [...(grouped.get(key) ?? []), suggestion]);
  });

  return [...grouped.entries()]
    .map(([key, items]) => {
      const sortedItems = [...items].sort(compareSuggestions);
      const primary = sortedItems[0];
      const examLabel = examLabelForSuggestion(primary);
      return {
        key,
        items: sortedItems,
        primary,
        examLabel,
        title:
          sortedItems.length > 1 && examLabel
            ? t("suggestions.group.examPlanning", { exam: examLabel })
            : primary.title
      };
    })
    .sort((left, right) => compareSuggestions(left.primary, right.primary));
}

function suggestionGroupKey(suggestion: SuggestedItem) {
  const examLabel = examLabelForSuggestion(suggestion);
  if (
    examLabel &&
    (suggestion.source_type === "planning_window" ||
      suggestion.suggestion_type === "exam_plan" ||
      suggestion.suggestion_type === "exam_date" ||
      suggestion.suggestion_type === "ap_recommendation")
  ) {
    return [
      "exam",
      examLabel,
      suggestion.linked_university ?? "",
      suggestion.linked_application ?? "",
      suggestion.source_type
    ].join(":");
  }

  return [
    suggestion.suggestion_type,
    suggestion.linked_university ?? "",
    suggestion.linked_application ?? "",
    suggestion.linked_essay ?? "",
    suggestion.recommended_end_date ?? suggestion.official_deadline ?? "",
    suggestion.source_type
  ].join(":");
}

function compareSuggestions(left: SuggestedItem, right: SuggestedItem) {
  const priorityDelta = PRIORITY_RANK[right.priority] - PRIORITY_RANK[left.priority];
  if (priorityDelta !== 0) return priorityDelta;
  return dateSortValue(left) - dateSortValue(right);
}

function dateSortValue(item: SuggestedItem) {
  const value = item.recommended_end_date || item.official_deadline || item.recommended_start_date;
  return value ? new Date(`${value}T00:00:00`).getTime() : Number.MAX_SAFE_INTEGER;
}

function examLabelForSuggestion(suggestion: SuggestedItem) {
  const haystack = `${suggestion.title} ${suggestion.description} ${suggestion.evidence_note}`.toUpperCase();
  if (haystack.includes("IELTS") && haystack.includes("TOEFL")) return "IELTS/TOEFL";
  if (haystack.includes("IELTS")) return "IELTS";
  if (haystack.includes("TOEFL")) return "TOEFL";
  if (haystack.includes("SAT")) return "SAT";
  if (haystack.includes("AP")) return "AP";
  return "";
}

function getVerificationStatus(
  suggestion: SuggestedItem,
  examLabel: string,
  t: ReturnType<typeof useI18n>["t"]
) {
  if (suggestion.source_url && ["official", "verified_university_data"].includes(suggestion.source_type)) {
    return t("suggestions.status.sourceAvailable");
  }
  if ((examLabel === "SAT" || examLabel === "AP") && !suggestion.source_url) {
    return t("suggestions.status.officialDateNotVerified");
  }
  if (suggestion.source_type === "planning_window") {
    return t("suggestions.status.planningItem");
  }
  return t("suggestions.status.verifyOfficialSource");
}

function firstSentence(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  const match = trimmed.match(/^(.+?[.!?])\s/);
  return match ? match[1] : trimmed;
}
