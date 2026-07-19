"use client";

import { ExternalLink, X } from "lucide-react";
import { AnimatePresence, m } from "motion/react";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { useI18n, type TranslationKey } from "@/shared/i18n";
import { AppIcon } from "@/shared/ui/icon";
import { MotionReveal } from "@/shared/ui/motion-reveal";
import { usePrefersReducedMotion } from "@/shared/ui/use-reduced-motion";

type Partner = {
  nameKey: TranslationKey;
  telegramUrl: string;
  src?: string;
  textMark?: string;
};

const PARTNERS: Partner[] = [
  {
    nameKey: "landing.partners.yrc",
    src: "/landing-partners/clean/yrc-clean.png",
    telegramUrl: "https://t.me/yrc_organization"
  },
  {
    nameKey: "landing.partners.nexusVolunteers",
    src: "/landing-partners/clean/nexus-volunteers-clean.png",
    telegramUrl: "https://t.me/NexusVolunteers"
  },
  {
    nameKey: "landing.partners.uniteens",
    src: "/landing-partners/clean/uniteens-clean.png",
    telegramUrl: "https://t.me/uniteens_uz"
  },
  {
    nameKey: "landing.partners.lexNova",
    src: "/landing-partners/clean/lex-nova-clean.png",
    telegramUrl: "https://t.me/lexnova_law"
  },
  {
    nameKey: "landing.partners.xproject",
    telegramUrl: "https://t.me/xprojectuz",
    textMark: "Xproject"
  },
  {
    nameKey: "landing.partners.xdebates",
    src: "/landing-partners/clean/xdebates-clean.png",
    telegramUrl: "https://t.me/xdebateuz"
  },
  {
    nameKey: "landing.partners.eduunity",
    src: "/landing-partners/clean/eduunity-clean.png",
    telegramUrl: "https://t.me/+IU3CKBjSsSlmNzFi"
  },
  {
    nameKey: "landing.partners.dynamicsVolunteers",
    telegramUrl: "https://t.me/dynvolunteers",
    textMark: "DV"
  }
];

function PartnerMark({ partner, modal = false }: { partner: Partner; modal?: boolean }) {
  const { t } = useI18n();
  const name = t(partner.nameKey);

  if (partner.src) {
    return (
      <Image
        alt={modal ? name : ""}
        className={`${modal ? "max-h-32 w-full" : "size-[72%]"} object-contain`}
        height={modal ? 160 : 130}
        loading={modal ? "eager" : "lazy"}
        src={partner.src}
        width={240}
      />
    );
  }

  const mark = partner.textMark ?? name;
  const longMark = mark.length > 3;

  return (
    <span
      className={`text-display-condensed-sm max-w-[84%] text-center leading-none text-primary-hover dark:text-primary ${
        modal ? (longMark ? "text-4xl" : "text-5xl") : longMark ? "text-[1.7rem] sm:text-[1.95rem] lg:text-[2.1rem]" : "text-4xl"
      }`}
    >
      {mark}
    </span>
  );
}

function PartnerLogo({
  decorative = false,
  onOpen,
  partner
}: {
  decorative?: boolean;
  onOpen?: (partner: Partner) => void;
  partner: Partner;
}) {
  const { t } = useI18n();
  const name = t(partner.nameKey);
  const className =
    "group/partner grid size-28 shrink-0 place-items-center overflow-hidden rounded-full border border-border/80 bg-card shadow-[0_18px_46px_hsl(var(--navy)/0.12)] transition-transform hover:-translate-y-1 focus-visible:-translate-y-1 sm:size-32 lg:size-36";

  if (decorative) {
    return (
      <div aria-hidden className={className}>
        <PartnerMark partner={partner} />
      </div>
    );
  }

  return (
    <button
      aria-label={t("landing.partners.openDetails", { name })}
      className={`${className} cursor-pointer overflow-hidden hover:border-primary/45 focus-visible:border-primary`}
      data-partner-name={name}
      data-partner-url={partner.telegramUrl}
      onClick={() => onOpen?.(partner)}
      type="button"
    >
      <PartnerMark partner={partner} />
    </button>
  );
}

