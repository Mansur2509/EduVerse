import type {
  Activity,
  Honor,
  Olympiad,
  Sport,
  ResearchProject,
  EssayDraft,
  PortfolioProject,
  Volunteer,
  Recommender
} from "@/entities/profile";
import type { ProfileItemField } from "../ui/profile-item-section";
import type { TranslationKey } from "@/shared/i18n";

const scaleOptions: ProfileItemField["options"] = [
  { value: "school", label: "activity.scale.school" as TranslationKey },
  { value: "city", label: "activity.scale.city" as TranslationKey },
  { value: "regional", label: "activity.scale.regional" as TranslationKey },
  { value: "national", label: "activity.scale.national" as TranslationKey },
  { value: "international", label: "activity.scale.international" as TranslationKey }
];

const activityCategoryOptions: ProfileItemField["options"] = [
  { value: "leadership", label: "activity.category.leadership" as TranslationKey },
  { value: "academic", label: "activity.category.academic" as TranslationKey },
  { value: "community", label: "activity.category.community" as TranslationKey },
  { value: "arts", label: "activity.category.arts" as TranslationKey },
  { value: "stem", label: "activity.category.stem" as TranslationKey },
  { value: "business", label: "activity.category.business" as TranslationKey },
  { value: "mun_debate", label: "activity.category.munDebate" as TranslationKey },
  { value: "work", label: "activity.category.work" as TranslationKey },
  { value: "other", label: "activity.category.other" as TranslationKey }
];

export const activityFields: ProfileItemField[] = [
  { key: "title", label: "profile.activity.title" as TranslationKey, required: true, maxLength: 150 },
  { key: "role", label: "profile.activity.role" as TranslationKey, maxLength: 150 },
  { key: "organization", label: "profile.activity.organization" as TranslationKey, maxLength: 150 },
  { key: "category", label: "profile.activity.category" as TranslationKey, type: "select", options: activityCategoryOptions },
  { key: "start_date", label: "profile.activity.startDate" as TranslationKey, type: "date" },
  { key: "end_date", label: "profile.activity.endDate" as TranslationKey, type: "date" },
  { key: "hours_per_week", label: "profile.activity.hoursPerWeek" as TranslationKey, type: "number" },
  { key: "weeks_per_year", label: "profile.activity.weeksPerYear" as TranslationKey, type: "number" },
  { key: "scale", label: "profile.activity.scale" as TranslationKey, type: "select", options: scaleOptions },
  { key: "impact_number", label: "profile.activity.impactNumber" as TranslationKey, maxLength: 100, placeholder: "profile.activity.impactNumberPlaceholder" as TranslationKey },
  { key: "description", label: "profile.activity.description" as TranslationKey, type: "textarea", maxLength: 1500 },
  { key: "proof_link", label: "proof_link" as TranslationKey, type: "url" },
];

export const honorFields: ProfileItemField[] = [
  { key: "title", label: "profile.honor.title" as TranslationKey, required: true, maxLength: 150 },
  { key: "issuing_organization", label: "profile.honor.organization" as TranslationKey, maxLength: 150 },
  { key: "level", label: "profile.honor.level" as TranslationKey, maxLength: 100 },
  { key: "year", label: "profile.honor.year" as TranslationKey, type: "number" },
  { key: "result_rank", label: "profile.honor.rank" as TranslationKey, maxLength: 100, placeholder: "profile.honor.rankPlaceholder" as TranslationKey },
  { key: "description", label: "profile.honor.description" as TranslationKey, type: "textarea", maxLength: 1500 },
  { key: "proof_link", label: "proof_link" as TranslationKey, type: "url" },
];

export const olympiadFields: ProfileItemField[] = [
  { key: "name", label: "profile.olympiad.name" as TranslationKey, required: true, maxLength: 150 },
  { key: "subject", label: "profile.olympiad.subject" as TranslationKey, maxLength: 100 },
  { key: "level", label: "profile.olympiad.level" as TranslationKey, maxLength: 100 },
  { key: "year", label: "profile.olympiad.year" as TranslationKey, type: "number" },
  { key: "result", label: "profile.olympiad.result" as TranslationKey, maxLength: 100 },
  { key: "rank_percentile", label: "profile.olympiad.rank" as TranslationKey, maxLength: 50 },
  { key: "description", label: "profile.olympiad.description" as TranslationKey, type: "textarea", maxLength: 1500 },
  { key: "proof_link", label: "proof_link" as TranslationKey, type: "url" },
];

