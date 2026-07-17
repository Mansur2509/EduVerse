import type { CSSProperties, HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  // Opt-in lift + border emphasis for cards that represent a single
  // clickable/navigable unit (a tool shortcut, a university, an event) --
  // left off by default so purely informational cards (stats, panels) don't
  // imply the whole surface is clickable when only an inner control is.
  interactive?: boolean;
  // Opt-in gentle entrance for a freshly-loaded batch of cards (e.g. new
  // recommendations, core tools on first paint). `.animate-fade-up` and its
  // reduced-motion override live in globals.css; staggering via
  // animationDelayMs is left to the caller (usually `index * 60`).
  animate?: "fade-up";
  animationDelayMs?: number;
};

export function Card({
  className,
  interactive,
  animate,
  animationDelayMs,
  style,
  ...props
}: CardProps) {
  const mergedStyle: CSSProperties | undefined =
    animate && animationDelayMs
      ? { ...style, animationDelay: `${animationDelayMs}ms` }
      : style;
  return (
    <div
      className={cn(
        "rounded-sm border bg-card p-4 shadow-card transition-[border-color,background-color,box-shadow,transform] duration-normal ease-academic",
        interactive && "hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg",
        animate === "fade-up" && "animate-fade-up",
        className
      )}
      style={mergedStyle}
      {...props}
    />
  );
}
