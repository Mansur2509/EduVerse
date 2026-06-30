"use client";

import { MessageCircle } from "lucide-react";

import { useI18n } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";

export const SUPPORT_URL = "https://t.me/Otvet_mne_uje_nakonec";

export function SupportLink({ className }: { className?: string }) {
  const { t } = useI18n();
  return (
    <a
      className={cn(
        "inline-flex min-h-9 items-center gap-2 rounded-sm border bg-surface px-3 text-xs font-semibold text-muted-foreground transition hover:border-primary/35 hover:text-foreground",
        className
      )}
      href={SUPPORT_URL}
      rel="noreferrer"
      target="_blank"
    >
      <MessageCircle aria-hidden className="size-4" />
      {t("support.link")}
    </a>
  );
}
