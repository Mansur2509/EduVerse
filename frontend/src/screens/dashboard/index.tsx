"use client";

import {
  AlertTriangle,
  ArrowRight,
  BookOpenCheck,
  CalendarClock,
  CalendarDays,
  CircleDollarSign,
  FilePenLine,
  GraduationCap,
  Map,
  Sparkles,
  type LucideIcon
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { ApplicationTrackerItem } from "@/entities/application";
import type { EssayWorkspace } from "@/entities/essay";
import type { EventRegistration } from "@/entities/event";
import {
  classCatalog,
  GapRecommendationsPanel,
  ReadinessCard,
  StrategyPanel,
  type ApplicationReadiness,
  type ProfileAssessmentEnvelope,
  type ProfileCompletion,
  type ProfileRecommendation,
  type ProfileStrategy,
  type StudentProfileDetails
} from "@/entities/profile";
import type { RecommendationItem } from "@/entities/recommendation";
import type { RoadmapPlan } from "@/entities/roadmap";
import type { SuggestedItem } from "@/entities/suggestion";
import { getApplicationsRequest } from "@/features/applications";
import { useAuth } from "@/features/auth";
import { getEssaysRequest } from "@/features/essays";
import { getMyEventRegistrationsRequest } from "@/features/events";
import {
  getApplicationReadinessRequest,
  getProfileAssessmentLatestRequest,
  getProfileCompletionRequest,
  getProfileRecommendationsRequest,
  getProfileRequest,
  getProfileStrategyRequest
} from "@/features/profile";
import { generateRoadmapRequest, getRoadmapRequest } from "@/features/roadmap";
import {
  addSuggestionToRoadmapRequest,
  dismissSuggestionRequest,
  generateSuggestionsRequest,
  SuggestionPanel
} from "@/features/suggestions";
import { getRecommendationsRequest } from "@/features/universities";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate, formatDateTime } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { HelpTooltip } from "@/shared/ui/help-tooltip";

type DashboardUrgency =
  | "overdue"
  | "critical"
  | "urgent"
  | "soon"
  | "upcoming"
  | "far"
  | "unknown";

// Mirrors backend timeline urgency thresholds so the dashboard warning matches
// the per-application timeline badges.
function urgencyForDays(days: number | null): DashboardUrgency {
  if (days === null) return "unknown";
  if (days < 0) return "overdue";
  if (days <= 7) return "critical";
  if (days <= 14) return "urgent";
  if (days <= 30) return "soon";
  if (days <= 90) return "upcoming";
  return "far";
}

