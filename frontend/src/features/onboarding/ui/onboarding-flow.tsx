"use client";

import { ArrowLeft, ArrowRight, Check, Compass, LogOut } from "lucide-react";
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import {
  classCatalog,
  majorCatalog,
  ReadinessCard,
  targetCountries,
  type ActivityProfile,
  type ApplicationReadiness,
  type OnboardingSection,
  type PlannedExam,
  type StudentProfileDetails,
  type TestScores
} from "@/entities/profile";
import type { OfficialExamDate } from "@/entities/exam";
import { useAuth } from "@/features/auth";
import { getOfficialExamDatesRequest } from "@/features/exams";
import {
  completeOnboardingRequest,
  getApplicationReadinessRequest,
  getProfileCompletionRequest,
  getProfileRequest,
  updateProfileRequest
} from "@/features/profile";
import { ApiError, getApiErrorMessage } from "@/shared/api/client";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDate } from "@/shared/lib/date-time";
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { LanguageSwitcher } from "@/shared/ui/language-switcher";
import { SupportLink } from "@/shared/ui/support-link";
import { UnsavedChangesDialog } from "@/shared/ui/unsaved-changes-dialog";

import { AdmissionsProposals } from "./admissions-proposals";
import { MajorAssessment } from "./major-assessment";

const DRAFT_KEY = "eduverse.onboarding.draft.v1";
const stepSections: Array<OnboardingSection | null> = [
  "identity",
  "academic",
  "exams",
  "activities",
  "support",
  null
];

type OnboardingForm = {
  fullName: string;
  birthDate: string;
  country: string;
  city: string;
  educationStatus: string;
  schoolOrUniversity: string;
  grade: string;
  expectedGraduationYear: string;
  gpa: string;
  gpaScale: string;
  intendedDegree: string;
  targetCountries: string;
  targetUniversities: string;
  universityUnsure: boolean;
  scholarshipNeed: "yes" | "no" | "unsure";
  intendedMajors: string[];
  majorUnsure: boolean;
  satScore: string;
  ieltsScore: string;
  toeflScore: string;
  actScore: string;
  apScores: string;
  takenExams: string;
  satDate: string;
  satTarget: string;
  ieltsDate: string;
  ieltsTarget: string;
  apDate: string;
  apTarget: string;
  apPlans: ApPlan[];
  otherExamName: string;
  otherExamDate: string;
  otherExamTarget: string;
  interestedClasses: string;
  apInterests: string;
  preparationNeeds: string;
  activities: Record<keyof ActivityProfile, string>;
  essayStatus: "yes" | "no" | "not_yet";
  essayStage: string;
  supportPriorities: string;
  careerInterests: string;
  researchInterest: boolean;
  financeLiteracyInterest: boolean;
  munDebateInterest: boolean;
};

type ApPlan = {
  id: string;
  subject: string;
  date: string;
  target: string;
};

const emptyActivities: OnboardingForm["activities"] = {
  extracurriculars: "",
  honors: "",
  sports: "",
  olympiads: "",
  research_projects: "",
  mun_debate: "",
  volunteering: "",
  leadership: "",
  work_internships: ""
};

const emptyForm: OnboardingForm = {
  fullName: "",
  birthDate: "",
  country: "",
  city: "",
  educationStatus: "",
  schoolOrUniversity: "",
  grade: "",
  expectedGraduationYear: "",
  gpa: "",
  gpaScale: "",
  intendedDegree: "",
  targetCountries: "",
  targetUniversities: "",
  universityUnsure: false,
  scholarshipNeed: "unsure",
  intendedMajors: [],
  majorUnsure: false,
  satScore: "",
  ieltsScore: "",
  toeflScore: "",
  actScore: "",
  apScores: "",
  takenExams: "",
  satDate: "",
  satTarget: "",
  ieltsDate: "",
  ieltsTarget: "",
  apDate: "",
  apTarget: "",
  apPlans: [{ id: "ap-1", subject: "", date: "", target: "" }],
  otherExamName: "",
  otherExamDate: "",
  otherExamTarget: "",
  interestedClasses: "",
  apInterests: "",
  preparationNeeds: "",
  activities: emptyActivities,
  essayStatus: "not_yet",
  essayStage: "",
  supportPriorities: "",
  careerInterests: "",
  researchInterest: false,
  financeLiteracyInterest: false,
  munDebateInterest: false
};

const activityFields: Array<keyof ActivityProfile> = [
  "extracurriculars",
  "honors",
  "sports",
  "olympiads",
  "research_projects",
  "mun_debate",
  "volunteering",
  "leadership",
  "work_internships"
];

function toList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toText(value: string[]) {
  return value.join(", ");
}

function scoreText(value: TestScores[string]) {
  return value === undefined
    ? ""
    : Array.isArray(value)
      ? value.join(", ")
      : String(value);
}

function findExam(profile: StudentProfileDetails, name: string) {
  return (profile.exam_plans.planned ?? []).find(
    (exam) => exam.name.toLowerCase() === name.toLowerCase()
  );
}

