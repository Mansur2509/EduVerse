import {
  BookOpenCheck,
  CalendarDays,
  CircleDollarSign,
  FilePenLine,
  FlaskConical,
  GraduationCap,
  Route,
  Shapes,
  type LucideIcon
} from "lucide-react";

import type { TranslationKey } from "@/shared/i18n";

export type BetaModuleId =
  | "universities"
  | "roadmap"
  | "essays"
  | "exams"
  | "finance"
  | "activities"
  | "research"
  | "pricing";

export type BetaModuleConfig = {
  icon: LucideIcon;
  eyebrowKey: TranslationKey;
  titleKey: TranslationKey;
  descriptionKey: TranslationKey;
  statusKey: TranslationKey;
  primaryActionKey: TranslationKey;
  primaryHref: string;
  secondaryActionKey: TranslationKey;
  secondaryHref: string;
  nextFeatureKey: TranslationKey;
  disclaimerKey?: TranslationKey;
  features: Array<{
    titleKey: TranslationKey;
    detailKey: TranslationKey;
  }>;
};

export const betaModules: Record<BetaModuleId, BetaModuleConfig> = {
  universities: {
    icon: GraduationCap,
    eyebrowKey: "beta.universities.eyebrow",
    titleKey: "beta.universities.title",
    descriptionKey: "beta.universities.description",
    statusKey: "beta.status.preview",
    primaryActionKey: "beta.actions.completeProfile",
    primaryHref: "/profile",
    secondaryActionKey: "beta.actions.exploreEvents",
    secondaryHref: "/events",
    nextFeatureKey: "beta.universities.next",
    disclaimerKey: "beta.disclaimer.admissions",
    features: [
      {
        titleKey: "beta.universities.feature1.title",
        detailKey: "beta.universities.feature1.detail"
      },
      {
        titleKey: "beta.universities.feature2.title",
        detailKey: "beta.universities.feature2.detail"
      },
      {
        titleKey: "beta.universities.feature3.title",
        detailKey: "beta.universities.feature3.detail"
      },
      {
        titleKey: "beta.universities.feature4.title",
        detailKey: "beta.universities.feature4.detail"
      }
    ]
  },
  roadmap: {
    icon: Route,
    eyebrowKey: "beta.roadmap.eyebrow",
    titleKey: "beta.roadmap.title",
    descriptionKey: "beta.roadmap.description",
    statusKey: "beta.status.preview",
    primaryActionKey: "beta.actions.completeProfile",
    primaryHref: "/profile",
    secondaryActionKey: "beta.actions.openDashboard",
    secondaryHref: "/dashboard",
    nextFeatureKey: "beta.roadmap.next",
    features: [
      {
        titleKey: "beta.roadmap.feature1.title",
        detailKey: "beta.roadmap.feature1.detail"
      },
      {
        titleKey: "beta.roadmap.feature2.title",
        detailKey: "beta.roadmap.feature2.detail"
      },
      {
        titleKey: "beta.roadmap.feature3.title",
        detailKey: "beta.roadmap.feature3.detail"
      },
      {
        titleKey: "beta.roadmap.feature4.title",
        detailKey: "beta.roadmap.feature4.detail"
      }
    ]
  },
  essays: {
    icon: FilePenLine,
    eyebrowKey: "beta.essays.eyebrow",
    titleKey: "beta.essays.title",
    descriptionKey: "beta.essays.description",
    statusKey: "beta.status.preview",
    primaryActionKey: "beta.actions.openRoadmap",
    primaryHref: "/roadmap",
    secondaryActionKey: "beta.actions.completeProfile",
    secondaryHref: "/profile",
    nextFeatureKey: "beta.essays.next",
    disclaimerKey: "beta.disclaimer.essays",
    features: [
      {
        titleKey: "beta.essays.feature1.title",
        detailKey: "beta.essays.feature1.detail"
      },
      {
        titleKey: "beta.essays.feature2.title",
        detailKey: "beta.essays.feature2.detail"
      },
      {
        titleKey: "beta.essays.feature3.title",
        detailKey: "beta.essays.feature3.detail"
      }
    ]
  },
  exams: {
    icon: BookOpenCheck,
    eyebrowKey: "beta.exams.eyebrow",
    titleKey: "beta.exams.title",
    descriptionKey: "beta.exams.description",
    statusKey: "beta.status.preview",
    primaryActionKey: "beta.actions.openRoadmap",
    primaryHref: "/roadmap",
    secondaryActionKey: "beta.actions.completeProfile",
    secondaryHref: "/profile",
    nextFeatureKey: "beta.exams.next",
    features: [
      {
        titleKey: "beta.exams.feature1.title",
        detailKey: "beta.exams.feature1.detail"
      },
      {
        titleKey: "beta.exams.feature2.title",
        detailKey: "beta.exams.feature2.detail"
      },
      {
        titleKey: "beta.exams.feature3.title",
        detailKey: "beta.exams.feature3.detail"
      },
      {
        titleKey: "beta.exams.feature4.title",
        detailKey: "beta.exams.feature4.detail"
      }
    ]
  },
  finance: {
    icon: CircleDollarSign,
    eyebrowKey: "beta.finance.eyebrow",
    titleKey: "beta.finance.title",
    descriptionKey: "beta.finance.description",
    statusKey: "beta.status.preview",
    primaryActionKey: "beta.actions.openRoadmap",
    primaryHref: "/roadmap",
    secondaryActionKey: "beta.actions.openDashboard",
    secondaryHref: "/dashboard",
    nextFeatureKey: "beta.finance.next",
    disclaimerKey: "beta.disclaimer.finance",
    features: [
      {
        titleKey: "beta.finance.feature1.title",
        detailKey: "beta.finance.feature1.detail"
      },
      {
        titleKey: "beta.finance.feature2.title",
        detailKey: "beta.finance.feature2.detail"
      },
      {
        titleKey: "beta.finance.feature3.title",
        detailKey: "beta.finance.feature3.detail"
      }
    ]
  },
  activities: {
    icon: CalendarDays,
    eyebrowKey: "beta.activities.eyebrow",
    titleKey: "beta.activities.title",
    descriptionKey: "beta.activities.description",
    statusKey: "beta.status.preview",
    primaryActionKey: "beta.actions.exploreEvents",
    primaryHref: "/events",
    secondaryActionKey: "beta.actions.completeProfile",
    secondaryHref: "/profile",
    nextFeatureKey: "beta.activities.next",
    features: [
      {
        titleKey: "beta.activities.feature1.title",
        detailKey: "beta.activities.feature1.detail"
      },
      {
        titleKey: "beta.activities.feature2.title",
        detailKey: "beta.activities.feature2.detail"
      },
      {
        titleKey: "beta.activities.feature3.title",
        detailKey: "beta.activities.feature3.detail"
      }
    ]
  },
  research: {
    icon: FlaskConical,
    eyebrowKey: "beta.research.eyebrow",
    titleKey: "beta.research.title",
    descriptionKey: "beta.research.description",
    statusKey: "beta.status.preview",
    primaryActionKey: "beta.actions.completeProfile",
    primaryHref: "/profile#profile-section-research",
    secondaryActionKey: "beta.actions.exploreEvents",
    secondaryHref: "/events",
    nextFeatureKey: "beta.research.next",
    features: [
      {
        titleKey: "beta.research.feature1.title",
        detailKey: "beta.research.feature1.detail"
      },
      {
        titleKey: "beta.research.feature2.title",
        detailKey: "beta.research.feature2.detail"
      },
      {
        titleKey: "beta.research.feature3.title",
        detailKey: "beta.research.feature3.detail"
      }
    ]
  },
  pricing: {
    icon: Shapes,
    eyebrowKey: "beta.pricing.eyebrow",
    titleKey: "beta.pricing.title",
    descriptionKey: "beta.pricing.description",
    statusKey: "beta.status.mock",
    primaryActionKey: "beta.actions.openDashboard",
    primaryHref: "/dashboard",
    secondaryActionKey: "beta.actions.exploreEvents",
    secondaryHref: "/events",
    nextFeatureKey: "beta.pricing.next",
    disclaimerKey: "beta.disclaimer.pricing",
    features: [
      {
        titleKey: "beta.pricing.feature1.title",
        detailKey: "beta.pricing.feature1.detail"
      },
      {
        titleKey: "beta.pricing.feature2.title",
        detailKey: "beta.pricing.feature2.detail"
      },
      {
        titleKey: "beta.pricing.feature3.title",
        detailKey: "beta.pricing.feature3.detail"
      },
      {
        titleKey: "beta.pricing.feature4.title",
        detailKey: "beta.pricing.feature4.detail"
      }
    ]
  }
};
