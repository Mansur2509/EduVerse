"use client";

import { useState } from "react";

import type { MilestoneCategory } from "@/entities/application";
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

export function MilestoneForm({
  onSubmit
}: {
  onSubmit: (values: { title: string; category: MilestoneCategory; due_date: string }) => void;
}) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<MilestoneCategory>("essays");
  const [dueDate, setDueDate] = useState("");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;
    onSubmit({ title: title.trim(), category, due_date: dueDate });
    setTitle("");
    setDueDate("");
  }

  return (
    <form className="flex flex-wrap gap-2" onSubmit={handleSubmit}>
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
      <input
        className={`${fieldClassName} basis-36`}
        onChange={(event) => setDueDate(event.target.value)}
        type="date"
        value={dueDate}
      />
      <Button size="sm" type="submit" variant="secondary">
        {t("applications.milestones.add")}
      </Button>
    </form>
  );
}
