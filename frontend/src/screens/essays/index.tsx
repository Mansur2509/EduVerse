"use client";

import { AlertTriangle, CheckCircle2, ExternalLink, Plus, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ESSAY_PRIORITIES,
  ESSAY_STATUSES,
  EssayCard,
  type AIEssayScoreReason,
  type AIEssayScoreReport,
  type EssayRevisionTask,
  type EssayWorkspace
} from "@/entities/essay";
import type { SuggestedItem } from "@/entities/suggestion";
import type { SavedUniversityLite } from "@/entities/university";
import {
  createEssayRequest,
  createEssayRevisionTaskRequest,
  deleteEssayRequest,
  generateEssayFeedbackRequest,
  generateEssaySuggestionsRequest,
  getEssaysRequest,
  getLatestEssayScoreRequest,
  scoreEssayRequest,
  updateEssayRequest,
  updateEssayRevisionTaskRequest
} from "@/features/essays";
import { EssayForm, type EssayFormValues } from "@/features/essays/ui/essay-form";
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
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { CollapsibleFilterPanel } from "@/shared/ui/collapsible-filter-panel";
import { fieldClassName } from "@/shared/ui/field";
import { HelpTooltip } from "@/shared/ui/help-tooltip";
import { LoadingNotice } from "@/shared/ui/loading-notice";
import { PaginationControls } from "@/shared/ui/pagination";
import { UnsavedChangesDialog } from "@/shared/ui/unsaved-changes-dialog";

const SCORE_FIELDS: Array<{
  key: "structure_score" | "clarity_score" | "authenticity_score" | "specificity_score" | "grammar_score" | "prompt_fit_score";
  labelKey: TranslationKey;
}> = [
  { key: "structure_score", labelKey: "essays.feedback.structure" },
  { key: "clarity_score", labelKey: "essays.feedback.clarity" },
  { key: "authenticity_score", labelKey: "essays.feedback.authenticity" },
  { key: "specificity_score", labelKey: "essays.feedback.specificity" },
  { key: "grammar_score", labelKey: "essays.feedback.grammar" },
  { key: "prompt_fit_score", labelKey: "essays.feedback.promptFit" }
];

const LABEL_STYLES: Record<string, string> = {
  weak: "border-danger/35 bg-danger/10 text-danger",
  developing: "border-warning/35 bg-warning/10 text-warning",
  solid: "border-accent/35 bg-accent/10 text-accent",
  strong: "border-success/35 bg-success/10 text-success",
  excellent: "border-success/35 bg-success/10 text-success"
};

const ESSAYS_PAGE_SIZE = 5;

type Translate = ReturnType<typeof useI18n>["t"];

function groupEssays(essays: EssayWorkspace[], t: Translate) {
  const groups = new Map<string, { key: string; label: string; items: EssayWorkspace[] }>();
  essays.forEach((essay) => {
    const universityLabel =
      essay.application_university_name ?? essay.university_name ?? t("essays.groups.general");
    const key = essay.application
      ? `application:${essay.application}`
      : essay.university
        ? `university:${essay.university}`
        : "general";
    const label =
      essay.application && essay.application_round
        ? t("essays.groups.application", {
            university: universityLabel,
            round: essay.application_round
          })
        : universityLabel;
    const existing = groups.get(key);
    if (existing) {
      existing.items.push(essay);
    } else {
      groups.set(key, { key, label, items: [essay] });
    }
  });
  return [...groups.values()];
}

