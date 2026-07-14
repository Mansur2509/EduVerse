"use client";

import { ThemeProvider as NextThemesProvider, useTheme } from "next-themes";
import { useEffect } from "react";
import type { ReactNode } from "react";

const LIGHT_META_COLOR = "#f9f6f1";
const DARK_META_COLOR = "#0e1420";

// Keeps the browser chrome (address bar / PWA title bar) in sync with the
// *resolved* theme, including an explicit user override -- a static
// `media="(prefers-color-scheme: dark)"` meta tag would only track the OS
// preference and ignore a manual light/dark choice, so this updates one
// tag's content imperatively whenever the resolved theme changes instead.
function ThemeColorMeta() {
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute(
        "content",
        resolvedTheme === "dark" ? DARK_META_COLOR : LIGHT_META_COLOR
      );
    }
  }, [resolvedTheme]);

  return null;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      defaultTheme="system"
      disableTransitionOnChange
      enableSystem
    >
      <ThemeColorMeta />
      {children}
    </NextThemesProvider>
  );
}

export { useTheme };
