"use client";

import { Building2, MapPin, Star } from "lucide-react";
import Link from "next/link";

import type { UniversityDetails } from "@/entities/university";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

import { StatValue } from "./stat-value";

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
  const { t } = useI18n();

  return (
    <Card className="flex h-full flex-col transition hover:border-primary/45">
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
        <Button
          aria-pressed={university.is_shortlisted}
          className="ml-auto"
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

      <h2 className="mt-4 text-2xl font-semibold">
        <Link className="hover:text-primary-hover" href={`/universities/${university.slug}`}>
          {university.name}
        </Link>
      </h2>
      <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
        <MapPin aria-hidden className="size-4 shrink-0" />
        {[university.city, university.country].filter(Boolean).join(", ")}
      </p>

      <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-muted-foreground">
            {t("universities.fields.acceptanceRate")}
          </dt>
          <dd className="mt-0.5 font-semibold">
            <StatValue suffix="%" value={university.acceptance_rate} />
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">{t("universities.fields.tuition")}</dt>
          <dd className="mt-0.5 font-semibold">
            <StatValue
              suffix={university.tuition_amount ? ` ${university.tuition_currency}` : ""}
              value={university.tuition_amount}
            />
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
