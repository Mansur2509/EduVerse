"use client";

import { AlertCircle } from "lucide-react";
import Link from "next/link";

import type { ProfileRecommendation, RecommendationPriority } from "@/entities/profile";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const PRIORITY_TONE: Record<RecommendationPriority, string> = {
  urgent: "border-danger/35 bg-danger/10 text-danger",
  high: "border-warning/35 bg-warning/10 text-warning",
  medium: "border-accent/35 bg-accent/10 text-accent",
  low: "border-muted-foreground/30 bg-surface text-muted-foreground"
};

export function GapRecommendationsPanel({
  recommendations,
  needsAssessment,
  isLoading = false,
  loadError = false,
  limit = 4
}: {
  recommendations: ProfileRecommendation[];
  needsAssessment: boolean;
  isLoading?: boolean;
  loadError?: boolean;
  limit?: number;
}) {
  const { t } = useI18n();
  const visible = recommendations.slice(0, limit);

  return (
    <Card className="p-4">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
        {t("profileRecommendations.title")}
      </p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        {t("profileRecommendations.description")}
      </p>

      {loadError ? (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-warning" role="alert">
          <AlertCircle aria-hidden className="size-3.5 shrink-0" />
          {t("profileRecommendations.loadError")}
        </p>
      ) : isLoading ? (
        <p className="mt-3 text-xs text-muted-foreground">{t("profileRecommendations.loading")}</p>
      ) : needsAssessment ? (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-muted-foreground">{t("profileRecommendations.needsAssessment")}</p>
          <Button asChild size="sm" variant="ghost">
            <Link href="/profile">{t("profileRecommendations.goToProfile")}</Link>
          </Button>
        </div>
      ) : visible.length === 0 ? (
        <p className="mt-3 text-xs text-muted-foreground">{t("profileRecommendations.empty")}</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {visible.map((item) => (
            <li className="rounded-sm border bg-surface p-2.5 text-xs" key={item.title}>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-sm border px-1.5 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide ${PRIORITY_TONE[item.priority]}`}
                >
                  {t(`profileRecommendations.priority.${item.priority}` as TranslationKey)}
                </span>
                <span className="font-semibold text-foreground">
                  {t(`profileRecommendations.item.${item.title}` as TranslationKey)}
                </span>
              </div>
              <p className="mt-1 font-medium text-primary-hover">
                {t(`profileRecommendations.action.${item.next_action}` as TranslationKey)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
