"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  HelpCircle,
  ListChecks,
  Star
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  formatTuitionAmount,
  getFieldVerification,
  type UniversityDetails,
  type UniversityFitAnalysis
} from "@/entities/university";
import { StatValue } from "@/entities/university/ui/stat-value";
import { VerifiedStat } from "@/entities/university/ui/verified-stat";
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

export function UniversityDetailScreen({ slug }: { slug: string }) {
  const { locale, t } = useI18n();
  const [university, setUniversity] = useState<UniversityDetails | null>(null);
  const [fit, setFit] = useState<UniversityFitAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isFitLoading, setIsFitLoading] = useState(true);
  const [hasFitError, setHasFitError] = useState(false);
  const [isShortlistPending, setIsShortlistPending] = useState(false);

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
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          {university.admissions_url ? (
            <a
              className="inline-flex items-center gap-1.5 font-semibold text-primary-hover hover:underline"
              href={university.admissions_url}
              rel="noreferrer"
              target="_blank"
            >
              {t("universities.fields.admissionsUrl")}
              <ExternalLink aria-hidden className="size-3.5" />
            </a>
          ) : null}
          {university.financial_aid_url ? (
            <a
              className="inline-flex items-center gap-1.5 font-semibold text-primary-hover hover:underline"
              href={university.financial_aid_url}
              rel="noreferrer"
              target="_blank"
            >
              {t("universities.fields.financialAidUrl")}
              <ExternalLink aria-hidden className="size-3.5" />
            </a>
          ) : null}
          {university.application_portal_url ? (
            <a
              className="inline-flex items-center gap-1.5 font-semibold text-primary-hover hover:underline"
              href={university.application_portal_url}
              rel="noreferrer"
              target="_blank"
            >
              {t("universities.fields.applicationPortalUrl")}
              <ExternalLink aria-hidden className="size-3.5" />
            </a>
          ) : null}
        </div>
        <Button
          className="mt-5"
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
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-6">
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
              <DetailItem label={t("universities.fields.ieltsMinimum")}>
                <VerifiedStat
                  value={university.ielts_minimum}
                  verification={getFieldVerification(
                    university.field_verifications,
                    "ielts_minimum"
                  )}
                />
              </DetailItem>
              <DetailItem label={t("universities.fields.testPolicy")}>
                {university.test_policy ? (
                  <VerifiedStat
                    value={t(
                      `universities.testPolicy.${university.test_policy}` as TranslationKey
                    )}
                    verification={getFieldVerification(
                      university.field_verifications,
                      "test_policy"
                    )}
                  />
                ) : (
                  <StatValue value={null} />
                )}
              </DetailItem>
              <DetailItem label={t("universities.fields.tuition")}>
                <VerifiedStat
                  suffix={university.tuition_amount ? ` ${university.tuition_currency}` : ""}
                  value={formatTuitionAmount(university.tuition_amount)}
                  verification={getFieldVerification(
                    university.field_verifications,
                    "tuition_amount"
                  )}
                />
              </DetailItem>
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
              <DetailItem label={t("universities.fields.scholarshipAvailable")}>
                <VerifiedStat
                  value={university.scholarship_available}
                  verification={getFieldVerification(
                    university.field_verifications,
                    "scholarship_available"
                  )}
                />
              </DetailItem>
              <DetailItem label={t("universities.fields.qsRanking")}>
                {university.qs_ranking ? (
                  <VerifiedStat
                    value={
                      university.qs_ranking_year
                        ? `#${university.qs_ranking} (${university.qs_ranking_year})`
                        : `#${university.qs_ranking}`
                    }
                    verification={getFieldVerification(
                      university.field_verifications,
                      "qs_ranking"
                    )}
                  />
                ) : (
                  <StatValue value={null} />
                )}
              </DetailItem>
            </dl>
            {university.essay_requirements ? (
              <div className="mt-5 border-t pt-4">
                <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  {t("universities.fields.essayRequirements")}
                </h3>
                <VerifiedStat
                  value={university.essay_requirements}
                  verification={getFieldVerification(
                    university.field_verifications,
                    "essay_requirements"
                  )}
                />
              </div>
            ) : null}
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
