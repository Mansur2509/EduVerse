import type { LucideIcon, LucideProps } from "lucide-react";

import { cn } from "@/shared/lib/cn";

export const ICON_SIZE = {
  xs: 14,
  sm: 16,
  md: 18,
  lg: 20,
  xl: 24
} as const;

export type IconSize = keyof typeof ICON_SIZE;

type AppIconProps = Omit<LucideProps, "size" | "strokeWidth"> & {
  icon: LucideIcon;
  size?: IconSize;
  decorative?: boolean;
};

export function AppIcon({
  className,
  decorative = true,
  icon: Glyph,
  size = "sm",
  ...props
}: AppIconProps) {
  return (
    <Glyph
      aria-hidden={decorative || undefined}
      className={cn("shrink-0", className)}
      focusable="false"
      size={ICON_SIZE[size]}
      strokeWidth={1.75}
      {...props}
    />
  );
}
