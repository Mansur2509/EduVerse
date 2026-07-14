"use client";

import { LoaderCircle, RefreshCw, TriangleAlert } from "lucide-react";

import { useI18n } from "@/shared/i18n";

import { Button } from "./button";
import { Card } from "./card";
import { AppIcon } from "./icon";

/**
 * Generic "something failed, here's a retry button" state (PERFORMANCE-011
 * PART 3) -- for a failed fetch that has no cached/stale data to fall back
 * on, so there's nothing else useful to show. Never a bare spinner, never a
 * blank screen, and never raw error text: `message` must already be a
 * translated, user-facing string.
 */
export function RetryNotice({
  message,
  onRetry,
  isRetrying = false,
  bare = false
}: {
  message?: string;
  onRetry: () => void;
  isRetrying?: boolean;
  /** Skip the outer Card -- for a section that's already inside its own
   * Card (e.g. one panel of a multi-panel screen where only that panel's
   * fetch failed), so a retry notice never nests Card-in-Card. */
  bare?: boolean;
}) {
  const { t } = useI18n();
  const content = (
    <>
      <p className="flex items-start gap-2 text-sm text-muted-foreground" role="alert">
        <AppIcon className="mt-0.5 text-danger" icon={TriangleAlert} />
        {message ?? t("common.somethingWentWrong")}
      </p>
      <Button
        className="mt-3"
        disabled={isRetrying}
        onClick={onRetry}
        size="sm"
        type="button"
        variant="secondary"
      >
        <AppIcon
          className={isRetrying ? "mr-2 animate-spin motion-reduce:animate-none" : "mr-2"}
          icon={isRetrying ? LoaderCircle : RefreshCw}
        />
        {isRetrying ? t("common.retrying") : t("common.retry")}
      </Button>
    </>
  );
  return bare ? content : <Card>{content}</Card>;
}