function PartnerDialog({ onClose, partner }: { onClose: () => void; partner: Partner }) {
  const { t } = useI18n();
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const name = t(partner.nameKey);

  useEffect(() => {
    closeRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <m.div
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 grid place-items-center bg-navy/70 p-4 backdrop-blur-sm"
      exit={{ opacity: 0 }}
      initial={{ opacity: 0 }}
      onClick={onClose}
    >
      <m.div
        animate={{ opacity: 1, scale: 1, y: 0 }}
        aria-labelledby="landing-partner-dialog-title"
        aria-modal="true"
        className="w-full max-w-md border bg-card p-5 text-foreground shadow-2xl shadow-black/30"
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-eyebrow text-primary-hover">{t("landing.partners.modalEyebrow")}</p>
            <h3 className="mt-2 font-serif text-2xl font-semibold" id="landing-partner-dialog-title">
              {name}
            </h3>
          </div>
          <button
            aria-label={t("landing.partners.close")}
            className="grid size-10 place-items-center border text-muted-foreground hover:bg-muted hover:text-foreground"
            onClick={onClose}
            ref={closeRef}
            type="button"
          >
            <AppIcon icon={X} />
          </button>
        </div>

        <div className="mt-6 grid min-h-36 place-items-center border bg-surface p-5">
          <PartnerMark modal partner={partner} />
        </div>

        <a
          className="mt-5 flex min-h-12 items-center justify-center gap-2 border bg-primary px-4 text-sm font-bold text-primary-foreground hover:bg-primary-hover"
          href={partner.telegramUrl}
          rel="noreferrer"
          target="_blank"
        >
          {t("landing.partners.openTelegram")}
          <ExternalLink aria-hidden className="size-4" />
        </a>
      </m.div>
    </m.div>
  );
}

export function PartnersSection() {
  const { t } = useI18n();
  const prefersReducedMotion = usePrefersReducedMotion();
  const [selectedPartner, setSelectedPartner] = useState<Partner | null>(null);
  const [paused, setPaused] = useState(false);
  const scrolling = !prefersReducedMotion;

  return (
    <section className="relative overflow-hidden bg-surface py-20 sm:py-24 lg:py-24" id="partners" tabIndex={-1}>
      <div aria-hidden className="absolute inset-x-0 top-0 h-px bg-primary/30" />
      <div aria-hidden className="absolute inset-0 bg-[radial-gradient(circle_at_8%_22%,hsl(var(--primary)/0.18),transparent_30%),radial-gradient(circle_at_92%_70%,hsl(var(--info)/0.12),transparent_30%)]" />
      <div aria-hidden className="absolute left-8 top-16 hidden size-24 rotate-45 border border-primary/25 lg:block" />
      <div aria-hidden className="absolute bottom-12 right-16 hidden size-12 rotate-45 bg-accent/25 lg:block" />
      <div className="relative mx-auto w-full max-w-[98rem] px-4 sm:px-6 lg:px-10">
        <MotionReveal>
          <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
            <div>
              <p className="text-eyebrow text-primary-hover">{t("landing.partners.eyebrow")}</p>
              <h2 className="text-display-condensed-sm mt-4 max-w-4xl">{t("landing.partners.title")}</h2>
            </div>
            <p className="max-w-2xl text-base leading-7 text-muted-foreground lg:justify-self-end">
              {t("landing.partners.description")}
            </p>
          </div>
        </MotionReveal>

        <MotionReveal delayMs={80}>
          <div
            className="group relative mt-12 overflow-x-auto overflow-y-hidden border-y border-border bg-[linear-gradient(90deg,hsl(var(--surface)),hsl(var(--background)),hsl(var(--surface)))] py-8 scrollbar-quiet md:overflow-hidden"
            onFocusCapture={() => setPaused(true)}
            onBlurCapture={() => setPaused(false)}
            onPointerEnter={() => setPaused(true)}
            onPointerLeave={() => setPaused(false)}
          >
            <div
              className={`flex w-max items-center gap-6 px-6 sm:gap-8 lg:gap-10 ${
                scrolling
                  ? `md:animate-[landing-partner-scroll_46s_linear_infinite] ${
                      paused ? "md:[animation-play-state:paused]" : ""
                    }`
                  : ""
              }`}
            >
              {PARTNERS.map((partner) => (
                <PartnerLogo key={partner.nameKey} onOpen={setSelectedPartner} partner={partner} />
              ))}
              {scrolling ? (
                <div className="hidden items-center gap-6 sm:gap-8 md:flex lg:gap-10">
                  {PARTNERS.map((partner) => (
                    <PartnerLogo decorative key={`${partner.nameKey}-duplicate`} partner={partner} />
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        </MotionReveal>
      </div>

      <AnimatePresence>
        {selectedPartner ? (
          <PartnerDialog onClose={() => setSelectedPartner(null)} partner={selectedPartner} />
        ) : null}
      </AnimatePresence>
    </section>
  );
}
