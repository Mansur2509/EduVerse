"use client";

import { useState } from "react";

import { ESSAY_TYPES, type EssayType, type EssayWorkspace } from "@/entities/essay";
import type { SavedUniversity } from "@/entities/university";
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
  prompt_text: string;
  word_limit: string;
};

export function EssayForm({
  essay,
  shortlist,
  onSubmit,
  onCancel,
  isSubmitting
}: {
  essay: EssayWorkspace | null;
  shortlist: SavedUniversity[];
  onSubmit: (values: EssayFormValues) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}) {
  const { t } = useI18n();
  const [initialValues] = useState<EssayFormValues>({
    title: essay?.title ?? "",
    essay_type: essay?.essay_type ?? "common_app",
    university: essay?.university ?? null,
    prompt_text: essay?.prompt_text ?? "",
    word_limit: essay?.word_limit ? String(essay.word_limit) : ""
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
      setError(t("common.error.requiredFields"));
      return false;
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
        <label className="block">
          <span className="text-xs font-semibold">{t("essays.form.title")}</span>
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
          </label>
        </div>
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
        <label className="block sm:w-48">
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
