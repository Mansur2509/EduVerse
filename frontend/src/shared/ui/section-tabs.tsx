"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/shared/lib/cn";

import { AppIcon } from "./icon";

type SectionTab = {
  href: string;
  label: string;
  icon?: LucideIcon;
};

export function SectionTabs({ ariaLabel, items }: { ariaLabel: string; items: SectionTab[] }) {
  const pathname = usePathname();

  return (
    <nav aria-label={ariaLabel} className="flex flex-wrap gap-2 border-b pb-3">
      {items.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            className={cn(
              "inline-flex min-h-9 items-center gap-2 rounded-sm border px-3 text-xs font-semibold transition-colors duration-fast ease-academic",
              isActive
                ? "border-primary bg-primary text-primary-foreground"
                : "bg-surface text-muted-foreground hover:border-navy/35 hover:text-foreground"
            )}
            href={item.href}
            key={item.href}
          >
            {item.icon ? <AppIcon icon={item.icon} size="xs" /> : null}
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
