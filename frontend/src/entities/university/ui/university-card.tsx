"use client";

import { Award, Building2, CalendarClock, GraduationCap, MapPin, Star, Trophy } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import {
  formatTuitionAmount,
  getFieldVerification,
  type UniversityDetails
} from "@/entities/university";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

import { StatValue } from "./stat-value";
import { VerificationBadge } from "./verified-stat";

// Real imagery only, sourced by the backend `fetch_university_cover_images`
// command from Wikipedia's REST API (Wikimedia Commons-hosted, exact-title
// matched -- see that command's docstring). cover_image_url is blank for any
// university not yet fetched or with no safe match, and the card must fall
// back to this designed header band rather than a broken image (see
// docs/UNIVERSITY_DATA_PROHIBITIONS.md). The band's hue is picked
// deterministically from the university's own name so the catalog reads as
// visually varied without implying any of these colors are official
// branding. A small fixed palette (not an arbitrary hash to a full hue
// wheel) keeps the result restrained rather than confetti-like.
const HEADER_BAND_CLASSES = [
  "from-navy to-navy/70",
  "from-primary/90 to-primary/60",
  "from-info to-info/70",
  "from-recommendation to-recommendation/70",
  "from-accent to-accent/70",
  "from-success to-success/70"
];

function headerBandClass(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  return HEADER_BAND_CLASSES[Math.abs(hash) % HEADER_BAND_CLASSES.length];
}

export function UniversityCard({
  university,
  isCompareSelected,
  canSelectCompare,
  onToggleCompare,
  onToggleShortlist,
  isShortlistPending
}: {
  university: UniversityDetails;
  isCompareSelected: boolean;
  canSelectCompare: boolean;
  onToggleCompare: (id: number) => void;
  onToggleShortlist: (university: UniversityDetails) => void;
  isShortlistPending?: boolean;
}) {
  const { locale, t } = useI18n();
  const [coverFailed, setCoverFailed] = useState(false);
  const showCover = Boolean(university.cover_image_url) && !coverFailed;

  return (
    <Card className="flex h-full min-w-0 flex-col overflow-hidden" interactive>
      <div
        className={`relative -mx-4 -mt-4 mb-3 flex h-14 shrink-0 items-center justify-between px-4 ${
          showCover ? "" : `bg-gradient-to-br ${headerBandClass(university.name)}`
        }`}
      >
        {showCover ? (
          <Image
            alt=""
            className="absolute inset-0 size-full object-cover"
            height={112}
            onError={() => setCoverFailed(true)}
            src={university.cover_image_url}
            unoptimized
            width={400}
          />
        ) : null}
        <GraduationCap
          aria-hidden
          className={`relative z-10 size-6 drop-shadow ${showCover ? "text-white" : "text-navy-foreground/90"}`}
          strokeWidth={1.5}
        />
        {university.global_rank ? (
          <span
            aria-label={t("universities.badges.globalRank", { rank: university.global_rank })}
            className={`relative z-10 flex items-center gap-1 rounded-sm px-2 py-1 text-xs font-semibold ${
              showCover ? "bg-black/40 text-white" : "bg-navy-foreground/15 text-navy-foreground"
            }`}
          >
            <Trophy aria-hidden className="size-3.5" />#{university.global_rank}
          </span>
        ) : null}
        {showCover && university.cover_image_source_title ? (
          <span
            className="absolute bottom-0.5 right-1.5 z-10 text-[0.6rem] font-medium text-white/80 drop-shadow"
            title={university.cover_image_source_url || undefined}
          >
            {university.cover_image_source_title}
          </span>
        ) : null}
      </div>
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
        {university.is_demo ? (
          <Badge tone="warning">{t("universities.demoDataBadge")}</Badge>
        ) : null}
        <Button
          aria-pressed={university.is_shortlisted}
          className="ml-auto shrink-0"
          disabled={isShortlistPending}
          onClick={() => onToggleShortlist(university)}
          size="sm"
          type="button"
          variant={university.is_shortlisted ? "secondary" : "ghost"}
        >
          <Star
            aria-hidden
            className="mr-1.5 size-4"
            fill={university.is_shortlisted ? "currentColor" : "none"}
          />
          {university.is_shortlisted
            ? t("universities.actions.shortlisted")
            : t("universities.actions.shortlist")}
        </Button>
      </div>

      <h2 className="mt-4 text-2xl font-semibold break-words">
        <Link className="hover:text-primary-hover" href={`/universities/${university.slug}`}>
          {university.name}
        </Link>
      </h2>
      <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
        <MapPin aria-hidden className="size-4 shrink-0" />
        <span className="truncate">
          {[university.city, university.country].filter(Boolean).join(", ")}
        </span>
      </p>

      {university.scholarship_available || university.application_deadline ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {university.scholarship_available ? (
            <Badge className="gap-1.5 normal-case tracking-normal" tone="scholarship">
              <Award aria-hidden className="size-3.5" />
              {t("universities.fields.scholarshipAvailable")}
            </Badge>
          ) : null}
          {university.application_deadline ? (
            <Badge className="gap-1.5 normal-case tracking-normal" tone="accent">
              <CalendarClock aria-hidden className="size-3.5" />
              {formatDate(university.application_deadline, locale)}
            </Badge>
          ) : null}
        </div>
      ) : null}

      <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-muted-foreground">
            {t("universities.fields.acceptanceRate")}
          </dt>
          <dd className="mt-0.5 flex flex-wrap items-center gap-1.5 font-semibold">
            <StatValue suffix="%" value={university.acceptance_rate} />
            {university.acceptance_rate !== null && university.acceptance_rate !== undefined ? (
              (() => {
                const verification = getFieldVerification(
                  university.field_verifications,
                  "acceptance_rate"
                );
                return verification ? <VerificationBadge status={verification.status} /> : null;
              })()
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">{t("universities.fields.tuition")}</dt>
          <dd className="mt-0.5 font-semibold">
            <span className="block">
              <StatValue
                suffix={
                  university.tuition_original_amount
                    ? ` ${university.tuition_original_currency || university.tuition_currency}`
                    : university.tuition_amount
                      ? ` ${university.tuition_currency}`
                      : ""
                }
                value={formatTuitionAmount(
                  university.tuition_original_amount ?? university.tuition_amount
                )}
              />
            </span>
            {university.tuition_usd_amount ? (
              <span className="block text-xs text-muted-foreground">
                {t("universities.cost.approxUsd", {
                  amount: formatTuitionAmount(university.tuition_usd_amount) ?? "-"
                })}
              </span>
            ) : null}
          </dd>
        </div>
      </dl>

      <label className="mt-5 flex items-center gap-2 text-xs text-muted-foreground">
        <input
          checked={isCompareSelected}
          className="size-4"
          disabled={!isCompareSelected && !canSelectCompare}
          onChange={() => onToggleCompare(university.id)}
          type="checkbox"
        />
        {t("universities.actions.addToCompare")}
      </label>

      <div className="mt-4 flex items-center gap-2">
        <Building2 aria-hidden className="size-4 shrink-0 text-muted-foreground" />
        <Link
          className="inline-flex min-h-9 flex-1 items-center justify-center rounded-sm border bg-surface px-4 text-sm font-semibold transition hover:bg-elevated"
          href={`/universities/${university.slug}`}
        >
          {t("universities.actions.viewDetails")}
        </Link>
      </div>
    </Card>
  );
}
