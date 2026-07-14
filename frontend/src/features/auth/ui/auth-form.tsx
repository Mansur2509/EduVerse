"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CircleAlert,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  LogIn,
  Mail,
  UserPlus,
  UserRound
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import { ApiError, getApiErrorMessage } from "@/shared/api/client";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { GoogleIcon } from "@/shared/ui/google-icon";
import { AppIcon } from "@/shared/ui/icon";
import { IconButton } from "@/shared/ui/icon-button";

import { useAuth } from "../model/auth-context";
import { getAuthConfigRequest, getGoogleOAuthStartUrl } from "../api/auth-api";

type AuthFormProps = {
  mode: "login" | "register";
  onAuthenticated?: () => void;
  onModeChange?: (mode: "login" | "register") => void;
  showModeLink?: boolean;
};

const DEMO_PASSWORD = "UniWay-Demo-842!";
const DEMO_ACCOUNTS = [
  {
    email: "student.demo@uniway.local",
    labelKey: "auth.demo.student",
    role: "student"
  }
] satisfies Array<{ email: string; labelKey: TranslationKey; role: string }>;

export function AuthForm({
  mode,
  onAuthenticated,
  onModeChange,
  showModeLink = true
}: AuthFormProps) {
  const router = useRouter();
  const { login, register } = useAuth();
  const { t } = useI18n();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [oauthNotice, setOauthNotice] = useState<{
    message: string;
    tone: "info" | "warning" | "error";
  } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pendingDemoRole, setPendingDemoRole] = useState<string | null>(null);
  const [isGoogleRedirecting, setIsGoogleRedirecting] = useState(false);
  const [isGoogleOAuthEnabled, setIsGoogleOAuthEnabled] = useState(false);
  const isRegister = mode === "register";

  useEffect(() => {
    let cancelled = false;
    getAuthConfigRequest()
      .then((config) => {
        if (!cancelled) {
          setIsGoogleOAuthEnabled(config.google_oauth_enabled);
        }
      })
      .catch(() => {
        // Fail closed: treat an unreachable config endpoint the same as
        // "not configured" rather than showing a button that cannot work.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setPassword("");
    setPasswordConfirm("");
    setShowPassword(false);
    setShowPasswordConfirm(false);
    setError(null);
    setOauthNotice(null);
  }, [mode]);

  useEffect(() => {
    const oauthStatus = new URLSearchParams(window.location.search).get("oauth");
    const messageByStatus: Record<
      string,
      { key: TranslationKey; tone: "info" | "warning" | "error" }
    > = {
      cancelled: { key: "auth.google.cancelled", tone: "info" },
      unavailable: { key: "auth.google.unavailable", tone: "warning" },
      invalid: { key: "auth.google.invalid", tone: "error" },
      conflict: { key: "auth.google.conflict", tone: "error" },
      blocked: { key: "auth.google.blocked", tone: "error" },
      failed: { key: "auth.google.failed", tone: "error" }
    };
    const notice = oauthStatus ? messageByStatus[oauthStatus] : undefined;
    if (notice) {
      setOauthNotice({ message: t(notice.key), tone: notice.tone });
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [t]);

  function localizedSubmitError(submitError: unknown, errorContext: "login" | "register" = mode) {
    let errorMessage = t("common.error.generic");

    if (submitError instanceof ApiError) {
      if (submitError.errorCode === "timeout") {
        errorMessage = t("common.error.timeout");
      } else if (submitError.errorCode === "network") {
        errorMessage = t("common.error.network");
      } else if (errorContext === "login" && submitError.status === 400) {
        // Login failures return a single backend validation message
        // ("Invalid email or password.") in English only; show a stable
        // localized message instead of leaking that raw text.
        errorMessage = t("auth.invalidCredentials");
      } else {
        errorMessage = getApiErrorMessage(submitError, errorMessage);
      }
    }

    // Map common backend errors to user-friendly messages
    if (typeof submitError === "object" && submitError !== null) {
      const errorData = Reflect.get(submitError, "data");
      if (typeof errorData === "object" && errorData !== null) {
        if (Reflect.has(errorData, "email") && errorContext === "register") {
          errorMessage = t("auth.emailAlreadyExists");
        }
      }
    }

    return errorMessage;
  }

  function completeAuth() {
    if (onAuthenticated) {
      onAuthenticated();
    } else {
      router.replace("/dashboard");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setOauthNotice(null);

    // Validate form before submission
    if (!email) {
      setError(t("auth.error.emailRequired"));
      return;
    }
    if (!password) {
      setError(t("auth.error.passwordRequired"));
      return;
    }
    if (isRegister && !fullName) {
      setError(t("auth.error.fullNameRequired"));
      return;
    }

    if (isRegister && password !== passwordConfirm) {
      setError(t("auth.passwordMismatch"));
      return;
    }

    if (isRegister && password.length < 8) {
      setError(t("auth.passwordTooShort"));
      return;
    }

    setIsSubmitting(true);

    try {
      if (isRegister) {
        await register({
          email,
          full_name: fullName,
          password,
          password_confirm: passwordConfirm
        });
      } else {
        await login({ email, password });
      }
      completeAuth();
    } catch (submitError) {
      setError(localizedSubmitError(submitError));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDemoLogin(account: (typeof DEMO_ACCOUNTS)[number]) {
    if (isSubmitting) return;
    setEmail(account.email);
    setPassword(DEMO_PASSWORD);
    setPasswordConfirm("");
    setError(null);
    setOauthNotice(null);
    setPendingDemoRole(account.role);
    setIsSubmitting(true);

    try {
      await login({ email: account.email, password: DEMO_PASSWORD });
      completeAuth();
    } catch (submitError) {
      setError(localizedSubmitError(submitError, "login"));
    } finally {
      setPendingDemoRole(null);
      setIsSubmitting(false);
    }
  }

  function handleGoogleLogin() {
    if (isSubmitting || isGoogleRedirecting) return;
    setError(null);
    setOauthNotice(null);
    setIsGoogleRedirecting(true);
    try {
      window.location.assign(getGoogleOAuthStartUrl());
    } catch {
      setIsGoogleRedirecting(false);
      setError(t("auth.google.failed"));
    }
  }

  return (
    <Card className="w-full max-w-md p-6 sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-hover">
        {isRegister ? t("auth.register.eyebrow") : t("auth.login.eyebrow")}
      </p>
      <h1 className="mt-2 text-3xl font-semibold">
        {isRegister ? t("auth.register.title") : t("auth.login.title")}
      </h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        {isRegister ? t("auth.register.description") : t("auth.login.description")}
      </p>
      {isRegister ? (
        <p className="mt-2 text-xs font-semibold text-muted-foreground">
          {t("auth.register.allRequired")}
        </p>
      ) : null}

      {oauthNotice ? (
        <div
          className={cn(
            "mt-5 flex items-start gap-2 rounded-sm border p-3 text-sm",
            oauthNotice.tone === "info" && "border-accent/35 bg-accent/10 text-foreground",
            oauthNotice.tone === "warning" && "border-warning/35 bg-warning/10 text-warning",
            oauthNotice.tone === "error" && "border-danger/35 bg-danger/10 text-danger"
          )}
          role={oauthNotice.tone === "error" ? "alert" : "status"}
        >
          <AppIcon className="mt-0.5" icon={CircleAlert} />
          <span>{oauthNotice.message}</span>
        </div>
      ) : null}

      <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
        {isRegister ? (
          <label className="block text-sm font-semibold">
            {t("auth.fullName")}
            <span className="relative block">
              <AppIcon className="absolute bottom-3 left-3 text-muted-foreground" icon={UserRound} />
              <input
                autoComplete="name"
                className={cn(fieldClassName, "pl-10")}
                maxLength={180}
                onChange={(event) => setFullName(event.target.value)}
                required
                type="text"
                value={fullName}
              />
            </span>
          </label>
        ) : null}

        <label className="block text-sm font-semibold">
          {t("auth.email")}
          <span className="relative block">
            <AppIcon className="absolute bottom-3 left-3 text-muted-foreground" icon={Mail} />
            <input
              autoComplete="email"
              className={cn(fieldClassName, "pl-10")}
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </span>
        </label>

        <div>
          <label className="block text-sm font-semibold" htmlFor="auth-password">
            {t("auth.password")}
          </label>
          <span className="relative block">
            <AppIcon className="absolute bottom-3 left-3 text-muted-foreground" icon={LockKeyhole} />
            <input
              autoComplete={isRegister ? "new-password" : "current-password"}
              className={cn(fieldClassName, "pl-10 pr-11")}
              id="auth-password"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type={showPassword ? "text" : "password"}
              value={password}
            />
            <IconButton
              className="absolute bottom-0 right-0 size-10 min-h-10"
              label={t(showPassword ? "auth.hidePassword" : "auth.showPassword")}
              onClick={() => setShowPassword((current) => !current)}
            >
              <AppIcon icon={showPassword ? EyeOff : Eye} />
            </IconButton>
          </span>
          {isRegister ? (
            <span className="mt-1.5 block text-xs font-normal leading-5 text-muted-foreground">
              {t("auth.passwordHelp")}
            </span>
          ) : null}
        </div>

        {isRegister ? (
          <div>
            <label className="block text-sm font-semibold" htmlFor="auth-password-confirm">
              {t("auth.confirmPassword")}
            </label>
            <span className="relative block">
              <AppIcon className="absolute bottom-3 left-3 text-muted-foreground" icon={LockKeyhole} />
              <input
                autoComplete="new-password"
                className={cn(fieldClassName, "pl-10 pr-11")}
                id="auth-password-confirm"
                minLength={8}
                onChange={(event) => setPasswordConfirm(event.target.value)}
                required
                type={showPasswordConfirm ? "text" : "password"}
                value={passwordConfirm}
              />
              <IconButton
                className="absolute bottom-0 right-0 size-10 min-h-10"
                label={t(showPasswordConfirm ? "auth.hidePassword" : "auth.showPassword")}
                onClick={() => setShowPasswordConfirm((current) => !current)}
              >
                <AppIcon icon={showPasswordConfirm ? EyeOff : Eye} />
              </IconButton>
            </span>
          </div>
        ) : null}

        {error ? (
          <p
            className="flex items-start gap-2 rounded-sm border border-danger/35 bg-danger/10 p-3 text-sm text-danger"
            role="alert"
          >
            <AppIcon className="mt-0.5" icon={CircleAlert} />
            <span>{error}</span>
          </p>
        ) : null}

        <Button className="w-full" disabled={isSubmitting} type="submit">
          <AppIcon
            className={cn("mr-2", isSubmitting && "animate-spin motion-reduce:animate-none")}
            icon={isSubmitting ? LoaderCircle : isRegister ? UserPlus : LogIn}
          />
          {isSubmitting ? t("auth.pleaseWait") : isRegister ? t("auth.createAccount") : t("auth.signIn")}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3" aria-hidden>
        <span className="h-px flex-1 bg-border" />
        <span className="text-xs font-semibold uppercase text-muted-foreground">
          {t("auth.google.or")}
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <Button
        aria-describedby={isGoogleOAuthEnabled ? undefined : "google-oauth-unavailable-note"}
        aria-label={t("auth.google.continue")}
        className="w-full"
        disabled={!isGoogleOAuthEnabled || isSubmitting || isGoogleRedirecting}
        onClick={handleGoogleLogin}
        type="button"
        variant="secondary"
      >
        {isGoogleRedirecting ? (
          <AppIcon className="mr-2 animate-spin motion-reduce:animate-none" icon={LoaderCircle} />
        ) : (
          <GoogleIcon className="mr-2" />
        )}
        <span>{isGoogleRedirecting ? t("auth.google.redirecting") : t("auth.google.continue")}</span>
      </Button>
      <p className="mt-2 text-xs leading-5 text-muted-foreground" id="google-oauth-unavailable-note">
        {isGoogleOAuthEnabled ? t("auth.google.securityNote") : t("auth.google.unavailable")}
      </p>

      <div className="mt-5 border-t pt-5">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
          {t("auth.demo.title")}
        </p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {t("auth.demo.description")}
        </p>
        <div className="mt-3 grid gap-2">
          {DEMO_ACCOUNTS.map((account) => (
            <Button
              disabled={isSubmitting}
              key={account.email}
              onClick={() => void handleDemoLogin(account)}
              size="sm"
              type="button"
              variant="secondary"
            >
              <AppIcon
                className={cn(
                  "mr-2",
                  pendingDemoRole === account.role && "animate-spin motion-reduce:animate-none"
                )}
                icon={pendingDemoRole === account.role ? LoaderCircle : UserRound}
              />
              {pendingDemoRole === account.role ? t("auth.pleaseWait") : t(account.labelKey)}
            </Button>
          ))}
        </div>
        <p className="mt-3 rounded-sm border border-warning/30 bg-warning/10 p-2 text-xs leading-5 text-warning">
          {t("auth.demo.warning")}
        </p>
      </div>

      {showModeLink ? (
        <p className="mt-5 text-center text-sm text-muted-foreground">
          {isRegister ? t("auth.alreadyRegistered") : t("auth.newToUniWay")}{" "}
          {onModeChange ? (
            <button
              className="font-semibold text-primary-hover hover:underline"
              onClick={() => onModeChange(isRegister ? "login" : "register")}
              type="button"
            >
              {isRegister ? t("auth.signIn") : t("auth.createAccount")}
            </button>
          ) : (
            <Link
              className="font-semibold text-primary-hover hover:underline"
              href={isRegister ? "/login" : "/register"}
            >
              {isRegister ? t("auth.signIn") : t("auth.createAccount")}
            </Link>
          )}
        </p>
      ) : null}
    </Card>
  );
}
