"use client";

import { BookOpen, RefreshCw, ShieldCheck } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useState } from "react";

import { useAuth } from "@/features/auth";
import { OnboardingFlow } from "@/features/onboarding";
import { getProfileCompletionRequest } from "@/features/profile";
import { useI18n } from "@/shared/i18n";
import { notifyAuthInvalid } from "@/shared/lib/auth-storage";
import { useSlowLoad } from "@/shared/lib/use-slow-load";
import { Button } from "@/shared/ui/button";
import { LanguageSwitcher } from "@/shared/ui/language-switcher";
import { SupportLink } from "@/shared/ui/support-link";
import { AppShell } from "@/widgets/app-shell";

import { AuthForm } from "@/features/auth/ui/auth-form";

type AuthMode = "login" | "register";
type OnboardingGateStatus = "checking" | "incomplete" | "complete" | "offline";
const AUTH_ROUTE_PATHS = new Set(["/login", "/register"]);

function AcademicBrand() {
  const { t } = useI18n();

  return (
    <section className="flex min-h-[18rem] flex-col justify-between border-b border-white/15 bg-navy px-6 py-8 text-navy-foreground lg:min-h-screen lg:border-b-0 lg:border-r lg:px-12 lg:py-12">
      <div className="flex items-center gap-3">
        <span className="grid size-11 place-items-center rounded-sm border border-white/25 bg-primary font-serif text-2xl font-bold">
          E
        </span>
        <div>
          <p className="font-serif text-2xl font-semibold tracking-tight">UniWay</p>
          <p className="text-xs uppercase tracking-[0.18em] text-white/65">
            {t("auth.gateway.institution")}
          </p>
        </div>
      </div>
      <div className="max-w-xl py-10 lg:py-16">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">
          {t("auth.gateway.eyebrow")}
        </p>
        <h1 className="mt-4 font-serif text-4xl font-semibold leading-tight sm:text-5xl">
          {t("auth.gateway.title")}
        </h1>
        <p className="mt-5 max-w-lg text-base leading-7 text-white/70">
          {t("auth.gateway.description")}
        </p>
      </div>
      <div className="grid gap-3 text-sm text-white/70 sm:grid-cols-2 lg:grid-cols-1">
        <p className="flex items-center gap-3">
          <ShieldCheck aria-hidden className="size-4 text-accent" />
          {t("auth.gateway.secure")}
        </p>
        <p className="flex items-center gap-3">
          <BookOpen aria-hidden className="size-4 text-accent" />
          {t("auth.gateway.academic")}
        </p>
      </div>
    </section>
  );
}

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
        <span className="mx-auto grid size-12 place-items-center rounded-sm bg-navy font-serif text-2xl font-bold text-navy-foreground">
          E
        </span>
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
      ["/login", "/register", "/onboarding"].includes(pathname)
    ) {
      router.replace("/dashboard");
    }
  }, [onboardingStatus, pathname, router, status]);

  useEffect(() => {
    if (status === "unauthenticated" && !isAuthRoute) {
      router.replace("/login");
    }
  }, [isAuthRoute, router, status]);

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
    return (
      <main className="min-h-screen bg-background lg:grid lg:grid-cols-[minmax(22rem,0.9fr)_minmax(30rem,1.1fr)]">
        <AcademicBrand />
        <section className="relative grid place-items-center px-4 py-10 sm:px-8 lg:px-12">
          <div className="absolute right-4 top-4 sm:right-8 sm:top-6">
            <LanguageSwitcher compact />
          </div>
          <div className="w-full max-w-md pt-10">
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
  if (["/login", "/register", "/onboarding"].includes(pathname)) {
    return <FullScreenStatus onboarding />;
  }

  return <AppShell>{children}</AppShell>;
}
