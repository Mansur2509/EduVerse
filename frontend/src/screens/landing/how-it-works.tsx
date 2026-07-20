"use client";

import type { LucideIcon } from "lucide-react";
import { CalendarDays, ClipboardCheck, Compass, FolderKanban, MapPinned, TrendingUp, UserCog } from "lucide-react";
import { m, useMotionValueEvent, useScroll, useTransform } from "motion/react";
import { useRef, useState } from "react";

import { useI18n, type TranslationKey } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";
import { Card } from "@/shared/ui/card";
import { usePrefersReducedMotion } from "@/shared/ui/use-reduced-motion";

const STEPS: Array<{ icon: LucideIcon; titleKey: TranslationKey; descriptionKey: TranslationKey; tone: string }> = [
  {
    icon: UserCog,
    titleKey: "landing.howItWorks.step1.title",
    descriptionKey: "landing.howItWorks.step1.description",
    tone: "primary"
  },
  {
    icon: Compass,
    titleKey: "landing.howItWorks.step2.title",
    descriptionKey: "landing.howItWorks.step2.description",
    tone: "info"
  },
  {
    icon: TrendingUp,
    titleKey: "landing.howItWorks.step3.title",
    descriptionKey: "landing.howItWorks.step3.description",
    tone: "recommendation"
  },
  {
    icon: ClipboardCheck,
    titleKey: "landing.howItWorks.step4.title",
    descriptionKey: "landing.howItWorks.step4.description",
    tone: "success"
  },
  {
    icon: CalendarDays,
    titleKey: "landing.howItWorks.step5.title",
    descriptionKey: "landing.howItWorks.step5.description",
    tone: "event"
  }
];

const TONE_CLASSES: Record<string, string> = {
  event: "border-event/35 bg-event/15 text-event",
  info: "border-info/35 bg-info/15 text-info",
  primary: "border-primary/35 bg-primary/15 text-primary",
  recommendation: "border-recommendation/35 bg-recommendation/15 text-recommendation",
  success: "border-success/35 bg-success/15 text-success"
};

export function HowItWorks() {
  const { t } = useI18n();
  const sectionRef = useRef<HTMLElement | null>(null);
  const prefersReducedMotion = usePrefersReducedMotion();
  const [activeIndex, setActiveIndex] = useState(0);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start 80%", "end 30%"]
  });
  const desktopX = useTransform(scrollYProgress, [0, 1], ["0%", "-22%"]);
  const pathScale = useTransform(scrollYProgress, [0, 1], [0.12, 1]);
  const progressRotate = useTransform(scrollYProgress, [0, 1], [-4, 4]);

  useMotionValueEvent(scrollYProgress, "change", (latest) => {
    if (prefersReducedMotion) return;
    setActiveIndex(Math.min(STEPS.length - 1, Math.max(0, Math.floor(latest * STEPS.length))));
  });

  return (
    <section
      className="relative overflow-hidden bg-surface py-16 sm:py-20 lg:py-24"
      id="how-it-works"
      ref={sectionRef}
      tabIndex={-1}
    >
      <div aria-hidden className="absolute inset-0 bg-[linear-gradient(120deg,hsl(var(--surface))_0_58%,hsl(var(--primary)/0.08)_58%_72%,transparent_72%)]" />
      <div aria-hidden className="absolute left-8 top-24 hidden h-[32rem] w-24 -rotate-12 bg-accent/20 lg:block" />
      <div className="relative mx-auto w-full max-w-[98rem] px-4 sm:px-6 lg:px-10">
        <div className="w-full">
          <div className="grid gap-6 lg:grid-cols-[0.82fr_1.18fr] lg:items-end">
            <div>
              <p className="text-eyebrow text-primary-hover">{t("landing.howItWorks.eyebrow")}</p>
              <h2 className="text-display-condensed-sm mt-4 max-w-3xl">{t("landing.howItWorks.title")}</h2>
            </div>
            <div className="flex items-center gap-3 border bg-card p-4 shadow-card">
              <MapPinned aria-hidden className="size-5 text-event" />
              <span className="text-sm font-semibold text-muted-foreground">{t("landing.howItWorks.pathNote")}</span>
            </div>
          </div>

          <div className="relative mt-10 overflow-hidden border-y border-border py-7 sm:mt-12 sm:py-8">
            <div aria-hidden className="absolute left-8 right-8 top-1/2 hidden h-px -translate-y-1/2 bg-border lg:block" />
            <m.div
              aria-hidden
              className="absolute left-8 top-1/2 hidden h-1 origin-left -translate-y-1/2 bg-gradient-to-r from-primary via-accent to-info lg:block"
              style={prefersReducedMotion ? undefined : { scaleX: pathScale }}
            />
            <m.div
              className="grid gap-5 md:grid-cols-2 lg:flex lg:w-[118rem]"
              style={prefersReducedMotion ? undefined : { x: desktopX }}
            >
              {STEPS.map((step, index) => {
                const Icon = step.icon;
                const active = activeIndex === index || prefersReducedMotion;
                return (
                  <Card
                    className={cn(
                      "relative min-h-72 overflow-hidden p-5 transition-[transform,box-shadow,border-color] lg:w-[24rem]",
                      active ? "border-primary/45 shadow-2xl shadow-primary/10" : "lg:scale-[0.94] lg:opacity-85"
                    )}
                    key={step.titleKey}
                  >
                    <div aria-hidden className="absolute -right-16 -top-16 size-40 rounded-full bg-primary/10 blur-2xl" />
                    <div className="relative flex h-full flex-col">
                      <div className="flex items-start justify-between gap-4">
                        <div className={cn("grid size-14 place-items-center border", TONE_CLASSES[step.tone])}>
                          <Icon aria-hidden className="size-7" />
                        </div>
                        <m.span
                          className="text-display-condensed-sm text-6xl leading-none text-border"
                          style={prefersReducedMotion ? undefined : { rotate: progressRotate }}
                        >
                          {String(index + 1).padStart(2, "0")}
                        </m.span>
                      </div>
                      <h3 className="mt-8 font-serif text-2xl font-semibold leading-tight">{t(step.titleKey)}</h3>
                      <p className="mt-4 text-sm leading-6 text-muted-foreground">{t(step.descriptionKey)}</p>
                      <div className="mt-auto pt-8">
                        <div className="grid grid-cols-[auto_1fr] items-center gap-3">
                          <span className={cn("grid size-10 place-items-center border", TONE_CLASSES[step.tone])}>
                            <FolderKanban aria-hidden className="size-5" />
                          </span>
                          <span className="h-2 bg-muted">
                            <span
                              className={cn(
                                "block h-2",
                                index <= activeIndex || prefersReducedMotion ? "w-full bg-primary" : "w-1/3 bg-border"
                              )}
                            />
                          </span>
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </m.div>
          </div>
        </div>
      </div>
    </section>
  );
}
