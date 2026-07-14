import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

import { Button } from "./button";

type IconButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "aria-label" | "title" | "type"
> & {
  label: string;
};

export function IconButton({ className, label, ...props }: IconButtonProps) {
  return (
    <Button
      aria-label={label}
      className={cn("size-11 min-h-11 shrink-0 p-0", className)}
      title={label}
      type="button"
      variant="ghost"
      {...props}
    />
  );
}
