import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-sm border bg-card p-4 shadow-card", className)}
      {...props}
    />
  );
}
