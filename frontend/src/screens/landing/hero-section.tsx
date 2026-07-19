"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";

import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { CountUp } from "@/shared/ui/count-up";
import { MotionReveal } from "@/shared/ui/motion-reveal";

import { HeroProductScene } from "./hero-product-scene";
import { UNIVERSITY_COUNT_DISPLAY } from "./site-stats";

export function HeroSection() {
  const { t } = useI18n();

  return (
    <section className="relative isolate min-h-[calc(100svh-4.5rem)] overflow-hidden bg-navy text-navy-foreground lg:h-[calc(100svh-4.5rem)] lg:min-h-[40rem]">
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-[linear-gradient(100deg,hsl(var(--navy))_0_54%,hsl(var(--primary-hover))_54%_71%,hsl(var(--info))_71%_100%)] opacity-95"
      />
      <div
        aria-hidden
        className="absolute inset-y-0 left-[7vw] -z-10 w-28 -skew-x-12 bg-accent/70"
      />
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 -z-10 h-44 bg-gradient-to-b from-transparent to-background"
      />
      <div aria-hidden className="absolute right-[6vw] top-[16vh] z-10 hidden text-accent/80 lg:block">
        <span className="absolute block size-10 rotate-45 border border-current" />
        <span className="absolute left-12 top-16 block size-5 rotate-45 bg-current" />
        <span className="absolute -left-10 top-28 block size-3 rotate-45 border border-current" />
      </div>

      <div className="mx-auto grid h-full w-full max-w-[98rem] gap-8 px-4 py-10 sm:px-6 sm:py-14 lg:grid-cols-[0.84fr_1.16fr] lg:items-center lg:gap-5 lg:px-10 lg:py-5 xl:py-6">
        <MotionReveal>
          <p className="text-eyebrow inline-flex border border-accent/45 bg-accent/15 px-3 py-2 text-accent">
            {t("landing.hero.eyebrow")}
          </p>
          <h1 className="text-landing-hero mt-4 max-w-4xl text-navy-foreground">
            <span className="block">{t("landing.hero.titleLead")}</span>
            <span className="block text-accent">{t("landing.hero.titleAccent")}</span>
            <span className="block">{t("landing.hero.titleTail")}</span>
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-white/[0.82] sm:text-lg lg:text-lg lg:leading-7">
            {t("landing.hero.subtitle")}
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button asChild className="min-h-14 px-7 text-base shadow-2xl shadow-black/25">
              <Link href="/register">
                {t("landing.hero.primaryCta")}
                <ArrowRight aria-hidden className="ml-2 size-4" />
              </Link>
            </Button>
            <Button asChild className="min-h-14 border-white/30 bg-white/[0.1] px-7 text-base text-navy-foreground hover:bg-white/[0.16]" variant="secondary">
              <Link href="/login">{t("landing.hero.secondaryCta")}</Link>
            </Button>
          </div>
          <div className="mt-5 grid max-w-3xl gap-3 text-sm font-semibold text-white/[0.82] sm:grid-cols-[auto_auto] sm:items-center">
            <div className="flex items-center gap-3 border border-white/15 bg-white/[0.08] px-4 py-3">
              <Sparkles aria-hidden className="size-5 text-accent" />
              <CountUp className="text-display-condensed-sm text-3xl leading-none text-white" suffix="+" target={UNIVERSITY_COUNT_DISPLAY} />
              <span>{t("landing.trust.universitiesSuffix")}</span>
            </div>
            <span className="border border-white/15 bg-white/[0.08] px-4 py-3">{t("landing.hero.dataNote")}</span>
          </div>
        </MotionReveal>

        <MotionReveal delayMs={120}>
          <HeroProductScene />
        </MotionReveal>
      </div>
    </section>
  );
}
