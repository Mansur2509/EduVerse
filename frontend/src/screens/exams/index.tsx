"use client";

import { CalendarClock, ExternalLink, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { OfficialExamDate } from "@/entities/exam";
import { getOfficialExamDatesRequest } from "@/features/exams";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { LoadingNotice } from "@/shared/ui/loading-notice";

const PAGE_SIZE = 200;

type ApPlanRow = {
  id: string;
  subject: string;
  dateId: string;
};

function ExamDateRow({ item }: { item: OfficialExamDate }) {
  const { locale, t } = useI18n();
  return (
    <li className="rounded-sm border bg-surface px-3 py-2 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold">{item.name}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {t(`exams.eventKind.${item.event_kind}` as TranslationKey)}
            {" / "}
            {formatDate(item.test_date, locale)}
            {item.test_time ? ` / ${item.test_time}` : ""}
          </p>
        </div>
        <Badge className="text-xs">
          {t(`exams.verification.${item.verification_status}` as TranslationKey)}
        </Badge>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {item.registration_deadline ? (
          <span>
            {t("exams.registrationDeadline", {
              date: formatDate(item.registration_deadline, locale)
            })}
          </span>
        ) : null}
        {item.late_registration_deadline ? (
          <span>
            {t("exams.lateDeadline", {
              date: formatDate(item.late_registration_deadline, locale)
            })}
          </span>
        ) : null}
        {item.late_test_date ? (
          <span>
            {t("exams.lateTesting", {
              date: formatDate(item.late_test_date, locale),
              time: item.late_test_time || "-"
            })}
          </span>
        ) : null}
      </div>
      {item.source_url ? (
        <a
          className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary-hover"
          href={item.source_url}
          rel="noreferrer"
          target="_blank"
        >
          {t("exams.source")}
          <ExternalLink aria-hidden className="size-3" />
        </a>
      ) : null}
    </li>
  );
}

export function ExamsScreen() {
  const { locale, t } = useI18n();
  const [dates, setDates] = useState<OfficialExamDate[]>([]);
  const [selectedSatDateId, setSelectedSatDateId] = useState("");
  const [apPlans, setApPlans] = useState<ApPlanRow[]>([{ id: "ap-1", subject: "", dateId: "" }]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const loadDates = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const response = await getOfficialExamDatesRequest({ page_size: PAGE_SIZE });
      setDates(response.results);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDates();
  }, [loadDates]);

  const satDates = useMemo(
    () => dates.filter((item) => item.exam_type === "SAT" && item.event_kind === "exam"),
    [dates]
  );
  const apExamDates = useMemo(
    () => dates.filter((item) => item.exam_type === "AP" && item.event_kind === "exam"),
    [dates]
  );
  const apDeadlineDates = useMemo(
    () => dates.filter((item) => item.exam_type === "AP" && item.event_kind !== "exam"),
    [dates]
  );
  const satPlanOptions = useMemo(() => satDates.slice(0, 5), [satDates]);
  const selectedSatDate = satPlanOptions.find((item) => String(item.id) === selectedSatDateId);
  const apSubjects = useMemo(
    () => Array.from(new Set(apExamDates.map((item) => item.name))).sort(),
    [apExamDates]
  );

  function updateApPlan(rowId: string, patch: Partial<ApPlanRow>) {
    setApPlans((current) =>
      current.map((row) => {
        if (row.id !== rowId) return row;
        const next = { ...row, ...patch };
        if (patch.subject !== undefined) {
          const matchingDate = apExamDates.find((item) => item.name === patch.subject);
          next.dateId = matchingDate ? String(matchingDate.id) : "";
        }
        return next;
      })
    );
  }

  function addApPlan() {
    setApPlans((current) => [
      ...current,
      { id: `ap-${Date.now()}`, subject: "", dateId: "" }
    ]);
  }

  function removeApPlan(rowId: string) {
    setApPlans((current) =>
      current.length > 1 ? current.filter((row) => row.id !== rowId) : current
    );
  }

  if (isLoading) {
    return <LoadingNotice message={t("exams.states.loading")} />;
  }

  if (hasError) {
    return (
      <Card className="border-danger/35 bg-danger/10">
        <p className="text-sm text-danger" role="alert">
          {t("exams.states.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void loadDates()} type="button">
          <RefreshCw aria-hidden className="mr-2 size-4" />
          {t("universities.actions.retry")}
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-8">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {t("exams.eyebrow")}
        </p>
        <div className="mt-3 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <h1 className="max-w-3xl text-3xl font-semibold sm:text-4xl">
              {t("exams.title")}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              {t("exams.description")}
            </p>
          </div>
          <Badge className="text-xs">{t("exams.datasetBadge")}</Badge>
        </div>
      </section>

      <Card className="border-warning/35 bg-warning/10 p-4">
        <p className="text-sm font-semibold text-warning">{t("exams.warningTitle")}</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {t("exams.warningDescription")}
        </p>
      </Card>

      <Card className="p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <h2 className="text-lg font-semibold">{t("exams.plan.title")}</h2>
            <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
              {t("exams.plan.description")}
            </p>
          </div>
          <Button onClick={addApPlan} size="sm" type="button" variant="secondary">
            {t("exams.plan.addApSubject")}
          </Button>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <section className="rounded-sm border bg-surface p-3">
            <label className="block">
              <span className="text-sm font-semibold">{t("exams.plan.satLabel")}</span>
              <select
                className={fieldClassName}
                onChange={(event) => setSelectedSatDateId(event.target.value)}
                value={selectedSatDateId}
              >
                <option value="">{t("exams.plan.selectDate")}</option>
                {satPlanOptions.map((item) => (
                  <option key={item.id} value={item.id}>
                    {formatDate(item.test_date, locale)}
                    {item.test_time ? ` / ${item.test_time}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <p className="mt-2 text-xs font-semibold text-muted-foreground">
              {selectedSatDate
                ? t("exams.plan.selectedSat", {
                    date: formatDate(selectedSatDate.test_date, locale)
                  })
                : t("exams.plan.dateUnavailable")}
            </p>
          </section>

          <section className="space-y-3 rounded-sm border bg-surface p-3">
            <h3 className="text-sm font-semibold">{t("exams.plan.apLabel")}</h3>
            {apPlans.map((row) => {
              const dateOptions = row.subject
                ? apExamDates.filter((item) => item.name === row.subject)
                : apExamDates;
              const selectedDate = apExamDates.find((item) => String(item.id) === row.dateId);
              return (
                <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" key={row.id}>
                  <select
                    aria-label={t("exams.plan.apSubject")}
                    className={fieldClassName}
                    onChange={(event) => updateApPlan(row.id, { subject: event.target.value })}
                    value={row.subject}
                  >
                    <option value="">{t("exams.plan.apSubject")}</option>
                    {apSubjects.map((subject) => (
                      <option key={subject} value={subject}>
                        {subject}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label={t("exams.plan.apDate")}
                    className={fieldClassName}
                    disabled={!row.subject && apExamDates.length === 0}
                    onChange={(event) => updateApPlan(row.id, { dateId: event.target.value })}
                    value={row.dateId}
                  >
                    <option value="">{t("exams.plan.selectDate")}</option>
                    {dateOptions.map((item) => (
                      <option key={item.id} value={item.id}>
                        {formatDate(item.test_date, locale)}
                        {item.test_time ? ` / ${item.test_time}` : ""}
                      </option>
                    ))}
                  </select>
                  <Button
                    disabled={apPlans.length <= 1}
                    onClick={() => removeApPlan(row.id)}
                    size="sm"
                    type="button"
                    variant="ghost"
                  >
                    {t("common.actions.close")}
                  </Button>
                  {row.subject ? (
                    <p className="text-xs font-semibold text-muted-foreground md:col-span-3">
                      {selectedDate
                        ? t("exams.plan.selectedAp", {
                            subject: row.subject,
                            date: formatDate(selectedDate.test_date, locale)
                          })
                        : t("exams.plan.dateUnavailable")}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </section>
        </div>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="p-4">
          <div className="flex items-center gap-2">
            <CalendarClock aria-hidden className="size-5 text-accent" />
            <h2 className="text-lg font-semibold">{t("exams.sat.title")}</h2>
          </div>
          <ul className="mt-4 max-h-[34rem] space-y-2 overflow-y-auto pr-1 scrollbar-quiet">
            {satDates.map((item) => (
              <ExamDateRow item={item} key={item.id} />
            ))}
          </ul>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2">
            <CalendarClock aria-hidden className="size-5 text-accent" />
            <h2 className="text-lg font-semibold">{t("exams.ap.title")}</h2>
          </div>
          <div className="mt-4 max-h-[34rem] space-y-2 overflow-y-auto pr-1 scrollbar-quiet">
            {apExamDates.map((item) => (
              <ExamDateRow item={item} key={item.id} />
            ))}
          </div>
        </Card>
      </section>

      <Card className="p-4">
        <h2 className="text-lg font-semibold">{t("exams.ap.deadlineTitle")}</h2>
        <ul className="mt-4 grid gap-2 md:grid-cols-2">
          {apDeadlineDates.map((item) => (
            <ExamDateRow item={item} key={item.id} />
          ))}
        </ul>
      </Card>
    </div>
  );
}
