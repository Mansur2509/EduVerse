"use client";

import { useState } from "react";

import type {
  RoadmapCategory,
  RoadmapPriority,
  RoadmapTask
} from "@/entities/roadmap";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { UnsavedChangesDialog } from "@/shared/ui/unsaved-changes-dialog";

const CATEGORIES: RoadmapCategory[] = [
  "profile",
  "exams",
  "essays",
  "universities",
  "scholarships",
  "activities",
  "research",
  "portfolio",
  "deadlines",
  "events",
  "recommendations"
];

const PRIORITIES: RoadmapPriority[] = ["low", "medium", "high", "urgent"];

export type RoadmapTaskFormValues = {
  title: string;
  description: string;
  category: RoadmapCategory;
  priority: RoadmapPriority;
  due_date: string;
};

export function RoadmapTaskForm({
  task,
  onSubmit,
  onCancel,
  isSubmitting
}: {
  task: RoadmapTask | null;
  onSubmit: (values: RoadmapTaskFormValues) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}) {
  const { t } = useI18n();
  const isManual = !task || task.source_type === "manual";
  const [initialValues] = useState<RoadmapTaskFormValues>({
    title: task?.title ?? "",
    description: task?.description ?? "",
    category: task?.category ?? "recommendations",
    priority: task?.priority ?? "medium",
    due_date: task?.due_date ?? ""
  });
  const [values, setValues] = useState<RoadmapTaskFormValues>(initialValues);
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
          <span className="text-xs font-semibold">{t("roadmap.form.title")}</span>
          <input
            className={fieldClassName}
            maxLength={240}
            onChange={(event) => setValues((current) => ({ ...current, title: event.target.value }))}
            required
            value={values.title}
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold">{t("roadmap.form.description")}</span>
          <textarea
            className={fieldClassName}
            onChange={(event) =>
              setValues((current) => ({ ...current, description: event.target.value }))
            }
            rows={3}
            value={values.description}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="text-xs font-semibold">{t("roadmap.form.category")}</span>
            <select
              className={fieldClassName}
              disabled={!isManual}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  category: event.target.value as RoadmapCategory
                }))
              }
              value={values.category}
            >
              {CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {t(`roadmap.category.${category}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("roadmap.form.priority")}</span>
            <select
              className={fieldClassName}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  priority: event.target.value as RoadmapPriority
                }))
              }
              value={values.priority}
            >
              {PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {t(`roadmap.priority.${priority}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("roadmap.form.dueDate")}</span>
            <input
              className={fieldClassName}
              onChange={(event) =>
                setValues((current) => ({ ...current, due_date: event.target.value }))
              }
              type="date"
              value={values.due_date}
            />
          </label>
        </div>
        {!isManual ? (
          <p className="text-xs italic text-muted-foreground">{t("roadmap.form.generatedNote")}</p>
        ) : null}
        {error ? (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button disabled={isSubmitting} size="sm" type="submit">
            {task ? t("roadmap.form.save") : t("roadmap.form.create")}
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
