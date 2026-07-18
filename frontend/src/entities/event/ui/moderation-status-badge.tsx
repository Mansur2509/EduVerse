"use client";

import type { EventModerationStatus } from "@/entities/event";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Badge, type BadgeTone } from "@/shared/ui/badge";

const STATUS_TONE: Record<EventModerationStatus, BadgeTone> = {
  draft: "muted",
  pending_review: "warning",
  published: "success",
  rejected: "danger",
  cancelled: "danger",
  archived: "muted"
};

export function ModerationStatusBadge({
  status,
  className
}: {
  status: EventModerationStatus;
  className?: string;
}) {
  const { t } = useI18n();

  return (
    <Badge className={className} tone={STATUS_TONE[status]}>
      {t(`organizer.status.${status}` as TranslationKey)}
    </Badge>
  );
}
