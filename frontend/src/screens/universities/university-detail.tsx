"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  FileText,
  HelpCircle,
  ListChecks,
  Route,
  Star
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import type { ApplicationTrackerItem } from "@/entities/application";
import type { StudentProfileDetails } from "@/entities/profile";
import type { RoadmapTask } from "@/entities/roadmap";
import {
  formatTuitionAmount,
  getFieldVerification,
  type UniversityDetails,
  type UniversityFitAnalysis
} from "@/entities/university";
import { StatValue } from "@/entities/university/ui/stat-value";
import { VerifiedStat } from "@/entities/university/ui/verified-stat";
import { createApplicationRequest, getApplicationsRequest } from "@/features/applications";
import { getEssaysRequest } from "@/features/essays";
import { getProfileItemsRequest, getProfileRequest } from "@/features/profile";
import { generateRoadmapRequest, getRoadmapTasksRequest } from "@/features/roadmap";
import {
  addToShortlistRequest,
  getUniversityFitRequest,
  getUniversityRequest,
  removeFromShortlistRequest
} from "@/features/universities";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const CATEGORY_STYLES: Record<string, string> = {
  reach: "border-danger/35 bg-danger/10 text-danger",
  competitive: "border-warning/35 bg-warning/10 text-warning",
  target: "border-accent/35 bg-accent/10 text-accent",
  safety: "border-success/35 bg-success/10 text-success"
};

