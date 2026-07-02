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
import { getApplicationTimelineRequest } from "@/features/applications";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { HelpTooltip } from "@/shared/ui/help-tooltip";

const DEFAULT_VISIBLE_EVENTS = 5;

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
        <span className="font-semibold">{exam.exam}</span>
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
          {exam.registration_deadline
            ? ` · ${t("applications.linkedExams.registrationDeadline", {
                date: formatDate(exam.registration_deadline, locale)
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

function EssayRow({ essay }: { essay: TimelineEssay }) {
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
      <span className="text-xs text-muted-foreground">{formatDate(essay.updated_at, locale)}</span>
    </li>
  );
}

export function ApplicationTimelinePanel({ applicationId }: { applicationId: number }) {
  const { t } = useI18n();
  const [timeline, setTimeline] = useState<ApplicationTimeline | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setHasError(false);
    setExpanded(false);
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
  }, [applicationId]);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">{t("applications.timeline.loading")}</p>;
  }
  if (hasError || !timeline) {
    return <p className="text-sm text-danger">{t("applications.timeline.error")}</p>;
  }

  const visibleEvents = expanded
    ? timeline.events
    : timeline.events.slice(0, DEFAULT_VISIBLE_EVENTS);

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
        <div className="flex items-center gap-1.5">
          <h3 className="text-sm font-semibold">{t("applications.timeline.independentTimeline")}</h3>
          <HelpTooltip label={t("applications.help.timeline")} />
        </div>
        {timeline.events.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">{t("applications.timeline.empty")}</p>
        ) : (
          <>
            <ul className="mt-2 space-y-2">
              {visibleEvents.map((event, index) => (
                <EventRow event={event} key={`${event.type}-${event.date ?? "na"}-${index}`} />
              ))}
            </ul>
            {timeline.events.length > DEFAULT_VISIBLE_EVENTS ? (
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
                      count: timeline.events.length - DEFAULT_VISIBLE_EVENTS
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
                <EssayRow essay={essay} key={essay.id} />
              ))}
            </ul>
          )}
          <Button asChild className="mt-2" size="sm" variant="ghost">
            <Link href="/essays">{t("applications.linkedEssays.open")}</Link>
          </Button>
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
