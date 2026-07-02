"use client";

import { ArrowDown, ArrowUp, Plus, Send, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useState
} from "react";

import {
  ModerationStatusBadge,
  type EventCategory,
  type EventFormField,
  type EventFormFieldType,
  type OrganizerEvent,
  type OrganizerEventInput
} from "@/entities/event";
import {
  createOrganizerEventRequest,
  getOrganizerEventCategoriesRequest,
  getOrganizerEventFormRequest,
  getOrganizerEventRequest,
  saveOrganizerEventFormRequest,
  submitOrganizerEventRequest,
  updateOrganizerEventRequest
} from "@/features/organizer-events";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { UnsavedChangesDialog } from "@/shared/ui/unsaved-changes-dialog";

type EventFormState = {
  title: string;
  shortDescription: string;
  description: string;
  categorySlug: string;
  organizerName: string;
  format: OrganizerEvent["format"];
  onlineUrl: string;
  startAt: string;
  endAt: string;
  registrationDeadline: string;
  capacity: string;
  priceType: OrganizerEvent["price_type"];
  priceAmount: string;
  currency: string;
  visibility: OrganizerEvent["visibility"];
  coverImageUrl: string;
  language: string;
  eligibility: string;
  country: string;
  city: string;
  venue: string;
  officialSourceUrl: string;
};

const emptyForm: EventFormState = {
  title: "",
  shortDescription: "",
  description: "",
  categorySlug: "",
  organizerName: "",
  format: "offline",
  onlineUrl: "",
  startAt: "",
  endAt: "",
  registrationDeadline: "",
  capacity: "",
  priceType: "free",
  priceAmount: "",
  currency: "",
  visibility: "public",
  coverImageUrl: "",
  language: "",
  eligibility: "",
  country: "",
  city: "",
  venue: "",
  officialSourceUrl: ""
};

const formFieldTypes: EventFormFieldType[] = [
  "short_text",
  "long_text",
  "single_choice",
  "multiple_choice",
  "number",
  "date",
  "email",
  "phone",
  "telegram",
  "url"
];

function toDateTimeInput(value: string | null) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 16);
}

function fromEvent(event: OrganizerEvent): EventFormState {
  return {
    title: event.title,
    shortDescription: event.short_description,
    description: event.description,
    categorySlug: event.category.slug,
    organizerName: event.organizer_name,
    format: event.format,
    onlineUrl: event.online_url,
    startAt: toDateTimeInput(event.start_at),
    endAt: toDateTimeInput(event.end_at),
    registrationDeadline: toDateTimeInput(event.registration_deadline),
    capacity: event.capacity?.toString() ?? "",
    priceType: event.price_type,
    priceAmount: event.price_amount ?? "",
    currency: event.currency,
    visibility: event.visibility,
    coverImageUrl: event.cover_image_url,
    language: event.language,
    eligibility: event.eligibility,
    country: event.location.country,
    city: event.location.city,
    venue: event.location.venue,
    officialSourceUrl: event.source.source_url
  };
}

function toApiInput(form: EventFormState): OrganizerEventInput {
  const isOnline = form.format === "online" || form.format === "hybrid";
  return {
    title: form.title.trim(),
    short_description: form.shortDescription.trim(),
    description: form.description.trim(),
    category_slug: form.categorySlug,
    organizer_name: form.organizerName.trim(),
    format: form.format,
    is_online: isOnline,
    online_url: isOnline ? form.onlineUrl.trim() : "",
    start_at: new Date(form.startAt).toISOString(),
    end_at: form.endAt ? new Date(form.endAt).toISOString() : null,
    registration_deadline: form.registrationDeadline
      ? new Date(form.registrationDeadline).toISOString()
      : null,
    capacity: form.capacity ? Number(form.capacity) : null,
    price_type: form.priceType,
    price_amount:
      form.priceType === "paid" && form.priceAmount
        ? form.priceAmount
        : null,
    currency: form.priceType === "paid" ? form.currency.trim().toUpperCase() : "",
    visibility: form.visibility,
    cover_image_url: form.coverImageUrl.trim(),
    language: form.language.trim(),
    eligibility: form.eligibility.trim(),
    location: {
      country: form.country.trim(),
      city: form.city.trim(),
      venue: form.venue.trim(),
      latitude: null,
      longitude: null
    },
    source: {
      source_title: form.title.trim(),
      source_url: form.officialSourceUrl.trim(),
      is_official: true
    }
  };
}