const STATUS_STYLES: Record<string, string> = {
  strong: "border-success/35 bg-success/10 text-success",
  on_track: "border-accent/35 bg-accent/10 text-accent",
  gap: "border-warning/35 bg-warning/10 text-warning",
  missing: "border-muted-foreground/30 bg-surface text-muted-foreground",
  not_verified: "border-muted-foreground/30 bg-surface text-muted-foreground",
  not_tracked: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

const TABS = [
  "overview",
  "requirements",
  "essays",
  "financial_aid",
  "deadlines",
  "contact",
  "sources",
  "roadmap"
] as const;

type Tab = (typeof TABS)[number];

export function UniversityDetailScreen({ slug }: { slug: string }) {
  const { locale, t } = useI18n();
  const [university, setUniversity] = useState<UniversityDetails | null>(null);
  const [fit, setFit] = useState<UniversityFitAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isFitLoading, setIsFitLoading] = useState(true);
  const [hasFitError, setHasFitError] = useState(false);
  const [isShortlistPending, setIsShortlistPending] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [profile, setProfile] = useState<StudentProfileDetails | null>(null);
  const [itemCounts, setItemCounts] = useState<Record<string, number>>({});
  const [roadmapTasks, setRoadmapTasks] = useState<RoadmapTask[]>([]);
  const [existingApplication, setExistingApplication] = useState<ApplicationTrackerItem | null>(
    null
  );
  const [isStartingApplication, setIsStartingApplication] = useState(false);

  const loadUniversity = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      setUniversity(await getUniversityRequest(slug));
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [slug]);

  const loadFit = useCallback(async () => {
    setIsFitLoading(true);
    setHasFitError(false);
    try {
      setFit(await getUniversityFitRequest(slug));
    } catch {
      setHasFitError(true);
    } finally {
      setIsFitLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void loadUniversity();
    void loadFit();
  }, [loadUniversity, loadFit]);

  useEffect(() => {
    async function loadRequirementsContext() {
      const [profileResult, activities, honors, olympiads, research, portfolio, essays] =
        await Promise.allSettled([
          getProfileRequest(),
          getProfileItemsRequest("activities"),
          getProfileItemsRequest("honors"),
          getProfileItemsRequest("olympiads"),
          getProfileItemsRequest("research-projects"),
          getProfileItemsRequest("portfolio-projects"),
          getEssaysRequest()
        ]);
      if (profileResult.status === "fulfilled") setProfile(profileResult.value);
      const honorsCount = honors.status === "fulfilled" ? honors.value.results.length : 0;
      const olympiadsCount = olympiads.status === "fulfilled" ? olympiads.value.results.length : 0;
      setItemCounts({
        activities: activities.status === "fulfilled" ? activities.value.results.length : 0,
        honors: honorsCount + olympiadsCount,
        research: research.status === "fulfilled" ? research.value.results.length : 0,
        portfolio: portfolio.status === "fulfilled" ? portfolio.value.results.length : 0,
        essays: essays.status === "fulfilled" ? essays.value.results.length : 0
      });
    }
    void loadRequirementsContext();
  }, []);

  useEffect(() => {
    if (!university) return;
    getRoadmapTasksRequest({ linked_university: String(university.id) })
      .then((response) => setRoadmapTasks(response.results))
      .catch(() => setRoadmapTasks([]));
    getApplicationsRequest({ university: String(university.id) })
      .then((response) => setExistingApplication(response.results[0] ?? null))
      .catch(() => setExistingApplication(null));
  }, [university]);

  async function toggleShortlist() {
    if (!university) return;
    setIsShortlistPending(true);
    try {
      if (university.is_shortlisted) {
        await removeFromShortlistRequest(university.slug);
      } else {
        await addToShortlistRequest(university.slug);
      }
      setUniversity((current) =>
        current ? { ...current, is_shortlisted: !current.is_shortlisted } : current
      );
    } catch {
      setHasError(true);
    } finally {
      setIsShortlistPending(false);
    }
  }

  async function handleStartApplication() {
    if (!university) return;
    setIsStartingApplication(true);
    try {
      const created = await createApplicationRequest({ university: university.id });
      setExistingApplication(created);
    } catch {
      // Surfaced implicitly: the button remains in its "start tracking" state.
    } finally {
      setIsStartingApplication(false);
    }
  }

  async function handleAddToRoadmap() {
    const response = await generateRoadmapRequest();
    if (university) {
      getRoadmapTasksRequest({ linked_university: String(university.id) })
        .then((result) => setRoadmapTasks(result.results))
        .catch(() => undefined);
    }
    return response;
  }

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">{t("universities.states.loadingDetail")}</p>
      </Card>
    );
  }

  if (hasError || !university) {
    return (
      <Card>
        <p className="text-sm text-danger" role="alert">
          {t("universities.states.detailError")}
        </p>
        <Button className="mt-4" onClick={() => void loadUniversity()} type="button">
          {t("universities.actions.retry")}
        </Button>
      </Card>
    );
  }

  const currentUniversity = university;
  const studentGpa = profile?.gpa ?? null;
  const studentSat = profile?.test_scores?.sat != null ? String(profile.test_scores.sat) : null;
  const studentIelts = profile?.test_scores?.ielts != null ? String(profile.test_scores.ielts) : null;

  function gpaStatus(): string {
    if (studentGpa === null) return "missing";
    if (currentUniversity.gpa_average === null) return "not_verified";
    if (fit?.risks.includes("gpa_below_average")) return "gap";
    if (fit?.strengths.includes("gpa_above_average")) return "strong";
    return "on_track";
  }

  function satStatus(): string {
    if (studentSat === null) return "missing";
    if (currentUniversity.sat_average === null) return "not_verified";
    if (fit?.risks.includes("sat_below_average")) return "gap";
    if (fit?.strengths.includes("sat_above_average")) return "strong";
    return "on_track";
  }

  function ieltsStatus(): string {
    if (studentIelts === null) return "missing";
    if (currentUniversity.ielts_minimum === null) return "not_verified";
    return Number(studentIelts) >= Number(currentUniversity.ielts_minimum) ? "on_track" : "gap";
  }

  const qualitativeRows: Array<{ key: string; labelKey: TranslationKey; count: number }> = [
    { key: "activities", labelKey: "universities.requirements.activities", count: itemCounts.activities ?? 0 },
    { key: "honors", labelKey: "universities.requirements.honorsOlympiads", count: itemCounts.honors ?? 0 },
    { key: "research", labelKey: "universities.requirements.research", count: itemCounts.research ?? 0 },
    { key: "portfolio", labelKey: "universities.requirements.portfolio", count: itemCounts.portfolio ?? 0 },
    { key: "essays", labelKey: "universities.requirements.essayStatus", count: itemCounts.essays ?? 0 }
  ];

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <div className="flex flex-wrap items-center gap-2">
          {university.institution_type ? (
            <Badge>
              {t(`universities.institutionType.${university.institution_type}` as TranslationKey)}
            </Badge>
          ) : (
            <span className="rounded-sm border bg-surface px-2.5 py-1 text-xs text-muted-foreground">
              {t("universities.institutionType.unknown")}
            </span>
          )}
          {university.qs_ranking ? (
            <Badge>
              {t("universities.fields.qsRanking")} #{university.qs_ranking}
              {university.qs_ranking_year ? ` (${university.qs_ranking_year})` : ""}
            </Badge>
          ) : null}
          {university.is_demo ? (
            <span className="rounded-sm border border-warning/35 bg-warning/10 px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-[0.08em] text-warning">
              {t("universities.demoDataBadge")}
            </span>
          ) : null}
        </div>
        <h1 className="mt-5 max-w-4xl text-3xl font-semibold sm:text-5xl">{university.name}</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          {[university.city, university.country].filter(Boolean).join(", ")}
        </p>
        {university.summary ? (
          <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
            {university.summary}
          </p>
        ) : null}
        <div className="mt-5 flex flex-wrap gap-3">
          <Button
            disabled={isShortlistPending}
            onClick={() => void toggleShortlist()}
            type="button"
            variant={university.is_shortlisted ? "secondary" : "primary"}
          >
            <Star
              aria-hidden
              className="mr-2 size-4"
              fill={university.is_shortlisted ? "currentColor" : "none"}
            />
            {university.is_shortlisted
              ? t("universities.actions.shortlisted")
              : t("universities.actions.shortlist")}
          </Button>
          {university.is_shortlisted ? (
            <Button asChild variant="ghost">
              <Link href="/roadmap">
                <Route aria-hidden className="mr-2 size-4" />
                {t("universities.actions.viewInRoadmap")}
              </Link>
            </Button>
          ) : null}
          {existingApplication ? (
            <Button asChild variant="ghost">
              <Link href="/applications">
                <ClipboardList aria-hidden className="mr-2 size-4" />
                {t("universities.actions.viewApplication")}
              </Link>
            </Button>
          ) : (
            <Button
              disabled={isStartingApplication}
              onClick={() => void handleStartApplication()}
              type="button"
              variant="ghost"
            >
              <ClipboardList aria-hidden className="mr-2 size-4" />
              {t("universities.actions.startApplication")}
            </Button>
          )}
        </div>
      </section>

      <div className="flex flex-wrap gap-2 border-b pb-3">
        {TABS.map((tab) => (
          <Button
            key={tab}
            onClick={() => setActiveTab(tab)}
            size="sm"
            type="button"
            variant={activeTab === tab ? "primary" : "ghost"}
          >
            {t(`universities.tabs.${tab}` as TranslationKey)}
          </Button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-6">
          {activeTab === "overview" ? (
            <>
              <Card>
                <h2 className="text-2xl font-semibold">{t("universities.detail.statistics")}</h2>
                <dl className="mt-5 grid gap-5 sm:grid-cols-2">
                  <DetailItem label={t("universities.fields.acceptanceRate")}>
                    <VerifiedStat
                      suffix="%"
                      value={university.acceptance_rate}
                      verification={getFieldVerification(
                        university.field_verifications,
                        "acceptance_rate"
                      )}
                    />
                  </DetailItem>
                  <DetailItem label={t("universities.fields.gpaAverage")}>
                    <VerifiedStat
                      value={university.gpa_average}
                      verification={getFieldVerification(university.field_verifications, "gpa_average")}
                    />
                  </DetailItem>
                  <DetailItem label={t("universities.fields.satAverage")}>
                    <VerifiedStat
                      value={university.sat_average}
                      verification={getFieldVerification(university.field_verifications, "sat_average")}
                    />
                  </DetailItem>
                  <DetailItem label={t("universities.fields.satRange")}>
                    {university.sat_p25 && university.sat_p75 ? (
                      <VerifiedStat
                        value={`${university.sat_p25}–${university.sat_p75}`}
                        verification={getFieldVerification(university.field_verifications, "sat_p25")}
                      />
                    ) : (
                      <StatValue value={null} />
                    )}
                  </DetailItem>
                  <DetailItem label={t("universities.fields.testPolicy")}>
                    {university.test_policy ? (
                      <VerifiedStat
                        value={t(`universities.testPolicy.${university.test_policy}` as TranslationKey)}
                        verification={getFieldVerification(university.field_verifications, "test_policy")}
                      />
                    ) : (
                      <StatValue value={null} />
                    )}
                  </DetailItem>
                  <DetailItem label={t("universities.fields.qsRanking")}>
                    {university.qs_ranking ? (
                      <VerifiedStat
                        value={
                          university.qs_ranking_year
                            ? `#${university.qs_ranking} (${university.qs_ranking_year})`
                            : `#${university.qs_ranking}`
                        }
                        verification={getFieldVerification(university.field_verifications, "qs_ranking")}
                      />
                    ) : (
                      <StatValue value={null} />
                    )}
                  </DetailItem>
                </dl>
              </Card>
              <Card>
                <h2 className="text-2xl font-semibold">{t("universities.detail.programs")}</h2>
                {university.programs.length === 0 ? (
                  <p className="mt-3 text-sm italic text-muted-foreground">
                    {t("universities.notVerifiedYet")}
                  </p>
                ) : (
                  <ul className="mt-3 space-y-2 text-sm">
                    {university.programs.map((program) => (
                      <li className="rounded-sm border bg-surface px-3 py-2" key={program.id}>
                        <span className="font-semibold">{program.name}</span>
                        {program.degree_level ? (
                          <span className="ml-2 text-muted-foreground">{program.degree_level}</span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </>
          ) : null}

          {activeTab === "requirements" ? (
            <Card>
              <h2 className="text-2xl font-semibold">{t("universities.requirements.title")}</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {t("universities.requirements.description")}
              </p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs uppercase tracking-wide text-muted-foreground">
                      <th className="py-2">{t("universities.requirements.metric")}</th>
                      <th className="py-2">{t("universities.requirements.universityValue")}</th>
                      <th className="py-2">{t("universities.requirements.yourProfile")}</th>
                      <th className="py-2">{t("universities.requirements.status")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <RequirementRow
                      label={t("universities.fields.gpaAverage")}
                      status={gpaStatus()}
                      universityValue={university.gpa_average ?? t("universities.notVerifiedYet")}
                      yourValue={studentGpa ?? t("universities.requirements.addToProfile")}
                    />
                    <RequirementRow
                      label={t("universities.fields.satAverage")}
                      status={satStatus()}
                      universityValue={university.sat_average ?? t("universities.notVerifiedYet")}
                      yourValue={studentSat ?? t("universities.requirements.addToProfile")}
                    />
                    <RequirementRow
                      label={t("universities.fields.ieltsMinimum")}
                      status={ieltsStatus()}
                      universityValue={university.ielts_minimum ?? t("universities.notVerifiedYet")}
                      yourValue={studentIelts ?? t("universities.requirements.addToProfile")}
                    />
                  </tbody>
                </table>
              </div>

              <h3 className="mt-6 text-sm font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                {t("universities.requirements.qualitativeTitle")}
              </h3>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <tbody>
                    {qualitativeRows.map((row) => (
                      <tr className="border-t" key={row.key}>
                        <td className="py-2">{t(row.labelKey)}</td>
                        <td className="py-2">
                          {row.count > 0
                            ? t("universities.requirements.present", { count: row.count })
                            : t("universities.requirements.missingItem")}
                        </td>
                        <td className="py-2">
                          <StatusBadge status={row.count > 0 ? "on_track" : "missing"} />
                        </td>
                      </tr>
                    ))}
                    <tr className="border-t">
                      <td className="py-2">{t("universities.requirements.recommendationLetters")}</td>
                      <td className="py-2 italic text-muted-foreground">
                        {t("universities.requirements.notTrackedYet")}
                      </td>
                      <td className="py-2">
                        <StatusBadge status="not_tracked" />
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="mt-4 text-xs leading-5 text-muted-foreground">
                {t("universities.requirements.disclaimer")}
              </p>
            </Card>
          ) : null}

          {activeTab === "essays" ? (
            <Card>
              <h2 className="text-2xl font-semibold">{t("universities.detail.essays")}</h2>
              {university.essay_requirements ? (
                <VerifiedStat
                  value={university.essay_requirements}
                  verification={getFieldVerification(university.field_verifications, "essay_requirements")}
                />
              ) : (
                <p className="mt-3 text-sm italic text-muted-foreground">
                  {t("universities.notVerifiedYet")}
                </p>
              )}
              <Button asChild className="mt-4" size="sm" variant="secondary">
                <Link href="/essays">
                  <FileText aria-hidden className="mr-2 size-4" />
                  {t("universities.essaysTab.openWorkspace")}
                </Link>
              </Button>
            </Card>
          ) : null}

          {activeTab === "financial_aid" ? (
            <>
              <Card>
                <h2 className="text-2xl font-semibold">{t("universities.detail.financialAid")}</h2>
                <dl className="mt-5 grid gap-5 sm:grid-cols-2">
                  <DetailItem label={t("universities.fields.tuition")}>
                    <VerifiedStat
                      suffix={university.tuition_amount ? ` ${university.tuition_currency}` : ""}
                      value={formatTuitionAmount(university.tuition_amount)}
                      verification={getFieldVerification(university.field_verifications, "tuition_amount")}
                    />
                  </DetailItem>
                  <DetailItem label={t("universities.fields.scholarshipAvailable")}>
                    <VerifiedStat
                      value={university.scholarship_available}
                      verification={getFieldVerification(
                        university.field_verifications,
                        "scholarship_available"
                      )}
                    />
                  </DetailItem>
                </dl>
                {university.financial_aid_url ? (
                  <a
                    className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-primary-hover hover:underline"
                    href={university.financial_aid_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {t("universities.fields.financialAidUrl")}
                    <ExternalLink aria-hidden className="size-3.5" />
                  </a>
                ) : (
                  <p className="mt-4 text-sm italic text-muted-foreground">
                    {t("universities.notVerifiedYet")}
                  </p>
                )}
              </Card>
              <Card>
                <h2 className="text-2xl font-semibold">{t("universities.detail.scholarships")}</h2>
                {university.scholarships.length === 0 ? (
                  <p className="mt-3 text-sm italic text-muted-foreground">
                    {t("universities.notVerifiedYet")}
                  </p>
                ) : (
                  <ul className="mt-3 space-y-2 text-sm">
                    {university.scholarships.map((scholarship) => (
                      <li className="rounded-sm border bg-surface px-3 py-2" key={scholarship.id}>
                        <span className="font-semibold">{scholarship.name}</span>
                        {scholarship.deadline ? (
                          <span className="ml-2 text-muted-foreground">
                            {formatDate(scholarship.deadline, locale)}
                          </span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </>
          ) : null}

          {activeTab === "deadlines" ? (
            <Card>
              <h2 className="text-2xl font-semibold">{t("universities.detail.deadlines")}</h2>
              <dl className="mt-5 grid gap-5 sm:grid-cols-2">
                <DetailItem label={t("universities.fields.applicationDeadline")}>
                  {university.application_deadline ? (
                    <VerifiedStat
                      value={formatDate(university.application_deadline, locale)}
                      verification={getFieldVerification(
                        university.field_verifications,
                        "application_deadline"
                      )}
                    />
                  ) : (
                    <StatValue value={null} />
                  )}
                </DetailItem>
              </dl>
              <h3 className="mt-5 border-t pt-4 text-sm font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                {t("universities.deadlinesTab.linkedTasks")}
              </h3>
              {roadmapTasks.filter((task) => task.category === "deadlines").length === 0 ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  {t("universities.deadlinesTab.noLinkedTasks")}
                </p>
              ) : (
                <ul className="mt-2 space-y-1.5 text-sm">
                  {roadmapTasks
                    .filter((task) => task.category === "deadlines")
                    .map((task) => (
                      <li
                        className="flex items-center justify-between gap-3 rounded-sm border bg-surface px-3 py-2"
                        key={task.id}
                      >
                        <span>{task.title}</span>
                        {task.due_date ? (
                          <span className="text-xs text-muted-foreground">
                            {formatDate(task.due_date, locale)}
                          </span>
                        ) : null}
                      </li>
                    ))}
                </ul>
              )}
            </Card>
          ) : null}

          {activeTab === "contact" ? (
            <Card>
              <h2 className="text-2xl font-semibold">{t("universities.detail.contact")}</h2>
              <ul className="mt-4 space-y-3 text-sm">
                <ContactLink label={t("universities.fields.admissionsUrl")} url={university.admissions_url} />
                <ContactLink
                  label={t("universities.fields.financialAidUrl")}
                  url={university.financial_aid_url}
                />
                <ContactLink
                  label={t("universities.fields.applicationPortalUrl")}
                  url={university.application_portal_url}
                />
                <ContactLink
                  label={t("universities.fields.internationalOfficeUrl")}
                  url={university.international_office_url}
                />
                <ContactLink
                  label={t("universities.fields.virtualInfoSessionUrl")}
                  url={university.virtual_info_session_url}
                />
              </ul>
            </Card>
          ) : null}

          {activeTab === "sources" ? (
            <>
              <Card>
                <h2 className="text-2xl font-semibold">{t("universities.detail.sources")}</h2>
                <ul className="mt-3 space-y-2 text-sm">
                  {university.data_sources.length === 0 ? (
                    <li>
                      <a
                        className="inline-flex items-center gap-2 font-semibold text-primary-hover hover:underline"
                        href={university.official_website}
                        rel="noreferrer"
                        target="_blank"
                      >
                        {university.name}
                        <ExternalLink aria-hidden className="size-4" />
                      </a>
                    </li>
                  ) : (
                    university.data_sources.map((source) => (
                      <li key={source.id}>
                        <a
                          className="inline-flex items-center gap-2 font-semibold text-primary-hover hover:underline"
                          href={source.source_url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          {source.source_title}
                          <ExternalLink aria-hidden className="size-4" />
                        </a>
                        {!source.is_official ? (
                          <span className="ml-2 text-xs text-muted-foreground">
                            {t("universities.detail.unofficialSource")}
                          </span>
                        ) : null}
                      </li>
                    ))
                  )}
                </ul>
              </Card>
              <Card>
                <h2 className="text-2xl font-semibold">{t("universities.sourcesTab.fieldVerifications")}</h2>
                {university.field_verifications.length === 0 ? (
                  <p className="mt-3 text-sm italic text-muted-foreground">
                    {t("universities.notVerifiedYet")}
                  </p>
                ) : (
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="text-xs uppercase tracking-wide text-muted-foreground">
                          <th className="py-2">{t("universities.sourcesTab.field")}</th>
                          <th className="py-2">{t("universities.sourcesTab.status")}</th>
                          <th className="py-2">{t("universities.sourcesTab.lastVerified")}</th>
                          <th className="py-2">{t("universities.sourcesTab.source")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {university.field_verifications.map((verification) => (
                          <tr className="border-t" key={verification.field_name}>
                            <td className="py-2">{verification.field_name}</td>
                            <td className="py-2">
                              {t(`universities.verification.status.${verification.status}` as TranslationKey)}
                            </td>
                            <td className="py-2">{formatDate(verification.last_verified_date, locale)}</td>
                            <td className="py-2">
                              <a
                                className="inline-flex items-center gap-1 text-primary-hover hover:underline"
                                href={verification.source_url}
                                rel="noreferrer"
                                target="_blank"
                              >
                                {t("universities.verification.source")}
                                <ExternalLink aria-hidden className="size-3.5" />
                              </a>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </>
          ) : null}

          {activeTab === "roadmap" ? (
            <Card>
              <h2 className="text-2xl font-semibold">{t("universities.roadmapTab.title")}</h2>
              <div className="mt-3">
                {existingApplication ? (
                  <p className="text-sm text-muted-foreground">
                    {t("universities.roadmapTab.applicationStatus", {
                      status: t(`applications.status.${existingApplication.status}` as TranslationKey)
                    })}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {t("universities.roadmapTab.noApplication")}
                  </p>
                )}
              </div>
              <h3 className="mt-5 border-t pt-4 text-sm font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                {t("universities.roadmapTab.linkedTasks")}
              </h3>
              {roadmapTasks.length === 0 ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  {t("universities.roadmapTab.noLinkedTasks")}
                </p>
              ) : (
                <ul className="mt-2 space-y-1.5 text-sm">
                  {roadmapTasks.map((task) => (
                    <li
                      className="flex items-center justify-between gap-3 rounded-sm border bg-surface px-3 py-2"
                      key={task.id}
                    >
                      <span>{task.title}</span>
                      {task.due_date ? (
                        <span className="text-xs text-muted-foreground">
                          {formatDate(task.due_date, locale)}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
              <Button className="mt-4" onClick={() => void handleAddToRoadmap()} size="sm" type="button">
                {t("universities.roadmapTab.addMissingRequirements")}
              </Button>
            </Card>
          ) : null}
        </div>

        <aside className="space-y-5">
          <Card className="bg-elevated/55">
            <h2 className="text-xl font-semibold">{t("universities.fit.title")}</h2>
            {isFitLoading ? (
              <p className="mt-3 text-sm text-muted-foreground">
                {t("universities.states.loading")}
              </p>
            ) : hasFitError || !fit ? (
              <>
                <p className="mt-3 text-sm text-danger" role="alert">
                  {t("universities.states.loadError")}
                </p>
                <Button className="mt-3" onClick={() => void loadFit()} type="button">
                  {t("universities.actions.retry")}
                </Button>
              </>
            ) : (
              <div className="mt-3 space-y-4">
                <span
                  className={`inline-flex items-center rounded-sm border px-3 py-1.5 text-sm font-semibold ${
                    fit.category
                      ? CATEGORY_STYLES[fit.category]
                      : "border-muted-foreground/30 bg-surface text-muted-foreground"
                  }`}
                >
                  {fit.category
                    ? t(`universities.fit.category.${fit.category}` as TranslationKey)
                    : t("universities.fit.category.unknown")}
                </span>

                <FitList
                  emptyKey={null}
                  icon={CheckCircle2}
                  iconClassName="text-success"
                  items={fit.strengths}
                  prefix="universities.fit.strengths"
                  title={t("universities.fit.strengthsTitle")}
                />
                <FitList
                  emptyKey={null}
                  icon={AlertTriangle}
                  iconClassName="text-danger"
                  items={fit.risks}
                  prefix="universities.fit.risks"
                  title={t("universities.fit.risksTitle")}
                />
                <FitList
                  emptyKey={null}
                  icon={HelpCircle}
                  iconClassName="text-muted-foreground"
                  items={fit.missing_fields}
                  prefix="universities.fit.missingFields"
                  title={t("universities.fit.missingFieldsTitle")}
                />
                <FitList
                  emptyKey={null}
                  icon={ListChecks}
                  iconClassName="text-accent"
                  items={fit.next_actions}
                  prefix="universities.fit.nextActions"
                  title={t("universities.fit.nextActionsTitle")}
                />

                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                    {t("universities.fit.sourceNotesTitle")}
                  </h3>
                  <ul className="mt-2 space-y-1.5 text-sm">
                    {fit.source_notes.map((note) => (
                      <li key={note.url}>
                        <a
                          className="inline-flex items-center gap-2 text-primary-hover hover:underline"
                          href={note.url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          {note.title}
                          <ExternalLink aria-hidden className="size-3.5" />
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>

                <p className="text-xs leading-5 text-muted-foreground">
                  {t("universities.fit.disclaimer")}
                </p>
              </div>
            )}
          </Card>
        </aside>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button asChild variant="secondary">
          <Link href="/universities">{t("universities.actions.backToList")}</Link>
        </Button>
      </div>
      <p className="text-xs leading-5 text-muted-foreground">{t("universities.disclaimer")}</p>
    </div>
  );
}

function DetailItem({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 text-sm">{children}</dd>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  return (
    <span
      className={`rounded-sm border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${STATUS_STYLES[status]}`}
    >
      {t(`universities.requirements.statusLabel.${status}` as TranslationKey)}
    </span>
  );
}

function RequirementRow({
  label,
  universityValue,
  yourValue,
  status
}: {
  label: string;
  universityValue: string | number;
  yourValue: string | number;
  status: string;
}) {
  return (
    <tr className="border-t">
      <td className="py-2 font-semibold">{label}</td>
      <td className="py-2">{universityValue}</td>
      <td className="py-2">{yourValue}</td>
      <td className="py-2">
        <StatusBadge status={status} />
      </td>
    </tr>
  );
}

function ContactLink({ label, url }: { label: string; url: string }) {
  const { t } = useI18n();
  return (
    <li className="flex items-center justify-between gap-3 rounded-sm border bg-surface px-3 py-2">
      <span className="font-semibold">{label}</span>
      {url ? (
        <a
          className="inline-flex items-center gap-1.5 text-primary-hover hover:underline"
          href={url}
          rel="noreferrer"
          target="_blank"
        >
          {t("universities.detail.openLink")}
          <ExternalLink aria-hidden className="size-3.5" />
        </a>
      ) : (
        <span className="text-xs italic text-muted-foreground">{t("universities.notVerifiedYet")}</span>
      )}
    </li>
  );
}

function FitList({
  title,
  items,
  prefix,
  icon: Icon,
  iconClassName
}: {
  title: string;
  items: string[];
  prefix: string;
  emptyKey: null;
  icon: typeof CheckCircle2;
  iconClassName: string;
}) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
        {title}
      </h3>
      <ul className="mt-2 space-y-1.5 text-sm">
        {items.map((item) => (
          <FitListItemText
            icon={Icon}
            iconClassName={iconClassName}
            key={item}
            translationKey={`${prefix}.${item}` as TranslationKey}
          />
        ))}
      </ul>
    </div>
  );
}

function FitListItemText({
  translationKey,
  icon: Icon,
  iconClassName
}: {
  translationKey: TranslationKey;
  icon: typeof CheckCircle2;
  iconClassName: string;
}) {
  const { t } = useI18n();
  return (
    <li className="flex items-start gap-2">
      <Icon aria-hidden className={`mt-0.5 size-4 shrink-0 ${iconClassName}`} />
      <span>{t(translationKey)}</span>
    </li>
  );
}
