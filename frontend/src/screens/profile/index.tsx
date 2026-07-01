"use client";

import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useState
} from "react";

import type {
  Activity,
  EssayDraft,
  Honor,
  Olympiad,
  PlannedExam,
  PortfolioProject,
  ProfileCompletion,
  ResearchProject,
  ScholarshipNeed,
  Sport,
  StudentProfileDetails,
  TestScores
} from "@/entities/profile";
import { useAuth } from "@/features/auth/model/auth-context";
import {
  getProfileCompletionRequest,
  getProfileRequest,
  updateProfileRequest,
  getProfileItemsRequest,
  createProfileItemRequest,
  updateProfileItemRequest,
  deleteProfileItemRequest
} from "@/features/profile";
import {
  activityFields,
  activityDisplay,
  honorFields,
  honorDisplay,
  olympiadFields,
  olympiadDisplay,
  sportFields,
  sportDisplay,
  researchFields,
  researchDisplay,
  essayFields,
  essayDisplay,
  portfolioFields,
  portfolioDisplay
} from "@/features/profile/lib/profile-items-config";
import { ProfileItemSection } from "@/features/profile/ui/profile-item-section";
import { useI18n } from "@/shared/i18n";
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { UnsavedChangesDialog } from "@/shared/ui/unsaved-changes-dialog";

type ProfileFormState = {
  fullName: string;
  birthDate: string;
  country: string;
  city: string;
  schoolOrUniversity: string;
  grade: string;
  expectedGraduationYear: string;
  gpa: string;
  gpaScale: string;
  gpaScaleType: StudentProfileDetails["original_gpa_scale_type"];
  curriculumType: StudentProfileDetails["curriculum_type"];
  curriculumCountry: string;
  educationStatus: string;
  intendedDegree: string;
  targetCountries: string;
  intendedMajors: string;
  targetUniversities: string;
  scholarshipNeed: ScholarshipNeed;
  interests: string;
  languages: string;
  sat: string;
  ielts: string;
  toefl: string;
  ap: string;
  satDate: string;
  satTarget: string;
  ieltsDate: string;
  ieltsTarget: string;
  apDate: string;
  apTarget: string;
  telegramUsername: string;
  phone: string;
};

const emptyForm: ProfileFormState = {
  fullName: "",
  birthDate: "",
  country: "",
  city: "",
  schoolOrUniversity: "",
  grade: "",
  expectedGraduationYear: "",
  gpa: "",
  gpaScale: "",
  gpaScaleType: "custom_unknown",
  curriculumType: "unknown",
  curriculumCountry: "",
  educationStatus: "",
  intendedDegree: "",
  targetCountries: "",
  intendedMajors: "",
  targetUniversities: "",
  scholarshipNeed: "unsure",
  interests: "",
  languages: "",
  sat: "",
  ielts: "",
  toefl: "",
  ap: "",
  satDate: "",
  satTarget: "",
  ieltsDate: "",
  ieltsTarget: "",
  apDate: "",
  apTarget: "",
  telegramUsername: "",
  phone: ""
};

function listToText(values: string[]) {
  return values.join(", ");
}

function textToList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function scoreToText(value: TestScores[string]) {
  if (Array.isArray(value)) {
    return listToText(value);
  }
  return value === undefined ? "" : String(value);
}

function profileToForm(profile: StudentProfileDetails): ProfileFormState {
  const plannedExams = profile.exam_plans.planned ?? [];
  const satPlan = plannedExams.find((exam) => exam.name === "SAT");
  const ieltsPlan = plannedExams.find((exam) => exam.name === "IELTS");
  const apPlan = plannedExams.find((exam) => exam.name === "AP");
  return {
    fullName: profile.full_name,
    birthDate: profile.birth_date ?? "",
    country: profile.country,
    city: profile.city,
    schoolOrUniversity: profile.school_or_university,
    grade: profile.grade,
    expectedGraduationYear: profile.expected_graduation_year?.toString() ?? "",
    gpa: profile.original_gpa_value === null ? "" : String(profile.original_gpa_value),
    gpaScale: profile.original_gpa_scale === null ? "" : String(profile.original_gpa_scale),
    gpaScaleType: profile.original_gpa_scale_type,
    curriculumType: profile.curriculum_type,
    curriculumCountry: profile.curriculum_country,
    educationStatus: profile.education_status,
    intendedDegree: profile.intended_degree,
    targetCountries: listToText(profile.target_countries),
    intendedMajors: listToText(profile.intended_majors),
    targetUniversities: listToText(profile.target_universities),
    scholarshipNeed: profile.scholarship_need,
    interests: listToText(profile.interests),
    languages: listToText(profile.languages),
    sat: scoreToText(profile.test_scores.sat),
    ielts: scoreToText(profile.test_scores.ielts),
    toefl: scoreToText(profile.test_scores.toefl),
    ap: scoreToText(profile.test_scores.ap),
    satDate: satPlan?.date ?? "",
    satTarget: satPlan?.target_score ?? "",
    ieltsDate: ieltsPlan?.date ?? "",
    ieltsTarget: ieltsPlan?.target_score ?? "",
    apDate: apPlan?.date ?? "",
    apTarget: apPlan?.target_score ?? "",
    telegramUsername: profile.telegram_username,
    phone: profile.phone
  };
}

