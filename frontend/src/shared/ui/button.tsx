import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-sm font-semibold tracking-[0.01em] transition-[color,background-color,border-color,transform] duration-fast ease-academic focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50 disabled:active:scale-100",
  {
    variants: {
      variant: {
        primary: "bg-primary-button text-primary-foreground hover:bg-primary-button-hover",
        secondary: "border border-border bg-surface text-foreground hover:border-navy/35 hover:bg-elevated",
        ghost: "text-muted-foreground hover:bg-elevated hover:text-foreground"
      },
      size: {
        default: "min-h-11 px-4 text-sm",
        sm: "min-h-9 px-3 text-xs"
      }
    },
    defaultVariants: {
      variant: "primary",
      size: "default"
    }
  }
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  };

export function Button({ asChild, className, variant, size, ...props }: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return <Component className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
