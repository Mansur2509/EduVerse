"use client";

import {
  CalendarClock,
  CheckCircle2,
  FileText,
  Globe2,
  GraduationCap,
  MapPinned,
  NotebookPen,
  Search,
  ShieldCheck,
  Ticket,
  WalletCards
} from "lucide-react";

import { useI18n } from "@/shared/i18n";
import { ParallaxLayer } from "@/shared/ui/parallax-layer";
import { TiltCard } from "@/shared/ui/tilt-card";

import { UNIVERSITY_COUNT_DISPLAY } from "./site-stats";

// Stable semantic depth map: z-index and translateZ layers stay separated so entrance motion cannot cross cards.
const HERO_LAYERS = {
  atmosphere: "z-0",
  rearDocument: "z-10",
  dossier: "z-20",
  frontFragment: "z-30",
  foregroundAccent: "z-40"
} as const;

export function HeroProductScene() {
  const { t } = useI18n();

  return (
    <div className="landing-hero-stage relative mx-auto min-h-[27rem] w-full max-w-[25rem] overflow-visible sm:min-h-[34rem] sm:max-w-[38rem] lg:min-h-[30rem] lg:max-w-[40rem] xl:min-h-[32rem] xl:max-w-[42rem]">
      <div
        aria-hidden
        className={`absolute -left-8 top-10 ${HERO_LAYERS.atmosphere} h-[78%] w-[62%] -rotate-6 bg-primary shadow-2xl shadow-black/30`}
      />
      <div
        aria-hidden
        className={`absolute bottom-10 right-0 ${HERO_LAYERS.atmosphere} h-[64%] w-[58%] rotate-6 bg-info/75 shadow-2xl shadow-black/20`}
      />
      <div
        aria-hidden
        className={`absolute left-8 top-20 ${HERO_LAYERS.rearDocument} h-[70%] w-[76%] border border-white/20`}
      />

      <TiltCard className={`absolute inset-x-5 top-7 ${HERO_LAYERS.dossier} sm:inset-x-10 lg:top-8`} maxTiltDeg={4}>
        <div className="landing-poster-object animate-[landing-poster-enter_700ms_cubic-bezier(0.16,1,0.3,1)_both]">
          <div className="landing-poster-paper relative min-h-[24rem] overflow-hidden border border-border bg-surface p-4 text-foreground sm:min-h-[31rem] sm:p-6 lg:min-h-[27rem]">
            <span
              aria-hidden
              className="absolute -right-5 top-5 text-display-condensed text-[6rem] leading-none text-primary/[0.08] sm:text-[8rem]"
            >
              UNI
            </span>
            <div className="relative z-10 flex items-center justify-between gap-4 border-b border-foreground/15 pb-4">
              <div>
                <p className="text-eyebrow text-primary">{t("landing.hero.sceneCommand")}</p>
                <h3 className="mt-2 max-w-sm font-serif text-xl font-semibold leading-tight sm:text-3xl lg:text-3xl">
                  {t("landing.hero.sceneNextMoveTitle")}
                </h3>
              </div>
              <div className="grid size-14 shrink-0 place-items-center border border-success/35 bg-success/15 text-success sm:size-16">
                <ShieldCheck aria-hidden className="size-7 sm:size-8" />
              </div>
            </div>

            <div className="relative z-10 mt-5 grid gap-3 sm:grid-cols-[1.08fr_0.92fr]">
              <div className="border border-primary/30 bg-primary/10 p-4">
                <div className="flex items-center justify-between">
                  <div className="grid size-12 place-items-center bg-primary text-primary-foreground">
                    <GraduationCap aria-hidden className="size-6" />
                  </div>
                  <p className="text-display-condensed-sm text-5xl leading-none text-primary">
                    {UNIVERSITY_COUNT_DISPLAY}+
                  </p>
                </div>
                <p className="mt-5 text-sm font-bold uppercase tracking-[0.12em] text-primary-hover">
                  {t("landing.hero.sceneUniversities")}
                </p>
              </div>

              <div className="border bg-card p-4 shadow-card">
                <div className="flex items-center gap-2">
                  <Search aria-hidden className="size-5 text-info" />
                  <p className="text-sm font-semibold">{t("landing.hero.sceneSearch")}</p>
                </div>
                <div className="mt-4 space-y-2 text-[0.66rem] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                  <span className="block border border-info/25 bg-info/10 px-2 py-1">{t("landing.hero.sceneShortlist")}</span>
                  <span className="block border border-accent/25 bg-accent/10 px-2 py-1">{t("landing.hero.sceneDeadline")}</span>
                </div>
              </div>
            </div>

            <div className="relative z-10 mt-3 grid gap-3 sm:grid-cols-3">
              <div className="border bg-card p-4">
                <NotebookPen aria-hidden className="size-6 text-recommendation" />
                <p className="mt-4 text-sm font-semibold">{t("landing.hero.sceneEssays")}</p>
              </div>
              <div className="border bg-card p-4">
                <CalendarClock aria-hidden className="size-6 text-accent" />
                <p className="mt-4 text-sm font-semibold">{t("landing.hero.sceneNotification")}</p>
              </div>
              <div className="border bg-card p-4">
                <WalletCards aria-hidden className="size-6 text-success" />
                <p className="mt-4 text-sm font-semibold">{t("landing.hero.sceneScholarship")}</p>
              </div>
            </div>

            <div className="relative z-10 mt-3 border border-success/30 bg-success/10 p-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 aria-hidden className="size-5 text-success" />
                <p className="text-sm font-semibold">{t("landing.hero.sceneVerified")}</p>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-[0.66rem] font-bold uppercase tracking-[0.12em] text-success">
                <span className="border border-success/25 bg-surface/70 px-2 py-1">{t("landing.hero.sceneSources")}</span>
                <span className="border border-success/25 bg-surface/70 px-2 py-1">{t("landing.hero.sceneFit")}</span>
              </div>
            </div>
          </div>
        </div>
      </TiltCard>

      <ParallaxLayer
        className={`absolute -left-1 top-20 ${HERO_LAYERS.frontFragment} w-36 -rotate-[13deg] sm:left-0 sm:top-24 sm:w-44 lg:w-44`}
        depth={0.38}
      >
        <div className="landing-hero-depth-front min-w-36 border border-white/20 bg-navy p-4 text-white shadow-2xl shadow-black/35 sm:min-w-44">
          <Globe2 aria-hidden className="size-7 text-info" />
          <p className="mt-5 text-sm font-semibold">{t("landing.hero.scenePlan")}</p>
        </div>
      </ParallaxLayer>

      <ParallaxLayer
        axis="y"
        className={`absolute right-0 top-2 ${HERO_LAYERS.foregroundAccent} w-44 rotate-[9deg] sm:right-3 sm:w-56`}
        depth={0.28}
      >
        <div className="landing-hero-depth-foreground min-w-44 border border-accent/35 bg-accent p-4 text-accent-foreground shadow-2xl shadow-accent/25 sm:min-w-56">
          <div className="flex items-center justify-between">
            <Ticket aria-hidden className="size-6" />
            <span className="border border-current/30 px-2 py-1 text-[0.62rem] font-bold uppercase tracking-[0.14em]">
              {t("landing.hero.sceneTicketStatus")}
            </span>
          </div>
          <p className="mt-5 text-sm font-bold leading-5">{t("landing.hero.sceneTicket")}</p>
        </div>
      </ParallaxLayer>

      <ParallaxLayer
        className={`absolute bottom-4 left-4 ${HERO_LAYERS.frontFragment} hidden w-56 -rotate-[8deg] border bg-card p-4 text-foreground shadow-2xl sm:block`}
        depth={0.5}
      >
        <div className="flex items-center gap-3">
          <MapPinned aria-hidden className="size-6 text-event" />
          <FileText aria-hidden className="size-6 text-primary" />
        </div>
        <div className="mt-5 grid gap-2 text-[0.65rem] font-bold uppercase tracking-[0.12em] text-muted-foreground">
          <span className="border bg-surface px-2 py-1">{t("landing.hero.sceneMap")}</span>
          <span className="w-fit border bg-surface px-2 py-1">{t("landing.hero.sceneProof")}</span>
        </div>
      </ParallaxLayer>
    </div>
  );
}
