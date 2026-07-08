"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { ApiError, getApiErrorMessage } from "@/shared/api/client";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";

import { useAuth } from "../model/auth-context";

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
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pendingDemoRole, setPendingDemoRole] = useState<string | null>(null);
  const isRegister = mode === "register";

  useEffect(() => {
    setPassword("");
    setPasswordConfirm("");
    setError(null);
  }, [mode]);

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

      <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
        {isRegister ? (
          <label className="block text-sm font-semibold">
            {t("auth.fullName")}
            <input
              autoComplete="name"
              className={fieldClassName}
              maxLength={180}
              onChange={(event) => setFullName(event.target.value)}
              required
              type="text"
              value={fullName}
            />
          </label>
        ) : null}

        <label className="block text-sm font-semibold">
          {t("auth.email")}
          <input
            autoComplete="email"
            className={fieldClassName}
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>

        <label className="block text-sm font-semibold">
          {t("auth.password")}
          <input
            autoComplete={isRegister ? "new-password" : "current-password"}
            className={fieldClassName}
            minLength={8}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          {isRegister ? (
            <span className="mt-1.5 block text-xs font-normal leading-5 text-muted-foreground">
              {t("auth.passwordHelp")}
            </span>
          ) : null}
        </label>

        {isRegister ? (
          <label className="block text-sm font-semibold">
            {t("auth.confirmPassword")}
            <input
              autoComplete="new-password"
              className={fieldClassName}
              minLength={8}
              onChange={(event) => setPasswordConfirm(event.target.value)}
              required
              type="password"
              value={passwordConfirm}
            />
          </label>
        ) : null}

        {error ? (
          <p
            className="rounded-sm border border-danger/35 bg-danger/10 p-3 text-sm text-danger"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <Button className="w-full" disabled={isSubmitting} type="submit">
          {isSubmitting
            ? t("auth.pleaseWait")
            : isRegister
              ? t("auth.createAccount")
              : t("auth.signIn")}
        </Button>
      </form>

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
