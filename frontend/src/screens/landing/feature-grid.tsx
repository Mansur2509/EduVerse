"use client";

import {
  BookOpenCheck,
  CalendarRange,
  CheckCircle2,
  ClipboardList,
  Compass,
  FileSearch,
  FolderKanban,
  GraduationCap,
  MapPinned,
  Search,
  Sparkles,
  Ticket,
  UsersRound
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { m, useScroll, useTransform } from "motion/react";
import { useRef } from "react";

import { useI18n, type TranslationKey } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";
import { Card } from "@/shared/ui/card";
import { MotionReveal } from "@/shared/ui/motion-reveal";
import { usePrefersReducedMotion } from "@/shared/ui/use-reduced-motion";

type FeatureTone = "success" | "recommendation" | "info" | "accent" | "event" | "primary";
type FeatureVisual =
  | "search"
  | "recommendation"
  | "profile"
  | "major"
  | "essay"
  | "applications"
  | "event"
  | "exams"
  | "organizer";

const TONE_CLASSES: Record<FeatureTone, string> = {
  success: "border-success/40 bg-success/15 text-success",
  recommendation: "border-recommendation/40 bg-recommendation/15 text-recommendation",
  info: "border-info/40 bg-info/15 text-info",
  accent: "border-accent/45 bg-accent/20 text-accent",
  event: "border-event/45 bg-event/15 text-event",
  primary: "border-primary/45 bg-primary/15 text-primary"
};

const SURFACE_CLASSES: Record<FeatureTone, string> = {
  success: "from-success/20 via-surface to-card",
  recommendation: "from-recommendation/20 via-surface to-card",
  info: "from-info/20 via-surface to-card",
  accent: "from-accent/20 via-surface to-card",
  event: "from-event/20 via-surface to-card",
  primary: "from-primary/20 via-surface to-card"
};

const FEATURES: Array<{
  icon: LucideIcon;
  tone: FeatureTone;
  visual: FeatureVisual;
  titleKey: TranslationKey;
  descriptionKey: TranslationKey;
  className: string;
  scale?: "large" | "tall" | "wide" | "compact";
}> = [
  {
    icon: GraduationCap,
    tone: "success",
    visual: "search",
    titleKey: "landing.features.universityDatabase.title",
    descriptionKey: "landing.features.universityDatabase.description",
    className: "lg:col-span-2 lg:row-span-2",
    scale: "large"
  },
  {
    icon: Sparkles,
    tone: "recommendation",
    visual: "recommendation",
    titleKey: "landing.features.recommendations.title",
    descriptionKey: "landing.features.recommendations.description",
    className: "lg:row-span-2",
    scale: "tall"
  },
  {
    icon: Compass,
    tone: "accent",
    visual: "major",
    titleKey: "landing.features.majorDiscovery.title",
    descriptionKey: "landing.features.majorDiscovery.description",
    className: "",
    scale: "compact"
  },
  {
    icon: FolderKanban,
    tone: "primary",
    visual: "applications",
    titleKey: "landing.features.applicationTracker.title",
    descriptionKey: "landing.features.applicationTracker.description",
    className: "lg:col-span-2",
    scale: "wide"
  },
  {
    icon: ClipboardList,
    tone: "info",
    visual: "profile",
    titleKey: "landing.features.profileBuilding.title",
    descriptionKey: "landing.features.profileBuilding.description",
    className: "",
    scale: "compact"
  },
  {
    icon: FileSearch,
    tone: "recommendation",
    visual: "essay",
    titleKey: "landing.features.essayChecker.title",
    descriptionKey: "landing.features.essayChecker.description",
    className: "",
    scale: "compact"
  },
  {
    icon: UsersRound,
    tone: "event",
    visual: "organizer",
    titleKey: "landing.features.organizerTools.title",
    descriptionKey: "landing.features.organizerTools.description",
    className: "lg:col-span-2",
    scale: "wide"
  },
  {
    icon: MapPinned,
    tone: "event",
    visual: "event",
    titleKey: "landing.features.eventMap.title",
    descriptionKey: "landing.features.eventMap.description",
    className: "",
    scale: "compact"
  },
  {
    icon: CalendarRange,
    tone: "success",
    visual: "exams",
    titleKey: "landing.features.examTools.title",
    descriptionKey: "landing.features.examTools.description",
    className: "",
    scale: "compact"
  }
];

function FeatureIcon({ icon: Icon, tone }: { icon: LucideIcon; tone: FeatureTone }) {
  return (
    <div className={cn("landing-feature-icon grid size-16 place-items-center border", TONE_CLASSES[tone])}>
      <Icon aria-hidden className="relative z-10 size-8" />
    </div>
  );
}

function SearchVisual({ large }: { large: boolean }) {
  const { t } = useI18n();

  return (
    <div className="relative mt-7 min-h-64 overflow-hidden border bg-navy p-4 text-white">
      <div className="absolute inset-0 bg-[linear-gradient(135deg,hsl(var(--info)/0.28),transparent_42%),linear-gradient(35deg,hsl(var(--primary)/0.22),transparent_55%)]" />
      <div className="relative z-10 max-w-md border border-white/20 bg-white/[0.08] p-3 backdrop-blur">
        <div className="flex items-center gap-3 bg-white p-3 text-foreground">
          <Search aria-hidden className="size-5 text-info" />
          <span className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            {t("landing.features.visual.searchQuery")}
          </span>
          <span className="ml-auto border border-primary/25 bg-primary/10 px-2 py-1 text-xs font-bold text-primary">
            {t("landing.features.visual.sourceTag")}
          </span>
        </div>
      </div>
      <div className="relative z-10 mt-5 grid gap-3 sm:grid-cols-3">
        {["MIT", "NUS", "Bocconi"].map((label, index) => (
          <div
            className={cn(
              "min-h-28 border border-white/20 bg-white/[0.1] p-4 shadow-2xl backdrop-blur",
              index === 1 && large ? "sm:mt-7" : ""
            )}
            key={label}
          >
            <p className="text-display-condensed-sm text-4xl leading-none text-accent">{label}</p>
            <div className="mt-5 flex flex-wrap gap-2 text-[0.62rem] font-bold uppercase tracking-[0.12em] text-white/75">
              <span className="border border-white/20 bg-white/10 px-2 py-1">{t("landing.features.visual.cost")}</span>
              <span className="border border-white/20 bg-white/10 px-2 py-1">{t("landing.features.visual.deadline")}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecommendationVisual() {
  const { t } = useI18n();

  return (
    <div className="mt-7 min-h-72 border bg-navy p-4 text-white">
      <div className="border border-white/15 bg-white/[0.08] p-4">
        <div className="flex items-center justify-between">
          <Sparkles aria-hidden className="size-7 text-recommendation" />
          <span className="border border-success/35 bg-success/15 px-3 py-1 text-xs font-bold text-success">
            {t("universities.fit.scoreLabel")}
          </span>
        </div>
        <div className="mt-6 space-y-4">
          {[
            "landing.hero.sceneProfile",
            "landing.features.majorDiscovery.title",
            "landing.globe.statVerified"
          ].map((labelKey, index) => (
            <div key={labelKey}>
              <div className="flex items-center justify-between text-xs font-semibold text-white/70">
                <span>{t(labelKey as TranslationKey)}</span>
                <span aria-hidden>{index === 0 ? "78" : index === 1 ? "84" : t("landing.features.visual.verified")}</span>
              </div>
              <span className="mt-2 block h-3 bg-white/15">
                <span
                  className={cn(
                    "block h-3",
                    index === 0 ? "w-[78%] bg-recommendation" : index === 1 ? "w-[84%] bg-info" : "w-[66%] bg-success"
                  )}
                />
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ApplicationVisual() {
  const { t } = useI18n();

  return (
    <div className="mt-7 grid gap-4 sm:grid-cols-[0.82fr_1.18fr]">
      <div className="border bg-primary p-5 text-primary-foreground shadow-2xl shadow-primary/25">
        <FolderKanban aria-hidden className="size-9" />
        <p className="mt-8 text-display-condensed-sm text-5xl leading-none">{t("landing.hero.sceneNextMove")}</p>
        <p className="mt-4 text-xs font-bold uppercase tracking-[0.12em] text-white/70">
          {t("landing.features.visual.pipeline")}
        </p>
      </div>
      <div className="grid gap-3">
        {[
          "applications.status.researching",
          "applications.status.preparing",
          "applications.status.submitted"
        ].map((labelKey, index) => (
          <div className="flex items-center gap-3 border bg-card p-4" key={labelKey}>
            <span className={cn("grid size-10 place-items-center border", index === 2 ? "bg-success/15 text-success" : "bg-accent/15 text-accent")}>
              <CheckCircle2 aria-hidden className="size-5" />
            </span>
            <span className="text-sm font-semibold">{t(labelKey as TranslationKey)}</span>
            <span className="ml-auto border bg-surface px-2 py-1 text-[0.62rem] font-bold uppercase tracking-[0.12em] text-muted-foreground">
              {index + 1}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OrganizerVisual() {
  const { t } = useI18n();

  return (
    <div className="mt-7 grid gap-4 sm:grid-cols-[1fr_0.72fr]">
      <div className="border bg-surface p-4">
        <div className="flex items-center justify-between">
          <UsersRound aria-hidden className="size-7 text-event" />
          <span className="border border-event/30 bg-event/15 px-2 py-1 text-xs font-bold text-event">
            {t("landing.organizer.liveLabel")}
          </span>
        </div>
        <div className="mt-5 grid grid-cols-3 gap-2 text-center text-[0.62rem] font-bold uppercase tracking-[0.12em]">
          {[
            "landing.features.visual.rsvp",
            "landing.features.visual.check",
            "landing.features.visual.qr",
            "landing.features.visual.csv",
            "landing.features.visual.waitlist",
            "landing.features.visual.live"
          ].map((labelKey, index) => (
            <span className={cn("border px-2 py-3", index % 2 === 0 ? "bg-event/15 text-event" : "bg-info/15 text-info")} key={labelKey}>
              {t(labelKey as TranslationKey)}
            </span>
          ))}
        </div>
      </div>
      <div className="border bg-navy p-4 text-white">
        <Ticket aria-hidden className="size-8 text-event" />
        <div className="mt-5 grid grid-cols-4 gap-1" aria-hidden>
          {Array.from({ length: 16 }).map((_, index) => (
            <span className={index % 3 === 0 ? "h-3 bg-white" : "h-3 bg-white/30"} key={index} />
          ))}
        </div>
      </div>
    </div>
  );
}

function CompactVisual({ visual, tone }: { visual: FeatureVisual; tone: FeatureTone }) {
  const { t } = useI18n();

  if (visual === "event") {
    return (
      <div className="mt-6 min-h-36 overflow-hidden border bg-navy p-3 text-white">
        <div className="relative h-28">
          <span className="absolute left-4 top-5 flex size-20 items-center justify-center border border-info/25 bg-info/15 text-[0.62rem] font-bold uppercase tracking-[0.12em] text-info">
            {t("landing.features.visual.map")}
          </span>
          <span className="absolute right-5 top-8 flex size-16 items-center justify-center border border-event/30 bg-event/20 text-[0.62rem] font-bold uppercase tracking-[0.12em] text-event">
            {t("landing.features.visual.rsvp")}
          </span>
          <MapPinned aria-hidden className="absolute left-1/2 top-1/2 size-10 -translate-x-1/2 -translate-y-1/2 text-event" />
        </div>
      </div>
    );
  }

  if (visual === "essay") {
    return (
      <div className="mt-6 border bg-card p-4">
        <div className="flex items-start gap-3">
          <FileSearch aria-hidden className="size-7 text-recommendation" />
          <div className="flex-1 space-y-2 text-[0.65rem] font-bold uppercase tracking-[0.12em] text-muted-foreground">
            <span className="block border bg-surface px-2 py-1">{t("landing.features.visual.prompt")}</span>
            <span className="block w-fit border bg-surface px-2 py-1">{t("landing.features.visual.structure")}</span>
            <span className="block border-l-4 border-recommendation bg-recommendation/10 px-2 py-2 text-recommendation">
              {t("landing.features.visual.evidenceNote")}
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (visual === "exams") {
    return (
      <div className="mt-6 grid grid-cols-3 gap-2">
        {["SAT", "IELTS", "AP"].map((label) => (
          <span className="border bg-success/10 p-3 text-center text-sm font-bold text-success" key={label}>
            {label}
          </span>
        ))}
      </div>
    );
  }

  if (visual === "profile") {
    return (
      <div className="mt-6 space-y-3">
        {[
          ["landing.features.visual.activities", "bg-success", "w-[84%]"],
          ["landing.features.visual.research", "bg-info", "w-[68%]"],
          ["landing.features.visual.letters", "bg-primary", "w-[52%]"]
        ].map(([label, className, width]) => (
          <div className="space-y-1" key={label}>
            <span className="text-[0.62rem] font-bold uppercase tracking-[0.12em] text-muted-foreground">
              {t(label as TranslationKey)}
            </span>
            <span className="block h-3 bg-muted">
              <span className={cn("block h-3", className, width)} />
            </span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={cn("mt-6 border p-4", TONE_CLASSES[tone])}>
      <BookOpenCheck aria-hidden className="size-8" />
      <div className="mt-5 grid grid-cols-2 gap-2 text-center text-[0.62rem] font-bold uppercase tracking-[0.12em]">
        <span className="border bg-card/60 px-2 py-3">{t("landing.features.visual.cs")}</span>
        <span className="border bg-card/60 px-2 py-3">{t("landing.features.visual.econ")}</span>
        <span className="col-span-2 border bg-card/60 px-2 py-3">{t("landing.features.visual.evidenceFit")}</span>
      </div>
    </div>
  );
}

function FeatureVisual({ visual, scale, tone }: { visual: FeatureVisual; scale: NonNullable<typeof FEATURES[number]["scale"]>; tone: FeatureTone }) {
  if (visual === "search") return <SearchVisual large={scale === "large"} />;
  if (visual === "recommendation") return <RecommendationVisual />;
  if (visual === "applications") return <ApplicationVisual />;
  if (visual === "organizer") return <OrganizerVisual />;
  return <CompactVisual tone={tone} visual={visual} />;
}

export function FeatureGrid() {
  const { t } = useI18n();
  const sectionRef = useRef<HTMLElement | null>(null);
  const prefersReducedMotion = usePrefersReducedMotion();
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start 82%", "end 28%"]
  });
  const sectionRuleScale = useTransform(scrollYProgress, [0, 1], [0.06, 1]);
  const sectionRuleOpacity = useTransform(scrollYProgress, [0, 0.18, 1], [0.25, 1, 0.88]);

  return (
    <section
      className="relative scroll-mt-24 overflow-hidden bg-background py-20 sm:py-24 lg:py-28"
      id="features"
      ref={sectionRef}
      tabIndex={-1}
    >
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-24 bg-[linear-gradient(180deg,hsl(var(--surface)),transparent)]"
      />
      <div className="relative mx-auto w-full max-w-[104rem] px-4 sm:px-6 lg:px-10">
        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-end">
          <div>
            <p className="text-eyebrow text-primary-hover">{t("landing.features.eyebrow")}</p>
            <h2 className="text-display-condensed-sm mt-4 max-w-4xl">{t("landing.features.title")}</h2>
          </div>
          <p className="max-w-2xl text-base leading-7 text-muted-foreground lg:justify-self-end">
            {t("landing.features.description")}
          </p>
        </div>

        <div className="relative mt-12 border-t border-border pt-8">
          <m.div
            aria-hidden
            className="absolute left-0 top-0 h-1 origin-left bg-gradient-to-r from-primary via-accent to-info"
            style={prefersReducedMotion ? undefined : { opacity: sectionRuleOpacity, scaleX: sectionRuleScale }}
          />
          <div className="grid items-stretch gap-5 sm:grid-cols-2 lg:auto-rows-[minmax(22rem,_auto)] lg:grid-cols-4">
            {FEATURES.map((feature, index) => {
              const scale = feature.scale ?? "compact";
              return (
                <MotionReveal className={feature.className} delayMs={index * 45} key={feature.titleKey}>
                  <Card
                    className={cn(
                      "group relative h-full min-h-[22rem] overflow-hidden border bg-gradient-to-br p-6 transition-[transform,box-shadow,border-color] hover:-translate-y-1 hover:shadow-2xl",
                      SURFACE_CLASSES[feature.tone],
                      scale === "large" ? "p-7" : "",
                      scale === "compact" ? "min-h-[20rem]" : "",
                      scale === "tall" || scale === "large" ? "lg:min-h-[45rem]" : "",
                      scale === "wide" ? "lg:min-h-[22rem]" : ""
                    )}
                    interactive
                  >
                    <div className="relative z-10 flex h-full flex-col">
                      <FeatureIcon icon={feature.icon} tone={feature.tone} />
                      <div className={scale === "wide" ? "sm:max-w-xl" : ""}>
                        <h3
                          className={cn(
                            "mt-5 font-serif font-semibold leading-tight",
                            scale === "large" ? "text-3xl sm:text-4xl" : "text-xl"
                          )}
                        >
                          {t(feature.titleKey)}
                        </h3>
                        <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
                          {t(feature.descriptionKey)}
                        </p>
                      </div>
                      <div className="mt-auto">
                        <FeatureVisual scale={scale} tone={feature.tone} visual={feature.visual} />
                      </div>
                    </div>
                  </Card>
                </MotionReveal>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
