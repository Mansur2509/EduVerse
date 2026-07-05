"use client";

import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  PROFILE_ASSESSMENT_CATEGORIES,
  type Activity,
  type AIProfileAssessment,
  type BudgetFlexibility,
  type CourseRigorLevel,
  type EssayDraft,
  type Honor,
  type Olympiad,
  type PlannedExam,
  type PortfolioProject,
  type ProfileAssessmentEnvelope,
  type ProfileCompletion,
  type Recommender,
  type ResearchProject,
  type ScholarshipNeed,
  type Sport,
  type StudentProfileDetails,
  type TestScores,
  type Volunteer
} from "@/entities/profile";
import type { OfficialExamDate } from "@/entities/exam";
import { useAuth } from "@/features/auth/model/auth-context";
import { type ApPlanRow, getOfficialExamDatesRequest, PlannedExamFields } from "@/features/exams";
import {
  getProfileAssessmentLatestRequest,
  getProfileCompletionRequest,
  getProfileRequest,
  runProfileAssessmentRequest,
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
  portfolioDisplay,
  volunteerFields,
  volunteerDisplay,
  recommenderFields,
  recommenderDisplay
} from "@/features/profile/lib/profile-items-config";
import { ProfileItemSection } from "@/features/profile/ui/profile-item-section";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";
import { useUnsavedChangesGuard } from "@/shared/lib/use-unsaved-changes-guard";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { fieldClassName } from "@/shared/ui/field";
import { HelpTooltip } from "@/shared/ui/help-tooltip";
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
  courseRigorLevel: CourseRigorLevel;
  apCoursesCount: string;
  ibCoursesCount: string;
  aLevelSubjectsCount: string;
  honorsCoursesCount: string;
  educationStatus: string;
  intendedDegree: string;
  targetCountries: string;
  intendedMajors: string;
  targetUniversities: string;
  scholarshipNeed: ScholarshipNeed;
  annualBudgetAmount: string;
  annualBudgetCurrency: string;
  budgetFlexibility: BudgetFlexibility;
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
  apPlans: ApPlanRow[];
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
  courseRigorLevel: "unknown",
  apCoursesCount: "",
  ibCoursesCount: "",
  aLevelSubjectsCount: "",
  honorsCoursesCount: "",
  educationStatus: "",
  intendedDegree: "",
  targetCountries: "",
  intendedMajors: "",
  targetUniversities: "",
  scholarshipNeed: "unsure",
  annualBudgetAmount: "",
  annualBudgetCurrency: "USD",
  budgetFlexibility: "unknown",
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
  apPlans: [{ id: "ap-1", subject: "", date: "", target: "" }],
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
  const satPlan = plannedExams.find((exam) => exam.exam_type === "SAT" || exam.name === "SAT");
  const ieltsPlan = plannedExams.find(
    (exam) => exam.exam_type === "IELTS" || exam.name === "IELTS"
  );
  // Every AP row (from onboarding's per-subject planning, e.g. "AP Biology")
  // is kept here, not just a single exam literally named "AP" -- otherwise
  // saving from this screen would silently drop the other rows.
  const apPlans: ApPlanRow[] = plannedExams
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
    schoolOrUniversity: profile.school_or_university,
    grade: profile.grade,
    expectedGraduationYear: profile.expected_graduation_year?.toString() ?? "",
    gpa: profile.original_gpa_value === null ? "" : String(profile.original_gpa_value),
    gpaScale: profile.original_gpa_scale === null ? "" : String(profile.original_gpa_scale),
    gpaScaleType: profile.original_gpa_scale_type,
    curriculumType: profile.curriculum_type,
    curriculumCountry: profile.curriculum_country,
    courseRigorLevel: profile.course_rigor_level,
    apCoursesCount: profile.ap_courses_count === null ? "" : String(profile.ap_courses_count),
    ibCoursesCount: profile.ib_courses_count === null ? "" : String(profile.ib_courses_count),
    aLevelSubjectsCount:
      profile.a_level_subjects_count === null ? "" : String(profile.a_level_subjects_count),
    honorsCoursesCount:
      profile.honors_courses_count === null ? "" : String(profile.honors_courses_count),
    educationStatus: profile.education_status,
    intendedDegree: profile.intended_degree,
    targetCountries: listToText(profile.target_countries),
    intendedMajors: listToText(profile.intended_majors),
    targetUniversities: listToText(profile.target_universities),
    scholarshipNeed: profile.scholarship_need,
    annualBudgetAmount:
      profile.annual_budget_amount === null ? "" : String(profile.annual_budget_amount),
    annualBudgetCurrency: profile.annual_budget_currency || "USD",
    budgetFlexibility: profile.budget_flexibility,
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
    apPlans: apPlans.length ? apPlans : [{ id: "ap-1", subject: "", date: "", target: "" }],
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
  label: ReactNode;
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
  id,
  title,
  description,
  children
}: {
  id?: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card className="scroll-mt-24 p-5" id={id}>
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

function ProfileAssessmentPanel({
  envelope,
  assessment,
  topCategories,
  isRefreshing,
  hasError,
  onRefresh
}: {
  envelope: ProfileAssessmentEnvelope | null;
  assessment: AIProfileAssessment | null;
  topCategories: typeof PROFILE_ASSESSMENT_CATEGORIES;
  isRefreshing: boolean;
  hasError: boolean;
  onRefresh: () => void;
}) {
  const { locale, t } = useI18n();
  const canRefresh = Boolean(envelope?.can_refresh);
  const refreshDisabled = isRefreshing || !canRefresh;

  return (
    <Card className="scroll-mt-24 p-5" id="profile-assessment">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
            {t("profileAssessment.eyebrow")}
          </p>
          <h2 className="mt-1 text-lg font-semibold">{t("profileAssessment.title")}</h2>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
            {t("profileAssessment.description")}
          </p>
        </div>
        <Button
          disabled={refreshDisabled}
          onClick={onRefresh}
          size="sm"
          type="button"
          variant="secondary"
        >
          {isRefreshing
            ? t("profileAssessment.refreshing")
            : t("profileAssessment.refresh")}
        </Button>
      </div>

      {hasError ? (
        <div className="mt-4 rounded-sm border border-warning/35 bg-warning/10 p-3 text-xs text-warning">
          {t("profileAssessment.error")}
        </div>
      ) : null}

      {!assessment ? (
        <div className="mt-4 rounded-sm border border-dashed bg-elevated/35 p-4">
          <p className="text-sm font-semibold">
            {envelope?.ai_available
              ? t("profileAssessment.empty")
              : t("profileAssessment.unavailable")}
          </p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {t("profileAssessment.emptyDescription")}
          </p>
        </div>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
          <div className="border bg-surface p-4">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
              {t("profileAssessment.overall")}
            </p>
            <div className="mt-2 flex items-end gap-2">
              <span className="text-4xl font-semibold text-accent">
                {assessment.overall_profile_score}
              </span>
              <span className="pb-1 text-xs font-semibold text-muted-foreground">
                {t("profileAssessment.outOf100")}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge className="text-xs">
                {t(`profileAssessment.confidence.${assessment.confidence}` as TranslationKey)}
              </Badge>
              {assessment.is_stale ? (
                <Badge className="border-warning/35 bg-warning/10 text-warning">
                  {t("profileAssessment.stale")}
                </Badge>
              ) : (
                <Badge className="border-success/35 bg-success/10 text-success">
                  {t("profileAssessment.current")}
                </Badge>
              )}
            </div>
            <p className="mt-3 text-xs leading-5 text-muted-foreground">
              {t("profileAssessment.lastAssessed", {
                date: formatDateTime(assessment.created_at, locale)
              })}
            </p>
          </div>

          <div className="space-y-4">
            <p className="text-sm leading-6 text-muted-foreground">
              {assessment.public_summary || t("profileAssessment.summaryFallback")}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {topCategories.map((category) => (
                <div className="rounded-sm border bg-surface p-3" key={category}>
                  <div className="flex items-center justify-between gap-3 text-xs">
                    <span className="font-semibold">
                      {t(`profileAssessment.category.${category}` as TranslationKey)}
                    </span>
                    <span className="font-bold text-accent">
                      {assessment.category_scores[category]}/10
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-sm bg-elevated">
                    <div
                      className="h-full bg-primary"
                      style={{
                        width: `${Math.max(0, Math.min(100, assessment.category_scores[category] * 10))}%`
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-primary-hover">
                  {t("profileAssessment.missingData")}
                </p>
                {assessment.missing_data.length ? (
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                    {assessment.missing_data.slice(0, 5).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {t("profileAssessment.noMissingData")}
                  </p>
                )}
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-primary-hover">
                  {t("profileAssessment.improvementAreas")}
                </p>
                {assessment.improvement_areas.length ? (
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                    {assessment.improvement_areas.slice(0, 5).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {t("profileAssessment.noImprovementAreas")}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {envelope?.reason === "daily_limit_reached" && envelope.next_available_at ? (
        <p className="mt-3 rounded-sm border bg-elevated/45 p-3 text-xs text-muted-foreground">
          {t("profileAssessment.dailyLimit", {
            date: formatDateTime(envelope.next_available_at, locale)
          })}
        </p>
      ) : null}
      <p className="mt-3 text-xs leading-5 text-muted-foreground">
        {envelope?.disclaimer ?? t("profileAssessment.disclaimer")}
      </p>
    </Card>
  );
}

export function ProfileScreen() {
  const { refreshUser } = useAuth();
  const { t } = useI18n();
  const [profile, setProfile] = useState<StudentProfileDetails | null>(null);
  const [completion, setCompletion] = useState<ProfileCompletion | null>(null);
  const [profileAssessment, setProfileAssessment] =
    useState<ProfileAssessmentEnvelope | null>(null);
  const [form, setForm] = useState<ProfileFormState>(emptyForm);
  const [savedForm, setSavedForm] = useState<ProfileFormState>(emptyForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);
  const [saved, setSaved] = useState(false);
  const [assessmentError, setAssessmentError] = useState(false);
  const [isRefreshingAssessment, setIsRefreshingAssessment] = useState(false);

  // Structured profile items
  const [activities, setActivities] = useState<Activity[]>([]);
  const [honors, setHonors] = useState<Honor[]>([]);
  const [olympiads, setOlympiads] = useState<Olympiad[]>([]);
  const [sports, setSports] = useState<Sport[]>([]);
  const [research, setResearch] = useState<ResearchProject[]>([]);
  const [essays, setEssays] = useState<EssayDraft[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioProject[]>([]);
  const [volunteering, setVolunteering] = useState<Volunteer[]>([]);
  const [recommenders, setRecommenders] = useState<Recommender[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [officialDates, setOfficialDates] = useState<OfficialExamDate[]>([]);
  const [officialDatesError, setOfficialDatesError] = useState(false);

  const loadProfile = useCallback(async () => {
    setIsLoading(true);
    setLoadFailed(false);
    setAssessmentError(false);
    try {
      const [profileResponse, completionResponse, assessmentResponse] =
        await Promise.allSettled([
          getProfileRequest(),
          getProfileCompletionRequest(),
          getProfileAssessmentLatestRequest()
        ]);
      if (profileResponse.status !== "fulfilled" || completionResponse.status !== "fulfilled") {
        throw new Error("profile_load_failed");
      }
      setProfile(profileResponse.value);
      setCompletion(completionResponse.value);
      if (assessmentResponse.status === "fulfilled") {
        setProfileAssessment(assessmentResponse.value);
      } else {
        setAssessmentError(true);
      }
      const nextForm = profileToForm(profileResponse.value);
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
      const [
        activitiesRes,
        honorsRes,
        olympiadsRes,
        sportsRes,
        researchRes,
        essaysRes,
        portfolioRes,
        volunteeringRes,
        recommendersRes
      ] = await Promise.allSettled([
        getProfileItemsRequest<Activity>("activities"),
        getProfileItemsRequest<Honor>("honors"),
        getProfileItemsRequest<Olympiad>("olympiads"),
        getProfileItemsRequest<Sport>("sports"),
        getProfileItemsRequest<ResearchProject>("research-projects"),
        getProfileItemsRequest<EssayDraft>("essays"),
        getProfileItemsRequest<PortfolioProject>("portfolio-projects"),
        getProfileItemsRequest<Volunteer>("volunteering"),
        getProfileItemsRequest<Recommender>("recommenders")
      ]);
      if (activitiesRes.status === "fulfilled") setActivities(activitiesRes.value.results);
      if (honorsRes.status === "fulfilled") setHonors(honorsRes.value.results);
      if (olympiadsRes.status === "fulfilled") setOlympiads(olympiadsRes.value.results);
      if (sportsRes.status === "fulfilled") setSports(sportsRes.value.results);
      if (researchRes.status === "fulfilled") setResearch(researchRes.value.results);
      if (essaysRes.status === "fulfilled") setEssays(essaysRes.value.results);
      if (portfolioRes.status === "fulfilled") setPortfolio(portfolioRes.value.results);
      if (volunteeringRes.status === "fulfilled") setVolunteering(volunteeringRes.value.results);
      if (recommendersRes.status === "fulfilled") setRecommenders(recommendersRes.value.results);
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

  useEffect(() => {
    let cancelled = false;
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
  }, []);

  function updateField<Key extends keyof ProfileFormState>(
    field: Key,
    value: ProfileFormState[Key]
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateApPlan(rowId: string, patch: Partial<ApPlanRow>) {
    setForm((current) => ({
      ...current,
      apPlans: current.apPlans.map((row) => (row.id === rowId ? { ...row, ...patch } : row))
    }));
  }

  function addApPlan() {
    setForm((current) => ({
      ...current,
      apPlans: [
        ...current.apPlans,
        { id: `ap-${Date.now()}`, subject: "", date: "", target: "" }
      ]
    }));
  }

  function removeApPlan(rowId: string) {
    setForm((current) => {
      if (current.apPlans.length <= 1) return current;
      return { ...current, apPlans: current.apPlans.filter((row) => row.id !== rowId) };
    });
  }

  const hasUnsavedProfileChanges = JSON.stringify(form) !== JSON.stringify(savedForm);
  const unsavedProfileGuard = useUnsavedChangesGuard({
    browserMessage: t("common.unsaved.browserMessage"),
    isDirty: hasUnsavedProfileChanges
  });
  const assessment = profileAssessment?.assessment ?? null;
  const topAssessmentCategories = useMemo(
    () =>
      assessment
        ? [...PROFILE_ASSESSMENT_CATEGORIES]
            .sort(
              (left, right) =>
                assessment.category_scores[right] - assessment.category_scores[left]
            )
            .slice(0, 5)
        : [],
    [assessment]
  );

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
        course_rigor_level: form.courseRigorLevel,
        ap_courses_count: form.apCoursesCount === "" ? null : Number(form.apCoursesCount),
        ib_courses_count: form.ibCoursesCount === "" ? null : Number(form.ibCoursesCount),
        a_level_subjects_count:
          form.aLevelSubjectsCount === "" ? null : Number(form.aLevelSubjectsCount),
        honors_courses_count:
          form.honorsCoursesCount === "" ? null : Number(form.honorsCoursesCount),
        education_status: form.educationStatus,
        intended_degree: form.intendedDegree,
        target_countries: textToList(form.targetCountries),
        intended_majors: textToList(form.intendedMajors),
        target_universities: textToList(form.targetUniversities),
        scholarship_need: form.scholarshipNeed,
        annual_budget_amount: form.annualBudgetAmount === "" ? null : form.annualBudgetAmount,
        annual_budget_currency: form.annualBudgetCurrency,
        budget_flexibility: form.budgetFlexibility,
        interests: textToList(form.interests),
        languages: textToList(form.languages),
        test_scores: testScores,
        exam_plans: {
          taken: profile?.exam_plans.taken ?? [],
          planned: [
            ...(
              [
                { name: "SAT", exam_type: "SAT", date: form.satDate, target_score: form.satTarget },
                {
                  name: "IELTS",
                  exam_type: "IELTS",
                  date: form.ieltsDate,
                  target_score: form.ieltsTarget
                },
                ...form.apPlans
                  .filter((plan) => plan.subject.trim() && (plan.date || plan.target.trim()))
                  .map((plan) => ({
                    name: plan.subject.trim(),
                    exam_type: "AP" as const,
                    date: plan.date,
                    target_score: plan.target
                  }))
              ] satisfies PlannedExam[]
            ).filter((exam) => exam.date || exam.target_score),
            // Preserve any planned exam this screen doesn't manage (e.g. ACT
            // or a custom "Other" entry from onboarding) instead of silently
            // dropping it on every Profile save.
            ...(profile?.exam_plans.planned ?? []).filter(
              (exam) => !["SAT", "IELTS", "AP"].includes(exam.exam_type ?? "")
            )
          ]
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

  async function handleRefreshAssessment() {
    setIsRefreshingAssessment(true);
    setAssessmentError(false);
    try {
      const response = await runProfileAssessmentRequest();
      setProfileAssessment(response);
    } catch {
      setAssessmentError(true);
    } finally {
      setIsRefreshingAssessment(false);
    }
  }

  // Item CRUD handlers
  const createItem = <T extends { id: number }>(
    type: "activities" | "honors" | "olympiads" | "sports" | "research-projects" | "essays" | "portfolio-projects" | "volunteering" | "recommenders",
    setter: (updater: (prev: T[]) => T[]) => void
  ) =>
    async (data: Record<string, unknown>) => {
      const result = await createProfileItemRequest(type, data);
      setter((prev: T[]) => [result as T, ...prev]);
      await getProfileCompletionRequest().then(setCompletion);
    };

  const updateItem = <T extends { id: number }>(
    type: "activities" | "honors" | "olympiads" | "sports" | "research-projects" | "essays" | "portfolio-projects" | "volunteering" | "recommenders",
    setter: (updater: (prev: T[]) => T[]) => void
  ) =>
    async (id: number, data: Record<string, unknown>) => {
      const result = await updateProfileItemRequest(type, id, data);
      setter((prev: T[]) => prev.map((item) => (item.id === id ? (result as T) : item)));
      await getProfileCompletionRequest().then(setCompletion);
    };

  const deleteItem = <T extends { id: number }>(
    type: "activities" | "honors" | "olympiads" | "sports" | "research-projects" | "essays" | "portfolio-projects" | "volunteering" | "recommenders",
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

  const structuredSections: Array<{
    id: string;
    title: TranslationKey;
    count: number;
  }> = [
    { id: "profile-section-activities", title: "profile.sections.activities", count: activities.length },
    { id: "profile-section-honors", title: "profile.sections.honors", count: honors.length },
    { id: "profile-section-olympiads", title: "profile.sections.olympiads", count: olympiads.length },
    { id: "profile-section-sports", title: "profile.sections.sports", count: sports.length },
    { id: "profile-section-research", title: "profile.sections.research", count: research.length },
    { id: "profile-section-volunteering", title: "profile.sections.volunteering", count: volunteering.length },
    { id: "profile-section-recommenders", title: "profile.sections.recommenders", count: recommenders.length },
    { id: "profile-section-essays", title: "profile.sections.essays", count: essays.length },
    { id: "profile-section-portfolio", title: "profile.sections.portfolio", count: portfolio.length }
  ];

  const sectionStatusLabel = (count: number) =>
    count > 0 ? t("profile.navigation.complete") : t("profile.navigation.needsEvidence");
  const sectionStatusTone = (count: number) => (count > 0 ? "complete" : "missing");

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

      <Card className="p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
              {t("profile.navigation.eyebrow")}
            </p>
            <h2 className="mt-1 text-lg font-semibold">{t("profile.navigation.title")}</h2>
            <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
              {t("profile.navigation.description")}
            </p>
          </div>
          <Button asChild size="sm" variant="secondary">
            <a href="#profile-section-activities">{t("profile.navigation.start")}</a>
          </Button>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {structuredSections.map((section) => (
            <a
              className="flex items-center justify-between gap-3 rounded-sm border bg-elevated/35 px-3 py-2 text-xs transition-colors hover:bg-elevated"
              href={`#${section.id}`}
              key={section.id}
            >
              <span className="font-semibold">{t(section.title)}</span>
              <span className="flex shrink-0 items-center gap-1.5">
                <span className="text-muted-foreground">
                  {t("profile.navigation.itemCount", { count: section.count })}
                </span>
                <span
                  className={`rounded-sm border px-1.5 py-0.5 text-[0.62rem] font-semibold uppercase tracking-wide ${
                    section.count > 0
                      ? "border-success/35 bg-success/10 text-success"
                      : "border-warning/35 bg-warning/10 text-warning"
                  }`}
                >
                  {sectionStatusLabel(section.count)}
                </span>
              </span>
            </a>
          ))}
        </div>
      </Card>

      <ProfileAssessmentPanel
        assessment={assessment}
        envelope={profileAssessment}
        hasError={assessmentError}
        isRefreshing={isRefreshingAssessment}
        onRefresh={() => void handleRefreshAssessment()}
        topCategories={topAssessmentCategories}
      />

      <ProfileSection
        description={t("profile.sections.personalHelp")}
        id="profile-foundation-personal"
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
        id="profile-foundation-education"
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
            placeholder={t("onboarding.field.gpaPlaceholder")}
            step="0.01"
            type="number"
            value={form.gpa}
          />
        </Field>
        <Field label={t("onboarding.field.gpaScale")}>
          <input
            className={fieldClassName}
            onChange={(event) => updateField("gpaScale", event.target.value)}
            placeholder={t("onboarding.field.gpaScalePlaceholder")}
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
        <Field
          label={
            <>
              {t("profile.courseRigorLevel")} <HelpTooltip label={t("help.curriculumRigor")} />
            </>
          }
        >
          <select
            className={fieldClassName}
            onChange={(event) =>
              updateField("courseRigorLevel", event.target.value as CourseRigorLevel)
            }
            value={form.courseRigorLevel}
          >
            <option value="unknown">{t("profile.courseRigorLevel.unknown")}</option>
            <option value="standard">{t("profile.courseRigorLevel.standard")}</option>
            <option value="advanced">{t("profile.courseRigorLevel.advanced")}</option>
            <option value="highly_advanced">{t("profile.courseRigorLevel.highly_advanced")}</option>
          </select>
        </Field>
        <Field label={t("profile.apCoursesCount")}>
          <input
            className={fieldClassName}
            max={40}
            min={0}
            onChange={(event) => updateField("apCoursesCount", event.target.value)}
            type="number"
            value={form.apCoursesCount}
          />
        </Field>
        <Field label={t("profile.ibCoursesCount")}>
          <input
            className={fieldClassName}
            max={40}
            min={0}
            onChange={(event) => updateField("ibCoursesCount", event.target.value)}
            type="number"
            value={form.ibCoursesCount}
          />
        </Field>
        <Field label={t("profile.aLevelSubjectsCount")}>
          <input
            className={fieldClassName}
            max={40}
            min={0}
            onChange={(event) => updateField("aLevelSubjectsCount", event.target.value)}
            type="number"
            value={form.aLevelSubjectsCount}
          />
        </Field>
        <Field label={t("profile.honorsCoursesCount")}>
          <input
            className={fieldClassName}
            max={40}
            min={0}
            onChange={(event) => updateField("honorsCoursesCount", event.target.value)}
            type="number"
            value={form.honorsCoursesCount}
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
        {profile?.curriculum_rigor ? (
          <div className="rounded-sm border bg-surface p-3 text-xs text-muted-foreground sm:col-span-2">
            <p className="font-semibold text-foreground">
              {t("profile.curriculumRigorSummary", {
                score: String(profile.curriculum_rigor.rigor_score),
                confidence: t(
                  `profile.curriculumRigor.confidence.${profile.curriculum_rigor.rigor_confidence}` as TranslationKey
                )
              })}
            </p>
            {profile.curriculum_rigor.missing_curriculum_data.length > 0 ? (
              <ul className="mt-2 list-disc space-y-0.5 pl-4">
                {profile.curriculum_rigor.missing_curriculum_data.map((code) => (
                  <li key={code}>
                    {t(`profile.curriculumRigor.missing.${code}` as TranslationKey)}
                  </li>
                ))}
              </ul>
            ) : null}
            {profile.major_curriculum_fit.recommended_coursework.length > 0 ? (
              <p className="mt-2">
                {t("profile.curriculumRigor.recommendedCoursework")}{" "}
                {profile.major_curriculum_fit.recommended_coursework
                  .map((code) => t(`profile.coursework.${code}` as TranslationKey))
                  .join(", ")}
              </p>
            ) : null}
          </div>
        ) : null}
      </ProfileSection>

      <ProfileSection
        description={t("profile.sections.admissionsHelp")}
        id="profile-foundation-admissions"
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
          label={
            <>
              {t("profile.annualBudgetAmount")} <HelpTooltip label={t("help.budgetComparison")} />
            </>
          }
        >
          <input
            className={fieldClassName}
            min={0}
            onChange={(event) => updateField("annualBudgetAmount", event.target.value)}
            placeholder={t("profile.annualBudgetAmountPlaceholder")}
            step="0.01"
            type="number"
            value={form.annualBudgetAmount}
          />
        </Field>
        <Field label={t("profile.annualBudgetCurrency")}>
          <input
            className={fieldClassName}
            maxLength={10}
            onChange={(event) =>
              updateField("annualBudgetCurrency", event.target.value.toUpperCase())
            }
            placeholder="USD"
            value={form.annualBudgetCurrency}
          />
        </Field>
        <Field label={t("profile.budgetFlexibility")}>
          <select
            className={fieldClassName}
            onChange={(event) =>
              updateField("budgetFlexibility", event.target.value as BudgetFlexibility)
            }
            value={form.budgetFlexibility}
          >
            <option value="unknown">{t("profile.budgetFlexibility.unknown")}</option>
            <option value="strict">{t("profile.budgetFlexibility.strict")}</option>
            <option value="flexible">{t("profile.budgetFlexibility.flexible")}</option>
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
            placeholder={t("profile.targetUniversitiesPlaceholder")}
            value={form.targetUniversities}
          />
        </Field>
      </ProfileSection>

      <ProfileSection
        description={t("profile.sections.testsHelp")}
        id="profile-foundation-tests"
        title={t("profile.sections.tests")}
      >
        <Field label={t("profile.test.sat")}>
          <input
            className={fieldClassName}
            max={1600}
            min={400}
            onChange={(event) => updateField("sat", event.target.value)}
            placeholder={t("onboarding.field.satScorePlaceholder")}
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
            placeholder={t("onboarding.field.ieltsScorePlaceholder")}
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
          <PlannedExamFields
            apPlans={form.apPlans}
            ieltsDate={form.ieltsDate}
            ieltsTarget={form.ieltsTarget}
            officialDates={officialDates}
            officialDatesError={officialDatesError}
            onAddApPlan={addApPlan}
            onIeltsDateChange={(value) => updateField("ieltsDate", value)}
            onIeltsTargetChange={(value) => updateField("ieltsTarget", value)}
            onRemoveApPlan={removeApPlan}
            onSatDateChange={(value) => updateField("satDate", value)}
            onSatTargetChange={(value) => updateField("satTarget", value)}
            onUpdateApPlan={updateApPlan}
            satDate={form.satDate}
            satTarget={form.satTarget}
          />
        </Field>
      </ProfileSection>

      <ProfileSection
        description={t("profile.sections.preferencesHelp")}
        id="profile-foundation-preferences"
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
        id="profile-foundation-contact"
        title={t("profile.sections.contact")}
      >
        <Field helper={t("profile.telegramHelp")} label={t("profile.telegram")}>
          <input
            className={fieldClassName}
            maxLength={33}
            onChange={(event) => updateField("telegramUsername", event.target.value)}
            placeholder={t("profile.telegramPlaceholder")}
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
          id="profile-section-activities"
          items={activities}
          fields={activityFields}
          onAdd={createItem("activities", setActivities)}
          onUpdate={updateItem("activities", setActivities)}
          onDelete={deleteItem("activities", setActivities)}
          itemDisplay={activityDisplay}
          statusLabel={sectionStatusLabel(activities.length)}
          statusTone={sectionStatusTone(activities.length)}
          title="profile.sections.activities"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.honorsHelp"
          id="profile-section-honors"
          items={honors}
          fields={honorFields}
          onAdd={createItem("honors", setHonors)}
          onUpdate={updateItem("honors", setHonors)}
          onDelete={deleteItem("honors", setHonors)}
          itemDisplay={honorDisplay}
          statusLabel={sectionStatusLabel(honors.length)}
          statusTone={sectionStatusTone(honors.length)}
          title="profile.sections.honors"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.olympiadsHelp"
          id="profile-section-olympiads"
          items={olympiads}
          fields={olympiadFields}
          onAdd={createItem("olympiads", setOlympiads)}
          onUpdate={updateItem("olympiads", setOlympiads)}
          onDelete={deleteItem("olympiads", setOlympiads)}
          itemDisplay={olympiadDisplay}
          statusLabel={sectionStatusLabel(olympiads.length)}
          statusTone={sectionStatusTone(olympiads.length)}
          title="profile.sections.olympiads"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.sportsHelp"
          id="profile-section-sports"
          items={sports}
          fields={sportFields}
          onAdd={createItem("sports", setSports)}
          onUpdate={updateItem("sports", setSports)}
          onDelete={deleteItem("sports", setSports)}
          itemDisplay={sportDisplay}
          statusLabel={sectionStatusLabel(sports.length)}
          statusTone={sectionStatusTone(sports.length)}
          title="profile.sections.sports"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.researchHelp"
          id="profile-section-research"
          items={research}
          fields={researchFields}
          onAdd={createItem("research-projects", setResearch)}
          onUpdate={updateItem("research-projects", setResearch)}
          onDelete={deleteItem("research-projects", setResearch)}
          itemDisplay={researchDisplay}
          statusLabel={sectionStatusLabel(research.length)}
          statusTone={sectionStatusTone(research.length)}
          title="profile.sections.research"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.essaysHelp"
          id="profile-section-essays"
          items={essays}
          fields={essayFields}
          onAdd={createItem("essays", setEssays)}
          onUpdate={updateItem("essays", setEssays)}
          onDelete={deleteItem("essays", setEssays)}
          itemDisplay={essayDisplay}
          statusLabel={sectionStatusLabel(essays.length)}
          statusTone={sectionStatusTone(essays.length)}
          title="profile.sections.essays"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.portfolioHelp"
          id="profile-section-portfolio"
          items={portfolio}
          fields={portfolioFields}
          onAdd={createItem("portfolio-projects", setPortfolio)}
          onUpdate={updateItem("portfolio-projects", setPortfolio)}
          onDelete={deleteItem("portfolio-projects", setPortfolio)}
          itemDisplay={portfolioDisplay}
          statusLabel={sectionStatusLabel(portfolio.length)}
          statusTone={sectionStatusTone(portfolio.length)}
          title="profile.sections.portfolio"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.volunteeringHelp"
          id="profile-section-volunteering"
          items={volunteering}
          fields={volunteerFields}
          onAdd={createItem("volunteering", setVolunteering)}
          onUpdate={updateItem("volunteering", setVolunteering)}
          onDelete={deleteItem("volunteering", setVolunteering)}
          itemDisplay={volunteerDisplay}
          statusLabel={sectionStatusLabel(volunteering.length)}
          statusTone={sectionStatusTone(volunteering.length)}
          title="profile.sections.volunteering"
          isLoading={itemsLoading}
        />
        <ProfileItemSection
          description="profile.sections.recommendersHelp"
          id="profile-section-recommenders"
          items={recommenders}
          fields={recommenderFields}
          onAdd={createItem("recommenders", setRecommenders)}
          onUpdate={updateItem("recommenders", setRecommenders)}
          onDelete={deleteItem("recommenders", setRecommenders)}
          itemDisplay={recommenderDisplay}
          statusLabel={sectionStatusLabel(recommenders.length)}
          statusTone={sectionStatusTone(recommenders.length)}
          title="profile.sections.recommenders"
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
