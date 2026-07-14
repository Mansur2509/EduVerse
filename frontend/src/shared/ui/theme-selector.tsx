"use client";

import { Laptop, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { useI18n } from "@/shared/i18n";
import { useTheme } from "@/shared/theme/provider";
import { cn } from "@/shared/lib/cn";

import { AppIcon } from "./icon";

const OPTIONS = [
  { value: "light", icon: Sun, labelKey: "settings.appearance.light" },
  { value: "dark", icon: Moon, labelKey: "settings.appearance.dark" },
  { value: "system", icon: Laptop, labelKey: "settings.appearance.system" }
] as const;

export function ThemeSelector({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme } = useTheme();
  const { t } = useI18n();
  // Reading `theme` before mount would show "system" as selected on the
  // server render regardless of the visitor's real stored preference --
  // next-themes only knows the true value once it hydrates from
  // localStorage. Rendering the group inert (no assumed selection) until
  // mounted avoids a one-frame flash of the wrong option being highlighted.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const activeIndex = Math.max(
    0,
    OPTIONS.findIndex((option) => option.value === theme)
  );

  function moveSelection(fromIndex: number, delta: number, event: React.KeyboardEvent) {
    event.preventDefault();
    const nextIndex = (fromIndex + delta + OPTIONS.length) % OPTIONS.length;
    const nextOption = OPTIONS[nextIndex];
    setTheme(nextOption.value);
    (event.currentTarget.parentElement?.children[nextIndex] as HTMLElement | undefined)?.focus();
  }

  return (
    <div
      aria-label={t("settings.appearance.label")}
      className={cn(
        "inline-flex rounded-sm border bg-surface p-0.5",
        compact ? "gap-0.5" : "gap-1"
      )}
      role="radiogroup"
    >
      {OPTIONS.map((option, index) => {
        const selected = mounted && theme === option.value;
        return (
          <button
            aria-checked={selected}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-sm px-2.5 py-1.5 text-xs font-semibold transition-colors duration-fast ease-academic",
              selected
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-elevated hover:text-foreground"
            )}
            key={option.value}
            onClick={() => setTheme(option.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight" || event.key === "ArrowDown") {
                moveSelection(index, 1, event);
              } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                moveSelection(index, -1, event);
              }
            }}
            role="radio"
            tabIndex={index === activeIndex ? 0 : -1}
            type="button"
          >
            <AppIcon icon={option.icon} size="sm" />
            {compact ? null : t(option.labelKey)}
          </button>
        );
      })}
    </div>
  );
}