export const sportFields: ProfileItemField[] = [
  { key: "sport_name", label: "profile.sport.name" as TranslationKey, required: true, maxLength: 150 },
  { key: "level", label: "profile.sport.level" as TranslationKey, maxLength: 100 },
  { key: "years_trained", label: "profile.sport.yearsTrained" as TranslationKey, maxLength: 100 },
  { key: "peak_result", label: "profile.sport.peakResult" as TranslationKey, maxLength: 150 },
  { key: "competition_name", label: "profile.sport.competition" as TranslationKey, maxLength: 150 },
  { key: "description", label: "profile.sport.description" as TranslationKey, type: "textarea", maxLength: 1500 },
  { key: "proof_link", label: "proof_link" as TranslationKey, type: "url" },
];

export const researchFields: ProfileItemField[] = [
  { key: "title", label: "profile.research.title" as TranslationKey, required: true, maxLength: 150 },
  { key: "field", label: "profile.research.field" as TranslationKey, maxLength: 150 },
  { key: "research_question", label: "profile.research.question" as TranslationKey, type: "textarea", maxLength: 500 },
  { key: "sample_size", label: "profile.research.sample" as TranslationKey, maxLength: 100 },
  { key: "countries_region", label: "profile.research.region" as TranslationKey, maxLength: 150 },
  { key: "methods_used", label: "profile.research.methods" as TranslationKey, maxLength: 150 },
  { key: "current_stage", label: "profile.research.stage" as TranslationKey, type: "select", options: [
    { value: "planning", label: "research.stage.planning" as TranslationKey },
    { value: "active", label: "research.stage.active" as TranslationKey },
    { value: "completed", label: "research.stage.completed" as TranslationKey },
    { value: "published", label: "research.stage.published" as TranslationKey },
  ]},
  { key: "manuscript_link", label: "profile.research.manuscript" as TranslationKey, type: "url" },
  { key: "publication_status", label: "profile.research.publication" as TranslationKey, maxLength: 100 },
  { key: "description", label: "profile.research.description" as TranslationKey, type: "textarea", maxLength: 1500, placeholder: "profile.research.descriptionPlaceholder" as TranslationKey },
];

export const essayFields: ProfileItemField[] = [
  { key: "essay_type", label: "profile.essay.type" as TranslationKey, required: true, maxLength: 100 },
  { key: "school_program", label: "profile.essay.school" as TranslationKey, maxLength: 150 },
  { key: "status", label: "profile.essay.status" as TranslationKey, type: "select", options: [
    { value: "draft", label: "essay.status.draft" as TranslationKey },
    { value: "in_progress", label: "essay.status.in_progress" as TranslationKey },
    { value: "submitted", label: "essay.status.submitted" as TranslationKey },
    { value: "reviewed", label: "essay.status.reviewed" as TranslationKey },
  ]},
  { key: "word_limit", label: "profile.essay.wordLimit" as TranslationKey, type: "number" },
  { key: "draft_status", label: "profile.essay.draftStatus" as TranslationKey, maxLength: 100 },
  { key: "last_reviewed_date", label: "profile.essay.reviewed" as TranslationKey, type: "date" },
  { key: "notes", label: "profile.essay.notes" as TranslationKey, type: "textarea", maxLength: 1000 },
];

export const portfolioFields: ProfileItemField[] = [
  { key: "title", label: "profile.portfolio.title" as TranslationKey, required: true, maxLength: 150 },
  { key: "project_type", label: "profile.portfolio.type" as TranslationKey, maxLength: 100 },
  { key: "link", label: "profile.portfolio.link" as TranslationKey, type: "url" },
  { key: "tech_stack", label: "profile.portfolio.tech" as TranslationKey, maxLength: 150 },
  { key: "users_impact", label: "profile.portfolio.impact" as TranslationKey, maxLength: 150 },
  { key: "status", label: "profile.portfolio.status" as TranslationKey, maxLength: 100 },
  { key: "description", label: "profile.portfolio.description" as TranslationKey, type: "textarea", maxLength: 1500 },
];

export const activityDisplay = (item: Activity) => (
  <div>
    <p className="font-semibold">{item.title}</p>
    {item.organization && <p className="text-xs text-muted-foreground">{item.organization}</p>}
  </div>
);

