"use client";

import Link from "next/link";
import { LogOut, Settings } from "lucide-react";
import type { ReactNode } from "react";

import { useAuth } from "@/features/auth/model/auth-context";
import { NotificationBell } from "@/features/notifications";
import { ProductTourModal, ProductTourProvider } from "@/features/product-tour";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Badge } from "@/shared/ui/badge";
import { BrandMark } from "@/shared/ui/brand-mark";
import { AppIcon } from "@/shared/ui/icon";
import { LanguageSwitcher } from "@/shared/ui/language-switcher";
import { SupportLink } from "@/shared/ui/support-link";
import { ThemeToggleButton } from "@/shared/ui/theme-selector";

import { NavLink } from "./nav-link";
import {
  adminNavigation,
  authenticatedAccountNavigation,
  organizerNavigation,
  primaryNavigation
} from "./navigation";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { t } = useI18n();

  if (!user) {
    return null;
  }

  const roleNavigation = [
    ...(user.role === "organizer" || user.role === "admin"
      ? organizerNavigation
      : []),
    ...(user.role === "admin" ? adminNavigation : [])
  ];
  const accountNavigation = authenticatedAccountNavigation;
  const mobileNavigation = [
    primaryNavigation[0],
    primaryNavigation[2],
    primaryNavigation[3],
    primaryNavigation[4],
    primaryNavigation[1]
  ];
  const initials =
    user.full_name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "EV";
  const roleKey = `roles.${user.role}` as TranslationKey;
  const planKey = `plans.${user.subscription.tier}` as TranslationKey;

  return (
    <ProductTourProvider>
    <div className="min-h-screen lg:fixed lg:inset-0 lg:flex lg:min-h-0 lg:overflow-hidden">
      <aside className="hidden h-dvh w-[16rem] shrink-0 flex-col border-r border-white/10 bg-navy px-3 py-5 text-navy-foreground lg:flex">
        <Link className="mb-6 flex shrink-0 items-center gap-3 px-2" href="/dashboard">
          <BrandMark className="size-9 shrink-0 overflow-hidden rounded-sm" />
          <span>
            <strong className="block font-serif text-lg">UniWay</strong>
            <span className="text-xs text-white/55">{t("shell.productSubtitle")}</span>
          </span>
        </Link>

        {/* Scrollable nav region: flex-1 + min-h-0 lets the nav scroll within the
            sidebar when the list is taller than the viewport, while the footer
            below stays pinned to the bottom with no dead space. The -inverse
            scrollbar variant matches the navy background instead of the
            light-surface thumb color washing out to a pale sliver. */}
        <div className="scrollbar-quiet-inverse min-h-0 flex-1 overflow-y-auto">
          <p className="mb-2 px-3 text-[0.68rem] font-bold uppercase tracking-[0.16em] text-white/45">
            {t("shell.workspaceNavigation")}
          </p>
          <nav aria-label={t("shell.primaryNavigation")} className="space-y-1">
            {primaryNavigation.map((item) => (
              <NavLink inverse item={item} key={item.href} />
            ))}
          </nav>

          {roleNavigation.length ? (
            <>
              <div className="my-4 border-t border-white/10" />
              <p className="mb-2 px-3 text-[0.68rem] font-bold uppercase tracking-[0.16em] text-white/45">
                {t("shell.roleSection")}
              </p>
              <nav aria-label={t("shell.roleNavigation")} className="space-y-1">
                {roleNavigation.map((item) => (
                  <NavLink inverse item={item} key={item.href} />
                ))}
              </nav>
            </>
          ) : null}

          <div className="my-4 border-t border-white/10" />

          <p className="mb-2 px-3 text-[0.68rem] font-bold uppercase tracking-[0.16em] text-white/45">
            {t("shell.accountSection")}
          </p>
          <nav aria-label={t("shell.accountNavigation")} className="space-y-1">
            {accountNavigation.map((item) => (
              <NavLink inverse item={item} key={item.href} />
            ))}
            <button
              aria-label={t("a11y.logout")}
              className="flex w-full items-center gap-3 rounded-sm px-3 py-2 text-left text-sm font-medium text-white/70 transition-colors hover:bg-white/10 hover:text-white"
              onClick={() => void logout()}
              type="button"
            >
              <AppIcon icon={LogOut} />
              <span>{t("navigation.logout")}</span>
            </button>
          </nav>
        </div>

        <div className="shrink-0 space-y-3 pt-5">
          <LanguageSwitcher inverse />
          <SupportLink className="w-full justify-center border-white/15 bg-white/5 text-white/70 hover:border-white/35 hover:bg-white/10 hover:text-white" />
          <div className="border-t border-white/10 pt-4">
            <div className="flex items-center justify-between gap-3">
              <p className="truncate text-sm font-semibold">{user.full_name || user.email}</p>
              <Badge>{t(planKey)}</Badge>
            </div>
            <p className="mt-1 text-xs text-white/55">
              {t("shell.signedInAs", { role: t(roleKey) })}
            </p>
          </div>
        </div>
      </aside>

      <div className="scrollbar-quiet min-w-0 flex-1 lg:h-dvh lg:overflow-y-auto">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b bg-surface px-4 sm:px-6 lg:px-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-hover">
              {t("shell.academicWorkspace")}
            </p>
            <p className="text-sm text-muted-foreground">{t("shell.nextMove")}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="block lg:hidden">
              <LanguageSwitcher compact />
            </div>
            <SupportLink className="lg:hidden" />
            <button
              aria-label={t("a11y.logout")}
              className="hidden items-center gap-2 text-sm font-semibold text-muted-foreground hover:text-foreground sm:flex lg:hidden"
              onClick={() => void logout()}
              type="button"
            >
              <AppIcon icon={LogOut} />
              {t("navigation.logout")}
            </button>
            <ThemeToggleButton />
            <Link
              aria-label={t("navigation.settings")}
              className="grid size-9 place-items-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              href="/settings"
              title={t("navigation.settings")}
            >
              <AppIcon decorative icon={Settings} />
            </Link>
            <NotificationBell />
            <div
              aria-label={t("shell.userAvatar")}
              className="grid size-9 place-items-center rounded-sm border border-primary/25 bg-primary/10 text-sm font-bold text-primary-hover"
            >
              {initials}
            </div>
          </div>
        </header>

        <nav
          aria-label={t("shell.compactNavigation")}
          className="flex gap-2 overflow-x-auto border-b bg-background px-4 py-2 lg:hidden"
        >
          {[...primaryNavigation, ...roleNavigation].map((item) => (
            <NavLink compactHorizontal item={item} key={item.href} />
          ))}
        </nav>

        <main className="mx-auto w-full max-w-[84rem] px-4 py-5 pb-24 sm:px-6 lg:px-8 lg:py-6">
          {children}
        </main>
      </div>

      <nav
        aria-label={t("shell.mobileNavigation")}
        className="fixed inset-x-0 bottom-0 z-30 flex justify-around border-t border-white/10 bg-navy px-2 py-1 lg:hidden"
      >
        {mobileNavigation.map((item) => (
          <NavLink compact inverse item={item} key={item.href} />
        ))}
      </nav>

      <ProductTourModal />
    </div>
    </ProductTourProvider>
  );
}
