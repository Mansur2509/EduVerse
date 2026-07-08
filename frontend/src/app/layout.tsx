import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/features/auth";
import { I18nProvider } from "@/shared/i18n/provider";

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

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html data-theme="light" lang="en" suppressHydrationWarning>
      <body>
        <I18nProvider>
          <AuthProvider>
            <AppGate>{children}</AppGate>
          </AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
