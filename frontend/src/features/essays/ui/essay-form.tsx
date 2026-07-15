"use client";

import { useState } from "react";

import type { ApplicationTrackerItem } from "@/entities/application";
import {
  ESSAY_PRIORITIES,
  ESSAY_TYPES,
  type EssayPriority,
  type EssayType,
  type EssayWorkspace
} from "@/entities/essay";
import type { SavedUniversityLite } from "@/entities/university";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { UnsavedChangesDialog } from "@/shared/ui/unsaved-changes-dialog";

export type EssayFormValues = {
  title: string;
  essay_type: EssayType;
  university: number | null;
  application: number | null;
  prompt_text: string;
  word_limit: string;
  due_date: string;
  source_url: string;
  notes: string;
  priority: EssayPriority;
};

export function EssayForm({
  essay,
  shortlist,
  isShortlistLoading = false,
  shortlistLoadError = false,
  applications,
  isApplicationsLoading = false,
  applicationsLoadError = false,
  onSubmit,
  onCancel,
  isSubmitting
}: {
  essay: EssayWorkspace | null;
  shortlist: SavedUniversityLite[];
  isShortlistLoading?: boolean;
  shortlistLoadError?: boolean;
  applications: ApplicationTrackerItem[];
  isApplicationsLoading?: boolean;
  applicationsLoadError?: boolean;
  onSubmit: (values: EssayFormValues) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}) {
  const { t } = useI18n();
  const [initialValues] = useState<EssayFormValues>({
    title: essay?.title ?? "",
    essay_type: essay?.essay_type ?? "common_app",
    university: essay?.university ?? null,
    application: essay?.application ?? null,
    prompt_text: essay?.prompt_text ?? "",
    word_limit: essay?.word_limit ? String(essay.word_limit) : "",
    due_date: essay?.due_date ?? "",
    source_url: essay?.source_url ?? "",
    notes: essay?.notes ?? "",
    priority: essay?.priority ?? "medium"
  });
  const [values, setValues] = useState<EssayFormValues>(initialValues);
  const [error, setError] = useState<string | null>(null);
  const hasUnsavedChanges = JSON.stringify(values) !== JSON.stringify(initialValues);
  const unsavedGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedChanges
  });

  async function submitValues() {
    setError(null);
    if (!values.title.trim()) {
      setError(t("essays.form.error.titleRequired"));
      return false;
    }
    if (values.word_limit) {
      const wordLimit = Number(values.word_limit);
      if (!Number.isInteger(wordLimit) || wordLimit < 10 || wordLimit > 2000) {
        setError(t("essays.form.error.wordLimitRange"));
        return false;
      }
    }
    try {
      await onSubmit(values);
      return true;
    } catch {
      setError(t("common.error.generic"));
      return false;
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    await submitValues();
  }

  return (
    <Card className="p-4">
      <form className="space-y-3" onSubmit={(event) => void handleSubmit(event)}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">
              {essay ? t("essays.form.editTitle") : t("essays.form.createTitle")}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {t("essays.form.wordLimitAutoNote")}
            </p>
          </div>
          <Button
            disabled={isSubmitting}
            onClick={() => unsavedGuard.requestLeave(onCancel)}
            size="sm"
            type="button"
            variant="ghost"
          >
            {t("common.actions.close")}
          </Button>
        </div>
        <label className="block">
          <span className="text-xs font-semibold">
            {t("essays.form.title")}
            <span aria-hidden className="ml-0.5 text-primary-hover">
              *
            </span>
          </span>
          <input
            className={fieldClassName}
            maxLength={240}
            onChange={(event) => setValues((current) => ({ ...current, title: event.target.value }))}
            required
            value={values.title}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-semibold">{t("essays.form.type")}</span>
            <select
              className={fieldClassName}
              onChange={(event) =>
                setValues((current) => ({ ...current, essay_type: event.target.value as EssayType }))
              }
              value={values.essay_type}
            >
              {ESSAY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`essays.type.${type}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("essays.form.university")}</span>
            <select
              className={fieldClassName}
              disabled={Boolean(values.application)}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  university: event.target.value ? Number(event.target.value) : null
                }))
              }
              value={values.university ?? ""}
            >
              <option value="">{t("essays.form.noUniversity")}</option>
              {shortlist.map((saved) => (
                <option key={saved.university.id} value={saved.university.id}>
                  {saved.university.name}
                </option>
              ))}
            </select>
            {shortlistLoadError ? (
              <p className="mt-1 text-xs text-warning" role="alert">
                {t("essays.form.shortlistLoadError")}
              </p>
            ) : isShortlistLoading ? (
              <p className="mt-1 text-xs text-muted-foreground">{t("common.loading")}</p>
            ) : null}
          </label>
        </div>
        <label className="block">
          <span className="text-xs font-semibold">{t("essays.form.application")}</span>
          <select
            className={fieldClassName}
            onChange={(event) => {
              const nextApplicationId = event.target.value ? Number(event.target.value) : null;
              const matched = applications.find((item) => item.id === nextApplicationId);
              setValues((current) => ({
                ...current,
                application: nextApplicationId,
                // Mirrors the backend's own validate(): linking an application
                // always forces the essay's university to match it, so the form
                // should never let the two visibly disagree before saving.
                university: matched ? matched.university : current.university
              }));
            }}
            value={values.application ?? ""}
          >
            <option value="">{t("essays.form.noApplication")}</option>
            {applications.map((application) => (
              <option key={application.id} value={application.id}>
                {application.university_name}
                {" · "}
                {t(`applications.round.${application.application_round}` as TranslationKey)}
                {application.archived_at ? ` (${t("essays.form.applicationArchived")})` : ""}
              </option>
            ))}
          </select>
          {values.application ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {t("essays.form.universityDerivedFromApplication")}
            </p>
          ) : null}
          {applicationsLoadError ? (
            <p className="mt-1 text-xs text-warning" role="alert">
              {t("essays.form.applicationsLoadError")}
            </p>
          ) : isApplicationsLoading ? (
            <p className="mt-1 text-xs text-muted-foreground">{t("common.loading")}</p>
          ) : null}
        </label>
        <label className="block">
          <span className="text-xs font-semibold">{t("essays.form.prompt")}</span>
          <textarea
            className={fieldClassName}
            onChange={(event) =>
              setValues((current) => ({ ...current, prompt_text: event.target.value }))
            }
            rows={3}
            value={values.prompt_text}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-semibold">{t("essays.form.wordLimit")}</span>
            <input
              className={fieldClassName}
              inputMode="numeric"
              min={0}
              onChange={(event) =>
                setValues((current) => ({ ...current, word_limit: event.target.value }))
              }
              type="number"
              value={values.word_limit}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              {values.word_limit
                ? t("essays.form.manualOverride")
                : t("essays.editor.wordLimitNeedsVerification")}
            </p>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("essays.form.dueDate")}</span>
            <input
              className={fieldClassName}
              onChange={(event) =>
                setValues((current) => ({ ...current, due_date: event.target.value }))
              }
              type="date"
              value={values.due_date}
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("essays.form.priority")}</span>
            <select
              className={fieldClassName}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  priority: event.target.value as EssayPriority
                }))
              }
              value={values.priority}
            >
              {ESSAY_PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {t(`essays.priority.${priority}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="block">
          <span className="text-xs font-semibold">{t("essays.form.sourceUrl")}</span>
          <input
            className={fieldClassName}
            onChange={(event) =>
              setValues((current) => ({ ...current, source_url: event.target.value }))
            }
            type="url"
            value={values.source_url}
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold">{t("essays.form.notes")}</span>
          <textarea
            className={fieldClassName}
            onChange={(event) =>
              setValues((current) => ({ ...current, notes: event.target.value }))
            }
            rows={2}
            value={values.notes}
          />
        </label>
        {error ? (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button disabled={isSubmitting} size="sm" type="submit">
            {essay ? t("essays.form.save") : t("essays.form.create")}
          </Button>
          <Button
            disabled={isSubmitting}
            onClick={() => unsavedGuard.requestLeave(onCancel)}
            size="sm"
            type="button"
            variant="ghost"
          >
            {t("common.actions.cancel")}
          </Button>
        </div>
      </form>
      <UnsavedChangesDialog
        description={t("common.unsaved.description")}
        isSaving={isSubmitting}
        leaveWithoutSavingLabel={t("common.unsaved.leaveWithoutSaving")}
        onLeaveWithoutSaving={unsavedGuard.leaveWithoutSaving}
        onSaveAndLeave={submitValues}
        onStay={unsavedGuard.stay}
        open={unsavedGuard.isPromptOpen}
        saveAndLeaveLabel={t("common.unsaved.saveAndLeave")}
        stayLabel={t("common.unsaved.stay")}
        title={t("common.unsaved.title")}
      />
    </Card>
  );
}
