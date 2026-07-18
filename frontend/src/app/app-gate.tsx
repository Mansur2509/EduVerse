"use client";

import { RefreshCw } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useState } from "react";

import { useAuth } from "@/features/auth";
import { OnboardingFlow } from "@/features/onboarding";
import { getProfileCompletionRequest } from "@/features/profile";
import { useI18n } from "@/shared/i18n";
import { notifyAuthInvalid } from "@/shared/lib/auth-storage";
import { useSlowLoad } from "@/shared/lib/use-slow-load";
import { BrandMark } from "@/shared/ui/brand-mark";
import { Button } from "@/shared/ui/button";
import { LanguageSwitcher } from "@/shared/ui/language-switcher";
import { SupportLink } from "@/shared/ui/support-link";
import { AppShell } from "@/widgets/app-shell";

import { AuthBrandPanel } from "./auth-brand-panel";
import { AuthForm } from "@/features/auth/ui/auth-form";
import { ForgotPasswordForm } from "@/features/auth/ui/forgot-password-form";
import { ResetPasswordForm } from "@/features/auth/ui/reset-password-form";

type AuthMode = "login" | "register";
type OnboardingGateStatus = "checking" | "incomplete" | "complete" | "offline";
const AUTH_ROUTE_PATHS = new Set([
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password"
]);

function FullScreenStatus({
  offline = false,
  onboarding = false,
  onRetry,
  onClearSession
}: {
  offline?: boolean;
  onboarding?: boolean;
  onRetry?: () => void;
  onClearSession?: () => void;
}) {
  const { t } = useI18n();
  const isSlow = useSlowLoad(!offline);
  const title = offline
    ? t("auth.gateway.offlineTitle")
    : onboarding
      ? t("onboarding.gate.checkingTitle")
      : t("auth.gateway.checkingTitle");
  const description = offline
    ? t("auth.gateway.offlineDescription")
    : onboarding
      ? t("onboarding.gate.checkingDescription")
      : t("auth.gateway.checkingDescription");

  return (
    <main className="grid min-h-screen place-items-center bg-background px-6">
      <div className="w-full max-w-lg border border-border bg-card p-8 text-center shadow-card">
        <BrandMark className="mx-auto block size-12 overflow-hidden rounded-sm" />
        <h1 className="mt-5 font-serif text-2xl font-semibold">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
        {offline && onRetry ? (
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Button className="gap-2" onClick={onRetry}>
              <RefreshCw aria-hidden className="size-4" />
              {t("auth.gateway.retry")}
            </Button>
            {onClearSession ? (
              <Button onClick={onClearSession} variant="ghost">
                {t("auth.gateway.clearSession")}
              </Button>
            ) : null}
          </div>
        ) : (
          <>
            <div
              aria-label={t("auth.checkingSession")}
              className="mx-auto mt-6 h-1 w-32 overflow-hidden bg-muted"
              role="status"
            >
              <span className="block h-full w-1/2 animate-pulse bg-primary" />
            </div>
            {isSlow ? (
              <p className="mt-4 text-xs leading-5 text-muted-foreground" role="status">
                {t("common.wakingUp")}
              </p>
            ) : null}
          </>
        )}
      </div>
    </main>
  );
}