export const honorDisplay = (item: Honor) => (
  <div>
    <p className="font-semibold">{item.title}</p>
    {item.issuing_organization && <p className="text-xs text-muted-foreground">{item.issuing_organization}</p>}
  </div>
);

export const olympiadDisplay = (item: Olympiad) => (
  <div>
    <p className="font-semibold">{item.name}</p>
    {item.subject && <p className="text-xs text-muted-foreground">{item.subject}</p>}
  </div>
);

export const sportDisplay = (item: Sport) => (
  <div>
    <p className="font-semibold">{item.sport_name}</p>
    {item.level && <p className="text-xs text-muted-foreground">{item.level}</p>}
  </div>
);

export const researchDisplay = (item: ResearchProject) => (
  <div>
    <p className="font-semibold">{item.title}</p>
    {item.field && <p className="text-xs text-muted-foreground">{item.field}</p>}
  </div>
);

export const essayDisplay = (item: EssayDraft) => (
  <div>
    <p className="font-semibold">{item.essay_type || item.school_program}</p>
    {item.essay_type && item.school_program && (
      <p className="text-xs text-muted-foreground">{item.school_program}</p>
    )}
  </div>
);

export const portfolioDisplay = (item: PortfolioProject) => (
  <div>
    <p className="font-semibold">{item.title}</p>
    {item.project_type && <p className="text-xs text-muted-foreground">{item.project_type}</p>}
  </div>
);

export const volunteerFields: ProfileItemField[] = [
  { key: "title", label: "profile.volunteer.title" as TranslationKey, required: true, maxLength: 150 },
  { key: "role", label: "profile.volunteer.role" as TranslationKey, maxLength: 150 },
  { key: "organization", label: "profile.volunteer.organization" as TranslationKey, maxLength: 150 },
  { key: "start_date", label: "profile.volunteer.startDate" as TranslationKey, type: "date" },
  { key: "end_date", label: "profile.volunteer.endDate" as TranslationKey, type: "date" },
  { key: "hours_per_week", label: "profile.volunteer.hoursPerWeek" as TranslationKey, type: "number" },
  { key: "weeks_per_year", label: "profile.volunteer.weeksPerYear" as TranslationKey, type: "number" },
  { key: "scale", label: "profile.volunteer.scale" as TranslationKey, type: "select", options: scaleOptions },
  { key: "impact_number", label: "profile.volunteer.impactNumber" as TranslationKey, maxLength: 100, placeholder: "profile.volunteer.impactNumberPlaceholder" as TranslationKey },
  { key: "beneficiaries", label: "profile.volunteer.beneficiaries" as TranslationKey, maxLength: 150 },
  { key: "description", label: "profile.volunteer.description" as TranslationKey, type: "textarea", maxLength: 1500 },
  { key: "proof_link", label: "proof_link" as TranslationKey, type: "url" },
];

export const recommenderFields: ProfileItemField[] = [
  { key: "name", label: "profile.recommender.name" as TranslationKey, required: true, maxLength: 150 },
  { key: "relationship_role", label: "profile.recommender.role" as TranslationKey, maxLength: 150 },
  { key: "status", label: "profile.recommender.status" as TranslationKey, type: "select", options: [
    { value: "not_started", label: "recommender.status.not_started" as TranslationKey },
    { value: "planned", label: "recommender.status.planned" as TranslationKey },
    { value: "requested", label: "recommender.status.requested" as TranslationKey },
    { value: "confirmed", label: "recommender.status.confirmed" as TranslationKey },
    { value: "submitted", label: "recommender.status.submitted" as TranslationKey },
  ]},
  { key: "requested_date", label: "profile.recommender.requestedDate" as TranslationKey, type: "date" },
  { key: "submitted_date", label: "profile.recommender.submittedDate" as TranslationKey, type: "date" },
  { key: "notes", label: "profile.recommender.notes" as TranslationKey, type: "textarea", maxLength: 1000 },
];

export const volunteerDisplay = (item: Volunteer) => (
  <div>
    <p className="font-semibold">{item.title}</p>
    {item.organization && <p className="text-xs text-muted-foreground">{item.organization}</p>}
  </div>
);

export const recommenderDisplay = (item: Recommender) => (
  <div>
    <p className="font-semibold">{item.name}</p>
    {item.relationship_role && <p className="text-xs text-muted-foreground">{item.relationship_role}</p>}
  </div>
);
