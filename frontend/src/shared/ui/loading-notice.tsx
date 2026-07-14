"use client";

import { LoaderCircle } from "lucide-react";

import { useI18n } from "@/shared/i18n";
import { useSlowLoad } from "@/shared/lib/use-slow-load";

import { Card } from "./card";
import { AppIcon } from "./icon";

/**
 * Standard loading card. While mounted (i.e. while the caller is loading) it
 * starts a timer and, if the load is taking unusually long, adds a "the server
 * may be waking up" hint — the honest explanation for a Render cold start —
 * instead of an unexplained spinner that looks stuck.
 */
export function LoadingNotice({ message }: { message: string }) {
  const { t } = useI18n();
  const isSlow = useSlowLoad(true);

  return (
    <Card>
      <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <AppIcon className="animate-spin motion-reduce:animate-none" icon={LoaderCircle} />
        {message}
      </p>
      {isSlow ? (
        <p className="mt-2 text-xs leading-5 text-muted-foreground" role="status">
          {t("common.wakingUp")}
        </p>
      ) : null}
    </Card>
  );
}