export function AppGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useI18n();
  const { status, retrySession } = useAuth();
  const [mode, setMode] = useState<AuthMode>(
    pathname === "/register" ? "register" : "login"
  );
  const [onboardingStatus, setOnboardingStatus] =
    useState<OnboardingGateStatus>("checking");
  const isAuthRoute = AUTH_ROUTE_PATHS.has(pathname);

  const checkOnboarding = useCallback(async () => {
    setOnboardingStatus("checking");
    try {
      const completion = await getProfileCompletionRequest();
      setOnboardingStatus(completion.is_complete ? "complete" : "incomplete");
    } catch {
      setOnboardingStatus("offline");
    }
  }, []);

  useEffect(() => {
    if (pathname === "/register") setMode("register");
    if (pathname === "/login") setMode("login");
  }, [pathname]);

  useEffect(() => {
    if (status === "authenticated") {
      void checkOnboarding();
    } else {
      setOnboardingStatus("checking");
    }
  }, [checkOnboarding, status]);

  useEffect(() => {
    if (
      status === "authenticated" &&
      onboardingStatus === "complete" &&
      ["/", "/login", "/register", "/onboarding"].includes(pathname)
    ) {
      router.replace("/dashboard");
    }
  }, [onboardingStatus, pathname, router, status]);

  useEffect(() => {
    // "/" is a public landing route (see the render guard below) -- an
    // unauthenticated visitor there must not be bounced to /login a moment
    // after the landing page has already rendered.
    if (status === "unauthenticated" && !isAuthRoute && pathname !== "/") {
      router.replace("/login");
    }
  }, [isAuthRoute, pathname, router, status]);

  // Public marketing route: render it immediately regardless of
  // session-check status, so logged-out visitors, crawlers, and the SSR
  // pass never see a spinner before real content -- the landing page has no
  // backend dependency at all, so a slow session check or an unreachable
  // backend (status "checking"/"unauthenticated"/"offline") must never
  // block it. Only a confirmed "authenticated" session falls through past
  // this guard, into the same onboarding-aware redirect-to-dashboard
  // handling used below for /login, /register, /onboarding.
  if (pathname === "/" && status !== "authenticated") {
    return <>{children}</>;
  }

  if (status === "checking") return <FullScreenStatus />;
  if (status === "offline") {
    return (
      <FullScreenStatus
        offline
        // Instant, network-free escape hatch: the backend is already known to
        // be unreachable here, so this must not itself wait on another
        // network round trip. `notifyAuthInvalid` synchronously clears stored
        // tokens and flips auth status to "unauthenticated" via the existing
        // AUTH_INVALID_EVENT listener in AuthProvider.
        onClearSession={notifyAuthInvalid}
        onRetry={() => void retrySession()}
      />
    );
  }

  if (status === "unauthenticated") {
    const isPasswordResetRoute =
      pathname === "/forgot-password" || pathname === "/reset-password";

    return (
      <main className="min-h-screen bg-background lg:grid lg:grid-cols-[minmax(22rem,0.9fr)_minmax(30rem,1.1fr)]">
        <AuthBrandPanel />
        <section className="relative grid place-items-center px-4 py-10 sm:px-8 lg:px-12">
          <div className="absolute right-4 top-4 sm:right-8 sm:top-6">
            <LanguageSwitcher compact />
          </div>
          <div className="w-full max-w-md pt-10">
            {isPasswordResetRoute ? (
              pathname === "/forgot-password" ? (
                <ForgotPasswordForm />
              ) : (
                <ResetPasswordForm />
              )
            ) : (
              <>
                <div className="mb-4 grid grid-cols-2 border border-border bg-surface p-1">
                  {(["login", "register"] as const).map((item) => (
                    <button
                      className={
                        mode === item
                          ? "min-h-10 bg-navy px-3 text-sm font-semibold text-navy-foreground"
                          : "min-h-10 px-3 text-sm font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
                      }
                      key={item}
                      onClick={() => setMode(item)}
                      type="button"
                    >
                      {item === "login" ? t("auth.signIn") : t("auth.createAccount")}
                    </button>
                  ))}
                </div>
                <AuthForm mode={mode} onModeChange={setMode} />
              </>
            )}
          </div>
        </section>
        <SupportLink className="fixed bottom-4 right-4 z-30 shadow-card" />
      </main>
    );
  }

  if (onboardingStatus === "checking") {
    return <FullScreenStatus onboarding />;
  }
  if (onboardingStatus === "offline") {
    return <FullScreenStatus offline onRetry={() => void checkOnboarding()} />;
  }
  if (onboardingStatus === "incomplete") {
    return <OnboardingFlow onCompleted={() => void checkOnboarding()} />;
  }
  if (["/", "/login", "/register", "/onboarding"].includes(pathname)) {
    return <FullScreenStatus onboarding />;
  }

  return <AppShell>{children}</AppShell>;
}