function numericScore(value: string) {
  if (!value.trim()) {
    return undefined;
  }
  const score = Number(value);
  return Number.isFinite(score) ? score : value.trim();
}

function Field({
  label,
  helper,
  children,
  wide = false
}: {
  label: string;
  helper?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <label className={wide ? "block sm:col-span-2" : "block"}>
      <span className="text-xs font-semibold">{label}</span>
      {children}
      {helper ? (
        <span className="mt-1 block text-xs leading-4 text-muted-foreground">
          {helper}
        </span>
      ) : null}
    </label>
  );
}

function ProfileSection({
  title,
  description,
  children
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card className="p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
        {description}
      </p>
      <div className="mt-4 grid gap-x-4 gap-y-3 sm:grid-cols-2">
        {children}
      </div>
    </Card>
  );
}

export function ProfileScreen() {
  const { refreshUser } = useAuth();
  const { t } = useI18n();
  const [profile, setProfile] = useState<StudentProfileDetails | null>(null);
  const [completion, setCompletion] = useState<ProfileCompletion | null>(null);
  const [form, setForm] = useState<ProfileFormState>(emptyForm);
  const [savedForm, setSavedForm] = useState<ProfileFormState>(emptyForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);
  const [saved, setSaved] = useState(false);

  // Structured profile items
  const [activities, setActivities] = useState<Activity[]>([]);
  const [honors, setHonors] = useState<Honor[]>([]);
  const [olympiads, setOlympiads] = useState<Olympiad[]>([]);
  const [sports, setSports] = useState<Sport[]>([]);
  const [research, setResearch] = useState<ResearchProject[]>([]);
  const [essays, setEssays] = useState<EssayDraft[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioProject[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);

  const loadProfile = useCallback(async () => {
    setIsLoading(true);
    setLoadFailed(false);
    try {
      const [profileResponse, completionResponse] = await Promise.all([
        getProfileRequest(),
        getProfileCompletionRequest()
      ]);
      setProfile(profileResponse);
      setCompletion(completionResponse);
      const nextForm = profileToForm(profileResponse);
      setForm(nextForm);
      setSavedForm(nextForm);
    } catch {
      setLoadFailed(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadItems = useCallback(async () => {
    setItemsLoading(true);
    try {
      const [activitiesRes, honorsRes, olympiadsRes, sportsRes, researchRes, essaysRes, portfolioRes] =
        await Promise.allSettled([
          getProfileItemsRequest<Activity>("activities"),
          getProfileItemsRequest<Honor>("honors"),
          getProfileItemsRequest<Olympiad>("olympiads"),
          getProfileItemsRequest<Sport>("sports"),
          getProfileItemsRequest<ResearchProject>("research-projects"),
          getProfileItemsRequest<EssayDraft>("essays"),
          getProfileItemsRequest<PortfolioProject>("portfolio-projects")
        ]);
      if (activitiesRes.status === "fulfilled") setActivities(activitiesRes.value.results);
      if (honorsRes.status === "fulfilled") setHonors(honorsRes.value.results);
      if (olympiadsRes.status === "fulfilled") setOlympiads(olympiadsRes.value.results);
      if (sportsRes.status === "fulfilled") setSports(sportsRes.value.results);
      if (researchRes.status === "fulfilled") setResearch(researchRes.value.results);
      if (essaysRes.status === "fulfilled") setEssays(essaysRes.value.results);
      if (portfolioRes.status === "fulfilled") setPortfolio(portfolioRes.value.results);
    } catch {
      // Silent fail for items load
    } finally {
      setItemsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProfile();
    void loadItems();
  }, [loadProfile, loadItems]);

  function updateField<Key extends keyof ProfileFormState>(
    field: Key,
    value: ProfileFormState[Key]
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const hasUnsavedProfileChanges = JSON.stringify(form) !== JSON.stringify(savedForm);
  const unsavedProfileGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedProfileChanges
  });

  async function saveProfileForm() {
    setIsSaving(true);
    setSaveFailed(false);
    setSaved(false);

    const testScores: TestScores = {};
    const sat = numericScore(form.sat);
    const ielts = numericScore(form.ielts);
    const toefl = numericScore(form.toefl);
    const ap = textToList(form.ap);
    if (sat !== undefined) testScores.sat = sat;
    if (ielts !== undefined) testScores.ielts = ielts;
    if (toefl !== undefined) testScores.toefl = toefl;
    if (ap.length > 0) testScores.ap = ap;

    try {
      const updatedProfile = await updateProfileRequest({
        full_name: form.fullName,
        birth_date: form.birthDate || null,
        country: form.country,
        city: form.city,
        school_or_university: form.schoolOrUniversity,
        grade: form.grade,
        expected_graduation_year: form.expectedGraduationYear
          ? Number(form.expectedGraduationYear)
          : null,
        gpa: form.gpa || null,
        gpa_scale: form.gpaScale || null,
        original_gpa_value: form.gpa || null,
        original_gpa_scale: form.gpaScale || null,
        original_gpa_scale_type: form.gpaScaleType,
        curriculum_type: form.curriculumType,
        curriculum_country: form.curriculumCountry,
        education_status: form.educationStatus,
        intended_degree: form.intendedDegree,
        target_countries: textToList(form.targetCountries),
        intended_majors: textToList(form.intendedMajors),
        target_universities: textToList(form.targetUniversities),
        scholarship_need: form.scholarshipNeed,
        interests: textToList(form.interests),
        languages: textToList(form.languages),
        test_scores: testScores,
        exam_plans: {
          taken: profile?.exam_plans.taken ?? [],
          planned: ([
            { name: "SAT", exam_type: "SAT", date: form.satDate, target_score: form.satTarget },
            { name: "IELTS", exam_type: "IELTS", date: form.ieltsDate, target_score: form.ieltsTarget },
            { name: "AP", exam_type: "AP", date: form.apDate, target_score: form.apTarget }
          ] satisfies PlannedExam[]).filter((exam) => exam.date || exam.target_score)
        },
        telegram_username: form.telegramUsername,
        phone: form.phone
      });
      const updatedCompletion = await getProfileCompletionRequest();
      setProfile(updatedProfile);
      setCompletion(updatedCompletion);
      const nextForm = profileToForm(updatedProfile);
      setForm(nextForm);
      setSavedForm(nextForm);
      setSaved(true);
      await refreshUser();
      return true;
    } catch {
      setSaveFailed(true);
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await saveProfileForm();
  }

  function discardProfileChanges() {
    setForm(savedForm);
    setSaveFailed(false);
    setSaved(false);
  }

  // Item CRUD handlers
  const createItem = <T extends { id: number }>(
    type: "activities" | "honors" | "olympiads" | "sports" | "research-projects" | "essays" | "portfolio-projects",
    setter: (updater: (prev: T[]) => T[]) => void
  ) =>
    async (data: Record<string, unknown>) => {
      const result = await createProfileItemRequest(type, data);
      setter((prev: T[]) => [result as T, ...prev]);
      await getProfileCompletionRequest().then(setCompletion);
    };

  const updateItem = <T extends { id: number }>(
    type: "activities" | "honors" | "olympiads" | "sports" | "research-projects" | "essays" | "portfolio-projects",
    setter: (updater: (prev: T[]) => T[]) => void
  ) =>
    async (id: number, data: Record<string, unknown>) => {
      const result = await updateProfileItemRequest(type, id, data);
      setter((prev: T[]) => prev.map((item) => (item.id === id ? (result as T) : item)));
      await getProfileCompletionRequest().then(setCompletion);
    };

  const deleteItem = <T extends { id: number }>(
    type: "activities" | "honors" | "olympiads" | "sports" | "research-projects" | "essays" | "portfolio-projects",
    setter: (updater: (prev: T[]) => T[]) => void
  ) =>
    async (id: number) => {
      await deleteProfileItemRequest(type, id);
      setter((prev: T[]) => prev.filter((item) => item.id !== id));
      await getProfileCompletionRequest().then(setCompletion);
    };

  if (isLoading) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">{t("profile.loading")}</p>
      </Card>
    );
  }

  if (loadFailed || !profile || !completion) {
    return (
      <Card>
        <p className="text-sm text-danger" role="alert">
          {t("profile.loadError")}
        </p>
        <Button className="mt-4" onClick={() => void loadProfile()} type="button">
          {t("profile.retry")}
        </Button>
      </Card>
    );
  }

  return (
    <form className="mx-auto max-w-6xl space-y-4" onSubmit={handleSubmit}>
      <section className="grid gap-4 rounded-sm border bg-card p-5 shadow-card lg:grid-cols-[minmax(0,1fr)_17rem] lg:items-start">
        <div>
          <Badge>{t("profile.eyebrow")}</Badge>
          <h1 className="mt-3 text-2xl font-semibold sm:text-3xl">{t("profile.title")}</h1>
          <p className="mt-2 max-w-2xl text-xs leading-5 text-muted-foreground">
            {t("profile.description")}
          </p>
        </div>
        <div className="border bg-elevated/55 p-4">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">{t("profile.completion.title")}</h2>
              <p className="mt-1 text-xs leading-4 text-muted-foreground">
                {t("profile.completion.description")}
              </p>
            </div>
            <span className="font-serif text-2xl font-semibold text-accent">
              {completion.percentage}%
            </span>
          </div>
          <div
            aria-label={t("a11y.profileCompletion", {
              percentage: completion.percentage
            })}
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={completion.percentage}
            className="mt-3 h-2 overflow-hidden rounded-sm bg-muted"
            role="progressbar"
          >
            <div
              className="h-full bg-primary transition-[width]"
              style={{ width: `${completion.percentage}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {t("profile.completion.summary", {
              completed: completion.completed_fields,
              total: completion.total_fields
            })}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {t("profile.completion.remaining", {
              count: completion.missing_fields.length
            })}
          </p>
        </div>
      </section>

      <ProfileSection
        description={t("profile.sections.personalHelp")}
        title={t("profile.sections.personal")}
      >
        <Field label={t("auth.fullName")}>
          <input
            className={fieldClassName}
            maxLength={180}
            onChange={(event) => updateField("fullName", event.target.value)}
            required
            value={form.fullName}
          />
        </Field>
        <Field label={t("auth.email")}>
          <input className={fieldClassName} disabled type="email" value={profile.email} />
        </Field>
        <Field label={t("profile.birthDate")}>
          <input
            className={fieldClassName}
            onChange={(event) => updateField("birthDate", event.target.value)}
            type="date"
            value={form.birthDate}
          />
        </Field>
        <Field label={t("profile.country")}>
          <input
            className={fieldClassName}
            maxLength={100}
            onChange={(event) => updateField("country", event.target.value)}
            value={form.country}
          />
        </Field>
        <Field label={t("profile.city")}>
          <input
            className={fieldClassName}
            maxLength={120}
            onChange={(event) => updateField("city", event.target.value)}
            value={form.city}
          />
        </Field>
      </ProfileSection>

      <ProfileSection
        description={t("profile.sections.educationHelp")}
        title={t("profile.sections.education")}
      >
        <Field label={t("profile.schoolOrUniversity")} wide>
          <input
            className={fieldClassName}
            maxLength={240}
            onChange={(event) => updateField("schoolOrUniversity", event.target.value)}
            value={form.schoolOrUniversity}
          />
        </Field>
        <Field label={t("profile.grade")}>
          <input
            className={fieldClassName}
            maxLength={50}
            onChange={(event) => updateField("grade", event.target.value)}
            value={form.grade}
          />
        </Field>
        <Field label={t("profile.educationStatus")}>
          <select
            className={fieldClassName}
            onChange={(event) => updateField("educationStatus", event.target.value)}
            value={form.educationStatus}
          >
            <option value="">{t("profile.options.select")}</option>
            <option value="school_student">{t("profile.options.education.school")}</option>
            <option value="university_student">{t("profile.options.education.university")}</option>
            <option value="gap_year">{t("profile.options.education.gapYear")}</option>
            <option value="graduate">{t("profile.options.education.graduate")}</option>
            <option value="other">{t("profile.options.education.other")}</option>
          </select>
        </Field>
        <Field label={t("onboarding.field.graduationYear")}>
          <input
            className={fieldClassName}
            onChange={(event) => updateField("expectedGraduationYear", event.target.value)}
            type="number"
            value={form.expectedGraduationYear}
          />
        </Field>
        <Field label={t("onboarding.field.gpa")}>
          <input
            className={fieldClassName}
            onChange={(event) => updateField("gpa", event.target.value)}
            step="0.01"
            type="number"
            value={form.gpa}
          />
        </Field>
        <Field label={t("onboarding.field.gpaScale")}>
          <input
            className={fieldClassName}
            onChange={(event) => updateField("gpaScale", event.target.value)}
            step="0.01"
            type="number"
            value={form.gpaScale}
          />
        </Field>
        <Field label={t("profile.gpaScaleType")}>
          <select
            className={fieldClassName}
            onChange={(event) =>
              updateField(
                "gpaScaleType",
                event.target.value as StudentProfileDetails["original_gpa_scale_type"]
              )
            }
            value={form.gpaScaleType}
          >
            <option value="custom_unknown">{t("profile.gpaScaleType.custom_unknown")}</option>
            <option value="4_0">{t("profile.gpaScaleType.4_0")}</option>
            <option value="5_0">{t("profile.gpaScaleType.5_0")}</option>
            <option value="percentage_100">{t("profile.gpaScaleType.percentage_100")}</option>
            <option value="ib_45">{t("profile.gpaScaleType.ib_45")}</option>
            <option value="a_level">{t("profile.gpaScaleType.a_level")}</option>
            <option value="ap_heavy">{t("profile.gpaScaleType.ap_heavy")}</option>
            <option value="uzbekistan_5">{t("profile.gpaScaleType.uzbekistan_5")}</option>
            <option value="kazakhstan_local">{t("profile.gpaScaleType.kazakhstan_local")}</option>
            <option value="kyrgyzstan_local">{t("profile.gpaScaleType.kyrgyzstan_local")}</option>
            <option value="tajikistan_local">{t("profile.gpaScaleType.tajikistan_local")}</option>
          </select>
        </Field>
        <Field label={t("profile.curriculumType")}>
          <select
            className={fieldClassName}
            onChange={(event) =>
              updateField(
                "curriculumType",
                event.target.value as StudentProfileDetails["curriculum_type"]
              )
            }
            value={form.curriculumType}
          >
            <option value="unknown">{t("profile.curriculumType.unknown")}</option>
            <option value="local_school">{t("profile.curriculumType.local_school")}</option>
            <option value="academic_lyceum">{t("profile.curriculumType.academic_lyceum")}</option>
            <option value="ib">{t("profile.curriculumType.ib")}</option>
            <option value="a_level">{t("profile.curriculumType.a_level")}</option>
            <option value="ap">{t("profile.curriculumType.ap")}</option>
            <option value="national_diploma">{t("profile.curriculumType.national_diploma")}</option>
            <option value="foundation">{t("profile.curriculumType.foundation")}</option>
            <option value="other">{t("profile.curriculumType.other")}</option>
          </select>
        </Field>
        <Field label={t("profile.curriculumCountry")}>
          <input
            className={fieldClassName}
            maxLength={100}
            onChange={(event) => updateField("curriculumCountry", event.target.value)}
            value={form.curriculumCountry}
          />
        </Field>
        {profile?.normalized_gpa_4 ? (
          <div className="rounded-sm border bg-surface p-3 text-xs text-muted-foreground sm:col-span-2">
            <p className="font-semibold text-foreground">
              {t("profile.normalizedGpa", { value: String(profile.normalized_gpa_4) })}
            </p>
            <p className="mt-1">{profile.academic_normalization_note}</p>
          </div>
        ) : null}
      </ProfileSection>

      <ProfileSection
        description={t("profile.sections.admissionsHelp")}
        title={t("profile.sections.admissions")}
      >
        <Field label={t("profile.intendedDegree")}>
          <select
            className={fieldClassName}
            onChange={(event) => updateField("intendedDegree", event.target.value)}
            value={form.intendedDegree}
          >
            <option value="">{t("profile.options.select")}</option>
            <option value="bachelor">{t("profile.options.degree.bachelor")}</option>
            <option value="master">{t("profile.options.degree.master")}</option>
            <option value="undecided">{t("profile.options.degree.undecided")}</option>
            <option value="other">{t("profile.options.degree.other")}</option>
          </select>
        </Field>
        <Field label={t("profile.scholarshipNeed")}>
          <select
            className={fieldClassName}
            onChange={(event) =>
              updateField("scholarshipNeed", event.target.value as ScholarshipNeed)
            }
            value={form.scholarshipNeed}
          >
            <option value="yes">{t("profile.options.scholarship.yes")}</option>
            <option value="no">{t("profile.options.scholarship.no")}</option>
            <option value="unsure">{t("profile.options.scholarship.unsure")}</option>
          </select>
        </Field>
        <Field
          helper={t("profile.targetCountriesHelp")}
          label={t("profile.targetCountries")}
        >
          <input
            className={fieldClassName}
            onChange={(event) => updateField("targetCountries", event.target.value)}
            value={form.targetCountries}
          />
        </Field>
        <Field
          helper={t("profile.intendedMajorsHelp")}
          label={t("profile.intendedMajors")}
        >
          <input
            className={fieldClassName}
            onChange={(event) => updateField("intendedMajors", event.target.value)}
            value={form.intendedMajors}
          />
        </Field>
        <Field
          helper={t("profile.targetUniversitiesHelp")}
          label={t("profile.targetUniversities")}
          wide
        >
          <input
            className={fieldClassName}
            onChange={(event) => updateField("targetUniversities", event.target.value)}
            value={form.targetUniversities}
          />
        </Field>
      </ProfileSection>

      <ProfileSection
        description={t("profile.sections.testsHelp")}
        title={t("profile.sections.tests")}
      >
        <Field label={t("profile.test.sat")}>
          <input
            className={fieldClassName}
            max={1600}
            min={400}
            onChange={(event) => updateField("sat", event.target.value)}
            type="number"
            value={form.sat}
          />
        </Field>
        <Field label={t("profile.test.ielts")}>
          <input
            className={fieldClassName}
            max={9}
            min={0}
            onChange={(event) => updateField("ielts", event.target.value)}
            step={0.5}
            type="number"
            value={form.ielts}
          />
        </Field>
        <Field label={t("profile.test.toefl")}>
          <input
            className={fieldClassName}
            max={120}
            min={0}
            onChange={(event) => updateField("toefl", event.target.value)}
            type="number"
            value={form.toefl}
          />
        </Field>
        <Field helper={t("profile.test.apHelp")} label={t("profile.test.ap")}>
          <input
            className={fieldClassName}
            onChange={(event) => updateField("ap", event.target.value)}
            value={form.ap}
          />
        </Field>
        <Field label={t("dashboard.examCountdown.title")} wide>
          <div className="grid gap-3 sm:grid-cols-3">
            {([
              ["SAT", "satDate", "satTarget"],
              ["IELTS", "ieltsDate", "ieltsTarget"],
              ["AP", "apDate", "apTarget"]
            ] as const).map(([exam, dateField, targetField]) => (
              <div className="border bg-surface p-3" key={exam}>
                <p className="font-semibold">{exam}</p>
                <input
                  aria-label={t("onboarding.field.examDate")}
                  className={fieldClassName}
                  onChange={(event) => updateField(dateField, event.target.value)}
                  type="date"
                  value={form[dateField]}
                />
                <input
                  aria-label={t("onboarding.field.targetScore")}
                  className={fieldClassName}
                  onChange={(event) => updateField(targetField, event.target.value)}
                  placeholder={t("onboarding.field.targetScore")}
                  value={form[targetField]}
                />
              </div>
            ))}
          </div>
        </Field>
      </ProfileSection>

      <ProfileSection
        description={t("profile.sections.preferencesHelp")}
        title={t("profile.sections.preferences")}
      >
        <Field helper={t("profile.languagesHelp")} label={t("profile.languages")}>
          <input
            className={fieldClassName}
            onChange={(event) => updateField("languages", event.target.value)}
            value={form.languages}
          />
        </Field>
        <Field helper={t("profile.interestsHelp")} label={t("profile.interests")}>
          <input
            className={fieldClassName}
            onChange={(event) => updateField("interests", event.target.value)}
            value={form.interests}
          />
        </Field>
      </ProfileSection>

      <ProfileSection
        description={t("profile.sections.contactHelp")}
        title={t("profile.sections.contact")}
      >
        <Field helper={t("profile.telegramHelp")} label={t("profile.telegram")}>
          <input
            className={fieldClassName}
            maxLength={33}
            onChange={(event) => updateField("telegramUsername", event.target.value)}
            value={form.telegramUsername}
          />
        </Field>
        <Field helper={t("profile.phoneHelp")} label={t("profile.phone")}>
          <input
            className={fieldClassName}
            maxLength={32}
            onChange={(event) => updateField("phone", event.target.value)}
            type="tel"
            value={form.phone}
          />
        </Field>
      </ProfileSection>

      {/* Structured Profile Items */}
      <div className="space-y-4 border-t pt-4">
        <ProfileItemSection
          description="profile.sections.activitiesHelp"
          items={activities}
          fields={activityFields}
          onAdd={createItem("activities", setActivities)}
          onUpdate={updateItem("activities", setActivities)}
          onDelete={deleteItem("activities", setActivities)}
          itemDisplay={activityDisplay}
          title="profile.sections.activities"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.honorsHelp"
          items={honors}
          fields={honorFields}
          onAdd={createItem("honors", setHonors)}
          onUpdate={updateItem("honors", setHonors)}
          onDelete={deleteItem("honors", setHonors)}
          itemDisplay={honorDisplay}
          title="profile.sections.honors"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.olympiadsHelp"
          items={olympiads}
          fields={olympiadFields}
          onAdd={createItem("olympiads", setOlympiads)}
          onUpdate={updateItem("olympiads", setOlympiads)}
          onDelete={deleteItem("olympiads", setOlympiads)}
          itemDisplay={olympiadDisplay}
          title="profile.sections.olympiads"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.sportsHelp"
          items={sports}
          fields={sportFields}
          onAdd={createItem("sports", setSports)}
          onUpdate={updateItem("sports", setSports)}
          onDelete={deleteItem("sports", setSports)}
          itemDisplay={sportDisplay}
          title="profile.sections.sports"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.researchHelp"
          items={research}
          fields={researchFields}
          onAdd={createItem("research-projects", setResearch)}
          onUpdate={updateItem("research-projects", setResearch)}
          onDelete={deleteItem("research-projects", setResearch)}
          itemDisplay={researchDisplay}
          title="profile.sections.research"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.essaysHelp"
          items={essays}
          fields={essayFields}
          onAdd={createItem("essays", setEssays)}
          onUpdate={updateItem("essays", setEssays)}
          onDelete={deleteItem("essays", setEssays)}
          itemDisplay={essayDisplay}
          title="profile.sections.essays"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.portfolioHelp"
          items={portfolio}
          fields={portfolioFields}
          onAdd={createItem("portfolio-projects", setPortfolio)}
          onUpdate={updateItem("portfolio-projects", setPortfolio)}
          onDelete={deleteItem("portfolio-projects", setPortfolio)}
          itemDisplay={portfolioDisplay}
          title="profile.sections.portfolio"
          isLoading={itemsLoading}
        />
      </div>

      {saveFailed ? (
        <Card className="border-danger/35 bg-danger/10">
          <p className="text-sm text-danger" role="alert">
            {t("profile.saveError")}
          </p>
        </Card>
      ) : null}
      {saved ? (
        <Card className="border-success/35 bg-success/10">
          <p className="text-sm text-success" role="status">
            {t("profile.saved")}
          </p>
        </Card>
      ) : null}

      <div className="sticky bottom-20 z-10 flex flex-wrap justify-end gap-2 rounded-sm border bg-surface p-3 shadow-card lg:bottom-4">
        <Button
          disabled={isSaving || !hasUnsavedProfileChanges}
          onClick={() => unsavedProfileGuard.requestLeave(discardProfileChanges)}
          type="button"
          variant="ghost"
        >
          {t("common.actions.cancel")}
        </Button>
        <Button disabled={isSaving} type="submit">
          {isSaving ? t("profile.saving") : t("profile.save")}
        </Button>
      </div>
      <UnsavedChangesDialog
        description={t("common.unsaved.description")}
        isSaving={isSaving}
        leaveWithoutSavingLabel={t("common.unsaved.leaveWithoutSaving")}
        onLeaveWithoutSaving={unsavedProfileGuard.leaveWithoutSaving}
        onSaveAndLeave={saveProfileForm}
        onStay={unsavedProfileGuard.stay}
        open={unsavedProfileGuard.isPromptOpen}
        saveAndLeaveLabel={t("common.unsaved.saveAndLeave")}
        stayLabel={t("common.unsaved.stay")}
        title={t("common.unsaved.title")}
      />
    </form>
  );
}
