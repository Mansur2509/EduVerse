"use client";

import { useState } from "react";

import type { ApplicationRound } from "@/entities/application";
import type { SavedUniversity } from "@/entities/university";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";

const ROUNDS: ApplicationRound[] = [
  "early_decision",
  "early_action",
  "restrictive_early_action",
  "regular_decision",
  "rolling",
  "scholarship",
  "other"
];

export type ApplicationFormValues = {
  university: number | null;
  application_round: ApplicationRound;
  deadline: string;
};

export function ApplicationForm({
  shortlist,
  onSubmit,
  onCancel,
  isSubmitting
}: {
  shortlist: SavedUniversity[];
  onSubmit: (values: ApplicationFormValues) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}) {
  const { t } = useI18n();
  const [values, setValues] = useState<ApplicationFormValues>({
    university: shortlist[0]?.university.id ?? null,
    application_round: "regular_decision",
    deadline: ""
  });
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!values.university) {
      setError(t("common.error.requiredFields"));
      return;
    }
    try {
      await onSubmit(values);
    } catch {
      setError(t("applications.form.duplicateError"));
    }
  }

  return (
    <Card className="p-4">
      <form className="space-y-3" onSubmit={(event) => void handleSubmit(event)}>
        <label className="block">
          <span className="text-xs font-semibold">{t("applications.form.university")}</span>
          <select
            className={fieldClassName}
            onChange={(event) =>
              setValues((current) => ({ ...current, university: Number(event.target.value) }))
            }
            value={values.university ?? ""}
          >
            <option value="">{t("applications.form.selectUniversity")}</option>
            {shortlist.map((saved) => (
              <option key={saved.university.id} value={saved.university.id}>
                {saved.university.name}
              </option>
            ))}
          </select>
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-semibold">{t("applications.form.round")}</span>
            <select
              className={fieldClassName}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  application_round: event.target.value as ApplicationRound
                }))
              }
              value={values.application_round}
            >
              {ROUNDS.map((round) => (
                <option key={round} value={round}>
                  {t(`applications.round.${round}` as TranslationKey)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold">{t("applications.form.deadline")}</span>
            <input
              className={fieldClassName}
              onChange={(event) =>
                setValues((current) => ({ ...current, deadline: event.target.value }))
              }
              type="date"
              value={values.deadline}
            />
          </label>
        </div>
        {error ? (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button disabled={isSubmitting} size="sm" type="submit">
            {t("applications.form.create")}
          </Button>
          <Button disabled={isSubmitting} onClick={onCancel} size="sm" type="button" variant="ghost">
            {t("common.actions.cancel")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
