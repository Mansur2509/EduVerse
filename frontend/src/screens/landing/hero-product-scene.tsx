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
import { TiltCard } from "@/shared/ui/tilt-card";

import { UNIVERSITY_COUNT_DISPLAY } from "./site-stats";

// Stable semantic depth map: z-index and translateZ layers stay separated so entrance motion cannot cross cards.
const HERO_LAYERS = {
  atmosphere: "z-0",
  rearDocument: "z-10",
  dossier: "relative z-20",
  frontRail: "relative z-30",
  foregroundAccent: "relative z-40"
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

      <div className="relative z-20 grid gap-3 px-2 pt-6 sm:grid-cols-[8.5rem_minmax(0,1fr)_9.75rem] sm:gap-4 lg:grid-cols-[9.5rem_minmax(0,1fr)_10.5rem] xl:grid-cols-[10rem_minmax(0,1fr)_11rem]">
        <div className={`${HERO_LAYERS.frontRail} hidden flex-col gap-3 pt-24 sm:flex lg:pt-28`}>
          <div className="border border-white/20 bg-navy p-3 text-white shadow-2xl shadow-black/30 lg:p-4">
            <Globe2 aria-hidden className="size-6 text-info" />
            <p className="mt-4 text-xs font-semibold leading-5 lg:text-sm">{t("landing.hero.scenePlan")}</p>
          </div>
          <div className="border bg-card p-3 text-foreground shadow-2xl shadow-black/15 lg:p-4">
            <div className="flex items-center gap-2">
              <MapPinned aria-hidden className="size-5 text-event" />
              <FileText aria-hidden className="size-5 text-primary" />
            </div>
            <div className="mt-4 grid gap-2 text-[0.62rem] font-bold uppercase tracking-[0.1em] text-muted-foreground">
              <span className="border bg-surface px-2 py-1">{t("landing.hero.sceneMap")}</span>
              <span className="border bg-surface px-2 py-1">{t("landing.hero.sceneProof")}</span>
            </div>
          </div>
        </div>

        <TiltCard className={`${HERO_LAYERS.dossier} min-w-0`} maxTiltDeg={2}>
          <div className="landing-poster-object animate-[landing-poster-enter_700ms_cubic-bezier(0.16,1,0.3,1)_both]">
            <div className="landing-poster-paper relative min-h-[24rem] overflow-hidden border border-border bg-surface p-4 text-foreground sm:min-h-[31rem] sm:p-5 lg:min-h-[27rem] lg:p-6">
              <span
                aria-hidden
                className="absolute -right-5 top-5 text-display-condensed text-[6rem] leading-none text-primary/[0.08] sm:text-[8rem]"
              >
                UNI
              </span>
              <div className="relative z-10 flex items-center justify-between gap-4 border-b border-foreground/15 pb-4">
                <div>
                  <p className="text-eyebrow text-primary">{t("landing.hero.sceneCommand")}</p>
                  <h3 className="mt-2 max-w-sm font-serif text-xl font-semibold leading-tight sm:text-2xl lg:text-3xl">
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

        <div className={`${HERO_LAYERS.foregroundAccent} hidden flex-col gap-3 pt-10 sm:flex`}>
          <div className="border border-accent/35 bg-accent p-3 text-accent-foreground shadow-2xl shadow-accent/20 lg:p-4">
            <div className="flex items-center justify-between gap-2">
              <Ticket aria-hidden className="size-5" />
              <span className="border border-current/30 px-2 py-1 text-[0.58rem] font-bold uppercase tracking-[0.12em]">
                {t("landing.hero.sceneTicketStatus")}
              </span>
            </div>
            <p className="mt-4 text-xs font-bold leading-5 lg:text-sm">{t("landing.hero.sceneTicket")}</p>
          </div>
        </div>
      </div>

      <div className="relative z-30 mt-3 grid gap-3 px-2 sm:hidden">
        <div className="grid grid-cols-2 gap-3">
          <div className="border border-white/20 bg-navy p-3 text-white shadow-2xl shadow-black/30">
            <Globe2 aria-hidden className="size-6 text-info" />
            <p className="mt-4 text-xs font-semibold leading-5">{t("landing.hero.scenePlan")}</p>
          </div>
          <div className="border border-accent/35 bg-accent p-3 text-accent-foreground shadow-2xl shadow-accent/20">
            <Ticket aria-hidden className="size-5" />
            <p className="mt-4 text-xs font-bold leading-5">{t("landing.hero.sceneTicket")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
