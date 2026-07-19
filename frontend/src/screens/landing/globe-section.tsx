"use client";

import { ArrowRight, Compass, Database, Globe2, GraduationCap, MapPin, ShieldCheck } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { MotionReveal } from "@/shared/ui/motion-reveal";
import { usePrefersReducedMotion } from "@/shared/ui/use-reduced-motion";

import type { GlobeSceneMarker } from "./globe-three-scene";
import { UNIVERSITY_COUNT_DISPLAY } from "./site-stats";

type Destination = {
  id: string;
  countryKey: TranslationKey;
  regionKey: TranslationKey;
  detailKey: TranslationKey;
  href: string;
  lat: number;
  lon: number;
  markerClass: string;
};

type ContentCategory = {
  labelKey: TranslationKey;
  detailKey: TranslationKey;
  value: string;
};

const GlobeThreeScene = dynamic(
  () => import("./globe-three-scene").then((module) => module.GlobeThreeScene),
  {
    loading: () => <GlobeLoading />,
    ssr: false
  }
);

const DESTINATIONS: Destination[] = [
  {
    id: "us",
    countryKey: "landing.globe.country.us",
    regionKey: "landing.globe.region.northAmerica",
    detailKey: "landing.globe.country.us.detail",
    href: "/universities?country=USA",
    lat: 39.5,
    lon: -98.35,
    markerClass: "left-[25%] top-[43%]"
  },
  {
    id: "uk",
    countryKey: "landing.globe.country.uk",
    regionKey: "landing.globe.region.europe",
    detailKey: "landing.globe.country.uk.detail",
    href: "/universities?country=United%20Kingdom",
    lat: 54.5,
    lon: -2.5,
    markerClass: "left-[50%] top-[33%]"
  },
  {
    id: "ca",
    countryKey: "landing.globe.country.ca",
    regionKey: "landing.globe.region.northAmerica",
    detailKey: "landing.globe.country.ca.detail",
    href: "/universities?country=Canada",
    lat: 56.1,
    lon: -106.3,
    markerClass: "left-[20%] top-[25%]"
  },
  {
    id: "sg",
    countryKey: "landing.globe.country.sg",
    regionKey: "landing.globe.region.asiaPacific",
    detailKey: "landing.globe.country.sg.detail",
    href: "/universities?country=Singapore",
    lat: 1.35,
    lon: 103.82,
    markerClass: "left-[70%] top-[63%]"
  },
  {
    id: "it",
    countryKey: "landing.globe.country.it",
    regionKey: "landing.globe.region.europe",
    detailKey: "landing.globe.country.it.detail",
    href: "/universities?country=Italy",
    lat: 41.9,
    lon: 12.5,
    markerClass: "left-[55%] top-[45%]"
  },
  {
    id: "kr",
    countryKey: "landing.globe.country.kr",
    regionKey: "landing.globe.region.asiaPacific",
    detailKey: "landing.globe.country.kr.detail",
    href: "/universities?country=South%20Korea",
    lat: 36.5,
    lon: 127.8,
    markerClass: "left-[80%] top-[43%]"
  }
];

const CONTENT_CATEGORIES: ContentCategory[] = [
  {
    labelKey: "landing.globe.category.countries",
    detailKey: "landing.globe.category.countries.detail",
    value: "6"
  },
  {
    labelKey: "landing.globe.category.universities",
    detailKey: "landing.globe.category.universities.detail",
    value: `${UNIVERSITY_COUNT_DISPLAY}+`
  },
  {
    labelKey: "landing.globe.category.programs",
    detailKey: "landing.globe.category.programs.detail",
    value: "CAT"
  },
  {
    labelKey: "landing.globe.category.scholarships",
    detailKey: "landing.globe.category.scholarships.detail",
    value: "SRC"
  },
  {
    labelKey: "landing.globe.category.events",
    detailKey: "landing.globe.category.events.detail",
    value: "MAP"
  }
];

function GlobeLoading() {
  return (
    <div className="absolute inset-0 grid place-items-center">
      <div className="size-[72%] rounded-full border border-white/15 bg-white/[0.04] shadow-[inset_-34px_-34px_80px_rgba(0,0,0,0.35)]" />
    </div>
  );
}

