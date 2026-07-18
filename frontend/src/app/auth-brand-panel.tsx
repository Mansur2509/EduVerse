"use client";

import { AnimatePresence, motion } from "motion/react";
import { BookOpen, Compass, GraduationCap, Languages, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { useI18n, type TranslationKey } from "@/shared/i18n";
import { BrandMark } from "@/shared/ui/brand-mark";
import { usePrefersReducedMotion } from "@/shared/ui/use-reduced-motion";

const HIGHLIGHTS: Array<{ icon: LucideIcon; titleKey: TranslationKey; descriptionKey: TranslationKey }> = [
  { icon: GraduationCap, titleKey: "auth.gateway.highlight1.title", descriptionKey: "auth.gateway.highlight1.description" },
  { icon: Compass, titleKey: "auth.gateway.highlight2.title", descriptionKey: "auth.gateway.highlight2.description" },
  { icon: ShieldCheck, titleKey: "auth.gateway.highlight3.title", descriptionKey: "auth.gateway.highlight3.description" },
  { icon: Languages, titleKey: "auth.gateway.highlight4.title", descriptionKey: "auth.gateway.highlight4.description" }
];

const ROTATE_INTERVAL_MS = 5000;

/**
 * Brand panel shown alongside the login/register/forgot-password forms in
 * AppGate. Shares the landing page's navy/ivory/crimson language and motion
 * primitives. AuthForm itself (the actual form side) is untouched -- this
 * component only redesigns the sibling panel.
 */
export function AuthBrandPanel() {
  const { t } = useI18n();
  const prefersReducedMotion = usePrefersReducedMotion();
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion) return;
    const timer = setInterval(() => {
      setActiveIndex((index) => (index + 1) % HIGHLIGHTS.length);
    }, ROTATE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [prefersReducedMotion]);

  const active = HIGHLIGHTS[prefersReducedMotion ? 0 : activeIndex];

  return (
    <section className="flex min-h-[18rem] flex-col justify-between border-b border-white/15 bg-navy px-6 py-8 text-navy-foreground lg:min-h-screen lg:border-b-0 lg:border-r lg:px-12 lg:py-12">
      <div className="flex items-center gap-3">
        <BrandMark className="size-11 shrink-0 overflow-hidden rounded-sm" />
        <div>
          <p className="font-serif text-2xl font-semibold tracking-tight">UniWay</p>
          <p className="text-xs uppercase tracking-[0.18em] text-white/65">
            {t("auth.gateway.institution")}
          </p>
        </div>
      </div>

      <div className="max-w-xl py-10 lg:py-16">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">
          {t("auth.gateway.eyebrow")}
        </p>
        <h1 className="mt-4 font-serif text-4xl font-semibold leading-tight sm:text-5xl">
          {t("auth.gateway.title")}
        </h1>
        <p className="mt-5 max-w-lg text-base leading-7 text-white/70">
          {t("auth.gateway.description")}
        </p>

        <div className="relative mt-8 min-h-[5.5rem] max-w-md overflow-hidden rounded-sm border border-white/15 bg-white/5 p-4">
          <AnimatePresence mode="wait">
            <motion.div
              animate={{ opacity: 1 }}
              className="flex items-start gap-3"
              exit={{ opacity: 0 }}
              initial={{ opacity: 0 }}
              key={active.titleKey}
              transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="grid size-9 shrink-0 place-items-center rounded-sm border border-accent/40 bg-accent/15 text-accent">
                <active.icon aria-hidden className="size-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-navy-foreground">{t(active.titleKey)}</p>
                <p className="mt-1 text-xs leading-5 text-white/65">{t(active.descriptionKey)}</p>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <div className="grid gap-3 text-sm text-white/70 sm:grid-cols-2 lg:grid-cols-1">
        <p className="flex items-center gap-3">
          <ShieldCheck aria-hidden className="size-4 text-accent" />
          {t("auth.gateway.secure")}
        </p>
        <p className="flex items-center gap-3">
          <BookOpen aria-hidden className="size-4 text-accent" />
          {t("auth.gateway.academic")}
        </p>
      </div>
    </section>
  );
}
