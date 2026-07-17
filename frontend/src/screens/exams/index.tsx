"use client";

import { CalendarClock, ExternalLink, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { OfficialExamDate } from "@/entities/exam";
import type { PlannedExam, StudentProfileDetails } from "@/entities/profile";
import { getOfficialExamDatesRequest } from "@/features/exams";
import { getProfileRequest, updateProfileRequest } from "@/features/profile";
import { createExamPlanRoadmapTaskRequest } from "@/features/roadmap";
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
  target: string;
  registrationStatus: "not_registered" | "registered" | "cancelled" | "not_required";
  testStatus: string;
  result: string;
  notificationIntervals: number[];
};

const DEFAULT_NOTIFICATION_INTERVALS = [30, 7, 1];
const NOTIFICATION_OPTIONS = [60, 30, 14, 7, 1];

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
            {item.test_date
              ? formatDate(item.test_date, locale)
              : t("exams.plan.officialDatesNotPublished")}
            {item.test_time ? ` / ${item.test_time}` : ""}
          </p>
        </div>
        <Badge className="text-xs">
          {t(`exams.dateStatus.${item.date_status}` as TranslationKey)}
        </Badge>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {item.countdown_days !== null ? (
          <span>{t("exams.countdown", { count: item.countdown_days })}</span>
        ) : null}
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
          {item.source_title || t("exams.source")}
          <ExternalLink aria-hidden className="size-3" />
        </a>
      ) : null}
    </li>
  );
}

