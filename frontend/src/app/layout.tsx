import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/features/auth";
import { I18nProvider } from "@/shared/i18n/provider";
import { ThemeProvider } from "@/shared/theme/provider";

import "./globals.css";
import { AppGate } from "./app-gate";

export const metadata: Metadata = {
  title: {
    default: "UniWay",
    template: "%s · UniWay"
  },
  description:
    "A calm academic workspace for admissions, events, exams, research, and student growth."
};

export const viewport: Viewport = {
  themeColor: "#f9f6f1"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <I18nProvider>
            <AuthProvider>
              <AppGate>{children}</AppGate>
            </AuthProvider>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
