"use client";

import { Check, ShieldCheck } from "lucide-react";

import type { SubscriptionPlan } from "@/entities/subscription";
import { useAuth } from "@/features/auth";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Badge } from "@/shared/ui/badge";
import { Card } from "@/shared/ui/card";

const plans: Array<{
  id: SubscriptionPlan;
  priceKey: TranslationKey;
  summaryKey: TranslationKey;
  statusKey: TranslationKey;
  featured?: boolean;
}> = [
  {
    id: "free",
    priceKey: "pricingPage.plan.free.price",
    summaryKey: "pricingPage.plan.free.summary",
    statusKey: "pricingPage.status.freeBeta"
  },
  {
    id: "starter",
    priceKey: "pricingPage.plan.starter.price",
    summaryKey: "pricingPage.plan.starter.summary",
    statusKey: "pricingPage.status.upcoming"
  },
  {
    id: "growth",
    priceKey: "pricingPage.plan.growth.price",
    summaryKey: "pricingPage.plan.growth.summary",
    statusKey: "pricingPage.status.comingSoon",
    featured: true
  },
  {
    id: "premium",
    priceKey: "pricingPage.plan.premium.price",
    summaryKey: "pricingPage.plan.premium.summary",
    statusKey: "pricingPage.status.notActive"
  }
];

const coreFeatures: TranslationKey[] = [
  "pricingPage.feature.eventMap",
  "pricingPage.feature.universities",
  "pricingPage.feature.roadmap",
  "pricingPage.feature.exams",
  "pricingPage.feature.finance",
  "pricingPage.feature.ai",
  "pricingPage.feature.essays"
];

export function PricingScreen() {
  const { user } = useAuth();
  const { t } = useI18n();

  return (
    <div className="space-y-7">
      <section className="grid gap-6 rounded-sm border bg-card p-6 shadow-card sm:p-9 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <Badge>{t("pricingPage.previewBadge")}</Badge>
          <p className="mt-5 text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
            {t("pricingPage.eyebrow")}
          </p>
          <h1 className="mt-2 max-w-4xl text-3xl font-semibold sm:text-5xl">
            {t("pricingPage.title")}
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
            {t("pricingPage.description")}
          </p>
          <div className="mt-5 grid gap-2 text-sm font-semibold text-muted-foreground sm:grid-cols-3">
            <p className="rounded-sm border bg-elevated px-3 py-2">
              {t("pricingPage.betaAccess")}
            </p>
            <p className="rounded-sm border bg-elevated px-3 py-2">
              {t("pricingPage.paidInactive")}
            </p>
            <p className="rounded-sm border bg-elevated px-3 py-2">
              {t("pricingPage.limitsMayChange")}
            </p>
          </div>
        </div>
        <div className="border-l-4 border-primary bg-elevated px-5 py-4">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
            {t("pricingPage.currentPlan")}
          </p>
          <p className="mt-1 font-serif text-2xl font-semibold">
            {t(`plans.${user?.subscription.tier ?? "free"}` as TranslationKey)}
          </p>
        </div>
      </section>

      <section
        aria-label={t("pricingPage.planComparison")}
        className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"
      >
        {plans.map((plan) => {
          const isCurrent = user?.subscription.tier === plan.id;
          return (
            <Card
              className={
                plan.featured
                  ? "relative flex flex-col border-primary/55 border-t-4"
                  : "relative flex flex-col border-t-4 border-t-navy"
              }
              key={plan.id}
            >
              <div className="flex min-h-7 items-start justify-between gap-3">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">
                  {t(`plans.${plan.id}` as TranslationKey)}
                </p>
                <Badge>{isCurrent ? t("pricingPage.active") : t(plan.statusKey)}</Badge>
              </div>
              <p className="mt-4 font-serif text-4xl font-semibold">{t(plan.priceKey)}</p>
              {plan.id === "free" ? (
                <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  {t("pricingPage.betaFree")}
                </p>
              ) : (
                <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  {t("pricingPage.notActiveDuringBeta")}
                </p>
              )}
              <p className="mt-5 min-h-24 text-sm leading-6 text-muted-foreground">
                {t(plan.summaryKey)}
              </p>
              {plan.id === "free" ? (
                <ul className="mt-5 space-y-3 border-t pt-5">
                  {coreFeatures.map((feature) => (
                    <li className="flex items-start gap-2 text-sm" key={feature}>
                      <Check aria-hidden className="mt-0.5 size-4 shrink-0 text-success" />
                      <span>{t(feature)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-auto border-t pt-5 text-sm font-semibold text-muted-foreground">
                  {t("pricingPage.plansComingSoon")}
                </p>
              )}
            </Card>
          );
        })}
      </section>

      <Card className="flex items-start gap-4 bg-muted/45">
        <ShieldCheck aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
        <div>
          <h2 className="text-sm font-semibold">{t("pricingPage.transparentTitle")}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {t("pricingPage.disclaimer")}
          </p>
        </div>
      </Card>
    </div>
  );
}