const DASHBOARD_URGENCY_STYLES: Record<DashboardUrgency, string> = {
  overdue: "border-danger/45 bg-danger/10 text-danger",
  critical: "border-danger/45 bg-danger/10 text-danger",
  urgent: "border-warning/45 bg-warning/10 text-warning",
  soon: "border-warning/35 bg-warning/10 text-warning",
  upcoming: "border-accent/35 bg-accent/10 text-accent",
  far: "border-muted-foreground/30 bg-surface text-muted-foreground",
  unknown: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

const PROFILE_SECTION_HREFS: Record<string, string> = {
  profile: "/profile",
  academics: "/profile#profile-foundation-education",
  exams: "/profile#profile-foundation-tests",
  activities: "/profile#profile-section-activities",
  leadership: "/profile#profile-section-activities",
  essays: "/profile#profile-section-essays",
  timeline: "/profile#profile-foundation-education",
  honors: "/profile#profile-section-honors",
  olympiads: "/profile#profile-section-olympiads",
  sports: "/profile#profile-section-sports",
  research: "/profile#profile-section-research",
  portfolio: "/profile#profile-section-portfolio",
  volunteering: "/profile#profile-section-volunteering",
  recommenders: "/profile#profile-section-recommenders"
};

function profileSectionHref(component: string) {
  return PROFILE_SECTION_HREFS[component] ?? "/profile";
}

export function DashboardScreen() {
  const { user } = useAuth();
  const { locale, t } = useI18n();
  const [completion, setCompletion] = useState<ProfileCompletion | null>(null);
  const [profile, setProfile] = useState<StudentProfileDetails | null>(null);
  const [readiness, setReadiness] = useState<ApplicationReadiness | null>(null);
  const [profileAssessment, setProfileAssessment] =
    useState<ProfileAssessmentEnvelope | null>(null);
  const [registrations, setRegistrations] = useState<EventRegistration[]>([]);
  const [roadmapPlan, setRoadmapPlan] = useState<RoadmapPlan | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestedItem[]>([]);
  const [applications, setApplications] = useState<ApplicationTrackerItem[]>([]);
  const [essays, setEssays] = useState<EssayWorkspace[]>([]);
  const [topRecommendations, setTopRecommendations] = useState<RecommendationItem[]>([]);
  const [profileRecommendations, setProfileRecommendations] = useState<ProfileRecommendation[]>([]);
  const [needsAssessment, setNeedsAssessment] = useState(false);
  const [profileStrategy, setProfileStrategy] = useState<ProfileStrategy | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGeneratingRoadmap, setIsGeneratingRoadmap] = useState(false);
  const [isRefreshingSuggestions, setIsRefreshingSuggestions] = useState(false);
  const [hasPartialError, setHasPartialError] = useState(false);

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setHasPartialError(false);
    const [
      completionResult,
      profileResult,
      registrationsResult,
      readinessResult,
      roadmapResult,
      suggestionsResult,
      applicationsResult,
      essaysResult,
      recommendationsResult,
      assessmentResult,
      profileRecommendationsResult,
      profileStrategyResult
    ] = await Promise.allSettled([
      getProfileCompletionRequest(),
      getProfileRequest(),
      getMyEventRegistrationsRequest(),
      getApplicationReadinessRequest(),
      getRoadmapRequest(),
      generateSuggestionsRequest(),
      getApplicationsRequest(),
      getEssaysRequest(),
      getRecommendationsRequest(),
      getProfileAssessmentLatestRequest(),
      getProfileRecommendationsRequest(),
      getProfileStrategyRequest()
    ]);

    if (completionResult.status === "fulfilled") {
      setCompletion(completionResult.value);
    } else {
      setHasPartialError(true);
    }
    if (registrationsResult.status === "fulfilled") {
      setRegistrations(registrationsResult.value.results);
    } else {
      setHasPartialError(true);
    }
    if (profileResult.status === "fulfilled") {
      setProfile(profileResult.value);
    } else {
      setHasPartialError(true);
    }
    if (readinessResult.status === "fulfilled") {
      setReadiness(readinessResult.value);
    } else {
      setHasPartialError(true);
    }
    if (roadmapResult.status === "fulfilled") {
      setRoadmapPlan(roadmapResult.value.plan);
    } else {
      setHasPartialError(true);
    }
    if (suggestionsResult.status === "fulfilled") {
      setSuggestions(suggestionsResult.value.suggestions);
    } else {
      setHasPartialError(true);
    }
    if (applicationsResult.status === "fulfilled") {
      setApplications(applicationsResult.value.results);
    } else {
      setHasPartialError(true);
    }
    if (essaysResult.status === "fulfilled") {
      setEssays(essaysResult.value.results);
    } else {
      setHasPartialError(true);
    }
    if (recommendationsResult.status === "fulfilled") {
      setTopRecommendations(
        [...recommendationsResult.value.recommendations]
          .sort((a, b) => b.fit_score - a.fit_score)
          .slice(0, 3)
      );
    } else {
      setHasPartialError(true);
    }
    if (assessmentResult.status === "fulfilled") {
      setProfileAssessment(assessmentResult.value);
    } else {
      setHasPartialError(true);
    }
    if (profileRecommendationsResult.status === "fulfilled") {
      setProfileRecommendations(profileRecommendationsResult.value.recommendations);
      setNeedsAssessment(profileRecommendationsResult.value.needs_assessment);
    } else {
      setHasPartialError(true);
    }
    if (profileStrategyResult.status === "fulfilled") {
      setProfileStrategy(profileStrategyResult.value);
    } else {
      setHasPartialError(true);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  async function handleGenerateRoadmap() {
    setIsGeneratingRoadmap(true);
    try {
      const response = await generateRoadmapRequest();
      setRoadmapPlan(response.plan);
    } catch {
      setHasPartialError(true);
    } finally {
      setIsGeneratingRoadmap(false);
    }
  }

  async function handleRefreshSuggestions() {
    setIsRefreshingSuggestions(true);
    setHasPartialError(false);
    try {
      const response = await generateSuggestionsRequest();
      setSuggestions(response.suggestions);
    } catch {
      setHasPartialError(true);
    } finally {
      setIsRefreshingSuggestions(false);
    }
  }

  async function handleAddSuggestion(suggestion: SuggestedItem) {
    try {
      await addSuggestionToRoadmapRequest(suggestion.id);
      setSuggestions((current) => current.filter((item) => item.id !== suggestion.id));
      const roadmapResponse = await getRoadmapRequest();
      setRoadmapPlan(roadmapResponse.plan);
    } catch {
      setHasPartialError(true);
    }
  }

  async function handleDismissSuggestion(suggestion: SuggestedItem) {
    try {
      await dismissSuggestionRequest(suggestion.id);
      setSuggestions((current) => current.filter((item) => item.id !== suggestion.id));
    } catch {
      setHasPartialError(true);
    }
  }

  const firstName = user?.full_name.trim().split(/\s+/)[0] || t("dashboard.student");
  const planKey = user
    ? (`plans.${user.subscription.tier}` as TranslationKey)
    : "plans.free";
  const completionPercentage = completion?.percentage ?? 0;
  const plannedExams = (profile?.exam_plans.planned ?? [])
    .filter((exam) => exam.date)
    .map((exam) => ({
      ...exam,
      daysLeft: Math.ceil(
        (new Date(`${exam.date}T00:00:00`).getTime() - Date.now()) / 86_400_000
      )
    }))
    .filter((exam) => exam.daysLeft >= 0)
    .sort((left, right) => left.daysLeft - right.daysLeft);
  const selectedClasses = profile?.interested_classes ?? [];
  const nextClass = classCatalog.find((item) =>
    selectedClasses.includes(item.value)
  );
  const roadmapTasks = useMemo(() => roadmapPlan?.tasks ?? [], [roadmapPlan]);
  const nextRoadmapTasks = roadmapTasks
    .filter((task) => task.status === "todo")
    .sort((left, right) => {
      if (!left.due_date && !right.due_date) return 0;
      if (!left.due_date) return 1;
      if (!right.due_date) return -1;
      return left.due_date.localeCompare(right.due_date);
    })
    .slice(0, 3);
  const urgentRoadmapCount = roadmapTasks.filter(
    (task) => task.priority === "urgent" && task.status === "todo"
  ).length;

  const applicationStatusCounts = useMemo(
    () => ({
      researching: applications.filter((item) => item.status === "researching").length,
      preparing: applications.filter((item) => item.status === "preparing").length,
      submitted: applications.filter((item) => item.status === "submitted").length,
      awaiting_decision: applications.filter((item) => item.status === "awaiting_decision").length
    }),
    [applications]
  );

  const essayStatusCounts = useMemo(
    () => ({
      not_started: essays.filter((item) => item.status === "not_started").length,
      needs_revision: essays.filter((item) => item.status === "needs_revision").length,
      ready: essays.filter((item) => item.status === "ready").length,
      submitted: essays.filter((item) => item.status === "submitted").length
    }),
    [essays]
  );

  const nextDeadline = useMemo(() => {
    const candidates: Array<{ label: string; date: string }> = [];
    applications.forEach((application) => {
      if (application.deadline) {
        candidates.push({ label: application.university_name, date: application.deadline });
      }
    });
    roadmapTasks
      .filter((task) => task.category === "deadlines" && task.due_date && task.status === "todo")
      .forEach((task) => {
        candidates.push({ label: task.title, date: task.due_date as string });
      });
    return candidates.sort((left, right) => left.date.localeCompare(right.date))[0] ?? null;
  }, [applications, roadmapTasks]);

  const nextDeadlineDays = useMemo(() => {
    if (!nextDeadline) return null;
    const parsed = new Date(`${nextDeadline.date}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.round((parsed.getTime() - today.getTime()) / 86_400_000);
  }, [nextDeadline]);

  const nextDeadlineUrgency = urgencyForDays(nextDeadlineDays);

  // Active applications (still being worked on) that have no user or verified
  // deadline yet — surfaced so a missing deadline is never treated as "safe".
  const missingDeadlineCount = useMemo(
    () =>
      applications.filter(
        (application) =>
          !application.deadline &&
          !["accepted", "rejected", "withdrawn"].includes(application.status)
      ).length,
    [applications]
  );

  const nextMilestones = useMemo(() => {
    const open = applications.flatMap((application) =>
      (application.milestones ?? [])
        .filter((milestone) => milestone.status === "todo" || milestone.status === "in_progress")
        .map((milestone) => ({ milestone, application }))
    );
    open.sort((left, right) => {
      if (left.milestone.due_date && right.milestone.due_date) {
        return left.milestone.due_date.localeCompare(right.milestone.due_date);
      }
      if (left.milestone.due_date) return -1;
      if (right.milestone.due_date) return 1;
      return 0;
    });
    return open.slice(0, 3);
  }, [applications]);

  const hasExamEvidence =
    plannedExams.length > 0 ||
    Boolean(
      profile &&
        Object.values(profile.test_scores).some((value) =>
          Array.isArray(value)
            ? value.length > 0
            : value !== null && value !== undefined && String(value).trim().length > 0
        )
    );
  const workflowSteps: Array<{
    key: string;
    titleKey: TranslationKey;
    href: string;
    isDone: boolean;
  }> = [
    {
      key: "profile",
      titleKey: "dashboard.workflow.step.profile",
      href: "/profile",
      isDone: completionPercentage >= 80
    },
    {
      key: "exams",
      titleKey: "dashboard.workflow.step.exams",
      href: "/profile#profile-foundation-tests",
      isDone: hasExamEvidence
    },
    {
      key: "recommendations",
      titleKey: "dashboard.workflow.step.recommendations",
      href: "/recommendations",
      isDone: topRecommendations.length > 0
    },
    {
      key: "events",
      titleKey: "dashboard.workflow.step.events",
      href: "/events",
      isDone: registrations.length > 0
    },
    {
      key: "applications",
      titleKey: "dashboard.workflow.step.applications",
      href: "/applications",
      isDone: applications.length > 0
    }
  ];
  const nextWorkflowStep = workflowSteps.find((step) => !step.isDone) ?? workflowSteps[0];

  return (
    <div className="space-y-3">
      <section className="overflow-hidden rounded-sm border bg-card shadow-card">
        <div className="grid lg:grid-cols-[1.35fr_0.65fr]">
          <div className="p-4 sm:p-5">
            <Badge>{t("dashboard.betaBadge")}</Badge>
            <p className="mt-3 text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
              {t("dashboard.eyebrow")}
            </p>
            <h1 className="mt-1.5 max-w-3xl text-xl font-semibold sm:text-3xl">
              {t("dashboard.welcome", { name: firstName })}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              {t("dashboard.commandCenterDescription")}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button asChild size="sm">
                <Link href="/events">
                  <Map aria-hidden className="mr-2 size-4" />
                  {t("dashboard.openEventMap")}
                </Link>
              </Button>
              <Button asChild variant="secondary" size="sm">
                <Link href="/profile">{t("dashboard.reviewProfile")}</Link>
              </Button>
            </div>
          </div>
          <div className="border-t bg-surface p-4 lg:border-l lg:border-t-0 lg:p-5">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">
              {t("dashboard.nextAction.label")}
            </p>
            <h2 className="mt-1.5 text-lg font-semibold">
              {nextWorkflowStep ? t(nextWorkflowStep.titleKey) : t("dashboard.nextAction.roadmap")}
            </h2>
            <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
              {t("dashboard.nextAction.description")}
            </p>
            {nextWorkflowStep ? (
              <Button asChild className="mt-3" size="sm" variant="secondary">
                <Link href={nextWorkflowStep.href}>{t("dashboard.nextAction.open")}</Link>
              </Button>
            ) : null}
            <ol className="mt-4 space-y-2">
              {workflowSteps.map((step, index) => {
                const isNext = nextWorkflowStep?.key === step.key && !step.isDone;
                return (
                  <li
                    className="flex items-center justify-between gap-3 rounded-sm border bg-card px-3 py-2 text-xs"
                    key={step.key}
                  >
                    <Link className="font-semibold hover:text-primary-hover" href={step.href}>
                      {index + 1}. {t(step.titleKey)}
                    </Link>
                    <span
                      className={`shrink-0 rounded-sm border px-1.5 py-0.5 text-[0.62rem] font-semibold uppercase tracking-wide ${
                        step.isDone
                          ? "border-success/35 bg-success/10 text-success"
                          : isNext
                            ? "border-accent/35 bg-accent/10 text-accent"
                            : "border-muted-foreground/25 bg-surface text-muted-foreground"
                      }`}
                    >
                      {step.isDone
                        ? t("dashboard.workflow.status.done")
                        : isNext
                          ? t("dashboard.workflow.status.next")
                          : t("dashboard.workflow.status.open")}
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </section>

      {hasPartialError ? (
        <Card className="flex items-center justify-between gap-4 border-warning/30 bg-warning/10">
          <p className="text-sm text-warning">{t("dashboard.partialError")}</p>
          <Button onClick={() => void loadDashboard()} type="button" variant="ghost">
            {t("events.actions.retry")}
          </Button>
        </Card>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
        <Card className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                {t("dashboard.profile.eyebrow")}
              </p>
              <h2 className="mt-1 text-lg font-semibold">
                {t("dashboard.profile.title")}
              </h2>
            </div>
            <span className="text-xl font-semibold text-accent">
              {isLoading ? "—" : `${completionPercentage}%`}
            </span>
          </div>
          <div
            aria-label={t("a11y.profileCompletion", {
              percentage: completionPercentage
            })}
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={completionPercentage}
            className="mt-4 h-2 overflow-hidden rounded-sm bg-elevated"
            role="progressbar"
          >
            <div
              className="h-full bg-primary transition-[width]"
              style={{ width: `${completionPercentage}%` }}
            />
          </div>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            {completion
              ? t("dashboard.profile.summary", {
                  completed: completion.completed_fields,
                  total: completion.total_fields
                })
              : t("dashboard.profile.loading")}
          </p>
          <div className="mt-3 rounded-sm border bg-surface p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                  {t("profileAssessment.shortTitle")}
                </p>
                <p className="mt-1 text-xs leading-4 text-muted-foreground">
                  {profileAssessment?.assessment
                    ? t("profileAssessment.dashboardSummary", {
                        score: profileAssessment.assessment.overall_profile_score,
                        confidence: t(
                          `profileAssessment.confidence.${profileAssessment.assessment.confidence}` as TranslationKey
                        )
                      })
                    : profileAssessment?.ai_available
                      ? t("profileAssessment.empty")
                      : t("profileAssessment.unavailable")}
                </p>
              </div>
              <span className="shrink-0 text-lg font-semibold text-accent">
                {profileAssessment?.assessment
                  ? profileAssessment.assessment.overall_profile_score
                  : "—"}
              </span>
            </div>
            {profileAssessment?.assessment?.missing_data.length ? (
              <p className="mt-2 text-xs text-warning">
                {t("profileAssessment.missingCount", {
                  count: profileAssessment.assessment.missing_data.length
                })}
              </p>
            ) : null}
          </div>
          <Button asChild className="mt-4" size="sm" variant="secondary">
            <Link href="/profile">
              {t("dashboard.profile.action")}
              <ArrowRight aria-hidden className="ml-2 size-3" />
            </Link>
          </Button>
        </Card>

        <Card className="p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                {t("dashboard.events.eyebrow")}
              </p>
              <h2 className="mt-1 text-lg font-semibold">
                {t("dashboard.events.title")}
              </h2>
            </div>
            <Button asChild size="sm" variant="ghost">
              <Link href="/events/my">{t("dashboard.events.viewAll")}</Link>
            </Button>
          </div>
          {isLoading ? (
            <p className="mt-4 text-xs text-muted-foreground">
              {t("dashboard.events.loading")}
            </p>
          ) : registrations.length === 0 ? (
            <div className="mt-4 rounded-sm border border-dashed bg-elevated/35 p-4">
              <p className="text-sm font-semibold">{t("dashboard.events.emptyTitle")}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {t("dashboard.events.emptyDescription")}
              </p>
              <Button asChild className="mt-3" size="sm">
                <Link href="/events">{t("dashboard.openEventMap")}</Link>
              </Button>
            </div>
          ) : (
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              {registrations.slice(0, 2).map((registration) => (
                <Link
                  className="rounded-sm border bg-elevated/45 p-3 text-sm transition-colors hover:bg-elevated"
                  href={`/events/${registration.event.slug}`}
                  key={registration.id}
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-success">
                    {t(
                      `events.registration.status.${registration.status}` as TranslationKey
                    )}
                  </p>
                  <h3 className="mt-1 font-semibold">{registration.event.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatDateTime(registration.event.start_at, locale)}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </Card>
      </section>

      <Card className="p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
              {t("dashboard.roadmapWidget.eyebrow")}
            </p>
            <h2 className="mt-1 text-lg font-semibold">{t("dashboard.roadmapWidget.title")}</h2>
          </div>
          <div className="flex items-center gap-3">
            {roadmapPlan ? (
              <span className="text-xs text-muted-foreground">
                {t("dashboard.roadmapWidget.urgentCount", { count: urgentRoadmapCount })}
              </span>
            ) : null}
            <Button asChild size="sm" variant="ghost">
              <Link href="/roadmap">{t("dashboard.roadmapWidget.openRoadmap")}</Link>
            </Button>
          </div>
        </div>
        {isLoading ? (
          <p className="mt-4 text-xs text-muted-foreground">
            {t("dashboard.roadmapWidget.loading")}
          </p>
        ) : !roadmapPlan || nextRoadmapTasks.length === 0 ? (
          <div className="mt-4 rounded-sm border border-dashed bg-elevated/35 p-4">
            <p className="text-sm font-semibold">
              {roadmapPlan
                ? t("dashboard.roadmapWidget.allCaughtUpTitle")
                : t("dashboard.roadmapWidget.emptyTitle")}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {roadmapPlan
                ? t("dashboard.roadmapWidget.allCaughtUpDescription")
                : t("dashboard.roadmapWidget.emptyDescription")}
            </p>
            <Button
              className="mt-3"
              disabled={isGeneratingRoadmap}
              onClick={() => void handleGenerateRoadmap()}
              size="sm"
            >
              {isGeneratingRoadmap
                ? t("roadmap.actions.generating")
                : t("dashboard.roadmapWidget.generate")}
            </Button>
          </div>
        ) : (
          <ul className="mt-4 space-y-2">
            {nextRoadmapTasks.map((task) => (
              <li
                className="flex items-center justify-between gap-3 rounded-sm border bg-elevated/45 p-3 text-sm"
                key={task.id}
              >
                <span className="font-semibold">{task.title}</span>
                {task.due_date ? (
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {formatDate(task.due_date, locale)}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <SuggestionPanel
        description={t("dashboard.suggestions.description")}
        isRefreshing={isRefreshingSuggestions}
        onAddToRoadmap={(suggestion) => void handleAddSuggestion(suggestion)}
        onDismiss={(suggestion) => void handleDismissSuggestion(suggestion)}
        onGenerate={() => void handleRefreshSuggestions()}
        suggestions={suggestions}
        title={t("dashboard.suggestions.title")}
      />

      <section className="grid gap-3 lg:grid-cols-2">
        <Card className="p-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:divide-x">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                {t("dashboard.applicationsWidget.title")}
              </p>
              {applications.length === 0 ? (
                <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                  <p>{t("dashboard.applicationsWidget.empty")}</p>
                  <p>{t("dashboard.applicationsWidget.emptyAction")}</p>
                </div>
              ) : (
                <dl className="mt-3 space-y-1.5 text-xs">
                  <DashboardCountRow
                    count={applicationStatusCounts.researching}
                    label={t("applications.status.researching")}
                  />
                  <DashboardCountRow
                    count={applicationStatusCounts.preparing}
                    label={t("applications.status.preparing")}
                  />
                  <DashboardCountRow
                    count={applicationStatusCounts.submitted}
                    label={t("applications.status.submitted")}
                  />
                  <DashboardCountRow
                    count={applicationStatusCounts.awaiting_decision}
                    label={t("applications.status.awaiting_decision")}
                  />
                </dl>
              )}
              <Button asChild className="mt-3" size="sm" variant="ghost">
                <Link href="/applications">{t("dashboard.applicationsWidget.open")}</Link>
              </Button>
            </div>

            <div className="sm:pl-4">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                {t("dashboard.essaysWidget.title")}
              </p>
              {essays.length === 0 ? (
                <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                  <p>{t("dashboard.essaysWidget.empty")}</p>
                  <p>{t("dashboard.essaysWidget.emptyAction")}</p>
                </div>
              ) : (
                <dl className="mt-3 space-y-1.5 text-xs">
                  <DashboardCountRow
                    count={essayStatusCounts.not_started}
                    label={t("essays.status.not_started")}
                  />
                  <DashboardCountRow
                    count={essayStatusCounts.needs_revision}
                    label={t("essays.status.needs_revision")}
                  />
                  <DashboardCountRow count={essayStatusCounts.ready} label={t("essays.status.ready")} />
                  <DashboardCountRow
                    count={essayStatusCounts.submitted}
                    label={t("essays.status.submitted")}
                  />
                </dl>
              )}
              <Button asChild className="mt-3" size="sm" variant="ghost">
                <Link href="/essays">{t("dashboard.essaysWidget.open")}</Link>
              </Button>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:divide-x">
            <div>
              <p className="flex items-center gap-1 text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                {t("dashboard.deadlineWidget.title")}
                <HelpTooltip label={t("applications.help.deadlineConfidence")} />
              </p>
              {nextDeadline ? (
                <>
                  <p className="mt-3 text-sm font-semibold">{nextDeadline.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatDate(nextDeadline.date, locale)}
                  </p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2">
                    {nextDeadlineUrgency !== "unknown" ? (
                      <span
                        className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${DASHBOARD_URGENCY_STYLES[nextDeadlineUrgency]}`}
                      >
                        {t(`applications.urgency.${nextDeadlineUrgency}` as TranslationKey)}
                      </span>
                    ) : null}
                    {nextDeadlineDays !== null && nextDeadlineDays >= 0 ? (
                      <span className="text-xs text-muted-foreground">
                        {t("applications.timeline.dueIn", { count: nextDeadlineDays })}
                      </span>
                    ) : null}
                  </div>
                </>
              ) : (
                <p className="mt-3 text-xs text-muted-foreground">
                  {t("dashboard.deadlineWidget.empty")}
                </p>
              )}
              {missingDeadlineCount > 0 ? (
                <p className="mt-2 text-xs font-semibold text-warning">
                  {t("dashboard.deadlineWidget.missingDeadlines", { count: missingDeadlineCount })}
                </p>
              ) : null}
              <Button asChild className="mt-3" size="sm" variant="ghost">
                <Link href="/roadmap">{t("dashboard.deadlineWidget.open")}</Link>
              </Button>
            </div>

            <div className="sm:pl-4">
              <p className="flex items-center gap-1 text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                {t("dashboard.milestonesWidget.title")}
                <HelpTooltip label={t("help.roadmapPriority")} />
              </p>
              {nextMilestones.length === 0 ? (
                <p className="mt-3 text-xs text-muted-foreground">
                  {applications.length === 0
                    ? t("dashboard.milestonesWidget.emptyNoApplications")
                    : t("dashboard.milestonesWidget.emptyNoMilestones")}
                </p>
              ) : (
                <ul className="mt-3 space-y-2 text-xs">
                  {nextMilestones.map(({ milestone, application }) => {
                    const days = milestone.due_date
                      ? Math.round(
                          (new Date(`${milestone.due_date}T00:00:00`).getTime() -
                            new Date(new Date().toDateString()).getTime()) /
                            86_400_000
                        )
                      : null;
                    const urgency = urgencyForDays(days);
                    return (
                      <li key={milestone.id}>
                        <Link
                          className="block rounded-sm px-1 py-1 hover:bg-elevated"
                          href="/applications"
                        >
                          <span className="flex items-center justify-between gap-2">
                            <span className="truncate font-semibold">{milestone.title}</span>
                            {milestone.due_date && urgency !== "unknown" ? (
                              <span
                                className={`shrink-0 rounded-sm border px-1.5 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide ${DASHBOARD_URGENCY_STYLES[urgency]}`}
                              >
                                {t(`applications.urgency.${urgency}` as TranslationKey)}
                              </span>
                            ) : null}
                          </span>
                          <span className="mt-0.5 block truncate text-muted-foreground">
                            {application.university_name}
                            {milestone.due_date ? ` · ${formatDate(milestone.due_date, locale)}` : ""}
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
              <Button asChild className="mt-3" size="sm" variant="ghost">
                <Link href="/applications">{t("dashboard.milestonesWidget.open")}</Link>
              </Button>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:divide-x">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                {t("dashboard.gapsWidget.title")}
              </p>
              {readiness && readiness.improvements.length > 0 ? (
                <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                  {readiness.improvements.slice(0, 4).map((component) => (
                    <li key={component}>
                      <Link
                        className="flex items-center justify-between gap-2 rounded-sm px-1 py-1 hover:bg-elevated"
                        href={profileSectionHref(component)}
                      >
                        <span className="flex min-w-0 items-center gap-1.5">
                          <AlertTriangle aria-hidden className="size-3 shrink-0 text-warning" />
                          <span className="truncate">
                            {t(`admissions.component.${component}` as TranslationKey)}
                          </span>
                        </span>
                        <ArrowRight aria-hidden className="size-3 shrink-0" />
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-xs text-muted-foreground">{t("dashboard.gapsWidget.empty")}</p>
              )}
              <Button asChild className="mt-3" size="sm" variant="ghost">
                <Link href="/profile">{t("dashboard.gapsWidget.strengthenProfile")}</Link>
              </Button>
            </div>

            <div className="sm:pl-4">
              <p className="flex items-center gap-1 text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                {t("dashboard.recommendationsWidget.title")}
                <HelpTooltip label={t("help.fitSubscores")} />
              </p>
              {topRecommendations.length === 0 ? (
                <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                  <p>{t("dashboard.recommendationsWidget.empty")}</p>
                  <p>{t("dashboard.recommendationsWidget.context")}</p>
                </div>
              ) : (
                <ul className="mt-3 space-y-1.5 text-xs">
                  {topRecommendations.map((item) => (
                    <li className="flex items-center justify-between gap-2" key={item.university.slug}>
                      <span className="truncate">{item.university.name}</span>
                      <span className="shrink-0 rounded-sm border bg-surface px-1.5 py-0.5 text-[0.65rem] font-bold">
                        {item.fit_score}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <Button asChild className="mt-3" size="sm" variant="ghost">
                <Link href="/recommendations">{t("dashboard.recommendationsWidget.open")}</Link>
              </Button>
            </div>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        {readiness ? (
          <ReadinessCard compact readiness={readiness} />
        ) : (
          <Card className="p-4">
            <p className="text-xs text-muted-foreground">
              {t("profile.loading")}
            </p>
          </Card>
        )}
        <Card className="p-4">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
            {t("dashboard.learning.title")}
          </p>
          <h2 className="mt-1 text-lg font-semibold">
            {nextClass ? t(nextClass.labelKey) : t("dashboard.learning.empty")}
          </h2>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            {t("dashboard.learning.description")}
          </p>
          {selectedClasses.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {selectedClasses.slice(0, 6).map((value) => {
                const catalogItem = classCatalog.find(
                  (item) => item.value === value
                );
                return (
                  <Badge key={value} className="text-xs">
                    {catalogItem ? t(catalogItem.labelKey) : value}
                  </Badge>
                );
              })}
            </div>
          ) : null}
          <Button asChild className="mt-4" size="sm" variant="secondary">
            <Link href="/profile">
              {t("dashboard.readiness.action")}
              <ArrowRight aria-hidden className="ml-2 size-3" />
            </Link>
          </Button>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <GapRecommendationsPanel
          isLoading={isLoading}
          needsAssessment={needsAssessment}
          recommendations={profileRecommendations}
        />
        <StrategyPanel isLoading={isLoading} strategy={profileStrategy} />
      </section>

      <Card className="p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
              {t("dashboard.examCountdown.eyebrow")}
            </p>
            <h2 className="mt-1 text-lg font-semibold">
              {t("dashboard.examCountdown.title")}
            </h2>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              {t("dashboard.examCountdown.description")}
            </p>
          </div>
          <Button asChild size="sm" variant="secondary">
            <Link href="/profile">{t("dashboard.examCountdown.manage")}</Link>
          </Button>
        </div>
        {plannedExams.length ? (
          <div className="mt-4 flex flex-wrap gap-3">
            {plannedExams.slice(0, 3).map((exam) => (
              <div
                className="min-w-[15rem] flex-1 border-l-4 border-primary bg-surface p-3"
                key={`${exam.name}-${exam.date}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-serif text-base font-semibold">{exam.name}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{exam.date}</p>
                  </div>
                  <CalendarClock aria-hidden className="size-4 text-accent shrink-0" />
                </div>
                <p className="mt-3 text-2xl font-semibold text-primary-hover">
                  {t("dashboard.examCountdown.days", { count: exam.daysLeft })}
                </p>
                {exam.target_score ? (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t("dashboard.examCountdown.target", { score: exam.target_score })}
                  </p>
                ) : null}
                <p className="mt-2 border-t pt-2 text-xs leading-4 text-muted-foreground">
                  {nextClass
                    ? `${t("dashboard.learning.next")}: ${t(nextClass.labelKey)}`
                    : t("dashboard.examCountdown.nextAction")}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-4 border border-dashed bg-elevated/35 p-4">
            <p className="text-sm font-semibold">{t("dashboard.examCountdown.emptyTitle")}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {t("dashboard.examCountdown.emptyDescription")}
            </p>
          </div>
        )}
      </Card>

      <section aria-labelledby="dashboard-workspace">
        <div className="mb-3 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
              {t("dashboard.workspace.eyebrow")}
            </p>
            <h2 className="mt-1 text-lg font-semibold" id="dashboard-workspace">
              {t("dashboard.workspace.title")}
            </h2>
          </div>
          <span className="hidden text-xs text-muted-foreground sm:block">
            {t("dashboard.workspace.betaNote")}
          </span>
        </div>
        <div className="flex flex-wrap gap-3">
          <DashboardModuleCard
            detail={t("dashboard.universities.detail")}
            disclaimer={t("beta.disclaimer.admissions")}
            href="/universities"
            icon={GraduationCap}
            title={t("dashboard.universities.title")}
          />
          <DashboardModuleCard
            detail={t("dashboard.exams.detail")}
            href="/exams"
            icon={BookOpenCheck}
            title={t("dashboard.exams.title")}
          />
          {profile?.onboarding_completed_at ? (
            <DashboardModuleCard
              detail={t("dashboard.essays.detail")}
              disclaimer={t("beta.disclaimer.essays")}
              href="/essays"
              icon={FilePenLine}
              title={t("dashboard.essays.title")}
            />
          ) : null}
          <DashboardModuleCard
            detail={t("dashboard.finance.detail")}
            disclaimer={t("beta.disclaimer.finance")}
            href="/finance"
            icon={CircleDollarSign}
            title={t("dashboard.finance.title")}
          />
          <DashboardModuleCard
            detail={t("dashboard.activities.detail")}
            href="/activities"
            icon={CalendarDays}
            title={t("dashboard.activities.title")}
          />
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card className="p-4">
          <div className="flex items-start gap-3">
            <Sparkles aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
            <div>
              <Badge className="text-xs">{t("dashboard.assistant.badge")}</Badge>
              <h2 className="mt-2 text-base font-semibold">
                {t("dashboard.assistant.title")}
              </h2>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                {t("dashboard.assistant.description")}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
            {t("dashboard.subscription.eyebrow")}
          </p>
          <div className="mt-2 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">{t(planKey)}</h2>
            <Badge className="text-xs">{t("dashboard.subscription.mock")}</Badge>
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
            <div>
              <dt className="text-muted-foreground">
                {t("dashboard.subscription.aiUsage")}
              </dt>
              <dd className="mt-0.5 font-semibold">
                {user?.subscription.ai_message_count ?? 0}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">
                {t("dashboard.subscription.essayUsage")}
              </dt>
              <dd className="mt-0.5 font-semibold">
                {user?.subscription.essay_review_count ?? 0}
              </dd>
            </div>
          </dl>
          <p className="mt-4 rounded-sm border bg-elevated/45 px-3 py-2 text-xs font-semibold text-muted-foreground">
            {t("dashboard.subscription.plansComingSoon")}
          </p>
        </Card>
      </section>

      <p className="text-xs leading-4 text-muted-foreground">
        {t("dashboard.disclaimer")}
      </p>
    </div>
  );
}

function DashboardModuleCard({
  icon: Icon,
  title,
  detail,
  href,
  disclaimer
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
  href: string;
  disclaimer?: string;
}) {
  const { t } = useI18n();

  return (
    <Card className="flex min-w-[14rem] flex-1 flex-col p-4">
      <Icon aria-hidden className="size-4 text-accent" />
      <h3 className="mt-2 text-base font-semibold">{title}</h3>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
      {disclaimer ? (
        <p className="mt-2 text-xs leading-4 text-muted-foreground">{disclaimer}</p>
      ) : null}
      <Link
        className="mt-auto inline-flex items-center gap-2 pt-3 text-xs font-semibold text-primary-hover hover:underline"
        href={href}
      >
        {t("dashboard.workspace.openModule")}
        <ArrowRight aria-hidden className="size-3" />
      </Link>
    </Card>
  );
}

function DashboardCountRow({ label, count }: { label: string; count: number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-semibold">{count}</span>
    </div>
  );
}
