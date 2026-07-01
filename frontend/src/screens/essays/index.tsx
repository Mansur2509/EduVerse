"use client";

import { AlertTriangle, CheckCircle2, Plus, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EssayCard, type EssayRevisionTask, type EssayWorkspace } from "@/entities/essay";
import type { SuggestedItem } from "@/entities/suggestion";
import type { SavedUniversity } from "@/entities/university";
import {
  createEssayRequest,
  createEssayRevisionTaskRequest,
  deleteEssayRequest,
  generateEssayFeedbackRequest,
  getEssaysRequest,
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
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { LoadingNotice } from "@/shared/ui/loading-notice";
import { PaginatedList } from "@/shared/ui/pagination";
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

export function EssaysScreen() {
  const { t } = useI18n();
  const [essays, setEssays] = useState<EssayWorkspace[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [suggestions, setSuggestions] = useState<SuggestedItem[]>([]);
  const [shortlist, setShortlist] = useState<SavedUniversity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [filter, setFilter] = useState<string>("all");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEssay, setEditingEssay] = useState<EssayWorkspace | null>(null);
  const [selectedEssayId, setSelectedEssayId] = useState<number | null>(null);
  const [draftText, setDraftText] = useState("");
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isGeneratingFeedback, setIsGeneratingFeedback] = useState(false);
  const [actionError, setActionError] = useState(false);
  const [pendingTaskId, setPendingTaskId] = useState<number | null>(null);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [isRefreshingSuggestions, setIsRefreshingSuggestions] = useState(false);

  const loadEssays = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const [essaysResponse, shortlistResponse, suggestionsResponse] = await Promise.allSettled([
        getEssaysRequest({ page_size: 100 }),
        getShortlistRequest(),
        getSuggestionsRequest()
      ]);
      if (essaysResponse.status === "rejected") {
        setHasError(true);
        return;
      }
      setEssays(essaysResponse.value.results);
      setShortlist(shortlistResponse.status === "fulfilled" ? shortlistResponse.value.results : []);
      setSuggestions(suggestionsResponse.status === "fulfilled" ? suggestionsResponse.value.results : []);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadEssays();
  }, [loadEssays]);

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
    if (filter === "all") return essays;
    if (filter === "common_app") return essays.filter((essay) => essay.essay_type === "common_app");
    const universityId = Number(filter);
    return essays.filter((essay) => essay.university === universityId);
  }, [essays, filter]);
  const totalEssayPages = Math.max(1, Math.ceil(filteredEssays.length / ESSAYS_PAGE_SIZE));
  const visibleEssays = filteredEssays.slice(
    (currentPage - 1) * ESSAYS_PAGE_SIZE,
    currentPage * ESSAYS_PAGE_SIZE
  );

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
      word_limit: values.word_limit ? Number(values.word_limit) : null
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
      </section>

      {actionError ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("essays.states.actionError")}
          </p>
        </Card>
      ) : null}

      {isFormOpen ? (
        <EssayForm
          essay={editingEssay}
          onCancel={() => {
            setIsFormOpen(false);
            setEditingEssay(null);
          }}
          onSubmit={handleFormSubmit}
          shortlist={shortlist}
        />
      ) : null}

      <SuggestionPanel
        description={t("essays.suggestions.description")}
        isRefreshing={isRefreshingSuggestions}
        onAddToRoadmap={(suggestion) => void handleAddSuggestion(suggestion)}
        onDismiss={(suggestion) => void handleDismissSuggestion(suggestion)}
        onGenerate={() => void handleRefreshSuggestions()}
        suggestions={essaySuggestions}
        title={t("essays.suggestions.title")}
      />

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

      {filteredEssays.length === 0 ? (
        <Card>
          <p className="text-sm text-muted-foreground">{t("essays.states.emptyFilter")}</p>
        </Card>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[20rem_1fr]">
          <PaginatedList
            currentPage={currentPage}
            getItemKey={(essay) => essay.id}
            items={visibleEssays}
            onPageChange={setCurrentPage}
            pageSize={ESSAYS_PAGE_SIZE}
            totalCount={filteredEssays.length}
            totalPages={totalEssayPages}
            renderItem={(essay) => (
              <EssayCard
                essay={essay}
                isSelected={essay.id === selectedEssayId}
                onSelect={(item) =>
                  draftGuard.requestLeave(() => setSelectedEssayId(item.id))
                }
              />
            )}
          />

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
                    </div>
                    <div className="flex flex-wrap gap-2">
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

                  <label className="mt-4 block">
                    <span className="text-xs font-semibold">{t("essays.editor.draftLabel")}</span>
                    <textarea
                      className={fieldClassName}
                      onChange={(event) => setDraftText(event.target.value)}
                      rows={14}
                      value={draftText}
                    />
                  </label>
                  <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>
                      {selectedEssay.word_limit
                        ? t("essays.editor.wordCountWithLimit", {
                            count: liveWordCount,
                            limit: selectedEssay.word_limit
                          })
                        : t("essays.editor.wordCount", { count: liveWordCount })}
                    </span>
                  </div>

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
                        : t("essays.actions.getFeedback")}
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
                      <h3 className="text-lg font-semibold">{t("essays.feedback.title")}</h3>
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
