"use client";

import { ChevronDown, Filter, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { useI18n } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";

import { Button } from "./button";
import { Card } from "./card";

type CollapsibleFilterPanelProps = {
  activeCount: number;
  children: ReactNode;
  onClear: () => void;
  storageKey: string;
  className?: string;
  defaultOpen?: boolean;
  resultCount?: number;
};

export function CollapsibleFilterPanel({
  activeCount,
  children,
  onClear,
  storageKey,
  className,
  defaultOpen = false,
  resultCount
}: CollapsibleFilterPanelProps) {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(defaultOpen);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(storageKey);
      if (stored !== null) {
        setIsOpen(stored === "open");
      }
    } catch {
      setIsOpen(defaultOpen);
    }
  }, [defaultOpen, storageKey]);

  function toggleOpen() {
    setIsOpen((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(storageKey, next ? "open" : "closed");
      } catch {
        // Ignore private-mode/localStorage failures; the panel still works.
      }
      return next;
    });
  }

  return (
    <Card className={cn("p-4", className)}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button
            aria-expanded={isOpen}
            onClick={toggleOpen}
            size="sm"
            type="button"
            variant="secondary"
          >
            <Filter aria-hidden className="mr-1.5 size-3.5" />
            {isOpen ? t("common.filters.hide") : t("common.filters.show")}
            {activeCount > 0 ? (
              <span className="ml-1.5 rounded-sm border bg-card px-1.5 py-0.5 text-[0.65rem] font-bold">
                {activeCount}
              </span>
            ) : null}
            <ChevronDown
              aria-hidden
              className={cn("ml-1.5 size-3.5 transition-transform", isOpen ? "rotate-180" : "")}
            />
          </Button>
          {resultCount !== undefined ? (
            <span className="text-xs font-semibold text-muted-foreground">
              {t("common.filters.resultCount", { count: resultCount })}
            </span>
          ) : null}
        </div>
        <Button
          disabled={activeCount === 0}
          onClick={onClear}
          size="sm"
          type="button"
          variant="ghost"
        >
          <X aria-hidden className="mr-1.5 size-3.5" />
          {t("common.filters.clear")}
        </Button>
      </div>
      {isOpen ? <div className="mt-4 border-t pt-4">{children}</div> : null}
    </Card>
  );
}