export function EssaysScreen() {
  const { locale, t } = useI18n();
  const [essays, setEssays] = useState<EssayWorkspace[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [suggestions, setSuggestions] = useState<SuggestedItem[]>([]);
  const [suggestionsRequested, setSuggestionsRequested] = useState(false);
  const [isSuggestionsLoading, setIsSuggestionsLoading] = useState(false);
  const [suggestionsLoadError, setSuggestionsLoadError] = useState(false);
  const [shortlist, setShortlist] = useState<SavedUniversityLite[]>([]);
  const [isShortlistLoading, setIsShortlistLoading] = useState(false);
  const [shortlistLoadError, setShortlistLoadError] = useState(false);
  const [shortlistRequested, setShortlistRequested] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [filter, setFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEssay, setEditingEssay] = useState<EssayWorkspace | null>(null);
  const [selectedEssayId, setSelectedEssayId] = useState<number | null>(null);
  const [draftText, setDraftText] = useState("");
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isGeneratingFeedback, setIsGeneratingFeedback] = useState(false);
  const [latestScore, setLatestScore] = useState<AIEssayScoreReport | null>(null);
  const [isScoringEssay, setIsScoringEssay] = useState(false);
  const [scoreNotice, setScoreNotice] = useState<{
    reason: AIEssayScoreReason;
    quotaRemaining: number | null;
    nextAvailableAt: string | null;
  } | null>(null);
  const [actionError, setActionError] = useState(false);
  const [pendingTaskId, setPendingTaskId] = useState<number | null>(null);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [isRefreshingSuggestions, setIsRefreshingSuggestions] = useState(false);
  const [isGeneratingEssaySuggestions, setIsGeneratingEssaySuggestions] = useState(false);
  const [essaySuggestionNotice, setEssaySuggestionNotice] = useState<{
    created: number;
    existing: number;
  } | null>(null);

  // Essays are the only thing this page actually needs to render on load.
  // Shortlist and suggestions used to be fetched in the same Promise.all --
  // that meant every Essays page view also fired the (much heavier)
  // shortlist query, and a slow/failing suggestions call could visually stall
  // essays even though the essays request itself had already succeeded.
  const loadEssays = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const essaysResponse = await getEssaysRequest({ page_size: 100 });
      setEssays(essaysResponse.results);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadEssays();
  }, [loadEssays]);

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

  // Shortlist only feeds the university dropdown inside the create/edit essay
  // modal, so it is fetched lazily the first time that modal opens (lite
  // payload: id/name/slug/country/city only, not the full university record).
  useEffect(() => {
    if (!isFormOpen || shortlistRequested) return;
    let cancelled = false;
    setShortlistRequested(true);
    setIsShortlistLoading(true);
    setShortlistLoadError(false);
    getShortlistRequest({ lite: true })
      .then((response) => {
        if (cancelled) return;
        setShortlist(response.results);
      })
      .catch(() => {
        if (cancelled) return;
        setShortlistLoadError(true);
      })
      .finally(() => {
        if (!cancelled) setIsShortlistLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isFormOpen, shortlistRequested]);

  const selectedEssay = essays.find((essay) => essay.id === selectedEssayId) ?? null;
  const hasUnsavedDraftChanges = Boolean(
    selectedEssay && draftText !== selectedEssay.draft_text
  );
  const draftGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedDraftChanges
  });

  useEffect(() => {
    if (selectedEssay) {
      setDraftText(selectedEssay.draft_text);
    }
    // Reset the draft buffer only when switching to a different essay, not on
    // every background update to the selected essay (which would clobber
    // unsaved in-progress edits).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEssayId]);

  useEffect(() => {
    setScoreNotice(null);
    if (!selectedEssayId) {
      setLatestScore(null);
      return;
    }
    let cancelled = false;
    getLatestEssayScoreRequest(selectedEssayId)
      .then((response) => {
        if (!cancelled) setLatestScore(response.score);
      })
      .catch(() => {
        if (!cancelled) setLatestScore(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedEssayId]);

  function updateEssayInList(updated: EssayWorkspace) {
    setEssays((current) => current.map((essay) => (essay.id === updated.id ? updated : essay)));
  }

  const universityFilters = useMemo(() => {
    const seen = new Map<number, string>();
    essays.forEach((essay) => {
      if (essay.university && essay.university_name) {
        seen.set(essay.university, essay.university_name);
      }
    });
    return [...seen.entries()];
  }, [essays]);

  const filteredEssays = useMemo(() => {
    let result = essays;
    if (filter === "common_app") {
      result = result.filter((essay) => essay.essay_type === "common_app");
    } else if (filter === "suggested") {
      result = result.filter((essay) => essay.status === "suggested" || essay.status === "planned");
    } else if (filter !== "all") {
      const universityId = Number(filter);
      result = result.filter((essay) => essay.university === universityId);
    }
    if (priorityFilter !== "all") {
      result = result.filter((essay) => essay.priority === priorityFilter);
    }
    return result;
  }, [essays, filter, priorityFilter]);
  const totalEssayPages = Math.max(1, Math.ceil(filteredEssays.length / ESSAYS_PAGE_SIZE));
  const visibleEssays = filteredEssays.slice(
    (currentPage - 1) * ESSAYS_PAGE_SIZE,
    currentPage * ESSAYS_PAGE_SIZE
  );
  const groupedVisibleEssays = useMemo(() => groupEssays(visibleEssays, t), [visibleEssays, t]);
  const activeFilterCount = [filter !== "all", priorityFilter !== "all"].filter(Boolean).length;

  useEffect(() => {
    if (currentPage > totalEssayPages) {
      setCurrentPage(totalEssayPages);
    }
  }, [currentPage, totalEssayPages]);

  async function handleFormSubmit(values: EssayFormValues) {
    const payload = {
      title: values.title,
      essay_type: values.essay_type,
      university: values.university,
      prompt_text: values.prompt_text,
      word_limit: values.word_limit ? Number(values.word_limit) : null,
      due_date: values.due_date || null,
      source_url: values.source_url,
      notes: values.notes,
      priority: values.priority
    };
    if (editingEssay) {
      const updated = await updateEssayRequest(editingEssay.id, payload);
      updateEssayInList(updated);
    } else {
      const created = await createEssayRequest(payload);
      setEssays((current) => [created, ...current]);
      setSelectedEssayId(created.id);
    }
    setIsFormOpen(false);
    setEditingEssay(null);
  }

  async function handleSaveDraft() {
    if (!selectedEssay) return false;
    setIsSavingDraft(true);
    setActionError(false);
    try {
      const updated = await updateEssayRequest(selectedEssay.id, { draft_text: draftText });
      updateEssayInList(updated);
      setDraftText(updated.draft_text);
      return true;
    } catch {
      setActionError(true);
      return false;
    } finally {
      setIsSavingDraft(false);
    }
  }

  function discardDraftChanges() {
    if (selectedEssay) {
      setDraftText(selectedEssay.draft_text);
    }
  }

  async function handleGenerateFeedback() {
    if (!selectedEssay) return;
    setIsGeneratingFeedback(true);
    setActionError(false);
    try {
      if (draftText !== selectedEssay.draft_text) {
        await updateEssayRequest(selectedEssay.id, { draft_text: draftText });
      }
      const response = await generateEssayFeedbackRequest(selectedEssay.id);
      updateEssayInList(response.essay);
    } catch {
      setActionError(true);
    } finally {
      setIsGeneratingFeedback(false);
    }
  }

  async function handleScoreEssay() {
    if (!selectedEssay) return;
    setIsScoringEssay(true);
    setActionError(false);
    setScoreNotice(null);
    try {
      if (draftText !== selectedEssay.draft_text) {
        await updateEssayRequest(selectedEssay.id, { draft_text: draftText });
      }
      const response = await scoreEssayRequest(selectedEssay.id);
      setScoreNotice({
        reason: response.reason,
        quotaRemaining: response.quota_remaining,
        nextAvailableAt: response.next_available_at
      });
      if (response.score) {
        setLatestScore(response.score);
      }
    } catch {
      setActionError(true);
    } finally {
      setIsScoringEssay(false);
    }
  }

  async function handleStatusChange(status: EssayWorkspace["status"]) {
    if (!selectedEssay) return;
    setActionError(false);
    try {
      const updated = await updateEssayRequest(selectedEssay.id, { status });
      updateEssayInList(updated);
    } catch {
      setActionError(true);
    }
  }

  async function handleDelete(essay: EssayWorkspace) {
    setActionError(false);
    try {
      await deleteEssayRequest(essay.id);
      setEssays((current) => current.filter((item) => item.id !== essay.id));
      if (selectedEssayId === essay.id) {
        setSelectedEssayId(null);
      }
    } catch {
      setActionError(true);
    }
  }

  async function handleRevisionTaskStatus(task: EssayRevisionTask, status: string) {
    if (!selectedEssay) return;
    setPendingTaskId(task.id);
    setActionError(false);
    try {
      await updateEssayRevisionTaskRequest(task.id, { status });
      const updatedTasks = selectedEssay.revision_tasks.map((item) =>
        item.id === task.id ? { ...item, status: status as EssayRevisionTask["status"] } : item
      );
      updateEssayInList({ ...selectedEssay, revision_tasks: updatedTasks });
    } catch {
      setActionError(true);
    } finally {
      setPendingTaskId(null);
    }
  }

  async function handleAddRevisionTask() {
    if (!selectedEssay || !newTaskTitle.trim()) return;
    setActionError(false);
    try {
      const created = await createEssayRevisionTaskRequest(selectedEssay.id, {
        title: newTaskTitle.trim(),
        category: "clarity"
      });
      updateEssayInList({
        ...selectedEssay,
        revision_tasks: [...selectedEssay.revision_tasks, created]
      });
      setNewTaskTitle("");
    } catch {
      setActionError(true);
    }
  }

  const liveWordCount = draftText.trim() ? draftText.trim().split(/\s+/).length : 0;
  const essaySuggestions = suggestions.filter((suggestion) => {
    const isEssaySuggestion =
      suggestion.suggestion_type === "essay_word_limit" ||
      suggestion.suggestion_type === "essay_deadline";
    if (!isEssaySuggestion) return false;
    return selectedEssay ? suggestion.linked_essay === selectedEssay.id : true;
  });

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

  async function handleGenerateEssaySuggestions() {
    setIsGeneratingEssaySuggestions(true);
    setActionError(false);
    setEssaySuggestionNotice(null);
    try {
      const response = await generateEssaySuggestionsRequest();
      const refreshed = await getEssaysRequest({ page_size: 100 });
      setEssays(refreshed.results);
      setCurrentPage(1);
      setEssaySuggestionNotice({
        created: response.created_count,
        existing: response.existing_count
      });
      if (!selectedEssayId && response.essays[0]) {
        setSelectedEssayId(response.essays[0].id);
      }
    } catch {
      setActionError(true);
    } finally {
      setIsGeneratingEssaySuggestions(false);
    }
  }

  async function handleAddSuggestion(suggestion: SuggestedItem) {
    setActionError(false);
    try {
      await addSuggestionToRoadmapRequest(suggestion.id);
      setSuggestions((current) => current.filter((item) => item.id !== suggestion.id));
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

  if (isLoading) {
    return <LoadingNotice message={t("essays.states.loading")} />;
  }

  if (hasError) {
    return (
      <Card>
        <p className="text-sm text-danger" role="alert">
          {t("essays.states.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void loadEssays()} type="button">
          {t("essays.actions.retry")}
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
              {t("essays.list.eyebrow")}
            </p>
            <h1 className="mt-2 max-w-3xl text-3xl font-semibold sm:text-4xl">
              {t("essays.list.title")}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              {t("essays.list.description")}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={isGeneratingEssaySuggestions}
              onClick={() => void handleGenerateEssaySuggestions()}
              type="button"
              variant="secondary"
            >
              <RefreshCw aria-hidden className="mr-2 size-4" />
              {isGeneratingEssaySuggestions
                ? t("essays.actions.generatingSuggestions")
                : t("essays.actions.generateSuggestions")}
            </Button>
            <Button
              onClick={() => {
                setEditingEssay(null);
                setIsFormOpen(true);
              }}
              type="button"
            >
              <Plus aria-hidden className="mr-2 size-4" />
              {t("essays.actions.newEssay")}
            </Button>
          </div>
        </div>
      </section>

      {essaySuggestionNotice ? (
        <Card className="border-success/30 bg-success/10">
          <p className="text-sm text-success">
            {t("essays.suggestionGeneration.notice", {
              created: essaySuggestionNotice.created,
              existing: essaySuggestionNotice.existing
            })}
          </p>
        </Card>
      ) : null}

      {actionError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("essays.states.actionError")}
          </p>
        </Card>
      ) : null}

      {essays.length > 0 && essays.every((essay) => essay.prompt_verification_status !== "verified") ? (
        <Card className="border-warning/35 bg-warning/10">
          <p className="text-sm text-warning">{t("essays.states.noVerifiedPrompts")}</p>
        </Card>
      ) : null}

      {isFormOpen ? (
        <EssayForm
          essay={editingEssay}
          isShortlistLoading={isShortlistLoading}
          onCancel={() => {
            setIsFormOpen(false);
            setEditingEssay(null);
          }}
          onSubmit={handleFormSubmit}
          shortlist={shortlist}
          shortlistLoadError={shortlistLoadError}
        />
      ) : null}

      <SuggestionPanel
        defaultOpen={false}
        description={t("essays.suggestions.description")}
        isLoading={isSuggestionsLoading}
        isRefreshing={isRefreshingSuggestions}
        loadError={suggestionsLoadError}
        loadErrorMessage={t("suggestions.states.loadError")}
        onAddToRoadmap={(suggestion) => void handleAddSuggestion(suggestion)}
        onDismiss={(suggestion) => void handleDismissSuggestion(suggestion)}
        onGenerate={() => void handleRefreshSuggestions()}
        onOpen={() => void loadSuggestions()}
        suggestions={essaySuggestions}
        title={t("essays.suggestions.title")}
      />

      <CollapsibleFilterPanel
        activeCount={activeFilterCount}
        onClear={() => {
          setFilter("all");
          setPriorityFilter("all");
          setCurrentPage(1);
        }}
        resultCount={filteredEssays.length}
        storageKey="eduverse.filters.essays"
      >
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => {
              setFilter("all");
              setCurrentPage(1);
            }}
            size="sm"
            type="button"
            variant={filter === "all" ? "primary" : "ghost"}
          >
            {t("essays.filters.all")}
          </Button>
          <Button
            onClick={() => {
              setFilter("common_app");
              setCurrentPage(1);
            }}
            size="sm"
            type="button"
            variant={filter === "common_app" ? "primary" : "ghost"}
          >
            {t("essays.filters.commonApp")}
          </Button>
          <Button
            onClick={() => {
              setFilter("suggested");
              setCurrentPage(1);
            }}
            size="sm"
            type="button"
            variant={filter === "suggested" ? "primary" : "ghost"}
          >
            {t("essays.filters.suggested")}
          </Button>
          {universityFilters.map(([id, name]) => (
            <Button
              key={id}
              onClick={() => {
                setFilter(String(id));
                setCurrentPage(1);
              }}
              size="sm"
              type="button"
              variant={filter === String(id) ? "primary" : "ghost"}
            >
              {name}
            </Button>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-muted-foreground">
            {t("essays.filters.priority")}
          </span>
          <Button
            onClick={() => {
              setPriorityFilter("all");
              setCurrentPage(1);
            }}
            size="sm"
            type="button"
            variant={priorityFilter === "all" ? "primary" : "ghost"}
          >
            {t("essays.filters.all")}
          </Button>
          {ESSAY_PRIORITIES.map((priority) => (
            <Button
              key={priority}
              onClick={() => {
                setPriorityFilter(priority);
                setCurrentPage(1);
              }}
              size="sm"
              type="button"
              variant={priorityFilter === priority ? "primary" : "ghost"}
            >
              {t(`essays.priority.${priority}` as TranslationKey)}
            </Button>
          ))}
        </div>
      </CollapsibleFilterPanel>

      {essays.length === 0 ? (
        <Card>
          <p className="text-sm text-muted-foreground">
            {shortlist.length === 0
              ? t("essays.states.noApplicationsYet")
              : t("essays.states.readyToGenerate")}
          </p>
        </Card>
      ) : filteredEssays.length === 0 ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("essays.states.emptyFilter")}</p>
        </Card>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[20rem_1fr]">
          <div className="space-y-4">
            {totalEssayPages <= 1 ? (
              <p className="text-sm font-semibold text-muted-foreground">
                {t("pagination.showingRange", {
                  start: 1,
                  end: filteredEssays.length,
                  total: filteredEssays.length
                })}
              </p>
            ) : null}
            {groupedVisibleEssays.map((group) => (
              <section className="space-y-2" key={group.key}>
                <h2 className="text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">
                  {group.label}
                </h2>
                <div className="space-y-3">
                  {group.items.map((essay) => (
                    <EssayCard
                      essay={essay}
                      isSelected={essay.id === selectedEssayId}
                      key={essay.id}
                      onSelect={(item) =>
                        draftGuard.requestLeave(() => setSelectedEssayId(item.id))
                      }
                    />
                  ))}
                </div>
              </section>
            ))}
            {totalEssayPages > 1 ? (
              <PaginationControls
                currentPage={currentPage}
                itemsOnPage={visibleEssays.length}
                onPageChange={setCurrentPage}
                pageSize={ESSAYS_PAGE_SIZE}
                totalCount={filteredEssays.length}
                totalPages={totalEssayPages}
              />
            ) : null}
          </div>

          <div>
            {!selectedEssay ? (
              <Card>
                <p className="text-sm text-muted-foreground">{t("essays.states.selectEssay")}</p>
              </Card>
            ) : (
              <div className="space-y-4">
                <Card className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-xl font-semibold">{selectedEssay.title}</h2>
                      {selectedEssay.prompt_text ? (
                        <p className="mt-1 text-sm leading-5 text-muted-foreground">
                          {selectedEssay.prompt_text}
                        </p>
                      ) : null}
                      {selectedEssay.notes ? (
                        <p className="mt-2 text-xs leading-5 text-muted-foreground">
                          {selectedEssay.notes}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => draftGuard.requestLeave(() => setSelectedEssayId(null))}
                        size="sm"
                        type="button"
                        variant="ghost"
                      >
                        {t("common.actions.close")}
                      </Button>
                      <Button
                        onClick={() => {
                          setEditingEssay(selectedEssay);
                          setIsFormOpen(true);
                        }}
                        size="sm"
                        type="button"
                        variant="secondary"
                      >
                        {t("essays.actions.editDetails")}
                      </Button>
                      <Button
                        onClick={() => void handleDelete(selectedEssay)}
                        size="sm"
                        type="button"
                        variant="ghost"
                      >
                        {t("essays.actions.delete")}
                      </Button>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 rounded-sm border bg-surface p-3 text-xs text-muted-foreground sm:grid-cols-2">
                    <div>
                      <span className="font-semibold text-foreground">
                        {t("essays.editor.promptStatus")}
                      </span>
                      <p>
                        {t(`essays.verification.${selectedEssay.prompt_verification_status}` as TranslationKey)}
                        {" · "}
                        {t(`essays.confidence.${selectedEssay.prompt_confidence}` as TranslationKey)}
                      </p>
                    </div>
                    <div>
                      <span className="font-semibold text-foreground">
                        {t("essays.editor.dueDate")}
                      </span>
                      <p>
                        {selectedEssay.due_date
                          ? formatDate(selectedEssay.due_date, locale)
                          : t("essays.editor.noDueDate")}
                      </p>
                    </div>
                    {selectedEssay.source_url ? (
                      <a
                        className="inline-flex items-center gap-1 font-semibold text-primary hover:text-primary-hover"
                        href={selectedEssay.source_url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        {t("essays.editor.source")}
                        <ExternalLink aria-hidden className="size-3" />
                      </a>
                    ) : (
                      <span>{t("essays.editor.noSource")}</span>
                    )}
                  </div>

                  <label className="mt-4 block">
                    <span className="text-xs font-semibold">{t("essays.editor.draftLabel")}</span>
                    <textarea
                      className={fieldClassName}
                      onChange={(event) => setDraftText(event.target.value)}
                      rows={14}
                      value={draftText}
                    />
                  </label>
                  <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span
                      className={
                        selectedEssay.word_limit
                          ? liveWordCount > selectedEssay.word_limit
                            ? "font-semibold text-danger"
                            : liveWordCount >= selectedEssay.word_limit * 0.9
                              ? "font-semibold text-warning"
                              : "text-muted-foreground"
                          : "text-muted-foreground"
                      }
                    >
                      {selectedEssay.word_limit
                        ? t("essays.editor.wordCountWithLimit", {
                            count: liveWordCount,
                            limit: selectedEssay.word_limit
                          })
                        : t("essays.editor.wordCount", { count: liveWordCount })}
                    </span>
                    <HelpTooltip label={t("essays.help.wordLimit")} />
                    {!selectedEssay.word_limit && selectedEssay.prompt_verification_status !== "verified" ? (
                      <span className="text-muted-foreground">
                        {t("essays.editor.wordLimitNeedsVerification")}
                      </span>
                    ) : null}
                  </div>

                  <label className="mt-3 block max-w-xs">
                    <span className="text-xs font-semibold">{t("essays.editor.statusLabel")}</span>
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        void handleStatusChange(event.target.value as EssayWorkspace["status"])
                      }
                      value={selectedEssay.status}
                    >
                      {ESSAY_STATUSES.map((statusValue) => (
                        <option key={statusValue} value={statusValue}>
                          {t(`essays.status.${statusValue}` as TranslationKey)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      disabled={isSavingDraft}
                      onClick={() => void handleSaveDraft()}
                      size="sm"
                      type="button"
                      variant="secondary"
                    >
                      {isSavingDraft ? t("essays.actions.saving") : t("essays.actions.saveDraft")}
                    </Button>
                    <Button
                      disabled={isSavingDraft || !hasUnsavedDraftChanges}
                      onClick={discardDraftChanges}
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      {t("essays.actions.discardDraft")}
                    </Button>
                    <Button
                      disabled={isGeneratingFeedback}
                      onClick={() => void handleGenerateFeedback()}
                      size="sm"
                      type="button"
                    >
                      <Sparkles aria-hidden className="mr-1.5 size-3.5" />
                      {isGeneratingFeedback
                        ? t("essays.actions.analyzing")
                        : t("essays.actions.ruleBasedCheck")}
                    </Button>
                    <Button
                      disabled={isScoringEssay}
                      onClick={() => void handleScoreEssay()}
                      size="sm"
                      type="button"
                      variant="secondary"
                    >
                      <Sparkles aria-hidden className="mr-1.5 size-3.5" />
                      {isScoringEssay ? t("essays.actions.scoring") : t("essays.actions.getScore")}
                    </Button>
                    <Button
                      onClick={() => void handleStatusChange("ready")}
                      size="sm"
                      type="button"
                      variant="secondary"
                    >
                      {t("essays.actions.markReady")}
                    </Button>
                    <Button
                      onClick={() => void handleStatusChange("submitted")}
                      size="sm"
                      type="button"
                      variant="secondary"
                    >
                      {t("essays.actions.markSubmitted")}
                    </Button>
                  </div>
                </Card>

                {selectedEssay.latest_feedback ? (
                  <Card className="bg-elevated/45 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold">{t("essays.feedback.title")}</h3>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {t("essays.feedback.ruleBasedNotice")}
                        </p>
                      </div>
                      <span
                        className={`rounded-sm border px-3 py-1 text-sm font-semibold ${LABEL_STYLES[selectedEssay.latest_feedback.overall_label]}`}
                      >
                        {t(`essays.feedback.label.${selectedEssay.latest_feedback.overall_label}` as TranslationKey)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {selectedEssay.latest_feedback.summary}
                    </p>
                    <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                      {SCORE_FIELDS.map((field) => {
                        const value = selectedEssay.latest_feedback?.[field.key];
                        if (value === null || value === undefined) return null;
                        return (
                          <div key={field.key}>
                            <dt className="text-xs text-muted-foreground">{t(field.labelKey)}</dt>
                            <dd className="text-lg font-semibold">{value}</dd>
                          </div>
                        );
                      })}
                    </dl>
                    {selectedEssay.latest_feedback.strengths.length > 0 ? (
                      <div className="mt-4">
                        <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                          {t("essays.feedback.strengths")}
                        </h4>
                        <ul className="mt-2 space-y-1.5 text-sm">
                          {selectedEssay.latest_feedback.strengths.map((strength) => (
                            <li className="flex items-start gap-2" key={strength}>
                              <CheckCircle2 aria-hidden className="mt-0.5 size-4 shrink-0 text-success" />
                              {t(`essays.feedback.strength.${strength}` as TranslationKey)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </Card>
                ) : null}

                {scoreNotice && scoreNotice.reason !== "scored" && scoreNotice.reason !== "cached" ? (
                  <Card className="border-warning/35 bg-warning/10">
                    <p className="text-sm text-warning" role="alert">
                      {scoreNotice.reason === "quota_exceeded"
                        ? t("essays.score.quotaExceeded", {
                            date: scoreNotice.nextAvailableAt
                              ? formatDate(scoreNotice.nextAvailableAt, locale)
                              : ""
                          })
                        : scoreNotice.reason === "ai_unavailable"
                          ? t("essays.score.unavailable")
                          : scoreNotice.reason === "missing_essay_text"
                            ? t("essays.score.missingText")
                            : t("essays.score.validationFailed")}
                    </p>
                  </Card>
                ) : null}

                {latestScore ? (
                  <Card className="bg-elevated/45 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold">{t("essays.score.title")}</h3>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {scoreNotice?.reason === "cached"
                            ? t("essays.score.cachedNotice")
                            : t("essays.score.notice")}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-sm border px-3 py-1 text-sm font-semibold">
                          {t("essays.score.overall", {
                            score: latestScore.overall_essay_readiness
                          })}
                        </span>
                        <Badge className="text-xs">
                          {t(`essays.confidence.${latestScore.confidence}` as TranslationKey)}
                        </Badge>
                      </div>
                    </div>

                    {scoreNotice?.quotaRemaining !== null && scoreNotice?.quotaRemaining !== undefined ? (
                      <p className="mt-2 text-xs text-muted-foreground">
                        {t("essays.score.quotaRemaining", { count: scoreNotice.quotaRemaining })}
                      </p>
                    ) : null}

                    <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <div>
                        <dt className="text-xs text-muted-foreground">{t("essays.score.promptFit")}</dt>
                        <dd className="text-lg font-semibold">{latestScore.subscores.prompt_fit}/25</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">{t("essays.score.structure")}</dt>
                        <dd className="text-lg font-semibold">{latestScore.subscores.structure}/20</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">
                          {t("essays.score.specificityEvidence")}
                        </dt>
                        <dd className="text-lg font-semibold">
                          {latestScore.subscores.specificity_evidence}/20
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">{t("essays.score.authenticity")}</dt>
                        <dd className="text-lg font-semibold">{latestScore.subscores.authenticity}/15</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">
                          {t("essays.score.languageClarity")}
                        </dt>
                        <dd className="text-lg font-semibold">{latestScore.subscores.language_clarity}/10</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">
                          {t("essays.score.wordLimitDiscipline")}
                        </dt>
                        <dd className="text-lg font-semibold">
                          {latestScore.subscores.word_limit_discipline !== null
                            ? `${latestScore.subscores.word_limit_discipline}/5`
                            : t("essays.score.notApplicable")}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">
                          {t("essays.score.schoolProgramAlignment")}
                        </dt>
                        <dd className="text-lg font-semibold">
                          {latestScore.subscores.school_program_alignment !== null
                            ? `${latestScore.subscores.school_program_alignment}/5`
                            : t("essays.score.notApplicable")}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">{t("essays.score.styleSignal")}</dt>
                        <dd className="text-lg font-semibold">
                          {t(
                            `essays.score.signal.${latestScore.ai_paraphrase_style_signal}` as TranslationKey
                          )}
                        </dd>
                      </div>
                    </dl>

                    {latestScore.source_warnings.length > 0 ? (
                      <div className="mt-4">
                        <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                          {t("essays.score.sourceWarnings")}
                        </h4>
                        <ul className="mt-2 space-y-1 text-sm text-warning">
                          {latestScore.source_warnings.map((warning) => (
                            <li key={warning}>{warning}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    {latestScore.approximate_suggestions.length > 0 ? (
                      <div className="mt-4">
                        <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                          {t("essays.score.suggestions")}
                        </h4>
                        <ul className="mt-2 space-y-1.5 text-sm">
                          {latestScore.approximate_suggestions.map((suggestion) => (
                            <li className="flex items-start gap-2" key={suggestion}>
                              <Sparkles aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
                              {suggestion}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    <ul className="mt-4 space-y-1 text-xs text-muted-foreground">
                      {latestScore.disclaimers.map((disclaimer) => (
                        <li key={disclaimer}>{disclaimer}</li>
                      ))}
                    </ul>
                  </Card>
                ) : null}

                <Card className="p-5">
                  <h3 className="text-lg font-semibold">{t("essays.revision.title")}</h3>
                  {selectedEssay.revision_tasks.length === 0 ? (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {t("essays.revision.empty")}
                    </p>
                  ) : (
                    <ul className="mt-3 space-y-2">
                      {selectedEssay.revision_tasks.map((task) => (
                        <li
                          className="flex flex-wrap items-start justify-between gap-3 rounded-sm border bg-surface p-3 text-sm"
                          key={task.id}
                        >
                          <div>
                            <span className="rounded-sm border bg-elevated px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
                              {t(`essays.revisionCategory.${task.category}` as TranslationKey)}
                            </span>
                            <p className="mt-1 font-semibold">{task.title}</p>
                            {task.description ? (
                              <p className="mt-1 text-xs text-muted-foreground">{task.description}</p>
                            ) : null}
                          </div>
                          {task.status === "todo" ? (
                            <div className="flex gap-2">
                              <Button
                                disabled={pendingTaskId === task.id}
                                onClick={() => void handleRevisionTaskStatus(task, "completed")}
                                size="sm"
                                type="button"
                              >
                                {t("essays.revision.complete")}
                              </Button>
                              <Button
                                disabled={pendingTaskId === task.id}
                                onClick={() => void handleRevisionTaskStatus(task, "skipped")}
                                size="sm"
                                type="button"
                                variant="ghost"
                              >
                                {t("essays.revision.skip")}
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              {t(`essays.revisionStatus.${task.status}` as TranslationKey)}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="mt-3 flex gap-2">
                    <input
                      className={fieldClassName}
                      onChange={(event) => setNewTaskTitle(event.target.value)}
                      placeholder={t("essays.revision.addPlaceholder")}
                      value={newTaskTitle}
                    />
                    <Button onClick={() => void handleAddRevisionTask()} size="sm" type="button" variant="secondary">
                      {t("essays.revision.add")}
                    </Button>
                  </div>
                </Card>
              </div>
            )}
          </div>
        </div>
      )}

      <p className="flex items-start gap-2 text-xs leading-5 text-muted-foreground">
        <AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0 text-warning" />
        {t("essays.disclaimer")}
      </p>
      <Badge className="text-xs">{t("essays.noGhostwritingNote")}</Badge>
      <UnsavedChangesDialog
        description={t("common.unsaved.description")}
        isSaving={isSavingDraft}
        leaveWithoutSavingLabel={t("common.unsaved.leaveWithoutSaving")}
        onLeaveWithoutSaving={draftGuard.leaveWithoutSaving}
        onSaveAndLeave={handleSaveDraft}
        onStay={draftGuard.stay}
        open={draftGuard.isPromptOpen}
        saveAndLeaveLabel={t("common.unsaved.saveAndLeave")}
        stayLabel={t("common.unsaved.stay")}
        title={t("common.unsaved.title")}
      />
    </div>
  );
}