export function ExamsScreen() {
  const { locale, t } = useI18n();
  const [dates, setDates] = useState<OfficialExamDate[]>([]);
  const [apSearch, setApSearch] = useState("");
  const [selectedSatDateId, setSelectedSatDateId] = useState("");
  const [apPlans, setApPlans] = useState<ApPlanRow[]>([
    {
      id: "ap-1",
      subject: "",
      dateId: "",
      target: "",
      registrationStatus: "not_registered",
      testStatus: "planned",
      result: "",
      notificationIntervals: DEFAULT_NOTIFICATION_INTERVALS
    }
  ]);
  const [profile, setProfile] = useState<StudentProfileDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saved" | "error">("idle");
  const [roadmapAddedRows, setRoadmapAddedRows] = useState<Set<string>>(new Set());

  const loadDates = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const [response, loadedProfile] = await Promise.all([
        getOfficialExamDatesRequest({ page_size: PAGE_SIZE, include_past: true }),
        getProfileRequest()
      ]);
      setDates(response.results);
      setProfile(loadedProfile);
      const planned = loadedProfile.exam_plans.planned ?? [];
      const satPlan = planned.find((item) => item.exam_type === "SAT" || item.name === "SAT");
      if (satPlan?.official_exam_date_id) {
        setSelectedSatDateId(String(satPlan.official_exam_date_id));
      }
      const savedApPlans = planned.filter(
        (item) => item.exam_type === "AP" || item.name.toLowerCase().startsWith("ap ")
      );
      if (savedApPlans.length > 0) {
        setApPlans(
          savedApPlans.map((item, index) => {
            const matchingDate = response.results.find(
              (dateItem) =>
                dateItem.id === item.official_exam_date_id ||
                (dateItem.name === item.name && dateItem.test_date === item.date)
            );
            return {
              id: `ap-${index + 1}`,
              subject: item.name === "AP" ? "" : item.name,
              dateId: matchingDate ? String(matchingDate.id) : "",
              target: item.target_score ?? "",
              registrationStatus: item.registration_status ?? "not_registered",
              testStatus: item.test_status ?? "planned",
              result: item.result ?? "",
              notificationIntervals:
                item.notification_intervals?.length
                  ? item.notification_intervals
                  : DEFAULT_NOTIFICATION_INTERVALS
            };
          })
        );
      }
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
    () =>
      dates.filter(
        (item) =>
          item.exam_type === "SAT" &&
          item.event_kind === "exam" &&
          item.date_status !== "outdated" &&
          item.test_date
      ),
    [dates]
  );
  const apExamDates = useMemo(
    () =>
      dates.filter(
        (item) =>
          item.exam_type === "AP" &&
          item.event_kind === "exam" &&
          item.date_status !== "outdated" &&
          item.test_date
      ),
    [dates]
  );
  const apDeadlineDates = useMemo(
    () =>
      dates.filter(
        (item) =>
          item.exam_type === "AP" &&
          item.event_kind !== "exam" &&
          item.date_status !== "outdated"
      ),
    [dates]
  );
  const satPlanOptions = useMemo(() => satDates.slice(0, 5), [satDates]);
  const verifiedSatPlanOptions = useMemo(
    () => satPlanOptions.filter((item) => item.date_status === "verified"),
    [satPlanOptions]
  );
  const verifiedApExamDates = useMemo(
    () => apExamDates.filter((item) => item.date_status === "verified"),
    [apExamDates]
  );
  const selectedSatDate = satPlanOptions.find((item) => String(item.id) === selectedSatDateId);
  const filteredApExamDates = useMemo(() => {
    const query = apSearch.trim().toLowerCase();
    if (!query) return apExamDates;
    return apExamDates.filter((item) => item.name.toLowerCase().includes(query));
  }, [apExamDates, apSearch]);
  const apSubjects = useMemo(
    () =>
      Array.from(
        new Set(
          dates
            .filter((item) => item.exam_type === "AP" && item.event_kind === "exam")
            .map((item) => item.name)
        )
      ).sort(),
    [dates]
  );

  function updateApPlan(rowId: string, patch: Partial<ApPlanRow>) {
    setApPlans((current) =>
      current.map((row) => {
        if (row.id !== rowId) return row;
        const next = { ...row, ...patch };
        if (patch.subject !== undefined) {
          const matchingDate = verifiedApExamDates.find((item) => item.name === patch.subject);
          next.dateId = matchingDate ? String(matchingDate.id) : "";
        }
        return next;
      })
    );
    setSaveState("idle");
  }

  function addApPlan() {
    setApPlans((current) => [
      ...current,
      {
        id: `ap-${Date.now()}`,
        subject: "",
        dateId: "",
        target: "",
        registrationStatus: "not_registered",
        testStatus: "planned",
        result: "",
        notificationIntervals: DEFAULT_NOTIFICATION_INTERVALS
      }
    ]);
    setSaveState("idle");
  }

  function removeApPlan(rowId: string) {
    setApPlans((current) =>
      current.length > 1 ? current.filter((row) => row.id !== rowId) : current
    );
    setSaveState("idle");
  }

  function toggleNotificationInterval(rowId: string, interval: number) {
    setApPlans((current) =>
      current.map((row) =>
        row.id === rowId
          ? {
              ...row,
              notificationIntervals: row.notificationIntervals.includes(interval)
                ? row.notificationIntervals.filter((value) => value !== interval)
                : [...row.notificationIntervals, interval].sort((left, right) => right - left)
            }
          : row
      )
    );
    setSaveState("idle");
  }

  async function saveExamPlans() {
    if (!profile) return;
    setIsSaving(true);
    setSaveState("idle");
    try {
      const preserved = (profile.exam_plans.planned ?? []).filter(
        (item) =>
          item.exam_type !== "AP" &&
          item.exam_type !== "SAT" &&
          item.name !== "SAT" &&
          !item.name.toLowerCase().startsWith("ap ")
      );
      const satDate = dates.find((item) => String(item.id) === selectedSatDateId);
      const existingSat = (profile.exam_plans.planned ?? []).find(
        (item) => item.exam_type === "SAT" || item.name === "SAT"
      );
      const satPlans: PlannedExam[] = satDate?.test_date
        ? [
            {
              ...(existingSat ?? { name: "SAT", target_score: "" }),
              name: "SAT",
              exam_type: "SAT",
              date: satDate.test_date,
              official_exam_date_id: satDate.id,
              notification_intervals:
                existingSat?.notification_intervals ?? DEFAULT_NOTIFICATION_INTERVALS
            }
          ]
        : existingSat
          ? [existingSat]
          : [];
      const plannedAp: PlannedExam[] = apPlans
        .filter((row) => row.subject.trim())
        .map((row) => {
          const officialDate = dates.find((item) => String(item.id) === row.dateId);
          return {
            name: row.subject.trim(),
            exam_type: "AP",
            date: officialDate?.test_date ?? "",
            target_score: row.target.trim(),
            test_status: row.testStatus,
            registration_status: row.registrationStatus,
            result: row.result.trim(),
            notification_intervals: row.notificationIntervals,
            ...(officialDate ? { official_exam_date_id: officialDate.id } : {})
          };
        });
      const updated = await updateProfileRequest({
        exam_plans: {
          taken: profile.exam_plans.taken ?? [],
          planned: [...preserved, ...satPlans, ...plannedAp]
        }
      });
      setProfile(updated);
      setSaveState("saved");
    } catch {
      setSaveState("error");
    } finally {
      setIsSaving(false);
    }
  }

  async function addPlanToRoadmap(row: ApPlanRow) {
    const officialDate = dates.find((item) => String(item.id) === row.dateId);
    if (!officialDate?.test_date || officialDate.date_status !== "verified") return;
    try {
      await createExamPlanRoadmapTaskRequest({
        official_exam_date_id: officialDate.id,
        title: row.subject,
        description: t("exams.plan.roadmapDescription")
      });
      setRoadmapAddedRows((current) => new Set(current).add(row.id));
    } catch {
      setSaveState("error");
    }
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
          <div className="flex flex-wrap gap-2">
            <Button onClick={addApPlan} size="sm" type="button" variant="secondary">
              {t("exams.plan.addApSubject")}
            </Button>
            <Button disabled={isSaving || !profile} onClick={() => void saveExamPlans()} size="sm" type="button">
              {isSaving ? t("common.actions.saving") : t("common.actions.save")}
            </Button>
          </div>
        </div>

        {saveState === "saved" ? (
          <p className="mt-3 text-sm font-semibold text-success" role="status">
            {t("exams.plan.saved")}
          </p>
        ) : saveState === "error" ? (
          <p className="mt-3 text-sm font-semibold text-danger" role="alert">
            {t("exams.plan.saveError")}
          </p>
        ) : null}

        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(14rem,0.65fr)_minmax(0,1.35fr)]">
          <section className="rounded-sm border bg-surface p-3">
            <label className="block">
              <span className="text-sm font-semibold">{t("exams.plan.satLabel")}</span>
              <select
                className={fieldClassName}
                onChange={(event) => setSelectedSatDateId(event.target.value)}
                value={selectedSatDateId}
              >
                <option value="">{t("exams.plan.selectDate")}</option>
                {verifiedSatPlanOptions.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.test_date ? formatDate(item.test_date, locale) : ""}
                    {item.test_time ? ` / ${item.test_time}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <p className="mt-2 text-xs font-semibold text-muted-foreground">
              {selectedSatDate
                ? t("exams.plan.selectedSat", {
                    date: selectedSatDate.test_date
                      ? formatDate(selectedSatDate.test_date, locale)
                      : t("exams.plan.officialDatesNotPublished")
                  })
                : t("exams.plan.dateUnavailable")}
            </p>
          </section>

          <section className="space-y-3 rounded-sm border bg-surface p-3">
            <h3 className="text-sm font-semibold">{t("exams.plan.apLabel")}</h3>
            {apExamDates.length === 0 ? (
              <p className="text-xs font-semibold text-warning">
                {t("exams.plan.officialDatesNotPublished")}
              </p>
            ) : null}
            {apPlans.map((row) => {
              const dateOptions = row.subject
                ? verifiedApExamDates.filter((item) => item.name === row.subject)
                : verifiedApExamDates;
              const selectedDate = verifiedApExamDates.find(
                (item) => String(item.id) === row.dateId
              );
              return (
                <div className="space-y-3 rounded-sm border bg-card p-3" key={row.id}>
                  <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(7rem,0.55fr)_auto]">
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
                      disabled={!row.subject || dateOptions.length === 0}
                      onChange={(event) => updateApPlan(row.id, { dateId: event.target.value })}
                      value={row.dateId}
                    >
                      <option value="">{t("exams.plan.selectDate")}</option>
                      {dateOptions.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.test_date ? formatDate(item.test_date, locale) : ""}
                          {item.test_time ? ` / ${item.test_time}` : ""}
                        </option>
                      ))}
                    </select>
                    <input
                      aria-label={t("exams.plan.targetScore")}
                      className={fieldClassName}
                      maxLength={40}
                      onChange={(event) => updateApPlan(row.id, { target: event.target.value })}
                      placeholder={t("exams.plan.targetScore")}
                      value={row.target}
                    />
                    <Button
                      disabled={apPlans.length <= 1}
                      onClick={() => removeApPlan(row.id)}
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      {t("common.actions.close")}
                    </Button>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <label className="block text-xs font-semibold">
                      {t("exams.plan.registrationStatus")}
                      <select
                        className={fieldClassName}
                        onChange={(event) =>
                          updateApPlan(row.id, {
                            registrationStatus: event.target.value as ApPlanRow["registrationStatus"]
                          })
                        }
                        value={row.registrationStatus}
                      >
                        {(["not_registered", "registered", "cancelled", "not_required"] as const).map(
                          (value) => (
                            <option key={value} value={value}>
                              {t(`exams.registrationStatus.${value}` as TranslationKey)}
                            </option>
                          )
                        )}
                      </select>
                    </label>
                    <label className="block text-xs font-semibold">
                      {t("exams.plan.progressStatus")}
                      <select
                        className={fieldClassName}
                        onChange={(event) => updateApPlan(row.id, { testStatus: event.target.value })}
                        value={row.testStatus}
                      >
                        {(["planned", "preparing", "registered", "taken", "result_recorded"] as const).map(
                          (value) => (
                            <option key={value} value={value}>
                              {t(`exams.progressStatus.${value}` as TranslationKey)}
                            </option>
                          )
                        )}
                      </select>
                    </label>
                  </div>
                  <label className="block text-xs font-semibold">
                    {t("exams.plan.result")}
                    <input
                      className={fieldClassName}
                      maxLength={80}
                      onChange={(event) => updateApPlan(row.id, { result: event.target.value })}
                      placeholder={t("exams.plan.result")}
                      value={row.result}
                    />
                  </label>
                  <fieldset>
                    <legend className="text-xs font-semibold">{t("exams.plan.reminders")}</legend>
                    <div className="mt-2 flex flex-wrap gap-3">
                      {NOTIFICATION_OPTIONS.map((interval) => (
                        <label className="flex items-center gap-1.5 text-xs" key={interval}>
                          <input
                            checked={row.notificationIntervals.includes(interval)}
                            onChange={() => toggleNotificationInterval(row.id, interval)}
                            type="checkbox"
                          />
                          {t("exams.plan.daysBefore", { count: interval })}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                  {row.subject ? (
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-muted-foreground">
                        {selectedDate?.test_date
                          ? t("exams.plan.selectedAp", {
                            subject: row.subject,
                            date: formatDate(selectedDate.test_date, locale)
                          })
                          : t("exams.plan.dateUnavailable")}
                      </p>
                      <Button
                        disabled={
                          !selectedDate?.test_date ||
                          selectedDate.date_status !== "verified" ||
                          roadmapAddedRows.has(row.id)
                        }
                        onClick={() => void addPlanToRoadmap(row)}
                        size="sm"
                        type="button"
                        variant="secondary"
                      >
                        {roadmapAddedRows.has(row.id)
                          ? t("exams.plan.addedToRoadmap")
                          : t("exams.plan.addToRoadmap")}
                      </Button>
                    </div>
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
          {satDates.length === 0 ? (
            <p className="mt-4 text-sm text-muted-foreground">
              {t("exams.plan.officialDatesNotPublished")}
            </p>
          ) : null}
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
          {apExamDates.length === 0 ? (
            <p className="mt-4 text-sm text-muted-foreground">
              {t("exams.plan.officialDatesNotPublished")}
            </p>
          ) : (
            <>
              <label className="mt-3 block">
                <span className="sr-only">{t("exams.ap.searchLabel")}</span>
                <input
                  aria-label={t("exams.ap.searchLabel")}
                  className={fieldClassName}
                  onChange={(event) => setApSearch(event.target.value)}
                  placeholder={t("exams.ap.searchPlaceholder")}
                  type="search"
                  value={apSearch}
                />
              </label>
              {filteredApExamDates.length === 0 ? (
                <p className="mt-4 text-sm text-muted-foreground">
                  {t("exams.ap.searchNoMatches")}
                </p>
              ) : null}
            </>
          )}
          <div className="mt-4 max-h-[34rem] space-y-2 overflow-y-auto pr-1 scrollbar-quiet">
            {filteredApExamDates.map((item) => (
              <ExamDateRow item={item} key={item.id} />
            ))}
          </div>
        </Card>
      </section>

      <Card className="p-4">
        <h2 className="text-lg font-semibold">{t("exams.ap.deadlineTitle")}</h2>
        {apDeadlineDates.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">
            {t("exams.plan.officialDatesNotPublished")}
          </p>
        ) : null}
        <ul className="mt-4 grid gap-2 md:grid-cols-2">
          {apDeadlineDates.map((item) => (
            <ExamDateRow item={item} key={item.id} />
          ))}
        </ul>
      </Card>
    </div>
  );
}
