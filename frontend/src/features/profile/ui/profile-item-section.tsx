"use client";

import { useState } from "react";
import { Plus, Trash2, X } from "lucide-react";

import { useI18n, type TranslationKey } from "@/shared/i18n";
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { UnsavedChangesDialog } from "@/shared/ui/unsaved-changes-dialog";

export type ProfileItemField = {
  key: string;
  label: TranslationKey;
  type?: "text" | "textarea" | "date" | "number" | "select" | "email" | "url";
  placeholder?: TranslationKey;
  required?: boolean;
  maxLength?: number;
  options?: Array<{ value: string; label: TranslationKey }>;
};

interface ProfileItemSectionProps<T extends { id: number }> {
  id?: string;
  title: TranslationKey;
  description: TranslationKey;
  items: T[];
  fields: ProfileItemField[];
  onAdd: (data: Record<string, unknown>) => Promise<void>;
  onUpdate: (id: number, data: Record<string, unknown>) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  isLoading?: boolean;
  itemDisplay: (item: T) => React.ReactNode;
  statusLabel?: string;
  statusTone?: "complete" | "missing";
}

export function ProfileItemSection<T extends { id: number }>({
  id,
  title,
  description,
  items,
  fields,
  onAdd,
  onUpdate,
  onDelete,
  isLoading,
  itemDisplay,
  statusLabel,
  statusTone = "missing",
}: ProfileItemSectionProps<T>) {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [initialFormData, setInitialFormData] = useState<Record<string, unknown>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasUnsavedChanges =
    isExpanded && JSON.stringify(formData) !== JSON.stringify(initialFormData);
  const unsavedGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedChanges
  });

  const submitForm = async () => {
    setError(null);
    setIsSubmitting(true);

    try {
      if (editingId) {
        await onUpdate(editingId, formData);
        setEditingId(null);
      } else {
        await onAdd(formData);
      }
      setFormData({});
      setInitialFormData({});
      setIsExpanded(false);
      return true;
    } catch {
      setError(t("common.error.generic"));
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitForm();
  };

  const startEdit = (item: T) => {
    setEditingId(item.id);
    const newFormData: Record<string, unknown> = {};
    fields.forEach((field) => {
      newFormData[field.key] = item[field.key as keyof T] ?? "";
    });
    setFormData(newFormData);
    setInitialFormData(newFormData);
    setIsExpanded(true);
  };

  const handleEdit = (item: T) => {
    unsavedGuard.requestLeave(() => startEdit(item));
  };

  const handleDelete = async (id: number) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await onDelete(id);
      setDeleteConfirm(null);
    } catch {
      setError(t("common.error.generic"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const discardForm = () => {
    setEditingId(null);
    setFormData({});
    setInitialFormData({});
    setIsExpanded(false);
    setError(null);
  };

  const openNewForm = () => {
    setEditingId(null);
    setFormData({});
    setInitialFormData({});
    setError(null);
    setIsExpanded(true);
  };

  const handleCancel = () => {
    unsavedGuard.requestLeave(discardForm);
  };

  const handleFieldChange = (key: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  if (isLoading) {
    return (
      <Card className="p-4" id={id}>
        <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
      </Card>
    );
  }

  return (
    <Card className="scroll-mt-24 p-4" id={id}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold">{t(title)}</h3>
            {statusLabel ? (
              <span
                className={`rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${
                  statusTone === "complete"
                    ? "border-success/35 bg-success/10 text-success"
                    : "border-warning/35 bg-warning/10 text-warning"
                }`}
              >
                {statusLabel}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{t(description)}</p>
        </div>
        <Button
          className="shrink-0 self-start sm:self-auto"
          onClick={() => (isExpanded ? handleCancel() : openNewForm())}
          size="sm"
          variant="secondary"
          disabled={isSubmitting}
        >
          {isExpanded ? (
            <X aria-hidden className="mr-1 size-3" />
          ) : (
            <Plus aria-hidden className="mr-1 size-3" />
          )}
          {isExpanded ? t("profile.sections.close") : t("profile.sections.add")}
        </Button>
      </div>

      {/* Item list */}
      {items.length > 0 && (
        <div className="mt-4 space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-start justify-between gap-3 rounded-sm border bg-elevated/45 p-3 text-sm"
            >
              <div className="min-w-0 flex-1">{itemDisplay(item)}</div>
              <div className="flex shrink-0 gap-1">
                <button
                  onClick={() => handleEdit(item)}
                  className="rounded px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-elevated hover:text-foreground"
                  type="button"
                >
                  {t("profile.sections.edit")}
                </button>
                <button
                  aria-label={t("profile.sections.delete")}
                  onClick={() => setDeleteConfirm(item.id)}
                  className="rounded px-2 py-1 text-xs font-medium text-danger hover:bg-danger/10"
                  type="button"
                >
                  <Trash2 aria-hidden className="size-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {items.length === 0 && !isExpanded && (
        <div className="mt-4 rounded-sm border border-dashed bg-elevated/35 p-4">
          <p className="text-xs text-muted-foreground">{t("profile.sections.empty")}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            {t("profile.sections.emptyAction")}
          </p>
        </div>
      )}

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div className="mt-4 rounded-sm border border-danger/30 bg-danger/10 p-3">
          <p className="text-xs text-danger">{t("profile.sections.deleteConfirm")}</p>
          <div className="mt-2 flex gap-2">
            <Button
              onClick={() => handleDelete(deleteConfirm)}
              size="sm"
              variant="ghost"
              disabled={isSubmitting}
              className="text-danger"
            >
              {t("profile.sections.delete")}
            </Button>
            <Button
              onClick={() => setDeleteConfirm(null)}
              size="sm"
              variant="ghost"
              disabled={isSubmitting}
            >
              {t("common.actions.cancel")}
            </Button>
          </div>
        </div>
      )}

      {/* Form */}
      {isExpanded && !deleteConfirm && (
        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          {error && (
            <p className="rounded-sm border border-danger/35 bg-danger/10 p-2 text-xs text-danger">
              {error}
            </p>
          )}

          {fields.map((field) => {
            const value = String(formData[field.key] ?? "");
            return (
              <label key={field.key} className="block">
                <span className="text-xs font-semibold">{t(field.label)}</span>
                {field.type === "textarea" ? (
                  <>
                    <textarea
                      className={`${fieldClassName} min-h-28 resize-y py-2 leading-5`}
                      maxLength={field.maxLength || 1500}
                      placeholder={field.placeholder ? t(field.placeholder) : ""}
                      required={field.required}
                      value={value}
                      onChange={(e) => handleFieldChange(field.key, e.target.value)}
                      rows={field.maxLength && field.maxLength > 500 ? 6 : 3}
                    />
                    {field.maxLength ? (
                      <p className="mt-1 text-right text-[0.68rem] text-muted-foreground">
                        {value.length}/{field.maxLength}
                      </p>
                    ) : null}
                  </>
                ) : field.type === "select" ? (
                  <select
                    className={fieldClassName}
                    required={field.required}
                    value={value}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  >
                    <option value="">{t("profile.options.select")}</option>
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {t(opt.label)}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    className={fieldClassName}
                    maxLength={field.maxLength || 150}
                    placeholder={field.placeholder ? t(field.placeholder) : ""}
                    required={field.required}
                    type={field.type || "text"}
                    value={value}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  />
                )}
              </label>
            );
          })}

          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={isSubmitting}>
              {editingId ? t("profile.sections.update") : t("profile.sections.add")}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={handleCancel}
              disabled={isSubmitting}
            >
              {t("common.actions.cancel")}
            </Button>
          </div>
          <UnsavedChangesDialog
            description={t("common.unsaved.description")}
            isSaving={isSubmitting}
            leaveWithoutSavingLabel={t("common.unsaved.leaveWithoutSaving")}
            onLeaveWithoutSaving={unsavedGuard.leaveWithoutSaving}
            onSaveAndLeave={submitForm}
            onStay={unsavedGuard.stay}
            open={unsavedGuard.isPromptOpen}
            saveAndLeaveLabel={t("common.unsaved.saveAndLeave")}
            stayLabel={t("common.unsaved.stay")}
            title={t("common.unsaved.title")}
          />
        </form>
      )}
    </Card>
  );
}
