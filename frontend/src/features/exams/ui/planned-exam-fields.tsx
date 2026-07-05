"use client";

import { useMemo } from "react";

import type { OfficialExamDate } from "@/entities/exam";
import { useI18n } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { fieldClassName } from "@/shared/ui/field";

export type ApPlanRow = {
  id: string;
  subject: string;
  date: string;
  target: string;
};

export type PlannedExamFieldsProps = {
  officialDates: OfficialExamDate[];
  officialDatesError?: boolean;
  satDate: string;
  satTarget: string;
  onSatDateChange: (value: string) => void;
  onSatTargetChange: (value: string) => void;
  ieltsDate: string;
  ieltsTarget: string;
  onIeltsDateChange: (value: string) => void;
  onIeltsTargetChange: (value: string) => void;
  apPlans: ApPlanRow[];
  onAddApPlan: () => void;
  onRemoveApPlan: (id: string) => void;
  onUpdateApPlan: (id: string, patch: Partial<ApPlanRow>) => void;
};

const MAX_SAT_SUGGESTIONS = 5;

/** Single source of truth for planned SAT/IELTS/AP fields, shared by
 * onboarding, Profile, and the Exams page so none of them can drift out of
 * sync with each other (e.g. Profile keeping a plain date input while
 * onboarding gained suggested-date selects and multi-row AP support). */
export function PlannedExamFields({
  officialDates,
  officialDatesError = false,
  satDate,
  satTarget,
  onSatDateChange,
  onSatTargetChange,
  ieltsDate,
  ieltsTarget,
  onIeltsDateChange,
  onIeltsTargetChange,
  apPlans,
  onAddApPlan,
  onRemoveApPlan,
  onUpdateApPlan
}: PlannedExamFieldsProps) {
  const { locale, t } = useI18n();
  const todayIso = new Date().toISOString().slice(0, 10);

  const satDateOptions = useMemo(
    () =>
      officialDates
        .filter(
          (item) =>
            item.exam_type === "SAT" && item.event_kind === "exam" && item.test_date >= todayIso
        )
        .slice(0, MAX_SAT_SUGGESTIONS),
    [officialDates, todayIso]
  );
  const apExamDateOptions = useMemo(
    () =>
      officialDates.filter(
        (item) =>
          item.exam_type === "AP" && item.event_kind === "exam" && item.test_date >= todayIso
      ),
    [officialDates, todayIso]
  );
  const apSubjectOptions = useMemo(
    () => Array.from(new Set(apExamDateOptions.map((item) => item.name))).sort(),
    [apExamDateOptions]
  );

  return (
    <div className="space-y-4">
      {officialDatesError ? (
        <p className="text-xs text-warning">{t("exams.plan.officialDatesUnavailable")}</p>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="border bg-surface p-4">
          <h3 className="font-semibold">SAT</h3>
          {satDateOptions.length > 0 ? (
            <select
              aria-label={t("exams.plan.examDate")}
              className={fieldClassName}
              onChange={(event) => onSatDateChange(event.target.value)}
              value={satDate}
            >
              <option value="">{t("exams.plan.selectDate")}</option>
              {satDateOptions.map((item) => (
                <option key={item.id} value={item.test_date}>
                  {formatDate(item.test_date, locale)}
                  {item.test_time ? ` / ${item.test_time}` : ""}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-label={t("exams.plan.examDate")}
              className={fieldClassName}
              onChange={(event) => onSatDateChange(event.target.value)}
              type="date"
              value={satDate}
            />
          )}
          <input
            aria-label={t("exams.plan.targetScore")}
            className={fieldClassName}
            onChange={(event) => onSatTargetChange(event.target.value)}
            placeholder={t("exams.plan.targetScore")}
            value={satTarget}
          />
          <p className="mt-2 text-xs text-muted-foreground">
            {satDate
              ? t("exams.plan.selectedSat", { date: formatDate(satDate, locale) })
              : t("exams.plan.dateUnavailable")}
          </p>
        </div>

        <div className="border bg-surface p-4">
          <h3 className="font-semibold">IELTS / TOEFL</h3>
          <p className="mt-1 text-xs text-muted-foreground">{t("exams.plan.manualDateLabel")}</p>
          <input
            aria-label={t("exams.plan.examDate")}
            className={fieldClassName}
            onChange={(event) => onIeltsDateChange(event.target.value)}
            type="date"
            value={ieltsDate}
          />
          <input
            aria-label={t("exams.plan.targetScore")}
            className={fieldClassName}
            onChange={(event) => onIeltsTargetChange(event.target.value)}
            placeholder={t("exams.plan.targetScore")}
            value={ieltsTarget}
          />
        </div>
      </div>

      <div className="space-y-3 border bg-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">{t("exams.plan.apPlanRows")}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{t("exams.plan.apPlanRowsHelp")}</p>
          </div>
          <Button onClick={onAddApPlan} size="sm" type="button" variant="secondary">
            {t("exams.plan.addApSubject")}
          </Button>
        </div>
        {apSubjectOptions.length === 0 ? (
          <p className="text-xs text-muted-foreground">{t("exams.plan.noUpcomingApDates")}</p>
        ) : null}
        {apPlans.map((row) => {
          const dateOptions = row.subject
            ? apExamDateOptions.filter((item) => item.name === row.subject)
            : apExamDateOptions;
          return (
            <div
              className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.7fr)_auto]"
              key={row.id}
            >
              <select
                aria-label={t("exams.plan.apSubject")}
                className={fieldClassName}
                onChange={(event) => onUpdateApPlan(row.id, { subject: event.target.value })}
                value={row.subject}
              >
                <option value="">{t("exams.plan.apSubject")}</option>
                {apSubjectOptions.map((subject) => (
                  <option key={subject} value={subject}>
                    {subject}
                  </option>
                ))}
              </select>
              <select
                aria-label={t("exams.plan.apDate")}
                className={fieldClassName}
                onChange={(event) => onUpdateApPlan(row.id, { date: event.target.value })}
                value={row.date}
              >
                <option value="">{t("exams.plan.selectDate")}</option>
                {dateOptions.map((item) => (
                  <option key={item.id} value={item.test_date}>
                    {formatDate(item.test_date, locale)}
                    {item.test_time ? ` / ${item.test_time}` : ""}
                  </option>
                ))}
              </select>
              <input
                aria-label={t("exams.plan.targetScore")}
                className={fieldClassName}
                onChange={(event) => onUpdateApPlan(row.id, { target: event.target.value })}
                placeholder={t("exams.plan.targetScore")}
                value={row.target}
              />
              <Button
                disabled={apPlans.length <= 1}
                onClick={() => onRemoveApPlan(row.id)}
                size="sm"
                type="button"
                variant="ghost"
              >
                {t("common.actions.close")}
              </Button>
              {row.subject ? (
                <p className="text-xs font-semibold text-muted-foreground md:col-span-4">
                  {row.date
                    ? t("exams.plan.selectedAp", { subject: row.subject, date: formatDate(row.date, locale) })
                    : t("exams.plan.dateUnavailable")}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