function profileToForm(profile: StudentProfileDetails): OnboardingForm {
  const sat = findExam(profile, "SAT");
  const ielts = findExam(profile, "IELTS");
  const ap = findExam(profile, "AP");
  const other = (profile.exam_plans.planned ?? []).find(
    (exam) => !["sat", "ielts", "ap"].includes(exam.name.toLowerCase())
  );
  const apPlans = (profile.exam_plans.planned ?? [])
    .filter((exam) => exam.exam_type === "AP" || exam.name.toLowerCase().startsWith("ap "))
    .map((exam, index) => ({
      id: `ap-${index + 1}`,
      subject: exam.name === "AP" ? "" : exam.name,
      date: exam.date ?? "",
      target: exam.target_score ?? ""
    }));

  return {
    fullName: profile.full_name,
    birthDate: profile.birth_date ?? "",
    country: profile.country,
    city: profile.city,
    educationStatus: profile.education_status,
    schoolOrUniversity: profile.school_or_university,
    grade: profile.grade,
    expectedGraduationYear: profile.expected_graduation_year?.toString() ?? "",
    gpa: profile.gpa === null ? "" : String(profile.gpa),
    gpaScale: profile.gpa_scale === null ? "" : String(profile.gpa_scale),
    intendedDegree: profile.intended_degree,
    targetCountries: toText(profile.target_countries),
    targetUniversities: toText(profile.target_universities),
    universityUnsure: profile.university_unsure,
    scholarshipNeed: profile.scholarship_need,
    intendedMajors: profile.intended_majors,
    majorUnsure: profile.major_unsure,
    satScore: scoreText(profile.test_scores.sat),
    ieltsScore: scoreText(profile.test_scores.ielts),
    toeflScore: scoreText(profile.test_scores.toefl),
    actScore: scoreText(profile.test_scores.act),
    apScores: scoreText(profile.test_scores.ap),
    takenExams: toText(profile.exam_plans.taken ?? []),
    satDate: sat?.date ?? "",
    satTarget: sat?.target_score ?? "",
    ieltsDate: ielts?.date ?? "",
    ieltsTarget: ielts?.target_score ?? "",
    apDate: ap?.date ?? "",
    apTarget: ap?.target_score ?? "",
    apPlans: apPlans.length
      ? apPlans
      : [{ id: "ap-1", subject: ap?.name === "AP" ? "" : ap?.name ?? "", date: ap?.date ?? "", target: ap?.target_score ?? "" }],
    otherExamName: other?.name ?? "",
    otherExamDate: other?.date ?? "",
    otherExamTarget: other?.target_score ?? "",
    interestedClasses: toText(profile.interested_classes),
    apInterests: toText(profile.ap_interests),
    preparationNeeds: toText(profile.preparation_needs),
    activities: Object.fromEntries(
      activityFields.map((field) => [field, toText(profile.activities[field] ?? [])])
    ) as OnboardingForm["activities"],
    essayStatus: profile.essay_status,
    essayStage: profile.essay_stage,
    supportPriorities: toText(profile.support_priorities),
    careerInterests: toText(profile.career_interests),
    researchInterest: profile.research_interest,
    financeLiteracyInterest: profile.finance_literacy_interest,
    munDebateInterest: profile.mun_debate_interest
  };
}

function Field({
  label,
  helper,
  children,
  wide = false,
  required = false
}: {
  label: string;
  helper?: string;
  children: ReactNode;
  wide?: boolean;
  required?: boolean;
}) {
  const { t } = useI18n();
  return (
    <label className={wide ? "block md:col-span-2" : "block"}>
      <span className="flex flex-wrap items-center gap-2 text-sm font-semibold">
        <span>
          {label}
          {required ? (
            <span aria-hidden className="ml-0.5 text-primary-hover">
              *
            </span>
          ) : null}
        </span>
        <span
          className={
            required
              ? "rounded-sm border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-[0.62rem] font-bold uppercase tracking-wide text-primary-hover"
              : "rounded-sm border bg-surface px-1.5 py-0.5 text-[0.62rem] font-bold uppercase tracking-wide text-muted-foreground"
          }
        >
          {required
            ? t("onboarding.requiredToContinue")
            : t("onboarding.optionalImproves")}
        </span>
      </span>
      {helper || !required ? (
        <span className="mt-1.5 block text-xs leading-5 text-muted-foreground">
          {helper || t("onboarding.optionalHelper")}
        </span>
      ) : null}
      <div className="mt-2">
        {children}
      </div>
    </label>
  );
}

function CheckField({
  checked,
  label,
  onChange
}: {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex min-h-11 cursor-pointer items-center gap-3 border bg-surface px-3 text-sm font-medium">
      <input
        checked={checked}
        className="size-4 accent-primary"
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <span>{label}</span>
    </label>
  );
}

function numericOrText(value: string) {
  if (!value.trim()) return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : value.trim();
}

function formPayload(
  form: OnboardingForm,
  sections: OnboardingSection[]
) {
  const testScores: TestScores = {};
  const scores = {
    sat: numericOrText(form.satScore),
    ielts: numericOrText(form.ieltsScore),
    toefl: numericOrText(form.toeflScore),
    act: numericOrText(form.actScore)
  };
  Object.entries(scores).forEach(([key, value]) => {
    if (value !== undefined) testScores[key] = value;
  });
  if (toList(form.apScores).length) testScores.ap = toList(form.apScores);

  const apPlanned: PlannedExam[] = form.apPlans
    .filter((plan) => plan.subject.trim() && (plan.date || plan.target.trim()))
    .map((plan) => ({
      name: plan.subject.trim(),
      exam_type: "AP" as const,
      current_score: form.apScores,
      date: plan.date,
      target_score: plan.target,
      planned_retake: Boolean(plan.date || plan.target),
      planned_retake_month: plan.date ? plan.date.slice(0, 7) : "",
      test_status: plan.date || plan.target ? "preparing" : "not_started"
    }));

  const planned: PlannedExam[] = [
    {
      name: "SAT",
      exam_type: "SAT" as const,
      current_score: form.satScore,
      date: form.satDate,
      target_score: form.satTarget,
      planned_retake: Boolean(form.satDate || form.satTarget),
      planned_retake_month: form.satDate ? form.satDate.slice(0, 7) : "",
      test_status: form.satDate || form.satTarget ? "preparing" : "not_started"
    },
    {
      name: "IELTS",
      exam_type: "IELTS" as const,
      current_score: form.ieltsScore,
      date: form.ieltsDate,
      target_score: form.ieltsTarget,
      planned_retake: Boolean(form.ieltsDate || form.ieltsTarget),
      planned_retake_month: form.ieltsDate ? form.ieltsDate.slice(0, 7) : "",
      test_status: form.ieltsDate || form.ieltsTarget ? "preparing" : "not_started"
    },
    ...apPlanned,
    {
      name: form.otherExamName,
      current_score: "",
      date: form.otherExamDate,
      target_score: form.otherExamTarget,
      planned_retake: Boolean(form.otherExamDate || form.otherExamTarget),
      planned_retake_month: form.otherExamDate ? form.otherExamDate.slice(0, 7) : "",
      test_status: form.otherExamDate || form.otherExamTarget ? "preparing" : "not_started"
    }
  ].filter((exam) => exam.name && (exam.date || exam.target_score));

  return {
    full_name: form.fullName,
    birth_date: form.birthDate || null,
    country: form.country,
    city: form.city,
    education_status: form.educationStatus,
    school_or_university: form.schoolOrUniversity,
    grade: form.grade,
    expected_graduation_year: form.expectedGraduationYear
      ? Number(form.expectedGraduationYear)
      : null,
    gpa: form.gpa || null,
    gpa_scale: form.gpaScale || null,
    intended_degree: form.intendedDegree,
    target_countries: toList(form.targetCountries),
    target_universities: toList(form.targetUniversities),
    university_unsure: form.universityUnsure,
    scholarship_need: form.scholarshipNeed,
    intended_majors: form.intendedMajors,
    major_unsure: form.majorUnsure,
    test_scores: testScores,
    exam_plans: { taken: toList(form.takenExams), planned },
    interested_classes: toList(form.interestedClasses),
    ap_interests: toList(form.apInterests),
    preparation_needs: toList(form.preparationNeeds),
    activities: Object.fromEntries(
      activityFields.map((field) => [field, toList(form.activities[field])])
    ) as ActivityProfile,
    essay_status: form.essayStatus,
    essay_stage: form.essayStage,
    support_priorities: toList(form.supportPriorities),
    career_interests: toList(form.careerInterests),
    research_interest: form.researchInterest,
    finance_literacy_interest: form.financeLiteracyInterest,
    mun_debate_interest: form.munDebateInterest,
    onboarding_sections: sections
  };
}