export function OrganizerEventFormScreen({ slug }: { slug?: string }) {
  const router = useRouter();
  const { t } = useI18n();
  const [form, setForm] = useState<EventFormState>(emptyForm);
  const [savedForm, setSavedForm] = useState<EventFormState>(emptyForm);
  const [categories, setCategories] = useState<EventCategory[]>([]);
  const [event, setEvent] = useState<OrganizerEvent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setLoadError(false);
    try {
      const [categoryResponse, eventResponse] = await Promise.all([
        getOrganizerEventCategoriesRequest(),
        slug ? getOrganizerEventRequest(slug) : Promise.resolve(null)
      ]);
      setCategories(categoryResponse);
      if (eventResponse) {
        setEvent(eventResponse);
        const nextForm = fromEvent(eventResponse);
        setForm(nextForm);
        setSavedForm(nextForm);
      } else if (categoryResponse[0]) {
        const nextForm = { ...emptyForm, categorySlug: categoryResponse[0].slug };
        setForm(nextForm);
        setSavedForm(nextForm);
      } else {
        setForm(emptyForm);
        setSavedForm(emptyForm);
      }
    } catch {
      setLoadError(true);
    } finally {
      setIsLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void load();
  }, [load]);

  function setField<Key extends keyof EventFormState>(
    field: Key,
    value: EventFormState[Key]
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const isEditable = !event || event.can_edit;
  const hasUnsavedChanges =
    isEditable && JSON.stringify(form) !== JSON.stringify(savedForm);
  const unsavedGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedChanges
  });

  async function saveEventDraft() {
    setIsSaving(true);
    setSaveError(false);
    setSaved(false);
    try {
      const input = toApiInput(form);
      const response =
        slug && event
          ? await updateOrganizerEventRequest(slug, input)
          : await createOrganizerEventRequest(input);
      setEvent(response);
      const nextForm = fromEvent(response);
      setForm(nextForm);
      setSavedForm(nextForm);
      setSaved(true);
      if (!slug) {
        router.replace(`/organizer/events/${response.slug}`);
      }
      return true;
    } catch {
      setSaveError(true);
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSave(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    await saveEventDraft();
  }

  async function handleSubmitForReview() {
    if (!event) {
      return;
    }
    if (!window.confirm(t("organizer.confirm.submit"))) {
      return;
    }
    setIsSubmitting(true);
    setSaveError(false);
    try {
      const response = await submitOrganizerEventRequest(event.slug);
      setEvent(response);
      setSaved(true);
    } catch {
      setSaveError(true);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">{t("organizer.form.loading")}</p>
      </Card>
    );
  }

  if (loadError) {
    return (
      <Card className="border-danger/35 bg-danger/10">
        <p className="text-sm text-danger" role="alert">
          {t("organizer.form.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void load()} type="button">
          {t("events.actions.retry")}
        </Button>
      </Card>
    );
  }

  const isOnline = form.format === "online" || form.format === "hybrid";
  const isPaid = form.priceType === "paid";

  return (
    <div className="space-y-6">
      <section className="rounded-sm border bg-card p-6 shadow-card sm:p-9">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
            {event ? t("organizer.form.editEyebrow") : t("organizer.form.newEyebrow")}
          </p>
          {event ? <ModerationStatusBadge status={event.status} /> : null}
        </div>
        <h1 className="mt-3 text-3xl font-semibold sm:text-5xl">
          {event ? t("organizer.form.editTitle") : t("organizer.form.newTitle")}
        </h1>
        <p className="mt-4 max-w-3xl leading-7 text-muted-foreground">
          {t("organizer.form.description")}
        </p>
        <p className="mt-2 text-xs font-semibold text-muted-foreground">
          {t("organizer.form.requiredLegend")}
        </p>
      </section>

      {!isEditable ? (
        <Card className="border-warning/30 bg-warning/10">
          <p className="text-sm text-warning">{t("organizer.form.readOnly")}</p>
        </Card>
      ) : null}

      <form className="space-y-6" onSubmit={handleSave}>
        <FormSection
          description={t("organizer.form.sections.basicsHelp")}
          title={t("organizer.form.sections.basics")}
        >
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.title")}
            onChange={(value) => setField("title", value)}
            required
            value={form.title}
          />
          <SelectField
            disabled={!isEditable}
            label={t("organizer.fields.category")}
            onChange={(value) => setField("categorySlug", value)}
            options={categories.map((category) => ({
              label: category.name,
              value: category.slug
            }))}
            required
            value={form.categorySlug}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.shortDescription")}
            maxLength={360}
            onChange={(value) => setField("shortDescription", value)}
            required
            value={form.shortDescription}
          />
          <TextAreaField
            disabled={!isEditable}
            label={t("organizer.fields.description")}
            onChange={(value) => setField("description", value)}
            required
            value={form.description}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.organizerName")}
            onChange={(value) => setField("organizerName", value)}
            required
            value={form.organizerName}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.language")}
            onChange={(value) => setField("language", value)}
            value={form.language}
          />
          <TextAreaField
            disabled={!isEditable}
            label={t("organizer.fields.eligibility")}
            onChange={(value) => setField("eligibility", value)}
            value={form.eligibility}
          />
        </FormSection>

        <FormSection
          description={t("organizer.form.sections.scheduleHelp")}
          title={t("organizer.form.sections.schedule")}
        >
          <SelectField
            disabled={!isEditable}
            label={t("organizer.fields.format")}
            onChange={(value) =>
              setField("format", value as OrganizerEvent["format"])
            }
            options={[
              { label: t("organizer.format.offline"), value: "offline" },
              { label: t("organizer.format.online"), value: "online" },
              { label: t("organizer.format.hybrid"), value: "hybrid" }
            ]}
            value={form.format}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.startAt")}
            onChange={(value) => setField("startAt", value)}
            required
            type="datetime-local"
            value={form.startAt}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.endAt")}
            onChange={(value) => setField("endAt", value)}
            type="datetime-local"
            value={form.endAt}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.registrationDeadline")}
            onChange={(value) => setField("registrationDeadline", value)}
            type="datetime-local"
            value={form.registrationDeadline}
          />
          <TextField
            disabled={!isEditable || !isOnline}
            label={t("organizer.fields.onlineUrl")}
            onChange={(value) => setField("onlineUrl", value)}
            required={isOnline}
            type="url"
            value={form.onlineUrl}
          />
        </FormSection>

        <FormSection
          description={t("organizer.form.sections.locationHelp")}
          title={t("organizer.form.sections.location")}
        >
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.country")}
            onChange={(value) => setField("country", value)}
            required
            value={form.country}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.city")}
            onChange={(value) => setField("city", value)}
            value={form.city}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.venue")}
            onChange={(value) => setField("venue", value)}
            value={form.venue}
          />
        </FormSection>

        <FormSection
          description={t("organizer.form.sections.accessHelp")}
          title={t("organizer.form.sections.access")}
        >
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.capacity")}
            min="1"
            onChange={(value) => setField("capacity", value)}
            type="number"
            value={form.capacity}
          />
          <SelectField
            disabled={!isEditable}
            label={t("organizer.fields.priceType")}
            onChange={(value) =>
              setField("priceType", value as OrganizerEvent["price_type"])
            }
            options={[
              { label: t("events.price.free"), value: "free" },
              { label: t("events.price.paid"), value: "paid" },
              { label: t("events.price.external"), value: "external" },
              { label: t("events.price.unknown"), value: "unknown" }
            ]}
            value={form.priceType}
          />
          <TextField
            disabled={!isEditable || !isPaid}
            label={t("organizer.fields.priceAmount")}
            min="0"
            onChange={(value) => setField("priceAmount", value)}
            required={isPaid}
            step="0.01"
            type="number"
            value={form.priceAmount}
          />
          <TextField
            disabled={!isEditable || !isPaid}
            label={t("organizer.fields.currency")}
            maxLength={3}
            onChange={(value) => setField("currency", value)}
            required={isPaid}
            value={form.currency}
          />
          <SelectField
            disabled={!isEditable}
            label={t("organizer.fields.visibility")}
            onChange={(value) =>
              setField("visibility", value as OrganizerEvent["visibility"])
            }
            options={[
              { label: t("organizer.visibility.public"), value: "public" },
              { label: t("organizer.visibility.private"), value: "private" }
            ]}
            value={form.visibility}
          />
          <p className="self-end text-xs leading-5 text-muted-foreground">
            {t("organizer.form.paymentPlaceholder")}
          </p>
        </FormSection>

        <FormSection
          description={t("organizer.form.sections.sourceHelp")}
          title={t("organizer.form.sections.source")}
        >
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.officialSourceUrl")}
            onChange={(value) => setField("officialSourceUrl", value)}
            required
            type="url"
            value={form.officialSourceUrl}
          />
          <TextField
            disabled={!isEditable}
            label={t("organizer.fields.coverImageUrl")}
            onChange={(value) => setField("coverImageUrl", value)}
            type="url"
            value={form.coverImageUrl}
          />
        </FormSection>

        {saveError ? (
          <Card className="border-danger/35 bg-danger/10">
            <p className="text-sm text-danger" role="alert">
              {t("organizer.form.saveError")}
            </p>
          </Card>
        ) : null}
        {saved ? (
          <p className="text-sm text-success" role="status">
            {t("organizer.form.saved")}
          </p>
        ) : null}

        <div className="flex flex-wrap gap-3">
          {isEditable ? (
            <Button disabled={isSaving || isSubmitting} type="submit">
              {isSaving
                ? t("organizer.actions.saving")
                : event
                  ? t("organizer.actions.save")
                  : t("organizer.actions.createDraft")}
            </Button>
          ) : null}
          {event?.can_submit ? (
            <Button
              disabled={isSaving || isSubmitting}
              onClick={() => void handleSubmitForReview()}
              type="button"
              variant="secondary"
            >
              <Send aria-hidden className="mr-2 size-4" />
              {isSubmitting
                ? t("organizer.actions.submitting")
                : t("organizer.actions.submit")}
            </Button>
          ) : null}
          <Button
            onClick={() =>
              unsavedGuard.requestLeave(() => router.push("/organizer/events"))
            }
            type="button"
            variant="ghost"
          >
            {t("organizer.actions.backToList")}
          </Button>
        </div>
      </form>
      {event ? (
        <EventRegistrationFormBuilder isEditable={isEditable} slug={event.slug} />
      ) : (
        <Card>
          <h2 className="text-2xl font-semibold">
            {t("organizer.formBuilder.title")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {t("organizer.formBuilder.createDraftFirst")}
          </p>
        </Card>
      )}
      <UnsavedChangesDialog
        description={t("common.unsaved.description")}
        isSaving={isSaving}
        leaveWithoutSavingLabel={t("common.unsaved.leaveWithoutSaving")}
        onLeaveWithoutSaving={unsavedGuard.leaveWithoutSaving}
        onSaveAndLeave={saveEventDraft}
        onStay={unsavedGuard.stay}
        open={unsavedGuard.isPromptOpen}
        saveAndLeaveLabel={t("common.unsaved.saveAndLeave")}
        stayLabel={t("common.unsaved.stay")}
        title={t("common.unsaved.title")}
      />
    </div>
  );
}

function createDraftField(order: number): EventFormField {
  return {
    id: -Date.now() - order,
    field_type: "short_text",
    label: "",
    help_text: "",
    is_required: false,
    order,
    choices: [],
    validation: {}
  };
}

function fieldNeedsChoices(fieldType: EventFormFieldType) {
  return fieldType === "single_choice" || fieldType === "multiple_choice";
}

function EventRegistrationFormBuilder({
  slug,
  isEditable
}: {
  slug: string;
  isEditable: boolean;
}) {
  const { t } = useI18n();
  const [fields, setFields] = useState<EventFormField[]>([]);
  const [savedFields, setSavedFields] = useState<EventFormField[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadFields = useCallback(async () => {
    setIsLoading(true);
    setLoadError(false);
    try {
      const response = await getOrganizerEventFormRequest(slug);
      setFields(response.fields);
      setSavedFields(response.fields);
    } catch {
      setLoadError(true);
    } finally {
      setIsLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void loadFields();
  }, [loadFields]);

  const hasUnsavedChanges =
    isEditable && JSON.stringify(fields) !== JSON.stringify(savedFields);
  const unsavedGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedChanges
  });

  function updateField<Key extends keyof EventFormField>(
    index: number,
    key: Key,
    value: EventFormField[Key]
  ) {
    setSaved(false);
    setFields((current) =>
      current.map((field, fieldIndex) => {
        if (fieldIndex !== index) {
          return field;
        }
        const nextField = { ...field, [key]: value };
        if (key === "field_type" && !fieldNeedsChoices(value as EventFormFieldType)) {
          nextField.choices = [];
        }
        return nextField;
      })
    );
  }

  function addField() {
    setSaved(false);
    setFields((current) => [...current, createDraftField(current.length)]);
  }

  function removeField(index: number) {
    setSaved(false);
    setFields((current) =>
      current.filter((_, fieldIndex) => fieldIndex !== index).map((field, order) => ({
        ...field,
        order
      }))
    );
  }

  function moveField(index: number, direction: -1 | 1) {
    setSaved(false);
    setFields((current) => {
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= current.length) {
        return current;
      }
      const next = [...current];
      [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
      return next.map((field, order) => ({ ...field, order }));
    });
  }

  async function saveFields() {
    setIsSaving(true);
    setSaveError(false);
    setSaved(false);
    try {
      const response = await saveOrganizerEventFormRequest(
        slug,
        fields.map((field, order) => ({ ...field, order }))
      );
      setFields(response.fields);
      setSavedFields(response.fields);
      setSaved(true);
      return true;
    } catch {
      setSaveError(true);
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">
          {t("organizer.formBuilder.loading")}
        </p>
      </Card>
    );
  }

  if (loadError) {
    return (
      <Card className="border-danger/35 bg-danger/10">
        <p className="text-sm text-danger" role="alert">
          {t("organizer.formBuilder.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void loadFields()} type="button">
          {t("events.actions.retry")}
        </Button>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div>
          <h2 className="text-2xl font-semibold">
            {t("organizer.formBuilder.title")}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            {t("organizer.formBuilder.description")}
          </p>
        </div>
        {isEditable ? (
          <Button onClick={addField} type="button" variant="secondary">
            <Plus aria-hidden className="mr-2 size-4" />
            {t("organizer.formBuilder.addField")}
          </Button>
        ) : null}
      </div>

      {fields.length === 0 ? (
        <div className="mt-6 rounded-sm border bg-elevated/55 p-5">
          <p className="text-sm font-semibold">
            {t("organizer.formBuilder.emptyTitle")}
          </p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {t("organizer.formBuilder.emptyDescription")}
          </p>
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          {fields.map((field, index) => (
            <div className="rounded-sm border bg-elevated/35 p-4" key={field.id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-semibold">
                  {t("organizer.formBuilder.fieldNumber", {
                    count: index + 1
                  })}
                </p>
                {isEditable ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={index === 0}
                      onClick={() => moveField(index, -1)}
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      <ArrowUp aria-hidden className="mr-1.5 size-3.5" />
                      {t("organizer.formBuilder.moveUp")}
                    </Button>
                    <Button
                      disabled={index === fields.length - 1}
                      onClick={() => moveField(index, 1)}
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      <ArrowDown aria-hidden className="mr-1.5 size-3.5" />
                      {t("organizer.formBuilder.moveDown")}
                    </Button>
                    <Button
                      className="text-danger"
                      onClick={() => removeField(index)}
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      <Trash2 aria-hidden className="mr-1.5 size-3.5" />
                      {t("organizer.formBuilder.remove")}
                    </Button>
                  </div>
                ) : null}
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <TextField
                  disabled={!isEditable}
                  label={t("organizer.formBuilder.fieldLabel")}
                  onChange={(value) => updateField(index, "label", value)}
                  required
                  value={field.label}
                />
                <SelectField
                  disabled={!isEditable}
                  label={t("organizer.formBuilder.fieldType")}
                  onChange={(value) =>
                    updateField(index, "field_type", value as EventFormFieldType)
                  }
                  options={formFieldTypes.map((fieldType) => ({
                    label: t(
                      `organizer.formBuilder.type.${fieldType}` as TranslationKey
                    ),
                    value: fieldType
                  }))}
                  value={field.field_type}
                />
                <TextField
                  disabled={!isEditable}
                  label={t("organizer.formBuilder.helpText")}
                  onChange={(value) => updateField(index, "help_text", value)}
                  value={field.help_text}
                />
                <label className="flex items-center gap-2 self-end text-sm font-semibold">
                  <input
                    checked={field.is_required}
                    disabled={!isEditable}
                    onChange={(event) =>
                      updateField(index, "is_required", event.target.checked)
                    }
                    type="checkbox"
                  />
                  {t("organizer.formBuilder.required")}
                </label>
                {fieldNeedsChoices(field.field_type) ? (
                  <label className="block md:col-span-2">
                    <span className="text-sm font-semibold">
                      {t("organizer.formBuilder.choices")}
                    </span>
                    <textarea
                      className={`${fieldClassName} min-h-24 py-3`}
                      disabled={!isEditable}
                      onChange={(event) =>
                        updateField(
                          index,
                          "choices",
                          event.target.value
                            .split("\n")
                            .map((choice) => choice.trim())
                            .filter(Boolean)
                        )
                      }
                      value={field.choices.join("\n")}
                    />
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {t("organizer.formBuilder.choicesHelp")}
                    </span>
                  </label>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}

      {fields.length > 0 ? (
        <div className="mt-6 rounded-sm border bg-card p-4">
          <h3 className="text-lg font-semibold">
            {t("organizer.formBuilder.previewTitle")}
          </h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {fields.map((field) => (
              <div className="rounded-sm border bg-elevated/35 p-3" key={`preview-${field.id}`}>
                <p className="text-sm font-semibold">
                  {field.label || t("organizer.formBuilder.untitledField")}
                  {field.is_required ? " *" : ""}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t(`organizer.formBuilder.type.${field.field_type}` as TranslationKey)}
                </p>
                {field.help_text ? (
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    {field.help_text}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {saveError ? (
        <p className="mt-4 text-sm text-danger" role="alert">
          {t("organizer.formBuilder.saveError")}
        </p>
      ) : null}
      {saved ? (
        <p className="mt-4 text-sm text-success" role="status">
          {t("organizer.formBuilder.saved")}
        </p>
      ) : null}

      {isEditable ? (
        <div className="mt-6 flex flex-wrap gap-3">
          <Button disabled={isSaving} onClick={() => void saveFields()} type="button">
            {isSaving
              ? t("organizer.actions.saving")
              : t("organizer.formBuilder.save")}
          </Button>
          <Button
            disabled={isSaving || !hasUnsavedChanges}
            onClick={() => {
              setFields(savedFields);
              setSaveError(false);
              setSaved(false);
            }}
            type="button"
            variant="secondary"
          >
            {t("organizer.formBuilder.cancelChanges")}
          </Button>
        </div>
      ) : null}

      <UnsavedChangesDialog
        description={t("common.unsaved.description")}
        isSaving={isSaving}
        leaveWithoutSavingLabel={t("common.unsaved.leaveWithoutSaving")}
        onLeaveWithoutSaving={unsavedGuard.leaveWithoutSaving}
        onSaveAndLeave={saveFields}
        onStay={unsavedGuard.stay}
        open={unsavedGuard.isPromptOpen}
        saveAndLeaveLabel={t("common.unsaved.saveAndLeave")}
        stayLabel={t("common.unsaved.stay")}
        title={t("common.unsaved.title")}
      />
    </Card>
  );
}

function FormSection({
  title,
  description,
  children
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <h2 className="text-2xl font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
      <div className="mt-6 grid gap-5 md:grid-cols-2">{children}</div>
    </Card>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  disabled = false,
  ...inputProps
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  disabled?: boolean;
  maxLength?: number;
  min?: string;
  step?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm font-semibold">
        {label}
        {required ? (
          <span aria-hidden className="ml-0.5 text-primary-hover">
            *
          </span>
        ) : null}
      </span>
      <input
        className={fieldClassName}
        disabled={disabled}
        onChange={(inputEvent) => onChange(inputEvent.target.value)}
        required={required}
        type={type}
        value={value}
        {...inputProps}
      />
    </label>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  required = false,
  disabled = false
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  disabled?: boolean;
}) {
  return (
    <label className="block md:col-span-2">
      <span className="text-sm font-semibold">
        {label}
        {required ? (
          <span aria-hidden className="ml-0.5 text-primary-hover">
            *
          </span>
        ) : null}
      </span>
      <textarea
        className={`${fieldClassName} min-h-32 py-3`}
        disabled={disabled}
        onChange={(inputEvent) => onChange(inputEvent.target.value)}
        required={required}
        value={value}
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  required = false,
  disabled = false
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ label: string; value: string }>;
  required?: boolean;
  disabled?: boolean;
}) {
  return (
    <label className="block">
      <span className="text-sm font-semibold">
        {label}
        {required ? (
          <span aria-hidden className="ml-0.5 text-primary-hover">
            *
          </span>
        ) : null}
      </span>
      <select
        className={fieldClassName}
        disabled={disabled}
        onChange={(inputEvent) => onChange(inputEvent.target.value)}
        required={required}
        value={value}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
