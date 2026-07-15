"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type {
  ApplicationTimeline,
  DateConfidence,
  TimelineDeadline,
  TimelineEssay,
  TimelineEvent,
  TimelineExam,
  TimelineSuggestedDate,
  Urgency
} from "@/entities/application";
import type { EssayWorkspace } from "@/entities/essay";
import { getApplicationTimelineRequest } from "@/features/applications";
import { getEssaysRequest, updateEssayRequest } from "@/features/essays";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { useSlowLoad } from "@/shared/lib/use-slow-load";
import { Button } from "@/shared/ui/button";
import { fieldClassName } from "@/shared/ui/field";
import { HelpTooltip } from "@/shared/ui/help-tooltip";
import { SkeletonText } from "@/shared/ui/skeleton";

const DEFAULT_VISIBLE_EVENTS = 5;

type ZoomMode = "year" | "month" | "week" | "list";
const ZOOM_MODES: ZoomMode[] = ["year", "month", "week", "list"];
const ZOOM_WINDOW_DAYS: Record<Exclude<ZoomMode, "list">, number> = {
  year: 365,
  month: 30,
  week: 7
};

function isWithinZoom(dateStr: string | null, zoom: ZoomMode): boolean {
  if (zoom === "list" || !dateStr) return true;
  const target = new Date(dateStr).getTime();
  if (Number.isNaN(target)) return true;
  const diffDays = Math.abs((target - Date.now()) / 86_400_000);
  return diffDays <= ZOOM_WINDOW_DAYS[zoom];
}

const COMPLETED_STATUSES = new Set(["done", "completed", "complete", "submitted"]);
function isCompletedEvent(status?: string): boolean {
  return status ? COMPLETED_STATUSES.has(status.toLowerCase()) : false;
}

const URGENCY_STYLES: Record<Urgency, string> = {
  overdue: "border-danger/45 bg-danger/10 text-danger",
  critical: "border-danger/45 bg-danger/10 text-danger",
  urgent: "border-warning/45 bg-warning/10 text-warning",
  soon: "border-warning/35 bg-warning/10 text-warning",
  upcoming: "border-accent/35 bg-accent/10 text-accent",
  far: "border-muted-foreground/30 bg-surface text-muted-foreground",
  unknown: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

const CONFIDENCE_STYLES: Record<DateConfidence, string> = {
  verified: "border-success/35 bg-success/10 text-success",
  partial: "border-accent/35 bg-accent/10 text-accent",
  user_provided: "border-accent/30 bg-surface text-accent",
  estimated: "border-muted-foreground/30 bg-surface text-muted-foreground",
  missing: "border-warning/40 bg-warning/10 text-warning"
};

function badgeClass(base: string) {
  return `inline-flex items-center rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${base}`;
}

function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  const { t } = useI18n();
  if (urgency === "unknown") return null;
  return (
    <span className={badgeClass(URGENCY_STYLES[urgency])}>
      {t(`applications.urgency.${urgency}` as TranslationKey)}
    </span>
  );
}

function ConfidenceBadge({ confidence }: { confidence: DateConfidence }) {
  const { t } = useI18n();
  return (
    <span className={badgeClass(CONFIDENCE_STYLES[confidence])}>
      {t(`applications.confidence.${confidence}` as TranslationKey)}
    </span>
  );
}

function DaysRemaining({ days }: { days: number | null }) {
  const { t } = useI18n();
  if (days === null) return null;
  if (days < 0) {
    return (
      <span className="text-xs font-semibold text-danger">
        {t("applications.timeline.overdueBy", { count: Math.abs(days) })}
      </span>
    );
  }
  if (days === 0) {
    return <span className="text-xs font-semibold text-danger">{t("applications.timeline.today")}</span>;
  }
  return (
    <span className="text-xs text-muted-foreground">
      {t("applications.timeline.dueIn", { count: days })}
    </span>
  );
}

