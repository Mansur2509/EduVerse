"use client";

import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  assessmentQuestions,
  majorCatalog,
  recommendFromAssessment,
  type AssessmentAnswer,
  type RecommendationResult
} from "@/entities/profile";
import { useI18n, type TranslationKey } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { LanguageSwitcher } from "@/shared/ui/language-switcher";

const ASSESSMENT_DRAFT_KEY = "uniway.onboarding.assessment.v1";

export function MajorAssessment({
  initialMajors,
  onBack,
  onUse
}: {
  initialMajors: string[];
  onBack: () => void;
  onUse: (majors: string[], result: RecommendationResult) => void;
}) {
  const { t } = useI18n();
  const [section, setSection] = useState(1);
  const [answers, setAnswers] = useState<Record<string, AssessmentAnswer>>({});
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [selectedMajors, setSelectedMajors] = useState(initialMajors);
  const questions = assessmentQuestions.filter(
    (question) => question.section === section
  );
  const sectionComplete = questions.every((question) => answers[question.id]);
  const categoryNames = useMemo(
    () =>
      new Map(
        majorCatalog.map((category) => [category.id, t(category.labelKey)])
      ),
    [t]
  );

  useEffect(() => {
    try {
      const stored = window.sessionStorage.getItem(ASSESSMENT_DRAFT_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as {
          section?: number;
          answers?: Record<string, AssessmentAnswer>;
        };
        setSection(Math.max(1, Math.min(8, parsed.section ?? 1)));
        setAnswers(parsed.answers ?? {});
      }
    } finally {
      setDraftLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (draftLoaded) {
      window.sessionStorage.setItem(
        ASSESSMENT_DRAFT_KEY,
        JSON.stringify({ section, answers })
      );
    }
  }, [answers, draftLoaded, section]);

  function toggleMajor(value: string) {
    setSelectedMajors((current) =>
      current.includes(value)
        ? current.filter((major) => major !== value)
        : [...current, value]
    );
  }

  function next() {
    if (section < 8) {
      setSection((current) => current + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const nextResult = recommendFromAssessment(answers);
    setResult(nextResult);
    setSelectedMajors((current) =>
      current.length ? current : nextResult.majors.slice(0, 5).map((major) => major.value)
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b bg-navy px-4 py-4 text-navy-foreground sm:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <button
            className="flex items-center gap-2 text-sm font-semibold text-white/75 hover:text-white"
            onClick={onBack}
            type="button"
          >
            <ArrowLeft aria-hidden className="size-4" />
            {t("onboarding.recommendation.back")}
          </button>
          <LanguageSwitcher compact inverse />
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-hover">
          {result
            ? t("onboarding.recommendation.results")
            : t("admissions.assessment.progress", { current: section })}
        </p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-5xl">
          {t("admissions.assessment.title")}
        </h1>
        <p className="mt-4 max-w-3xl leading-7 text-muted-foreground">
          {t("admissions.assessment.description")}
        </p>

        {result ? (
          <div className="mt-8 space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              {result.clusters.map((cluster, index) => (
                <Card key={cluster}>
                  <span className="text-xs font-bold uppercase tracking-[0.14em] text-primary-hover">
                    0{index + 1}
                  </span>
                  <h2 className="mt-2 text-xl font-semibold">
                    {categoryNames.get(cluster)}
                  </h2>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">
                    {t(
                      `admissions.clusterReason.${cluster}` as TranslationKey
                    )}
                  </p>
                </Card>
              ))}
            </div>
            <Card>
              <h2 className="text-2xl font-semibold">
                {t("onboarding.field.majors")}
              </h2>
              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                {result.majors.map((major) => (
                  <label
                    className="flex min-h-11 cursor-pointer items-center gap-3 border bg-surface px-3 text-sm font-medium"
                    key={major.id}
                  >
                    <input
                      checked={selectedMajors.includes(major.value)}
                      className="size-4 accent-primary"
                      onChange={() => toggleMajor(major.value)}
                      type="checkbox"
                    />
                    {major.labelKey ? t(major.labelKey) : major.value}
                  </label>
                ))}
              </div>
              <Button
                className="mt-6"
                disabled={!selectedMajors.length}
                onClick={() => {
                  window.sessionStorage.removeItem(ASSESSMENT_DRAFT_KEY);
                  onUse(selectedMajors, result);
                }}
                type="button"
              >
                <Check aria-hidden className="mr-2 size-4" />
                {t("admissions.assessment.use")}
              </Button>
            </Card>
          </div>
        ) : (
          <>
            <div className="mt-7 h-1.5 bg-muted">
              <div
                className="h-full bg-primary"
                style={{ width: `${(section / 8) * 100}%` }}
              />
            </div>
            <Card className="mt-6">
              <h2 className="text-2xl font-semibold">
                {t(
                  `admissions.assessment.section${section}` as TranslationKey
                )}
              </h2>
              <div className="mt-6 space-y-6">
                {questions.map((question, questionIndex) => (
                  <fieldset className="border-t pt-5 first:border-t-0 first:pt-0" key={question.id}>
                    <legend className="text-sm font-semibold">
                      {questionIndex + 1}. {t(question.labelKey)}
                    </legend>
                    <div className="mt-3 grid grid-cols-5 gap-2">
                      {([1, 2, 3, 4, 5] as AssessmentAnswer[]).map((answer) => (
                        <label
                          className={
                            answers[question.id] === answer
                              ? "cursor-pointer border border-primary bg-primary px-2 py-3 text-center text-xs font-semibold text-primary-foreground"
                              : "cursor-pointer border bg-surface px-2 py-3 text-center text-xs text-muted-foreground hover:bg-elevated"
                          }
                          key={answer}
                        >
                          <input
                            checked={answers[question.id] === answer}
                            className="sr-only"
                            name={question.id}
                            onChange={() =>
                              setAnswers((current) => ({
                                ...current,
                                [question.id]: answer
                              }))
                            }
                            type="radio"
                          />
                          <span className="block text-base font-semibold">{answer}</span>
                          <span className="mt-1 hidden leading-4 lg:block">
                            {t(
                              `admissions.assessment.scale${answer}` as TranslationKey
                            )}
                          </span>
                        </label>
                      ))}
                    </div>
                  </fieldset>
                ))}
              </div>
            </Card>
            <div className="mt-6 flex justify-between gap-3">
              <Button
                disabled={section === 1}
                onClick={() => setSection((current) => current - 1)}
                type="button"
                variant="ghost"
              >
                <ArrowLeft aria-hidden className="mr-2 size-4" />
                {t("admissions.assessment.previous")}
              </Button>
              <Button disabled={!sectionComplete} onClick={next} type="button">
                {section < 8
                  ? t("admissions.assessment.next")
                  : t("admissions.assessment.results")}
                <ArrowRight aria-hidden className="ml-2 size-4" />
              </Button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
