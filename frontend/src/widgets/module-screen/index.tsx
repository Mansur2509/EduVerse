"use client";

import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  CircleDashed,
  Compass,
  Flag,
  ShieldCheck
} from "lucide-react";

import { useI18n } from "@/shared/i18n";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { Reveal } from "@/shared/ui/reveal";

import { betaModules, type BetaModuleId } from "./beta-modules";

export type ModuleScreenProps = {
  eyebrow: string;
  title: string;
  description: string;
  status?: string;
  primaryAction: string;
  secondaryAction?: string;
  secondaryHref?: string;
  highlights: Array<{
    title: string;
    detail: string;
  }>;
  disclaimer?: string;
};

export function ModuleScreen({
  eyebrow,
  title,
  description,
  status,
  primaryAction,
  secondaryAction,
  secondaryHref = "/dashboard",
  highlights,
  disclaimer
}: ModuleScreenProps) {
  const { t } = useI18n();

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-sm border bg-card shadow-card">
        <div className="grid lg:grid-cols-[1.4fr_0.6fr]">
          <div className="p-6 sm:p-9">
            <Badge>{status ?? t("module.preview")}</Badge>
            <p className="mt-5 text-eyebrow text-primary-hover">
              {eyebrow}
            </p>
            <h1 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl">
              {title}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
              {description}
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Button type="button">{primaryAction}</Button>
              {secondaryAction ? (
                <Button asChild variant="secondary">
                  <Link href={secondaryHref}>
                    {secondaryAction}
                    <ArrowRight aria-hidden className="ml-2 size-4" />
                  </Link>
                </Button>
              ) : null}
            </div>
          </div>
          <div className="border-t bg-surface p-6 lg:border-l lg:border-t-0 lg:p-8">
            <div className="rounded-sm border bg-elevated/70 p-5">
              <ShieldCheck aria-hidden className="size-7 text-accent" />
              <h2 className="mt-4 text-xl font-semibold">{t("module.clearDecisions")}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {t("module.clearDecisionsDetail")}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="foundation-heading">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-hover">
              {t("module.foundation")}
            </p>
            <h2 className="mt-1 text-2xl font-semibold" id="foundation-heading">
              {t("module.organizes")}
            </h2>
          </div>
          <span className="hidden text-sm text-muted-foreground sm:block">
            {t("module.phaseImplementation")}
          </span>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {highlights.map((highlight, index) => {
            const icons = [CheckCircle2, CalendarClock, BookOpen];
            const Icon = icons[index % icons.length];

            return (
              <Card key={highlight.title}>
                <Icon aria-hidden className="size-5 text-accent" />
                <h3 className="mt-4 text-lg font-semibold">{highlight.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{highlight.detail}</p>
              </Card>
            );
          })}
        </div>
      </section>

      <Card className="flex items-start gap-4 bg-muted/45">
        <CircleDashed aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
        <div>
          <h2 className="font-sans text-sm font-semibold">{t("module.foundationStatus")}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {t("module.placeholder")}
          </p>
          {disclaimer ? <p className="mt-3 text-xs leading-5 text-muted-foreground">{disclaimer}</p> : null}
        </div>
      </Card>
    </div>
  );
}

export function BetaModuleScreen({ module }: { module: BetaModuleId }) {
  const { t } = useI18n();
  const config = betaModules[module];
  const ModuleIcon = config.icon;

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-sm border bg-card shadow-card">
        <div className="grid lg:grid-cols-[1.35fr_0.65fr]">
          <div className="p-6 sm:p-9">
            <div className="flex items-center gap-3">
              <span className="grid size-11 shrink-0 place-items-center rounded-sm border border-recommendation/30 bg-recommendation/10 text-recommendation">
                <ModuleIcon aria-hidden className="size-5" />
              </span>
              <Badge>{t(config.statusKey)}</Badge>
            </div>
            <p className="mt-5 text-eyebrow text-primary-hover">
              {t(config.eyebrowKey)}
            </p>
            <h1 className="text-display mt-2 max-w-3xl">
              {t(config.titleKey)}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
              {t(config.descriptionKey)}
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Button asChild>
                <Link href={config.primaryHref}>
                  {t(config.primaryActionKey)}
                  <ArrowRight aria-hidden className="ml-2 size-4" />
                </Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href={config.secondaryHref}>
                  {t(config.secondaryActionKey)}
                </Link>
              </Button>
            </div>
          </div>
          <div className="grid place-items-center border-t bg-surface p-8 lg:border-l lg:border-t-0">
            <div className="w-full max-w-xs rounded-sm border bg-elevated/70 p-6">
              <span className="grid size-11 shrink-0 place-items-center rounded-sm border border-recommendation/30 bg-recommendation/10 text-recommendation">
                <ModuleIcon aria-hidden className="size-5" />
              </span>
              <p className="mt-6 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">
                {t("beta.nextPlanned")}
              </p>
              <p className="mt-2 text-lg font-semibold">{t(config.nextFeatureKey)}</p>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby={`${module}-features`}>
        <div className="mb-4">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-hover">
            {t("beta.modulePreview")}
          </p>
          <h2 className="mt-1 text-2xl font-semibold" id={`${module}-features`}>
            {t("beta.whatItWillDo")}
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {config.features.map((feature, index) => {
            const Icon = index % 2 === 0 ? CheckCircle2 : Compass;
            return (
              <Reveal delayMs={index * 60} key={feature.titleKey}>
                <Card className="hover:border-recommendation/45" interactive>
                  <span className="grid size-9 shrink-0 place-items-center rounded-sm border border-recommendation/30 bg-recommendation/10 text-recommendation">
                    <Icon aria-hidden className="size-4" />
                  </span>
                  <h3 className="mt-4 text-lg font-semibold">{t(feature.titleKey)}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {t(feature.detailKey)}
                  </p>
                </Card>
              </Reveal>
            );
          })}
        </div>
      </section>

      <Card className="flex items-start gap-4 border-warning/30 bg-warning/10">
        <CircleDashed aria-hidden className="mt-0.5 size-5 shrink-0 text-warning" />
        <div>
          <h2 className="text-sm font-semibold">{t("beta.previewStatus")}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {t("beta.previewStatusDetail")}
          </p>
          {config.disclaimerKey ? (
            <p className="mt-3 flex items-start gap-2 text-xs leading-5 text-muted-foreground">
              <Flag aria-hidden className="mt-0.5 size-4 shrink-0 text-warning" />
              {t(config.disclaimerKey)}
            </p>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
