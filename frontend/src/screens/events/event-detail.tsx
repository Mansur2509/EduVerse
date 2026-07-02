"use client";

import {
  CalendarClock,
  ExternalLink,
  MapPin,
  Monitor,
  Users,
  WalletCards
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useState } from "react";

import type { EventDetails, EventFormField } from "@/entities/event";
import { useAuth } from "@/features/auth/model/auth-context";
import {
  cancelEventRegistrationRequest,
  getEventRequest,
  registerForEventRequest
} from "@/features/events";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";

function priceText(event: EventDetails, t: ReturnType<typeof useI18n>["t"]) {
  if (event.price_type === "paid" && event.price_amount) {
    return t("events.price.amount", {
      amount: event.price_amount,
      currency: event.currency
    });
  }
  return t(`events.price.${event.price_type}` as TranslationKey);
}

export function EventDetailScreen({ slug }: { slug: string }) {
  const router = useRouter();
  const { user } = useAuth();
  const { locale, t } = useI18n();
  const [event, setEvent] = useState<EventDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [actionError, setActionError] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<"registered" | "cancelled" | null>(null);
  const [registrationAnswers, setRegistrationAnswers] = useState<Record<string, unknown>>({});

  const loadEvent = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      setEvent(await getEventRequest(slug));
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void loadEvent();
  }, [loadEvent]);

  async function handleRegistration() {
    if (!user) {
      router.push("/login");
      return;
    }

    setIsSubmitting(true);
    setActionError(false);
    setActionSuccess(null);
    try {
      if (event?.registration_status) {
        await cancelEventRegistrationRequest(slug);
        setActionSuccess("cancelled");
      } else {
        await registerForEventRequest(slug, registrationAnswers);
        setActionSuccess("registered");
        setRegistrationAnswers({});
      }
      setEvent(await getEventRequest(slug));
    } catch {
      setActionError(true);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">{t("events.states.loadingDetail")}</p>
      </Card>
    );
  }

  if (hasError || !event) {
    return (
      <Card>
        <p className="text-sm text-danger" role="alert">
          {t("events.states.detailError")}
        </p>
        <Button className="mt-4" onClick={() => void loadEvent()} type="button">
          {t("events.actions.retry")}
        </Button>
      </Card>
    );
  }

  const isRegistered = Boolean(event.registration_status);

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>{event.category.name}</Badge>
          {event.registration_status ? (
            <span className="rounded-sm border border-success/30 bg-success/10 px-2.5 py-1 text-xs font-semibold text-success">
              {t(
                `events.registration.status.${event.registration_status}` as TranslationKey
              )}
            </span>
          ) : null}
        </div>
        <h1 className="mt-5 max-w-4xl text-3xl font-semibold sm:text-5xl">{event.title}</h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
          {event.short_description}
        </p>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-6">
          <Card>
            <h2 className="text-2xl font-semibold">{t("events.detail.about")}</h2>
            <p className="mt-4 whitespace-pre-line text-sm leading-7 text-muted-foreground">
              {event.description}
            </p>
          </Card>

          <Card>
            <h2 className="text-2xl font-semibold">{t("events.detail.information")}</h2>
            <dl className="mt-5 grid gap-5 sm:grid-cols-2">
              <DetailItem icon={CalendarClock} label={t("events.fields.start")}>
                {formatDateTime(event.start_at, locale)}
              </DetailItem>
              <DetailItem icon={CalendarClock} label={t("events.fields.end")}>
                {event.end_at ? formatDateTime(event.end_at, locale) : t("events.value.notSet")}
              </DetailItem>
              <DetailItem
                icon={event.is_online ? Monitor : MapPin}
                label={t("events.fields.location")}
              >
                {event.is_online
                  ? t("events.location.online")
                  : [event.location.venue, event.location.city, event.location.country]
                      .filter(Boolean)
                      .join(", ")}
              </DetailItem>
              <DetailItem icon={WalletCards} label={t("events.fields.price")}>
                {priceText(event, t)}
              </DetailItem>
              <DetailItem icon={Users} label={t("events.fields.capacity")}>
                {event.spots_left === null
                  ? t("events.value.unlimited")
                  : t("events.spotsLeft", { count: event.spots_left })}
              </DetailItem>
              <DetailItem icon={CalendarClock} label={t("events.fields.deadline")}>
                {event.registration_deadline
                  ? formatDateTime(event.registration_deadline, locale)
                  : t("events.value.notSet")}
              </DetailItem>
            </dl>
          </Card>
        </div>

        <aside className="space-y-5">
          <Card className="bg-elevated/55">
            <h2 className="text-xl font-semibold">{t("events.detail.registration")}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {isRegistered
                ? t("events.registration.currentStatus", {
                    status: t(
                      `events.registration.status.${event.registration_status}` as TranslationKey
                    )
                  })
                : t("events.registration.profileSnapshot")}
            </p>
            {!isRegistered && event.registration_form_fields.length > 0 ? (
              <div className="mt-5 space-y-4">
                <div>
                  <h3 className="text-sm font-semibold">
                    {t("events.registration.customFormTitle")}
                  </h3>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {t("events.registration.customFormDescription")}
                  </p>
                  {event.registration_form_fields.some((field) => field.is_required) ? (
                    <p className="mt-1 text-xs font-semibold text-muted-foreground">
                      {t("events.registration.requiredLegend")}
                    </p>
                  ) : null}
                </div>
                {event.registration_form_fields.map((field) => (
                  <RegistrationField
                    field={field}
                    key={field.id}
                    onChange={(value) =>
                      setRegistrationAnswers((current) => ({
                        ...current,
                        [String(field.id)]: value
                      }))
                    }
                    t={t}
                    value={registrationAnswers[String(field.id)]}
                  />
                ))}
              </div>
            ) : null}
            {event.registration_ticket ? (
              <div className="mt-5 rounded-sm border bg-elevated/60 p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                  {t("events.ticket.title")}
                </p>
                <p className="mt-2 break-all font-mono text-xs">
                  {event.registration_ticket.code}
                </p>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  {t("events.ticket.doNotShare")}
                </p>
              </div>
            ) : null}
            <Button
              className="mt-5 w-full"
              disabled={isSubmitting}
              onClick={() => void handleRegistration()}
              type="button"
              variant={isRegistered ? "secondary" : "primary"}
            >
              {isSubmitting
                ? t("events.actions.working")
                : isRegistered
                  ? t("events.actions.cancelRegistration")
                  : user
                    ? t("events.actions.register")
                    : t("events.actions.loginToRegister")}
            </Button>
            {actionError ? (
              <p className="mt-4 text-sm text-danger" role="alert">
                {t("events.registration.actionError")}
              </p>
            ) : null}
            {actionSuccess ? (
              <p className="mt-4 text-sm text-success" role="status">
                {t(`events.registration.${actionSuccess}` as TranslationKey)}
              </p>
            ) : null}
          </Card>

          <Card>
            <h2 className="text-lg font-semibold">{t("events.fields.organizer")}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{event.organizer_name}</p>
            <a
              className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-primary-hover hover:underline"
              href={event.source.source_url}
              rel="noreferrer"
              target="_blank"
            >
              {t("events.actions.officialSource")}
              <ExternalLink aria-hidden className="size-4" />
            </a>
          </Card>
        </aside>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button asChild variant="secondary">
          <Link href="/events">{t("events.actions.backToEvents")}</Link>
        </Button>
        <Button asChild variant="ghost">
          <Link href="/events/my">{t("events.actions.myEvents")}</Link>
        </Button>
      </div>
      <p className="text-xs leading-5 text-muted-foreground">{t("events.disclaimer")}</p>
    </div>
  );
}