function GlobeFallback({
  active,
  destinations,
  onSelect
}: {
  active: Destination;
  destinations: Destination[];
  onSelect: (id: string) => void;
}) {
  const { t } = useI18n();

  return (
    <div className="landing-globe-sphere absolute inset-8 overflow-hidden rounded-full border border-info/30 bg-[radial-gradient(circle_at_34%_28%,hsl(var(--info)/0.58),hsl(var(--navy))_56%,hsl(var(--navy))_100%)]">
      <svg aria-hidden className="absolute inset-0 size-full text-white/20" fill="none" viewBox="0 0 500 500">
        <circle cx="250" cy="250" r="188" stroke="currentColor" strokeWidth="1.2" />
        <ellipse cx="250" cy="250" rx="104" ry="188" stroke="currentColor" strokeWidth="1" />
        <ellipse cx="250" cy="250" rx="188" ry="68" stroke="currentColor" strokeWidth="1" />
        <path d="M92 177c78 36 238 36 316 0M92 323c78-36 238-36 316 0" stroke="currentColor" />
        <path d="M143 126c62 70 62 178 0 248M357 126c-62 70-62 178 0 248" stroke="currentColor" />
        <path d="M166 218l33-44 41 13 24-31 58 33-18 50 51 30-63 45-45-24-30 37-58-29 22-42-35-18z" fill="currentColor" opacity="0.38" />
        <path d="M94 250l48-38 31 19-26 54-42-2zM333 192l65 28 17 52-59 19-48-41z" fill="currentColor" opacity="0.24" />
      </svg>
      {destinations.map((destination) => {
        const selected = destination.id === active.id;
        return (
          <button
            aria-label={t(destination.countryKey)}
            className={`landing-globe-marker absolute ${destination.markerClass} grid place-items-center border transition-transform hover:scale-110 focus-visible:scale-110 ${
              selected
                ? "size-10 border-accent bg-accent text-accent-foreground shadow-2xl shadow-accent/40"
                : "size-7 border-white/45 bg-white/20 text-white backdrop-blur"
            }`}
            data-country-id={destination.id}
            key={destination.id}
            onClick={(event) => {
              event.stopPropagation();
              onSelect(destination.id);
            }}
            type="button"
          >
            <MapPin aria-hidden className="size-4" />
          </button>
        );
      })}
    </div>
  );
}

