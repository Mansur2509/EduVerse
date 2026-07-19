"use client";

import { Award, GraduationCap, Languages, Wallet } from "lucide-react";

import { formatTuitionAmount, type StudyDestination } from "@/entities/university";
import { useI18n } from "@/shared/i18n";
import { Badge } from "@/shared/ui/badge";
import { Card } from "@/shared/ui/card";

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

function costRangeLabel(destination: StudyDestination): string | null {
  const min = formatTuitionAmount(destination.min_tuition_usd);
  const max = formatTuitionAmount(destination.max_tuition_usd);
  if (!min && !max) {
    return null;
  }
  if (min && max && min !== max) {
    return `$${min} - $${max}`;
  }
  return `$${min ?? max}`;
}

export function StudyDestinationCard({ destination }: { destination: StudyDestination }) {
  const { t } = useI18n();
  const costLabel = costRangeLabel(destination);
  const countryCode = destination.country_code?.toUpperCase();

  return (
    <Card className="flex h-full flex-col overflow-hidden" interactive>
      <div
        className={`relative -mx-4 -mt-4 mb-3 flex h-20 shrink-0 items-center justify-center overflow-hidden bg-gradient-to-br ${headerBandClass(destination.country)}`}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/15 via-transparent to-white/10"
        />
        {countryCode ? (
          <span
            aria-hidden
            className="relative z-10 grid h-10 min-w-14 place-items-center rounded-sm border border-navy-foreground/30 bg-navy-foreground/12 px-3 text-sm font-bold tracking-[0.18em] text-navy-foreground shadow-md"
          >
            {countryCode}
          </span>
        ) : (
          <GraduationCap
            aria-hidden
            className="relative z-10 size-8 text-navy-foreground/85"
            strokeWidth={1.5}
          />
        )}
      </div>

      <h3 className="text-xl font-semibold">{destination.country}</h3>

      <dl className="mt-4 space-y-2.5 text-sm">
        <div className="flex items-center gap-2.5">
          <span className="grid size-7 shrink-0 place-items-center rounded-sm border border-accent/30 bg-accent/10 text-accent">
            <GraduationCap aria-hidden className="size-3.5" strokeWidth={1.75} />
          </span>
          <dt className="sr-only">{t("universities.destinations.universityCount")}</dt>
          <dd>
            {t("universities.destinations.universityCountValue", {
              count: destination.university_count
            })}
          </dd>
        </div>
        {destination.primary_language ? (
          <div className="flex items-center gap-2.5">
            <span className="grid size-7 shrink-0 place-items-center rounded-sm border border-info/30 bg-info/10 text-info">
              <Languages aria-hidden className="size-3.5" strokeWidth={1.75} />
            </span>
            <dt className="sr-only">{t("universities.destinations.language")}</dt>
            <dd>{destination.primary_language}</dd>
          </div>
        ) : null}
        {costLabel ? (
          <div className="flex items-center gap-2.5">
            <span className="grid size-7 shrink-0 place-items-center rounded-sm border border-primary/30 bg-primary/10 text-primary-hover">
              <Wallet aria-hidden className="size-3.5" strokeWidth={1.75} />
            </span>
            <dt className="sr-only">{t("universities.destinations.costRange")}</dt>
            <dd>{costLabel}</dd>
          </div>
        ) : null}
      </dl>

      {destination.has_scholarships ? (
        <Badge className="mt-4 w-fit gap-1.5 normal-case tracking-normal" tone="scholarship">
          <Award aria-hidden className="size-3.5" />
          {t("universities.destinations.scholarshipsAvailable")}
        </Badge>
      ) : null}
    </Card>
  );
}
