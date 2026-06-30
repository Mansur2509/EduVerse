"use client";

import { HelpCircle } from "lucide-react";

import { cn } from "@/shared/lib/cn";

export function HelpTooltip({
  label,
  className
}: {
  label: string;
  className?: string;
}) {
  return (
    <span className={cn("group relative inline-flex items-center", className)}>
      <HelpCircle
        aria-label={label}
        className="size-3.5 text-muted-foreground"
        role="img"
        tabIndex={0}
      />
      <span className="pointer-events-none absolute left-1/2 top-full z-40 mt-2 hidden w-56 -translate-x-1/2 rounded-sm border bg-card px-3 py-2 text-xs font-normal leading-5 text-foreground shadow-card group-hover:block group-focus-within:block">
        {label}
      </span>
    </span>
  );
}
