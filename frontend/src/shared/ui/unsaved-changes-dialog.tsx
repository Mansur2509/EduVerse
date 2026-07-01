"use client";

import { Button } from "@/shared/ui/button";

export function UnsavedChangesDialog({
  open,
  title,
  description,
  saveAndLeaveLabel,
  leaveWithoutSavingLabel,
  stayLabel,
  isSaving,
  onSaveAndLeave,
  onLeaveWithoutSaving,
  onStay
}: {
  open: boolean;
  title: string;
  description: string;
  saveAndLeaveLabel: string;
  leaveWithoutSavingLabel: string;
  stayLabel: string;
  isSaving?: boolean;
  onSaveAndLeave: () => void | boolean | Promise<unknown>;
  onLeaveWithoutSaving: () => void | Promise<unknown>;
  onStay: () => void;
}) {
  if (!open) return null;

  async function handleSaveAndLeave() {
    const result = await onSaveAndLeave();
    if (result !== false) {
      await onLeaveWithoutSaving();
    }
  }

  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-foreground/35 px-4"
      role="dialog"
    >
      <div className="w-full max-w-md rounded-sm border bg-card p-5 shadow-card">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button disabled={isSaving} onClick={onStay} type="button" variant="ghost">
            {stayLabel}
          </Button>
          <Button
            disabled={isSaving}
            onClick={() => void onLeaveWithoutSaving()}
            type="button"
            variant="secondary"
          >
            {leaveWithoutSavingLabel}
          </Button>
          <Button disabled={isSaving} onClick={() => void handleSaveAndLeave()} type="button">
            {saveAndLeaveLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