export function GlobeSection() {
  const { t } = useI18n();
  const prefersReducedMotion = usePrefersReducedMotion();
  const [activeId, setActiveId] = useState(DESTINATIONS[0].id);
  const [categoryIndex, setCategoryIndex] = useState(0);
  const active = DESTINATIONS.find((destination) => destination.id === activeId) ?? DESTINATIONS[0];
  const activeCategory = CONTENT_CATEGORIES[categoryIndex] ?? CONTENT_CATEGORIES[0];

  const sceneMarkers = useMemo<GlobeSceneMarker[]>(
    () =>
      DESTINATIONS.map((destination) => ({
        id: destination.id,
        label: t(destination.countryKey),
        lat: destination.lat,
        lon: destination.lon
      })),
    [t]
  );

  useEffect(() => {
    if (prefersReducedMotion) return;
    const timer = window.setInterval(() => {
      setCategoryIndex((current) => (current + 1) % CONTENT_CATEGORIES.length);
    }, 4600);
    return () => window.clearInterval(timer);
  }, [prefersReducedMotion]);

  return (
    <section
      className="relative overflow-hidden bg-navy py-20 text-navy-foreground sm:py-24 lg:py-28"
      id="global-path"
      tabIndex={-1}
    >
      <div
        aria-hidden
        className="absolute inset-0 bg-[linear-gradient(115deg,hsl(var(--navy))_0_52%,hsl(var(--primary-hover))_52%_68%,hsl(var(--navy))_68%_100%)]"
      />
      <div
        aria-hidden
        className="absolute -right-20 top-20 h-72 w-72 border border-info/25 bg-info/10 blur-2xl"
      />
      <div
        aria-hidden
        className="absolute bottom-0 left-0 h-32 w-full bg-[linear-gradient(180deg,transparent,hsl(var(--background)/0.24))]"
      />
      <div className="relative mx-auto grid w-full max-w-[98rem] gap-12 px-4 sm:px-6 lg:grid-cols-[0.88fr_1.12fr] lg:items-center lg:px-10">
        <MotionReveal>
          <p className="text-eyebrow text-accent">{t("landing.globe.eyebrow")}</p>
          <h2 className="text-display-condensed-sm mt-4 max-w-4xl text-navy-foreground">
            {t("landing.globe.title")}
          </h2>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-white/75">
            {t("landing.globe.description")}
          </p>

          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            <div className="border border-white/20 bg-white/[0.08] p-5">
              <p className="text-display-condensed-sm text-5xl leading-none text-white">{UNIVERSITY_COUNT_DISPLAY}+</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-[0.14em] text-white/65">
                {t("landing.globe.statUniversities")}
              </p>
            </div>
            <div className="border border-white/20 bg-white/[0.08] p-5">
              <p className="text-display-condensed-sm text-5xl leading-none text-white">4</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-[0.14em] text-white/65">
                {t("landing.globe.statLanguages")}
              </p>
            </div>
            <div className="border border-white/20 bg-white/[0.08] p-5">
              <ShieldCheck aria-hidden className="size-10 text-success" />
              <p className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-white/65">
                {t("landing.globe.statVerified")}
              </p>
            </div>
          </div>
        </MotionReveal>

        <MotionReveal delayMs={100}>
          <div className="grid gap-6 xl:grid-cols-[1fr_0.56fr] xl:items-center">
            <div
              aria-label={t("landing.globe.countryTabsLabel")}
              className="landing-globe-stage relative mx-auto aspect-square w-full max-w-[39rem] select-none"
              role="group"
            >
              <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle_at_42%_18%,rgba(255,255,255,0.16),transparent_34%),radial-gradient(circle_at_50%_58%,hsl(var(--info)/0.2),transparent_58%)]" />
              <GlobeFallback active={active} destinations={DESTINATIONS} onSelect={setActiveId} />
              <GlobeThreeScene
                activeId={active.id}
                ariaLabel={t("landing.globe.canvasLabel")}
                fallbackLabel={t("landing.globe.webglFallback")}
                markers={sceneMarkers}
                onSelect={setActiveId}
                renderedLabel={t("landing.globe.loading3d")}
              />
              <div
                aria-hidden
                className="absolute inset-x-20 bottom-5 h-14 rounded-[50%] bg-black/35 blur-2xl"
              />
            </div>

            <div
              className="border border-white/15 bg-white/[0.08] p-5 shadow-2xl shadow-black/30 backdrop-blur"
              data-active-country-panel={active.id}
            >
              <div className="flex items-center gap-2 text-accent">
                <Globe2 aria-hidden className="size-5" />
                <p className="text-eyebrow">{t(active.regionKey)}</p>
              </div>
              <h3 className="mt-4 text-display-condensed-sm text-4xl leading-none text-white">
                {t(active.countryKey)}
              </h3>
              <p className="mt-4 text-sm leading-6 text-white/[0.74]">{t(active.detailKey)}</p>

              <div className="mt-6 border border-info/25 bg-info/10 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 text-info">
                    <Database aria-hidden className="size-5" />
                    <p className="text-eyebrow">{t(activeCategory.labelKey)}</p>
                  </div>
                  <span className="text-display-condensed-sm text-3xl leading-none text-white">
                    {activeCategory.value}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-white/70">
                  {t(activeCategory.detailKey, { count: UNIVERSITY_COUNT_DISPLAY })}
                </p>
              </div>

              <div className="mt-4 flex items-center gap-3 border border-success/25 bg-success/10 p-3 text-sm font-semibold text-white">
                <GraduationCap aria-hidden className="size-5 text-success" />
                {t("landing.globe.coverageNote")}
              </div>
              <Button asChild className="mt-6 w-full border-white/20 bg-white/[0.1] text-white hover:bg-white/[0.16]" variant="secondary">
                <Link href={active.href}>
                  {t("landing.globe.cta")}
                  <ArrowRight aria-hidden className="ml-2 size-4" />
                </Link>
              </Button>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-2" aria-label={t("landing.globe.countryTabsLabel")} role="group">
            {DESTINATIONS.map((destination) => (
              <button
                className={`border px-3 py-2 text-xs font-bold uppercase tracking-[0.12em] ${
                  destination.id === active.id
                    ? "border-accent bg-accent text-accent-foreground"
                    : "border-white/15 bg-white/[0.06] text-white/[0.72] hover:bg-white/[0.12] hover:text-white"
                }`}
                data-country-id={destination.id}
                key={destination.id}
                onClick={() => setActiveId(destination.id)}
                type="button"
              >
                <Compass aria-hidden className="mr-2 inline size-3.5" />
                {t(destination.countryKey)}
              </button>
            ))}
          </div>
        </MotionReveal>
      </div>
    </section>
  );
}
