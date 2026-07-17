"use client";

import Link from "next/link";
import {
  BookOpenCheck,
  ClipboardList,
  GraduationCap,
  Map,
  ScrollText,
  X
} from "lucide-react";
import { useEffect, useRef } from "react";

import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { AppIcon } from "@/shared/ui/icon";
import { IconButton } from "@/shared/ui/icon-button";

import { useProductTour } from "../model/product-tour-context";

const CORE_FEATURES: Array<{
  href: string;
  icon: typeof ScrollText;
  titleKey: TranslationKey;
  descriptionKey: TranslationKey;
  actionKey: TranslationKey;
}> = [
  {
    href: "/essays",
    icon: ScrollText,
    titleKey: "productTour.essay.title",
    descriptionKey: "productTour.essay.description",
    actionKey: "productTour.essay.action"
  },
  {
    href: "/universities",
    icon: GraduationCap,
    titleKey: "productTour.universities.title",
    descriptionKey: "productTour.universities.description",
    actionKey: "productTour.universities.action"
  },
  {
    href: "/events",
    icon: Map,
    titleKey: "productTour.events.title",
    descriptionKey: "productTour.events.description",
    actionKey: "productTour.events.action"
  },
  {
    href: "/applications",
    icon: ClipboardList,
    titleKey: "productTour.applications.title",
    descriptionKey: "productTour.applications.description",
    actionKey: "productTour.applications.action"
  }
];

export function ProductTourModal() {
  const { isOpen, dismiss } = useProductTour();
  const { t } = useI18n();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    dialogRef.current?.querySelector<HTMLElement>("button")?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        dismiss();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, dismiss]);

  if (!isOpen) return null;

  return (
    <div
      aria-labelledby="product-tour-title"
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-foreground/35 px-4 py-8"
      role="dialog"
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-sm border bg-card p-5 shadow-card sm:p-6"
        ref={dialogRef}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-hover">
              {t("productTour.eyebrow")}
            </p>
            <h2 className="mt-1 text-xl font-semibold sm:text-2xl" id="product-tour-title">
              {t("productTour.title")}
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
              {t("productTour.intro")}
            </p>
          </div>
          <IconButton className="shrink-0" label={t("productTour.close")} onClick={dismiss}>
            <AppIcon decorative icon={X} />
          </IconButton>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {CORE_FEATURES.map((feature) => (
            <div className="flex flex-col gap-2 rounded-sm border bg-surface p-4" key={feature.href}>
              <div className="flex items-center gap-2">
                <span className="grid size-9 shrink-0 place-items-center rounded-sm border border-primary/25 bg-primary/10 text-primary-hover">
                  <AppIcon icon={feature.icon} />
                </span>
                <h3 className="font-semibold">{t(feature.titleKey)}</h3>
              </div>
              <p className="flex-1 text-sm leading-6 text-muted-foreground">
                {t(feature.descriptionKey)}
              </p>
              <Button asChild className="w-full" onClick={dismiss} size="sm" variant="secondary">
                <Link href={feature.href}>{t(feature.actionKey)}</Link>
              </Button>
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-start gap-2 rounded-sm border bg-surface p-3">
          <AppIcon className="mt-0.5 shrink-0 text-muted-foreground" icon={BookOpenCheck} />
          <p className="text-xs leading-5 text-muted-foreground">
            <span className="font-semibold text-foreground">{t("productTour.moreTitle")}: </span>
            {t("productTour.moreDescription")}
          </p>
        </div>

        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button onClick={dismiss} type="button" variant="ghost">
            {t("productTour.skip")}
          </Button>
          <Button onClick={dismiss} type="button">
            {t("productTour.dismiss")}
          </Button>
        </div>
      </div>
    </div>
  );
}