function DeadlineRow({ deadline }: { deadline: TimelineDeadline }) {
  const { locale, t } = useI18n();
  return (
    <div className="rounded-sm border bg-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold">
          {t(`applications.deadlineKind.${deadline.kind}` as TranslationKey)}
        </span>
        <UrgencyBadge urgency={deadline.urgency} />
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        {deadline.date ? (
          <span className="text-sm">{formatDate(deadline.date, locale)}</span>
        ) : (
          <span className="text-sm font-semibold text-warning">
            {t("applications.deadlines.notVerified")}
          </span>
        )}
        <ConfidenceBadge confidence={deadline.confidence} />
        <DaysRemaining days={deadline.days_remaining} />
      </div>
      {deadline.cycle_label ? (
        <div className="mt-1 flex items-center gap-1">
          <p className="text-xs text-muted-foreground">
            {t("applications.deadlines.cycleLabel", { cycle: deadline.cycle_label })}
          </p>
          {deadline.cycle_explanation ? (
            <HelpTooltip label={deadline.cycle_explanation} />
          ) : null}
        </div>
      ) : null}
      {deadline.source_url ? (
        <a
          className="mt-1.5 inline-block text-xs font-semibold text-primary-hover underline"
          href={deadline.source_url}
          rel="noreferrer noopener"
          target="_blank"
        >
          {deadline.confidence === "missing"
            ? t("applications.deadlines.verifyAction")
            : t("applications.deadlines.viewSource")}
        </a>
      ) : null}
    </div>
  );
}

function eventTitle(event: TimelineEvent, t: (key: TranslationKey) => string): string {
  if (event.title) return event.title;
  return t(`applications.eventType.${event.type}` as TranslationKey);
}

function EventRow({ event }: { event: TimelineEvent }) {
  const { locale, t } = useI18n();
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-sm border bg-surface px-3 py-2">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold">{eventTitle(event, t)}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-2">
          {event.date ? (
            <span className="text-xs text-muted-foreground">{formatDate(event.date, locale)}</span>
          ) : null}
          <ConfidenceBadge confidence={event.confidence} />
        </div>
      </div>
      <div className="flex flex-col items-end gap-1">
        <UrgencyBadge urgency={event.urgency} />
        <DaysRemaining days={event.days_remaining} />
      </div>
    </li>
  );
}

function SuggestedRow({ suggestion }: { suggestion: TimelineSuggestedDate }) {
  const { locale, t } = useI18n();
  const reason = t(`applications.suggestedReason.${suggestion.reason_key}` as TranslationKey);
  return (
    <li className="rounded-sm border bg-surface px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold">
          {t(`applications.eventType.${suggestion.type}` as TranslationKey)}
        </span>
        <div className="flex items-center gap-1.5">
          <UrgencyBadge urgency={suggestion.urgency} />
          <HelpTooltip
            label={`${reason.replace("{{weeks}}", String(suggestion.weeks_before))}`}
          />
        </div>
      </div>
      <p className="mt-1 text-sm">
        {suggestion.date
          ? t("applications.suggestedDates.suggestedFinish", {
              date: formatDate(suggestion.date, locale)
            })
          : null}
      </p>
    </li>
  );
}

function ExamRow({ exam }: { exam: TimelineExam }) {
  const { locale, t } = useI18n();
  return (
    <li className="rounded-sm border bg-surface px-3 py-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-1 font-semibold">
          {exam.exam}
          <HelpTooltip label={t("help.examDateSource")} />
        </span>
        {exam.severity ? (
          <span className={badgeClass(CONFIDENCE_STYLES.estimated)}>
            {t(`applications.examSeverity.${exam.severity}` as TranslationKey)}
          </span>
        ) : null}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span>
          {exam.current_score !== null
            ? t("applications.linkedExams.current", { score: exam.current_score })
            : t("applications.linkedExams.noScore")}
        </span>
        {exam.threshold !== null ? (
          <span>{t("applications.linkedExams.threshold", { score: exam.threshold })}</span>
        ) : null}
        {exam.planned_retake ? (
          <span className="font-semibold text-accent">
            {t("applications.linkedExams.plannedRetake")}
          </span>
        ) : null}
      </div>
      {exam.official_test_date ? (
        <p className="mt-1 text-xs text-muted-foreground">
          {t("applications.linkedExams.officialDate", {
            date: formatDate(exam.official_test_date, locale)
          })}
          {exam.official_test_time ? ` / ${exam.official_test_time}` : ""}
          {exam.registration_deadline
            ? ` · ${t("applications.linkedExams.registrationDeadline", {
                date: formatDate(exam.registration_deadline, locale)
              })}`
            : ""}
          {exam.late_registration_deadline
            ? ` / ${t("applications.linkedExams.lateDeadline", {
                date: formatDate(exam.late_registration_deadline, locale)
              })}`
            : ""}
          {exam.late_test_date
            ? ` / ${t("applications.linkedExams.lateTesting", {
                date: formatDate(exam.late_test_date, locale),
                time: exam.late_test_time || "-"
              })}`
            : ""}
        </p>
      ) : null}
      {exam.scores_arrive_before_deadline === false ? (
        <p className="mt-1 text-xs font-semibold text-warning">
          {t("applications.linkedExams.afterDeadlineWarning")}
        </p>
      ) : null}
    </li>
  );
}

