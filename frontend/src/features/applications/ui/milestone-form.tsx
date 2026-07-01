"use client";

import { useState } from "react";

import type { MilestoneCategory, MilestonePriority } from "@/entities/application";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { fieldClassName } from "@/shared/ui/field";

const CATEGORIES: MilestoneCategory[] = [
  "essays",
  "recommendations",
  "tests",
  "financial_aid",
  "documents",
  "submission",
  "interview",
  "decision"
];

const PRIORITIES: MilestonePriority[] = ["low", "medium", "high"];

export type MilestoneFormValues = {
  title: string;
  category: MilestoneCategory;
  due_date: string;
  priority: MilestonePriority;
  notes: string;
};

export function MilestoneForm({
  onSubmit
}: {
  onSubmit: (values: MilestoneFormValues) => void | Promise<void>;
}) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<MilestoneCategory>("essays");
  const [dueDate, setDueDate] = useState("");
  const [priority, setPriority] = useState<MilestonePriority>("medium");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    // Guard against empty titles and against a double-click creating duplicates:
    // the button is disabled and re-entry blocked until the save resolves.
    if (!title.trim() || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onSubmit({ title: title.trim(), category, due_date: dueDate, priority, notes: notes.trim() });
      setTitle("");
      setDueDate("");
      setPriority("medium");
      setNotes("");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="space-y-2" onSubmit={handleSubmit}>
      <div className="flex flex-wrap gap-2">
        <input
          className={`${fieldClassName} flex-1 basis-40`}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={t("applications.milestones.titlePlaceholder")}
          value={title}
        />
        <select
          className={`${fieldClassName} basis-32`}
          onChange={(event) => setCategory(event.target.value as MilestoneCategory)}
          value={category}
        >
          {CATEGORIES.map((item) => (
            <option key={item} value={item}>
              {t(`applications.milestoneCategory.${item}` as TranslationKey)}
            </option>
          ))}
        </select>
        <select
          aria-label={t("applications.milestones.priority")}
          className={`${fieldClassName} basis-28`}
          onChange={(event) => setPriority(event.target.value as MilestonePriority)}
          value={priority}
        >
          {PRIORITIES.map((item) => (
            <option key={item} value={item}>
              {t(`applications.priority.${item}` as TranslationKey)}
            </option>
          ))}
        </select>
        <input
          className={`${fieldClassName} basis-36`}
          onChange={(event) => setDueDate(event.target.value)}
          type="date"
          value={dueDate}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <input
          className={`${fieldClassName} flex-1 basis-40`}
          onChange={(event) => setNotes(event.target.value)}
          placeholder={t("applications.milestones.notesPlaceholder")}
          value={notes}
        />
        <Button disabled={isSubmitting || !title.trim()} size="sm" type="submit" variant="secondary">
          {t("applications.milestones.add")}
        </Button>
      </div>
    </form>
  );
}