// Timeout/network failures are synthesized client-side (see shared/api/client.ts)
// and must never surface their raw, English-only message; every other error
// falls back to the backend's own (already localized where applicable) text.
function localizedSaveError(
  error: unknown,
  t: (key: TranslationKey) => string,
  fallback: string
): string {
  if (error instanceof ApiError) {
    if (error.errorCode === "timeout") return t("common.error.timeout");
    if (error.errorCode === "network") return t("common.error.network");
  }
  return getApiErrorMessage(error, fallback);
}

function hasAnyExamSignal(form: OnboardingForm) {
  return Boolean(
    form.takenExams.trim() ||
      form.satScore.trim() ||
      form.ieltsScore.trim() ||
      form.toeflScore.trim() ||
      form.actScore.trim() ||
      form.apScores.trim() ||
      form.satDate ||
      form.satTarget.trim() ||
      form.ieltsDate ||
      form.ieltsTarget.trim() ||
      form.apDate ||
      form.apTarget.trim() ||
      form.apPlans.some((plan) => plan.subject.trim() || plan.date || plan.target.trim()) ||
      form.otherExamDate ||
      form.otherExamTarget.trim()
  );
}

function getStepValidationIssues(
  form: OnboardingForm,
  step: number,
  t: (key: TranslationKey) => string
) {
  const issues: string[] = [];
  const requireValue = (value: string | string[], label: string) => {
    const isMissing = Array.isArray(value) ? value.length === 0 : !value.trim();
    if (isMissing) issues.push(label);
  };

  if (step === 0) {
    requireValue(form.fullName, t("auth.fullName"));
    requireValue(form.birthDate, t("profile.birthDate"));
    requireValue(form.country, t("profile.country"));
    requireValue(form.city, t("profile.city"));
    requireValue(form.educationStatus, t("profile.educationStatus"));
    requireValue(form.schoolOrUniversity, t("profile.schoolOrUniversity"));
    requireValue(form.grade, t("profile.grade"));
    requireValue(form.expectedGraduationYear, t("onboarding.field.graduationYear"));
    requireValue(form.gpa, t("onboarding.field.gpa"));
    requireValue(form.gpaScale, t("onboarding.field.gpaScale"));
    const graduationYear = Number(form.expectedGraduationYear);
    if (form.expectedGraduationYear && (!Number.isInteger(graduationYear) || graduationYear < 2025 || graduationYear > 2041)) {
      issues.push(t("onboarding.validation.graduationYear"));
    }
    const gpa = Number(form.gpa);
    const gpaScale = Number(form.gpaScale);
    if (form.gpa && form.gpaScale && (gpa < 0 || gpaScale <= 0 || gpa > gpaScale)) {
      issues.push(t("onboarding.validation.gpaScale"));
    }
  }

  if (step === 1) {
    requireValue(form.intendedDegree, t("profile.intendedDegree"));
    requireValue(toList(form.targetCountries), t("profile.targetCountries"));
    if (!form.majorUnsure && form.intendedMajors.length === 0) {
      issues.push(t("onboarding.field.majors"));
    }
  }

  if (step === 2) {
    if (!hasAnyExamSignal(form)) {
      issues.push(t("onboarding.validation.examPlan"));
    }
    requireValue(form.interestedClasses, t("onboarding.field.interestedClasses"));
    requireValue(form.preparationNeeds, t("onboarding.field.preparationNeeds"));
  }

  if (step === 4) {
    requireValue(form.supportPriorities, t("onboarding.field.supportPriorities"));
  }

  return issues;
}