function RegistrationField({
  field,
  value,
  onChange,
  t
}: {
  field: EventFormField;
  value: unknown;
  onChange: (value: unknown) => void;
  t: ReturnType<typeof useI18n>["t"];
}) {
  const labelNode = (
    <>
      {field.label}
      {field.is_required ? (
        <span aria-hidden className="ml-0.5 text-primary-hover">
          *
        </span>
      ) : null}
    </>
  );
  const stringValue = typeof value === "string" ? value : "";

  if (field.field_type === "long_text") {
    return (
      <label className="block">
        <span className="text-sm font-semibold">{labelNode}</span>
        <textarea
          className={`${fieldClassName} min-h-28 py-3`}
          onChange={(event) => onChange(event.target.value)}
          required={field.is_required}
          value={stringValue}
        />
        {field.help_text ? <FieldHelp text={field.help_text} /> : null}
      </label>
    );
  }

  if (field.field_type === "single_choice") {
    return (
      <label className="block">
        <span className="text-sm font-semibold">{labelNode}</span>
        <select
          className={fieldClassName}
          onChange={(event) => onChange(event.target.value)}
          required={field.is_required}
          value={stringValue}
        >
          <option value="">{t("events.registration.chooseOption")}</option>
          {field.choices.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>
        {field.help_text ? <FieldHelp text={field.help_text} /> : null}
      </label>
    );
  }

  if (field.field_type === "multiple_choice") {
    const selectedValues = Array.isArray(value)
      ? value.filter((item): item is string => typeof item === "string")
      : [];
    return (
      <fieldset>
        <legend className="text-sm font-semibold">{labelNode}</legend>
        <div className="mt-2 space-y-2">
          {field.choices.map((choice) => (
            <label className="flex items-center gap-2 text-sm" key={choice}>
              <input
                checked={selectedValues.includes(choice)}
                onChange={(event) => {
                  onChange(
                    event.target.checked
                      ? [...selectedValues, choice]
                      : selectedValues.filter((item) => item !== choice)
                  );
                }}
                type="checkbox"
              />
              {choice}
            </label>
          ))}
        </div>
        {field.help_text ? <FieldHelp text={field.help_text} /> : null}
      </fieldset>
    );
  }

  const inputType =
    field.field_type === "number"
      ? "number"
      : field.field_type === "date"
        ? "date"
        : field.field_type === "email"
          ? "email"
          : field.field_type === "url"
            ? "url"
            : "text";

  return (
    <label className="block">
      <span className="text-sm font-semibold">{labelNode}</span>
      <input
        className={fieldClassName}
        onChange={(event) => onChange(event.target.value)}
        required={field.is_required}
        type={inputType}
        value={stringValue}
      />
      {field.help_text ? <FieldHelp text={field.help_text} /> : null}
    </label>
  );
}

function FieldHelp({ text }: { text: string }) {
  return <span className="mt-1 block text-xs leading-5 text-muted-foreground">{text}</span>;
}

function DetailItem({
  icon: Icon,
  label,
  children
}: {
  icon: typeof CalendarClock;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
      <div>
        <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          {label}
        </dt>
        <dd className="mt-1 text-sm">{children}</dd>
      </div>
    </div>
  );
}
