"use client";

import { ExternalLink } from "lucide-react";

import type { UniversityFieldVerification, VerificationStatus } from "@/entities/university";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";

import { StatValue } from "./stat-value";

const BADGE_STYLES: Record<VerificationStatus, string> = {
  verified: "border-success/35 bg-success/10 text-success",
  partial: "border-warning/35 bg-warning/10 text-warning",
  estimated: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

export function VerificationBadge({ status }: { status: VerificationStatus }) {
  const { t } = useI18n();
  return (
    <span
      className={`rounded-sm border px-1.5 py-0.5 text-[0.62rem] font-semibold uppercase tracking-wide ${BADGE_STYLES[status]}`}
    >
      {t(`universities.verification.status.${status}` as TranslationKey)}
    </span>
  );
}

export function VerifiedStat({
  value,
  suffix,
  verification
}: {
  value: string | number | boolean | null;
  suffix?: string;
  verification?: UniversityFieldVerification;
}) {
  const { locale, t } = useI18n();
  const isMissing = value === null || value === undefined || value === "";

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <StatValue suffix={suffix} value={value} />
        {!isMissing && verification ? <VerificationBadge status={verification.status} /> : null}
      </div>
      {!isMissing && verification ? (
        <div className="mt-1 flex flex-wrap items-center gap-2 text-[0.65rem] text-muted-foreground">
          <span>
            {t("universities.verification.lastVerified", {
              date: formatDate(verification.last_verified_date, locale)
            })}
          </span>
          <a
            className="inline-flex items-center gap-1 underline hover:text-primary-hover"
            href={verification.source_url}
            rel="noreferrer"
            target="_blank"
          >
            {t("universities.verification.source")}
            <ExternalLink aria-hidden className="size-3" />
          </a>
        </div>
      ) : null}
    </div>
  );
}
