"use client";

import { Star } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { UniversityDetails } from "@/entities/university";
import { StatValue } from "@/entities/university/ui/stat-value";
import {
  addToShortlistRequest,
  compareUniversitiesRequest,
  removeFromShortlistRequest
} from "@/features/universities";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

type CompareRow = {
  labelKey: TranslationKey;
  render: (university: UniversityDetails) => React.ReactNode;
};

export function UniversityCompareScreen({ ids }: { ids: string }) {
  const { locale, t } = useI18n();
  const [universities, setUniversities] = useState<UniversityDetails[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [pendingId, setPendingId] = useState<number | null>(null);

  const parsedIds = useMemo(
    () =>
      ids
        .split(",")
        .map((value) => Number.parseInt(value.trim(), 10))
        .filter((value) => Number.isInteger(value)),
    [ids]
  );

  const loadComparison = useCallback(async () => {
    if (parsedIds.length < 2) {
      setHasError(true);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setHasError(false);
    try {
      setUniversities(await compareUniversitiesRequest(parsedIds));
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [parsedIds]);

  useEffect(() => {
    void loadComparison();
  }, [loadComparison]);

  async function toggleShortlist(university: UniversityDetails) {
    setPendingId(university.id);
    try {
      if (university.is_shortlisted) {
        await removeFromShortlistRequest(university.slug);
      } else {
        await addToShortlistRequest(university.slug);
      }
      setUniversities((current) =>
        current.map((item) =>
          item.id === university.id ? { ...item, is_shortlisted: !item.is_shortlisted } : item
        )
      );
    } catch {
      setHasError(true);
    } finally {
      setPendingId(null);
    }
  }

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">{t("universities.states.loading")}</p>
      </Card>
    );
  }

  if (hasError || universities.length < 2) {
    return (
      <Card>
        <p className="text-sm text-danger" role="alert">
          {t("universities.compare.error")}
        </p>
        <Button asChild className="mt-4">
          <Link href="/universities">{t("universities.actions.backToList")}</Link>
        </Button>
      </Card>
    );
  }

  const rows: CompareRow[] = [
    {
      labelKey: "universities.fields.institutionType",
      render: (university) =>
        university.institution_type ? (
          t(`universities.institutionType.${university.institution_type}` as TranslationKey)
        ) : (
          <StatValue value={null} />
        )
    },
    {
      labelKey: "universities.fields.acceptanceRate",
      render: (university) => <StatValue suffix="%" value={university.acceptance_rate} />
    },
    {
      labelKey: "universities.fields.gpaAverage",
      render: (university) => <StatValue value={university.gpa_average} />
    },
    {
      labelKey: "universities.fields.satAverage",
      render: (university) => <StatValue value={university.sat_average} />
    },
    {
      labelKey: "universities.fields.tuition",
      render: (university) => (
        <StatValue
          suffix={university.tuition_amount ? ` ${university.tuition_currency}` : ""}
          value={university.tuition_amount}
        />
      )
    },
    {
      labelKey: "universities.fields.applicationDeadline",
      render: (university) =>
        university.application_deadline ? (
          formatDate(university.application_deadline, locale)
        ) : (
          <StatValue value={null} />
        )
    },
    {
      labelKey: "universities.fields.scholarshipAvailable",
      render: (university) => <StatValue value={university.scholarship_available} />
    }
  ];

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <h1 className="text-3xl font-semibold sm:text-5xl">{t("universities.compare.title")}</h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
          {t("universities.compare.description")}
        </p>
      </section>

      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="border-b bg-elevated/55">
              <th className="p-4 text-left text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                {t("universities.compare.field")}
              </th>
              {universities.map((university) => (
                <th className="min-w-[180px] p-4 text-left" key={university.id}>
                  <Link
                    className="font-semibold hover:text-primary-hover"
                    href={`/universities/${university.slug}`}
                  >
                    {university.name}
                  </Link>
                  <p className="mt-1 text-xs font-normal text-muted-foreground">
                    {[university.city, university.country].filter(Boolean).join(", ")}
                  </p>
                  <Button
                    className="mt-3"
                    disabled={pendingId === university.id}
                    onClick={() => void toggleShortlist(university)}
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
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className="border-b last:border-0" key={row.labelKey}>
                <th className="p-4 text-left text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                  {t(row.labelKey)}
                </th>
                {universities.map((university) => (
                  <td className="p-4" key={university.id}>
                    {row.render(university)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Button asChild variant="secondary">
        <Link href="/universities">{t("universities.actions.backToList")}</Link>
      </Button>
      <p className="text-xs leading-5 text-muted-foreground">{t("universities.disclaimer")}</p>
    </div>
  );
}
