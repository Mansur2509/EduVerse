"use client";

import { MessageCircle, X } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { createFeedbackRequest } from "@/features/feedback";
import { useI18n } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";

import { Button } from "./button";
import { fieldClassName } from "./field";

export const SUPPORT_URL = "https://t.me/Otvet_mne_uje_nakonec";
const FEEDBACK_STORAGE_KEY = "eduverse.feedback.local.v1";
const FEEDBACK_TYPES = ["issue", "idea", "confusing", "data"] as const;

type FeedbackType = (typeof FEEDBACK_TYPES)[number];
// "success": submitted to the backend, visible to admins.
// "localFallback": the backend call failed; saved on this device only, NOT
// submitted to the team — the UI must say so explicitly rather than implying
// it was received.
// "error": could not even save locally.
type FeedbackStatus = "success" | "localFallback" | "error" | null;

type StoredFeedback = {
  id: string;
  createdAt: string;
  type: FeedbackType;
  page: string;
  message: string;
  contact: string;
};

export function SupportLink({ className }: { className?: string }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<FeedbackType>("issue");
  const [page, setPage] = useState(pathname || "");
  const [message, setMessage] = useState("");
  const [contact, setContact] = useState("");
  const [status, setStatus] = useState<FeedbackStatus>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function openDialog() {
    setPage(pathname || "");
    setStatus(null);
    setIsOpen(true);
  }

  function closeDialog() {
    setIsOpen(false);
    setStatus(null);
  }

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
        setStatus(null);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  function saveLocallyOnly(): boolean {
    try {
      const existing = window.localStorage.getItem(FEEDBACK_STORAGE_KEY);
      const parsed = existing ? (JSON.parse(existing) as StoredFeedback[]) : [];
      const nextItem: StoredFeedback = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        createdAt: new Date().toISOString(),
        type: feedbackType,
        page: page.trim(),
        message: message.trim(),
        contact: contact.trim()
      };
      window.localStorage.setItem(
        FEEDBACK_STORAGE_KEY,
        JSON.stringify([nextItem, ...parsed].slice(0, 25))
      );
      return true;
    } catch {
      return false;
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!message.trim()) {
      setStatus("error");
      return;
    }

    setIsSubmitting(true);
    setStatus(null);
    try {
      await createFeedbackRequest({
        feedback_type: feedbackType,
        page_module: page.trim(),
        message: message.trim(),
        contact: contact.trim()
      });
      setMessage("");
      setContact("");
      setStatus("success");
    } catch {
      // Backend unreachable or rejected the request: never claim it was
      // submitted. Fall back to a local-only save and say so plainly.
      if (saveLocallyOnly()) {
        setMessage("");
        setContact("");
        setStatus("localFallback");
      } else {
        setStatus("error");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <button
        className={cn(
          "inline-flex min-h-9 items-center gap-2 rounded-sm border bg-surface px-3 text-xs font-semibold text-muted-foreground transition hover:border-primary/35 hover:text-foreground",
          className
        )}
        onClick={openDialog}
        type="button"
      >
        <MessageCircle aria-hidden className="size-4" />
        {t("support.link")}
      </button>

      {isOpen ? (
        <div
          aria-modal="true"
          className="fixed inset-0 z-50 grid place-items-center bg-navy/55 p-4"
          role="dialog"
        >
          <div className="max-h-[calc(100vh-2rem)] w-full max-w-lg overflow-y-auto rounded-sm border bg-card p-5 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                  {t("support.eyebrow")}
                </p>
                <h2 className="mt-1 text-xl font-semibold">{t("support.title")}</h2>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  {t("support.description")}
                </p>
                <p className="mt-2 text-xs font-semibold text-muted-foreground">
                  {t("support.requiredLegend")}
                </p>
              </div>
              <button
                aria-label={t("support.close")}
                className="rounded-sm p-1 text-muted-foreground hover:bg-elevated hover:text-foreground"
                onClick={closeDialog}
                type="button"
              >
                <X aria-hidden className="size-4" />
              </button>
            </div>

            <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
              <label className="block">
                <span className="text-xs font-semibold">{t("support.type")}</span>
                <select
                  className={fieldClassName}
                  onChange={(event) => setFeedbackType(event.target.value as FeedbackType)}
                  value={feedbackType}
                >
                  {FEEDBACK_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {t(`support.type.${type}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-xs font-semibold">{t("support.page")}</span>
                <input
                  className={fieldClassName}
                  maxLength={160}
                  onChange={(event) => setPage(event.target.value)}
                  placeholder={t("support.pagePlaceholder")}
                  value={page}
                />
              </label>
              <label className="block">
                <span className="text-xs font-semibold">
                  {t("support.message")}
                  <span aria-hidden className="ml-0.5 text-primary-hover">
                    *
                  </span>
                </span>
                <textarea
                  className={`${fieldClassName} min-h-28 resize-y py-2 leading-5`}
                  maxLength={1500}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder={t("support.messagePlaceholder")}
                  required
                  value={message}
                />
                <span className="mt-1 block text-right text-[0.68rem] text-muted-foreground">
                  {message.length}/1500
                </span>
              </label>
              <label className="block">
                <span className="text-xs font-semibold">{t("support.contact")}</span>
                <input
                  className={fieldClassName}
                  maxLength={180}
                  onChange={(event) => setContact(event.target.value)}
                  placeholder={t("support.contactPlaceholder")}
                  value={contact}
                />
              </label>

              <p className="rounded-sm border border-warning/30 bg-warning/10 p-2 text-xs leading-5 text-warning">
                {t("support.privacy")}
              </p>

              {status === "success" ? (
                <p className="rounded-sm border border-success/35 bg-success/10 p-2 text-xs text-success">
                  {t("support.success")}
                </p>
              ) : null}
              {status === "localFallback" ? (
                <p className="rounded-sm border border-warning/35 bg-warning/10 p-2 text-xs text-warning">
                  {t("support.localFallback")}
                </p>
              ) : null}
              {status === "error" ? (
                <p className="rounded-sm border border-danger/35 bg-danger/10 p-2 text-xs text-danger">
                  {t("support.error")}
                </p>
              ) : null}

              <div className="flex flex-wrap justify-between gap-2 border-t pt-3">
                <Button asChild size="sm" variant="ghost">
                  <a href={SUPPORT_URL} rel="noreferrer" target="_blank">
                    {t("support.openChat")}
                  </a>
                </Button>
                <div className="flex gap-2">
                  <Button disabled={isSubmitting} onClick={closeDialog} size="sm" type="button" variant="ghost">
                    {t("common.actions.cancel")}
                  </Button>
                  <Button disabled={isSubmitting} size="sm" type="submit">
                    {isSubmitting ? t("support.submitting") : t("support.submit")}
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