function EssayRow({
  essay,
  isUnlinking,
  onUnlink
}: {
  essay: TimelineEssay;
  isUnlinking: boolean;
  onUnlink: (essayId: number) => void;
}) {
  const { locale, t } = useI18n();
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-sm border bg-surface px-3 py-2 text-sm">
      <div className="min-w-0">
        <p className="truncate font-semibold">{essay.title}</p>
        <p className="text-xs text-muted-foreground">
          {t(`essays.status.${essay.status}` as TranslationKey)}
          {" · "}
          {essay.word_limit
            ? t("applications.linkedEssays.wordProgress", {
                count: essay.word_count,
                limit: essay.word_limit
              })
            : t("applications.linkedEssays.wordCount", { count: essay.word_count })}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">{formatDate(essay.updated_at, locale)}</span>
        <Button
          disabled={isUnlinking}
          onClick={() => onUnlink(essay.id)}
          size="sm"
          type="button"
          variant="ghost"
        >
          {isUnlinking ? t("applications.linkedEssays.unlinking") : t("applications.linkedEssays.unlink")}
        </Button>
      </div>
    </li>
  );
}

export function ApplicationTimelinePanel({ applicationId }: { applicationId: number }) {
  const { t } = useI18n();
  const [timeline, setTimeline] = useState<ApplicationTimeline | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const isSlow = useSlowLoad(isLoading);
  const [retryToken, setRetryToken] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [zoom, setZoom] = useState<ZoomMode>("year");
  const [showCompleted, setShowCompleted] = useState(false);

  const [unlinkingEssayId, setUnlinkingEssayId] = useState<number | null>(null);
  const [essayActionError, setEssayActionError] = useState(false);
  const [isEssayPickerOpen, setIsEssayPickerOpen] = useState(false);
  const [candidateEssays, setCandidateEssays] = useState<EssayWorkspace[]>([]);
  const [candidatesRequested, setCandidatesRequested] = useState(false);
  const [isCandidatesLoading, setIsCandidatesLoading] = useState(false);
  const [candidatesLoadError, setCandidatesLoadError] = useState(false);
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [isLinkingEssay, setIsLinkingEssay] = useState(false);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setHasError(false);
    setExpanded(false);
    setIsEssayPickerOpen(false);
    getApplicationTimelineRequest(applicationId)
      .then((data) => {
        if (active) setTimeline(data);
      })
      .catch(() => {
        if (active) setHasError(true);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [applicationId, retryToken]);

  async function handleUnlinkEssay(essayId: number) {
    setEssayActionError(false);
    setUnlinkingEssayId(essayId);
    try {
      await updateEssayRequest(essayId, { application: null });
      setTimeline((prev) =>
        prev
          ? { ...prev, linked_essays: prev.linked_essays.filter((essay) => essay.id !== essayId) }
          : prev
      );
    } catch {
      setEssayActionError(true);
    } finally {
      setUnlinkingEssayId(null);
    }
  }

  function handleOpenEssayPicker() {
    setIsEssayPickerOpen(true);
    if (candidatesRequested) return;
    setCandidatesRequested(true);
    setIsCandidatesLoading(true);
    setCandidatesLoadError(false);
    getEssaysRequest({ page_size: 200 })
      .then((response) => setCandidateEssays(response.results))
      .catch(() => setCandidatesLoadError(true))
      .finally(() => setIsCandidatesLoading(false));
  }

  async function handleLinkEssay() {
    if (!selectedCandidateId) return;
    setEssayActionError(false);
    setIsLinkingEssay(true);
    try {
      const linked = await updateEssayRequest(Number(selectedCandidateId), {
        application: applicationId
      });
      setTimeline((prev) =>
        prev
          ? {
              ...prev,
              linked_essays: [
                ...prev.linked_essays.filter((essay) => essay.id !== linked.id),
                {
                  id: linked.id,
                  title: linked.title,
                  essay_type: linked.essay_type,
                  status: linked.status,
                  word_limit: linked.word_limit,
                  word_count: linked.word_count,
                  updated_at: linked.updated_at,
                  source_url: linked.source_url
                }
              ]
            }
          : prev
      );
      setSelectedCandidateId("");
      setIsEssayPickerOpen(false);
      // The essay may have moved from another application to this one, or
      // been linked for the first time -- either way the candidate list is
      // now stale (it still shows this essay as linkable). Force a fresh
      // fetch next time the picker reopens rather than showing an outdated
      // "already linked here" essay as still pickable.
      setCandidatesRequested(false);
    } catch {
      setEssayActionError(true);
    } finally {
      setIsLinkingEssay(false);
    }
  }

  const linkableEssays = candidateEssays.filter(
    (essay) => essay.application !== applicationId
  );

  if (isLoading) {
    return (
      <div>
        <p className="text-sm text-muted-foreground" role="status">
          {t("applications.timeline.loading")}
        </p>
        {isSlow ? (
          <p className="mt-2 text-xs leading-5 text-muted-foreground" role="status">
            {t("common.wakingUp")}
          </p>
        ) : null}
      </div>
    );
  }
  if (hasError || !timeline) {
    return (
      <div>
        <p className="text-sm text-danger" role="alert">
          {t("applications.timeline.error")}
        </p>
        <Button
          className="mt-3"
          onClick={() => setRetryToken((value) => value + 1)}
          size="sm"
          type="button"
          variant="secondary"
        >
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  const zoomedEvents = timeline.events.filter((event) => isWithinZoom(event.date, zoom));
  const completionFilteredEvents = showCompleted
    ? zoomedEvents
    : zoomedEvents.filter((event) => !isCompletedEvent(event.status));
  const hiddenCompletedCount = zoomedEvents.length - completionFilteredEvents.length;
  const visibleEvents = expanded
    ? completionFilteredEvents
    : completionFilteredEvents.slice(0, DEFAULT_VISIBLE_EVENTS);

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-1.5">
          <h3 className="text-sm font-semibold">{t("applications.deadlines.title")}</h3>
          <HelpTooltip label={t("applications.help.deadlineConfidence")} />
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {timeline.deadlines.map((deadline) => (
            <DeadlineRow deadline={deadline} key={`${deadline.kind}-${deadline.source_label}`} />
          ))}
        </div>
      </div>

      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <h3 className="text-sm font-semibold">{t("applications.timeline.independentTimeline")}</h3>
            <HelpTooltip label={t("applications.help.timeline")} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1 text-xs">
              <span className="font-semibold text-muted-foreground">
                {t("applications.timeline.zoom")}
              </span>
              <select
                className={fieldClassName}
                onChange={(event) => setZoom(event.target.value as ZoomMode)}
                value={zoom}
              >
                {ZOOM_MODES.map((mode) => (
                  <option key={mode} value={mode}>
                    {t(`applications.timeline.zoom.${mode}` as TranslationKey)}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
              <input
                checked={showCompleted}
                onChange={(event) => setShowCompleted(event.target.checked)}
                type="checkbox"
              />
              {t("applications.timeline.showCompleted")}
            </label>
          </div>
        </div>
        {timeline.events.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">{t("applications.timeline.empty")}</p>
        ) : completionFilteredEvents.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">
            {hiddenCompletedCount > 0
              ? t("applications.timeline.allCompleted")
              : t("applications.timeline.emptyForZoom")}
          </p>
        ) : (
          <>
            <ul className="mt-2 space-y-2">
              {visibleEvents.map((event, index) => (
                <EventRow event={event} key={`${event.type}-${event.date ?? "na"}-${index}`} />
              ))}
            </ul>
            {completionFilteredEvents.length > DEFAULT_VISIBLE_EVENTS ? (
              <Button
                className="mt-2"
                onClick={() => setExpanded((value) => !value)}
                size="sm"
                type="button"
                variant="ghost"
              >
                {expanded
                  ? t("applications.timeline.showLess")
                  : t("applications.timeline.showMore", {
                      count: completionFilteredEvents.length - DEFAULT_VISIBLE_EVENTS
                    })}
              </Button>
            ) : null}
          </>
        )}
      </div>

      {timeline.suggested_dates.length > 0 ? (
        <div>
          <div className="flex items-center gap-1.5">
            <h3 className="text-sm font-semibold">{t("applications.suggestedDates.title")}</h3>
            <HelpTooltip label={t("applications.help.suggestedDate")} />
          </div>
          <ul className="mt-2 space-y-2">
            {timeline.suggested_dates.map((suggestion) => (
              <SuggestedRow key={`${suggestion.type}-${suggestion.date}`} suggestion={suggestion} />
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted-foreground">
            {t("applications.suggestedDates.addHint")}
          </p>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold">{t("applications.linkedEssays.title")}</h3>
          {timeline.linked_essays.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">
              {t("applications.linkedEssays.empty")}
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {timeline.linked_essays.map((essay) => (
                <EssayRow
                  essay={essay}
                  isUnlinking={unlinkingEssayId === essay.id}
                  key={essay.id}
                  onUnlink={(essayId) => void handleUnlinkEssay(essayId)}
                />
              ))}
            </ul>
          )}

          {essayActionError ? (
            <p className="mt-2 text-xs text-danger" role="alert">
              {t("applications.states.actionError")}
            </p>
          ) : null}

          <div className="mt-2 flex flex-wrap gap-2">
            <Button asChild size="sm" variant="ghost">
              <Link href="/essays">{t("applications.linkedEssays.open")}</Link>
            </Button>
            {!isEssayPickerOpen ? (
              <Button onClick={handleOpenEssayPicker} size="sm" type="button" variant="ghost">
                {t("applications.linkedEssays.linkExisting")}
              </Button>
            ) : null}
          </div>

          {isEssayPickerOpen ? (
            <div className="mt-2 flex flex-wrap items-end gap-2">
              <label className="block flex-1">
                <span className="text-xs font-semibold">
                  {t("applications.linkedEssays.selectEssayLabel")}
                </span>
                <select
                  className={fieldClassName}
                  onChange={(event) => setSelectedCandidateId(event.target.value)}
                  value={selectedCandidateId}
                >
                  <option value="">{t("applications.linkedEssays.selectEssayPlaceholder")}</option>
                  {linkableEssays.map((essay) => (
                    <option key={essay.id} value={essay.id}>
                      {essay.title}
                      {essay.application_university_name
                        ? ` (${t("applications.linkedEssays.linkedElsewhere", {
                            university: essay.application_university_name
                          })})`
                        : ""}
                    </option>
                  ))}
                </select>
                {candidatesLoadError ? (
                  <p className="mt-1 text-xs text-warning" role="alert">
                    {t("applications.linkedEssays.loadCandidatesError")}
                  </p>
                ) : isCandidatesLoading ? (
                  <SkeletonText className="mt-1 w-1/2" />
                ) : !isCandidatesLoading && linkableEssays.length === 0 ? (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t("applications.linkedEssays.noCandidates")}
                  </p>
                ) : null}
              </label>
              <Button
                disabled={!selectedCandidateId || isLinkingEssay}
                onClick={() => void handleLinkEssay()}
                size="sm"
                type="button"
              >
                {isLinkingEssay
                  ? t("applications.linkedEssays.linking")
                  : t("applications.linkedEssays.link")}
              </Button>
              <Button
                onClick={() => setIsEssayPickerOpen(false)}
                size="sm"
                type="button"
                variant="ghost"
              >
                {t("common.actions.cancel")}
              </Button>
            </div>
          ) : null}
        </div>

        <div>
          <div className="flex items-center gap-1.5">
            <h3 className="text-sm font-semibold">{t("applications.linkedExams.title")}</h3>
            <HelpTooltip label={t("applications.help.scoreSend")} />
          </div>
          {timeline.linked_exams.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">
              {t("applications.linkedExams.empty")}
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {timeline.linked_exams.map((exam) => (
                <ExamRow exam={exam} key={exam.exam} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