export function OnboardingFlow({ onCompleted }: { onCompleted?: () => void }) {
  const { logout } = useAuth();
  const { locale, t } = useI18n();
  const [form, setForm] = useState<OnboardingForm>(emptyForm);
  const [savedForm, setSavedForm] = useState<OnboardingForm>(emptyForm);
  const [sections, setSections] = useState<OnboardingSection[]>([]);
  const [step, setStep] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const [recommendationOpen, setRecommendationOpen] = useState(false);
  const [majorSearch, setMajorSearch] = useState("");
  const [readiness, setReadiness] = useState<ApplicationReadiness | null>(null);
  const [officialDates, setOfficialDates] = useState<OfficialExamDate[]>([]);
  const officialDatesRequestedRef = useRef(false);
  const [officialDatesError, setOfficialDatesError] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const profile = await getProfileRequest();
        const stored = window.sessionStorage.getItem(DRAFT_KEY);
        const backendForm = profileToForm(profile);
        const nextForm = stored ? { ...backendForm, ...JSON.parse(stored) } : backendForm;
        setForm(nextForm);
        setSavedForm(backendForm);
        setSections(profile.onboarding_sections);
      } catch (loadError) {
        setError(localizedSaveError(loadError, t, t("onboarding.error.load")));
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, [t]);

  useEffect(() => {
    if (!isLoading) {
      window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(form));
    }
  }, [form, isLoading]);

  useEffect(() => {
    if (step !== 2 || officialDatesRequestedRef.current) return;
    let cancelled = false;
    officialDatesRequestedRef.current = true;
    setOfficialDatesError(false);
    getOfficialExamDatesRequest({ page_size: 200 })
      .then((response) => {
        if (!cancelled) setOfficialDates(response.results);
      })
      .catch(() => {
        if (!cancelled) setOfficialDatesError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [step]);

  const update = useCallback(
    <Key extends keyof OnboardingForm>(key: Key, value: OnboardingForm[Key]) => {
      setForm((current) => ({ ...current, [key]: value }));
      setError(null);
    },
    []
  );

  const visibleCategories = useMemo(() => {
    const query = majorSearch.trim().toLowerCase();
    if (!query) return majorCatalog;
    return majorCatalog
      .map((category) => ({
        ...category,
        majors: category.majors.filter((major) =>
          (major.labelKey ? t(major.labelKey) : major.value)
            .toLowerCase()
            .includes(query)
        )
      }))
      .filter((category) => category.majors.length > 0);
  }, [majorSearch, t]);
  const satDateOptions = useMemo(
    () =>
      officialDates
        .filter((item) => item.exam_type === "SAT" && item.event_kind === "exam")
        .slice(0, 5),
    [officialDates]
  );
  const apExamDateOptions = useMemo(
    () =>
      officialDates.filter((item) => item.exam_type === "AP" && item.event_kind === "exam"),
    [officialDates]
  );
  const apSubjectOptions = useMemo(
    () => Array.from(new Set(apExamDateOptions.map((item) => item.name))).sort(),
    [apExamDateOptions]
  );

  const hasUnsavedChanges = JSON.stringify(form) !== JSON.stringify(savedForm);
  const unsavedGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedChanges
  });

  async function saveCurrentStep(nextStep: number) {
    setIsSaving(true);
    setError(null);
    const section = stepSections[step];
    const nextSections =
      section && !sections.includes(section) ? [...sections, section] : sections;
    try {
      await updateProfileRequest(formPayload(form, nextSections));
      if (nextStep === 5) {
        setReadiness(await getApplicationReadinessRequest());
      }
      setSections(nextSections);
      setSavedForm(form);
      setStep(nextStep);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return true;
    } catch (saveError) {
      setError(localizedSaveError(saveError, t, t("onboarding.error.save")));
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function saveOnboardingDraft() {
    setIsSaving(true);
    setError(null);
    try {
      await updateProfileRequest(formPayload(form, sections));
      setSavedForm(form);
      return true;
    } catch (saveError) {
      setError(localizedSaveError(saveError, t, t("onboarding.error.save")));
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function finish() {
    setIsSaving(true);
    setError(null);
    setMissing([]);
    try {
      await updateProfileRequest(formPayload(form, sections));
      setSavedForm(form);
      const completion = await getProfileCompletionRequest();
      if (!completion.can_complete) {
        setMissing([...completion.missing_fields, ...completion.missing_sections]);
        setError(t("onboarding.error.missing"));
        return;
      }
      await completeOnboardingRequest();
      window.sessionStorage.removeItem(DRAFT_KEY);
      onCompleted?.();
    } catch (finishError) {
      setError(localizedSaveError(finishError, t, t("onboarding.error.finish")));
    } finally {
      setIsSaving(false);
    }
  }

  function toggleMajor(value: string) {
    update(
      "intendedMajors",
      form.intendedMajors.includes(value)
        ? form.intendedMajors.filter((major) => major !== value)
        : [...form.intendedMajors, value]
    );
  }

  function toggleTextList(field: "targetCountries" | "interestedClasses", value: string) {
    const values = toList(form[field]);
    update(
      field,
      toText(
        values.includes(value)
          ? values.filter((item) => item !== value)
          : [...values, value]
      )
    );
  }

  function updateApPlan(rowId: string, patch: Partial<ApPlan>) {
    update(
      "apPlans",
      form.apPlans.map((row) => {
        if (row.id !== rowId) return row;
        const next = { ...row, ...patch };
        if (patch.subject !== undefined) {
          const matchingDate = apExamDateOptions.find((item) => item.name === patch.subject);
          next.date = matchingDate?.test_date ?? "";
        }
        return next;
      })
    );
  }

  function addApPlan() {
    update("apPlans", [
      ...form.apPlans,
      { id: `ap-${Date.now()}`, subject: "", date: "", target: "" }
    ]);
  }

  function removeApPlan(rowId: string) {
    if (form.apPlans.length <= 1) return;
    update(
      "apPlans",
      form.apPlans.filter((row) => row.id !== rowId)
    );
  }

  if (isLoading) {
    return (
      <main className="grid min-h-screen place-items-center bg-background px-6">
        <p className="text-sm text-muted-foreground">{t("onboarding.loading")}</p>
      </main>
    );
  }

  if (recommendationOpen) {
    return (
      <MajorAssessment
        initialMajors={form.intendedMajors}
        onBack={() => setRecommendationOpen(false)}
        onUse={(majors, result) => {
          update("intendedMajors", majors);
          update(
            "interestedClasses",
            toText([
              ...new Set([
                ...toList(form.interestedClasses),
                ...result.classes.map((item) => item.value)
              ])
            ])
          );
          update("majorUnsure", false);
          setRecommendationOpen(false);
        }}
      />
    );
  }

  const stepTitle = t(`onboarding.step.${step + 1}.title` as TranslationKey);
  const stepDescription = t(
    `onboarding.step.${step + 1}.description` as TranslationKey
  );
  const currentStepIssues = getStepValidationIssues(form, step, t);
  const canContinueStep = currentStepIssues.length === 0;

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b border-white/10 bg-navy px-4 py-4 text-navy-foreground sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-sm bg-primary font-serif text-xl font-bold">
              E
            </span>
            <div>
              <p className="font-serif text-lg font-semibold">EduVerse</p>
              <p className="text-[0.65rem] uppercase tracking-[0.16em] text-white/55">
                {t("onboarding.required")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <SupportLink className="hidden border-white/15 bg-white/5 text-white/70 hover:border-white/35 hover:bg-white/10 hover:text-white sm:inline-flex" />
            <LanguageSwitcher compact inverse />
            <button
              aria-label={t("a11y.logout")}
              className="grid size-10 place-items-center border border-white/15 text-white/70 hover:bg-white/10 hover:text-white"
              onClick={() => unsavedGuard.requestLeave(() => logout())}
              type="button"
            >
              <LogOut aria-hidden className="size-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[92rem] gap-8 px-4 py-7 sm:px-8 lg:grid-cols-[15rem_minmax(0,1fr)] lg:py-10 xl:grid-cols-[15rem_minmax(0,1fr)_20rem]">
        <aside>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-hover">
            {t("onboarding.progress", { current: step + 1, total: 6 })}
          </p>
          <div className="mt-4 h-1.5 bg-muted">
            <div className="h-full bg-primary" style={{ width: `${((step + 1) / 6) * 100}%` }} />
          </div>
          <ol className="mt-6 hidden space-y-1 lg:block">
            {Array.from({ length: 6 }, (_, index) => (
              <li
                className={
                  index === step
                    ? "border-l-4 border-primary bg-card px-4 py-3 text-sm font-semibold"
                    : index < step
                      ? "border-l-4 border-success px-4 py-3 text-sm text-foreground"
                      : "border-l-4 border-border px-4 py-3 text-sm text-muted-foreground"
                }
                key={index}
              >
                {index < step ? <Check aria-hidden className="mr-2 inline size-4" /> : null}
                {t(`onboarding.step.${index + 1}.short` as TranslationKey)}
              </li>
            ))}
          </ol>
        </aside>

        <section className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
            {t("onboarding.stepLabel", { number: step + 1 })}
          </p>
          <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">{stepTitle}</h1>
          <p className="mt-3 max-w-3xl leading-7 text-muted-foreground">
            {stepDescription}
          </p>

          <p className="mt-4 text-xs font-semibold text-muted-foreground">
            {t("onboarding.requiredLegend")}
          </p>
          {currentStepIssues.length > 0 ? (
            <div className="mt-3 rounded-sm border border-warning/35 bg-warning/10 p-3 text-xs leading-5 text-warning">
              <p className="font-semibold">{t("onboarding.validation.blocked")}</p>
              <ul className="mt-1 list-inside list-disc">
                {currentStepIssues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <Card className="mt-3 p-5 sm:p-7">
            {step === 0 ? (
              <div className="grid gap-5 md:grid-cols-2">
                <Field label={t("auth.fullName")} required>
                  <input className={fieldClassName} onChange={(event) => update("fullName", event.target.value)} required value={form.fullName} />
                </Field>
                <Field label={t("profile.birthDate")} required>
                  <input className={fieldClassName} onChange={(event) => update("birthDate", event.target.value)} required type="date" value={form.birthDate} />
                </Field>
                <Field label={t("profile.country")} required>
                  <input className={fieldClassName} onChange={(event) => update("country", event.target.value)} required value={form.country} />
                </Field>
                <Field label={t("profile.city")} required>
                  <input className={fieldClassName} onChange={(event) => update("city", event.target.value)} required value={form.city} />
                </Field>
                <Field label={t("profile.educationStatus")} required>
                  <select className={fieldClassName} onChange={(event) => update("educationStatus", event.target.value)} required value={form.educationStatus}>
                    <option value="">{t("profile.options.select")}</option>
                    <option value="school_student">{t("profile.options.education.school")}</option>
                    <option value="university_student">{t("profile.options.education.university")}</option>
                    <option value="gap_year">{t("profile.options.education.gapYear")}</option>
                    <option value="graduate">{t("profile.options.education.graduate")}</option>
                    <option value="other">{t("profile.options.education.other")}</option>
                  </select>
                </Field>
                <Field label={t("profile.schoolOrUniversity")} required>
                  <input className={fieldClassName} onChange={(event) => update("schoolOrUniversity", event.target.value)} required value={form.schoolOrUniversity} />
                </Field>
                <Field label={t("profile.grade")} required>
                  <input className={fieldClassName} onChange={(event) => update("grade", event.target.value)} required value={form.grade} />
                </Field>
                <Field label={t("onboarding.field.graduationYear")} required>
                  <input className={fieldClassName} max={2041} min={2025} onChange={(event) => update("expectedGraduationYear", event.target.value)} required type="number" value={form.expectedGraduationYear} />
                </Field>
                <Field label={t("onboarding.field.gpa")} required>
                  <input className={fieldClassName} min={0} onChange={(event) => update("gpa", event.target.value)} placeholder={t("onboarding.field.gpaPlaceholder")} required step="0.01" type="number" value={form.gpa} />
                </Field>
                <Field label={t("onboarding.field.gpaScale")} required>
                  <input className={fieldClassName} min={0} onChange={(event) => update("gpaScale", event.target.value)} placeholder={t("onboarding.field.gpaScalePlaceholder")} required step="0.01" type="number" value={form.gpaScale} />
                </Field>
              </div>
            ) : null}

            {step === 1 ? (
              <div className="space-y-7">
                <div className="grid gap-5 md:grid-cols-2">
                  <Field label={t("profile.intendedDegree")} required>
                    <select className={fieldClassName} onChange={(event) => update("intendedDegree", event.target.value)} required value={form.intendedDegree}>
                      <option value="">{t("profile.options.select")}</option>
                      <option value="bachelor">{t("profile.options.degree.bachelor")}</option>
                      <option value="master">{t("profile.options.degree.master")}</option>
                      <option value="undecided">{t("profile.options.degree.undecided")}</option>
                      <option value="other">{t("profile.options.degree.other")}</option>
                    </select>
                  </Field>
                  <Field label={t("profile.scholarshipNeed")}>
                    <select className={fieldClassName} onChange={(event) => update("scholarshipNeed", event.target.value as OnboardingForm["scholarshipNeed"])} value={form.scholarshipNeed}>
                      <option value="yes">{t("profile.options.scholarship.yes")}</option>
                      <option value="no">{t("profile.options.scholarship.no")}</option>
                      <option value="unsure">{t("profile.options.scholarship.unsure")}</option>
                    </select>
                  </Field>
                  <Field
                    helper={t("admissions.country.description")}
                    label={t("admissions.country.title")}
                    required
                    wide
                  >
                    <div className="mt-2 grid max-h-64 gap-2 overflow-y-auto border p-3 sm:grid-cols-2 lg:grid-cols-3">
                      {targetCountries.map((country) => (
                        <CheckField
                          checked={toList(form.targetCountries).includes(country)}
                          key={country}
                          label={country}
                          onChange={() => toggleTextList("targetCountries", country)}
                        />
                      ))}
                    </div>
                  </Field>
                  <Field helper={t("profile.targetUniversitiesHelp")} label={t("profile.targetUniversities")}>
                    <input className={fieldClassName} disabled={form.universityUnsure} onChange={(event) => update("targetUniversities", event.target.value)} placeholder={t("profile.targetUniversitiesPlaceholder")} value={form.targetUniversities} />
                    <div className="mt-2">
                      <CheckField checked={form.universityUnsure} label={t("onboarding.field.universityUnsure")} onChange={(checked) => update("universityUnsure", checked)} />
                    </div>
                  </Field>
                </div>
                <div className="border-t pt-6">
                  <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
                    <div>
                      <h2 className="text-xl font-semibold">{t("onboarding.field.majors")}</h2>
                      <span className="mt-1 inline-flex rounded-sm border border-primary/30 bg-primary/10 px-2 py-1 text-[0.65rem] font-bold uppercase tracking-wide text-primary-hover">
                        {t("onboarding.requiredToContinue")}
                      </span>
                      <p className="mt-1 text-sm text-muted-foreground">{t("onboarding.field.majorsHelp")}</p>
                    </div>
                    <input className={`${fieldClassName} mt-0 sm:w-72`} onChange={(event) => setMajorSearch(event.target.value)} placeholder={t("onboarding.majorSearch")} value={majorSearch} />
                  </div>
                  <div className="mt-5 max-h-[28rem] space-y-5 overflow-y-auto border p-4">
                    {visibleCategories.map((category) => (
                      <div key={category.id}>
                        <h3 className="text-sm font-bold uppercase tracking-[0.1em] text-primary-hover">{t(category.labelKey)}</h3>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          {category.majors.map((major) => (
                            <CheckField checked={form.intendedMajors.includes(major.value)} key={major.id} label={major.labelKey ? t(major.labelKey) : major.value} onChange={() => toggleMajor(major.value)} />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <CheckField
                      checked={form.majorUnsure}
                      label={t("onboarding.field.majorUnsure")}
                      onChange={(checked) => {
                        update("majorUnsure", checked);
                        if (checked) setRecommendationOpen(true);
                      }}
                    />
                    <Button className="gap-2" onClick={() => setRecommendationOpen(true)} type="button" variant="secondary">
                      <Compass aria-hidden className="size-4" />
                      {t("onboarding.recommendation.open")}
                    </Button>
                  </div>
                </div>
              </div>
            ) : null}

            {step === 2 ? (
              <div className="space-y-7">
                <div className="grid gap-5 md:grid-cols-2">
                  <Field helper={t("onboarding.field.commaHelp")} label={t("onboarding.field.takenExams")}>
                    <input className={fieldClassName} onChange={(event) => update("takenExams", event.target.value)} value={form.takenExams} />
                  </Field>
                  <Field helper={t("onboarding.field.commaHelp")} label={t("onboarding.field.interestedClasses")} required>
                    <input className={fieldClassName} onChange={(event) => update("interestedClasses", event.target.value)} required value={form.interestedClasses} />
                  </Field>
                  {(["satScore", "ieltsScore", "toeflScore", "actScore"] as const).map((field) => (
                    <Field key={field} label={t(`onboarding.field.${field}` as TranslationKey)}>
                      <input
                        className={fieldClassName}
                        onChange={(event) => update(field, event.target.value)}
                        placeholder={
                          field === "satScore"
                            ? t("onboarding.field.satScorePlaceholder")
                            : field === "ieltsScore"
                              ? t("onboarding.field.ieltsScorePlaceholder")
                              : undefined
                        }
                        type="number"
                        value={form[field]}
                      />
                    </Field>
                  ))}
                  <Field helper={t("onboarding.field.commaHelp")} label={t("onboarding.field.apScores")}>
                    <input className={fieldClassName} onChange={(event) => update("apScores", event.target.value)} value={form.apScores} />
                  </Field>
                  <Field helper={t("onboarding.field.commaHelp")} label={t("onboarding.field.apInterests")}>
                    <input className={fieldClassName} onChange={(event) => update("apInterests", event.target.value)} value={form.apInterests} />
                  </Field>
                  <Field helper={t("onboarding.field.commaHelp")} label={t("onboarding.field.preparationNeeds")} required wide>
                    <input className={fieldClassName} onChange={(event) => update("preparationNeeds", event.target.value)} required value={form.preparationNeeds} />
                  </Field>
                </div>
                <div className="border-t pt-6">
                  <h2 className="text-xl font-semibold">
                    {t("admissions.classes.selectedTitle")}
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {t("admissions.classes.selectedDescription")}
                  </p>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {classCatalog.map((item) => (
                      <CheckField
                        checked={toList(form.interestedClasses).includes(item.value)}
                        key={item.id}
                        label={t(item.labelKey)}
                        onChange={() =>
                          toggleTextList("interestedClasses", item.value)
                        }
                      />
                    ))}
                  </div>
                </div>
                <div className="border-t pt-6">
                  <h2 className="text-xl font-semibold">{t("onboarding.field.examDates")}</h2>
                  <p className="mt-1 text-xs font-semibold text-primary-hover">
                    {t("onboarding.validation.examPlan")}
                  </p>
                  {officialDatesError ? (
                    <p className="mt-2 text-xs text-warning">
                      {t("onboarding.field.officialDatesUnavailable")}
                    </p>
                  ) : null}
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <div className="border bg-surface p-4">
                      <h3 className="font-semibold">SAT</h3>
                      {satDateOptions.length > 0 ? (
                        <select
                          aria-label={t("onboarding.field.examDate")}
                          className={fieldClassName}
                          onChange={(event) => update("satDate", event.target.value)}
                          value={form.satDate}
                        >
                          <option value="">{t("onboarding.field.selectSuggestedDate")}</option>
                          {satDateOptions.map((item) => (
                            <option key={item.id} value={item.test_date}>
                              {formatDate(item.test_date, locale)}
                              {item.test_time ? ` / ${item.test_time}` : ""}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          aria-label={t("onboarding.field.examDate")}
                          className={fieldClassName}
                          onChange={(event) => update("satDate", event.target.value)}
                          type="date"
                          value={form.satDate}
                        />
                      )}
                      <input
                        aria-label={t("onboarding.field.targetScore")}
                        className={fieldClassName}
                        onChange={(event) => update("satTarget", event.target.value)}
                        placeholder={t("onboarding.field.targetScore")}
                        value={form.satTarget}
                      />
                      <p className="mt-2 text-xs text-muted-foreground">
                        {form.satDate
                          ? t("onboarding.field.selectedSatDate", {
                              date: formatDate(form.satDate, locale)
                            })
                          : t("onboarding.field.dateUnavailable")}
                      </p>
                    </div>

                    <div className="border bg-surface p-4">
                      <h3 className="font-semibold">IELTS</h3>
                      <input
                        aria-label={t("onboarding.field.examDate")}
                        className={fieldClassName}
                        onChange={(event) => update("ieltsDate", event.target.value)}
                        type="date"
                        value={form.ieltsDate}
                      />
                      <input
                        aria-label={t("onboarding.field.targetScore")}
                        className={fieldClassName}
                        onChange={(event) => update("ieltsTarget", event.target.value)}
                        placeholder={t("onboarding.field.targetScore")}
                        value={form.ieltsTarget}
                      />
                    </div>
                  </div>

                  <div className="mt-4 space-y-3 border bg-surface p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="font-semibold">{t("onboarding.field.apPlanRows")}</h3>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {t("onboarding.field.apPlanRowsHelp")}
                        </p>
                      </div>
                      <Button onClick={addApPlan} size="sm" type="button" variant="secondary">
                        {t("exams.plan.addApSubject")}
                      </Button>
                    </div>
                    {form.apPlans.map((row) => {
                      const dateOptions = row.subject
                        ? apExamDateOptions.filter((item) => item.name === row.subject)
                        : apExamDateOptions;
                      return (
                        <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.7fr)_auto]" key={row.id}>
                          <select
                            aria-label={t("exams.plan.apSubject")}
                            className={fieldClassName}
                            onChange={(event) => updateApPlan(row.id, { subject: event.target.value })}
                            value={row.subject}
                          >
                            <option value="">{t("exams.plan.apSubject")}</option>
                            {apSubjectOptions.map((subject) => (
                              <option key={subject} value={subject}>
                                {subject}
                              </option>
                            ))}
                          </select>
                          <select
                            aria-label={t("exams.plan.apDate")}
                            className={fieldClassName}
                            onChange={(event) => updateApPlan(row.id, { date: event.target.value })}
                            value={row.date}
                          >
                            <option value="">{t("onboarding.field.selectSuggestedDate")}</option>
                            {dateOptions.map((item) => (
                              <option key={item.id} value={item.test_date}>
                                {formatDate(item.test_date, locale)}
                                {item.test_time ? ` / ${item.test_time}` : ""}
                              </option>
                            ))}
                          </select>
                          <input
                            aria-label={t("onboarding.field.targetScore")}
                            className={fieldClassName}
                            onChange={(event) => updateApPlan(row.id, { target: event.target.value })}
                            placeholder={t("onboarding.field.targetScore")}
                            value={row.target}
                          />
                          <Button
                            disabled={form.apPlans.length <= 1}
                            onClick={() => removeApPlan(row.id)}
                            size="sm"
                            type="button"
                            variant="ghost"
                          >
                            {t("common.actions.close")}
                          </Button>
                          {row.subject ? (
                            <p className="text-xs font-semibold text-muted-foreground md:col-span-4">
                              {row.date
                                ? t("exams.plan.selectedAp", {
                                    subject: row.subject,
                                    date: formatDate(row.date, locale)
                                  })
                                : t("onboarding.field.dateUnavailable")}
                            </p>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-4 grid gap-4 border bg-surface p-4 md:grid-cols-3">
                    <input aria-label={t("onboarding.field.otherExam")} className={fieldClassName} onChange={(event) => update("otherExamName", event.target.value)} placeholder={t("onboarding.field.otherExam")} value={form.otherExamName} />
                    <input aria-label={t("onboarding.field.examDate")} className={fieldClassName} onChange={(event) => update("otherExamDate", event.target.value)} type="date" value={form.otherExamDate} />
                    <input aria-label={t("onboarding.field.targetScore")} className={fieldClassName} onChange={(event) => update("otherExamTarget", event.target.value)} placeholder={t("onboarding.field.targetScore")} value={form.otherExamTarget} />
                  </div>
                </div>
              </div>
            ) : null}

            {step === 3 ? (
              <div className="grid gap-5 md:grid-cols-2">
                {activityFields.map((field) => (
                  <Field helper={t("onboarding.field.commaHelp")} key={field} label={t(`onboarding.activity.${field}` as TranslationKey)}>
                    <textarea className={`${fieldClassName} min-h-24 py-3`} onChange={(event) => update("activities", { ...form.activities, [field]: event.target.value })} value={form.activities[field]} />
                  </Field>
                ))}
              </div>
            ) : null}

            {step === 4 ? (
              <div className="grid gap-5 md:grid-cols-2">
                <Field label={t("onboarding.field.essayStatus")}>
                  <select className={fieldClassName} onChange={(event) => update("essayStatus", event.target.value as OnboardingForm["essayStatus"])} value={form.essayStatus}>
                    <option value="yes">{t("onboarding.option.essay.yes")}</option>
                    <option value="no">{t("onboarding.option.essay.no")}</option>
                    <option value="not_yet">{t("onboarding.option.essay.notYet")}</option>
                  </select>
                </Field>
                <Field label={t("onboarding.field.essayStage")}>
                  <input className={fieldClassName} onChange={(event) => update("essayStage", event.target.value)} value={form.essayStage} />
                </Field>
                <Field helper={t("onboarding.field.commaHelp")} label={t("onboarding.field.supportPriorities")} required wide>
                  <input className={fieldClassName} onChange={(event) => update("supportPriorities", event.target.value)} required value={form.supportPriorities} />
                </Field>
                <Field helper={t("onboarding.field.commaHelp")} label={t("onboarding.field.careerInterests")} wide>
                  <input className={fieldClassName} onChange={(event) => update("careerInterests", event.target.value)} value={form.careerInterests} />
                </Field>
                <CheckField checked={form.researchInterest} label={t("onboarding.field.researchInterest")} onChange={(checked) => update("researchInterest", checked)} />
                <CheckField checked={form.financeLiteracyInterest} label={t("onboarding.field.financeInterest")} onChange={(checked) => update("financeLiteracyInterest", checked)} />
                <CheckField checked={form.munDebateInterest} label={t("onboarding.field.munInterest")} onChange={(checked) => update("munDebateInterest", checked)} />
              </div>
            ) : null}

            {step === 5 ? (
              <div className="space-y-6">
                <h2 className="text-2xl font-semibold">{t("onboarding.review.title")}</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {t("onboarding.review.description")}
                </p>
                <dl className="mt-6 grid gap-4 sm:grid-cols-2">
                  {[
                    [t("auth.fullName"), form.fullName],
                    [t("profile.schoolOrUniversity"), form.schoolOrUniversity],
                    [t("profile.intendedDegree"), form.intendedDegree],
                    [t("profile.intendedMajors"), form.intendedMajors.join(", ") || t("onboarding.review.notSure")],
                    [t("profile.targetCountries"), form.targetCountries],
                    [
                      t("onboarding.field.examDates"),
                      [
                        form.satDate ? `SAT ${form.satDate}` : "",
                        form.ieltsDate ? `IELTS ${form.ieltsDate}` : "",
                        ...form.apPlans
                          .filter((plan) => plan.subject || plan.date)
                          .map((plan) => `${plan.subject || "AP"} ${plan.date}`.trim()),
                        form.otherExamDate ? `${form.otherExamName || t("onboarding.field.otherExam")} ${form.otherExamDate}` : ""
                      ].filter(Boolean).join(", ") || t("onboarding.review.none")
                    ]
                  ].map(([label, value]) => (
                    <div className="border-l-4 border-navy bg-surface px-4 py-3" key={label}>
                      <dt className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">{label}</dt>
                      <dd className="mt-1 font-semibold">{value}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-6 border border-warning/30 bg-warning/10 p-4 text-sm leading-6 text-warning">
                  {t("onboarding.review.disclaimer")}
                </div>
                {form.essayStatus === "yes" ? (
                  <div className="mt-4 border border-success/30 bg-success/10 p-4 text-sm text-success">
                    {t("onboarding.review.essayAvailable")}
                  </div>
                ) : null}
                {readiness ? <ReadinessCard readiness={readiness} /> : null}
              </div>
            ) : null}

            {error ? (
              <div className="mt-6 border border-danger/35 bg-danger/10 p-4 text-sm text-danger" role="alert">
                <p>{error}</p>
                {missing.length ? (
                  <p className="mt-2 text-xs">{missing.join(", ")}</p>
                ) : null}
              </div>
            ) : null}

            <div className="mt-8 flex flex-col-reverse justify-between gap-3 border-t pt-5 sm:flex-row">
              <Button disabled={step === 0 || isSaving} onClick={() => setStep((current) => Math.max(0, current - 1))} type="button" variant="ghost">
                <ArrowLeft aria-hidden className="mr-2 size-4" />
                {t("onboarding.back")}
              </Button>
              {step < 5 ? (
                <Button disabled={isSaving || !canContinueStep} onClick={() => void saveCurrentStep(step + 1)} type="button">
                  {isSaving
                    ? t("onboarding.saving")
                    : canContinueStep
                      ? t("onboarding.saveContinue")
                      : t("onboarding.validation.completeRequired")}
                  <ArrowRight aria-hidden className="ml-2 size-4" />
                </Button>
              ) : (
                <Button disabled={isSaving || !canContinueStep} onClick={() => void finish()} type="button">
                  {isSaving
                    ? t("onboarding.finishing")
                    : canContinueStep
                      ? t("onboarding.finish")
                      : t("onboarding.validation.completeRequired")}
                </Button>
              )}
            </div>
          </Card>
        </section>

        <aside className="lg:col-span-2 xl:col-span-1">
          <AdmissionsProposals
            essayStage={form.essayStage}
            hasActivities={Object.values(form.activities).some(
              (value) => toList(value).length > 0
            )}
            hasExamPlan={Boolean(
              form.satDate ||
                form.ieltsDate ||
                form.apDate ||
                form.otherExamDate ||
                form.satScore ||
                form.ieltsScore ||
                form.toeflScore ||
                form.actScore
            )}
            majors={form.intendedMajors}
            onAddClass={(value) => {
              if (!toList(form.interestedClasses).includes(value)) {
                update(
                  "interestedClasses",
                  toText([...toList(form.interestedClasses), value])
                );
              }
            }}
            scholarshipNeed={form.scholarshipNeed}
            selectedClasses={toList(form.interestedClasses)}
            targetCountries={toList(form.targetCountries)}
          />
        </aside>
      </div>
      <UnsavedChangesDialog
        description={t("common.unsaved.description")}
        isSaving={isSaving}
        leaveWithoutSavingLabel={t("common.unsaved.leaveWithoutSaving")}
        onLeaveWithoutSaving={unsavedGuard.leaveWithoutSaving}
        onSaveAndLeave={saveOnboardingDraft}
        onStay={unsavedGuard.stay}
        open={unsavedGuard.isPromptOpen}
        saveAndLeaveLabel={t("common.unsaved.saveAndLeave")}
        stayLabel={t("common.unsaved.stay")}
        title={t("common.unsaved.title")}
      />
    </main>
  );
}
