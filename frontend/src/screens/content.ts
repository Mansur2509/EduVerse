import { DISCLAIMERS } from "@/shared/constants/disclaimers";
import type { ModuleScreenProps } from "@/widgets/module-screen";

export const screenContent = {
  onboarding: {
    eyebrow: "Start with context",
    title: "Build a profile that makes every recommendation more useful.",
    description:
      "Capture goals, current preparation, interests, target countries, scholarship needs, and the kind of support you want.",
    primaryAction: "Begin onboarding",
    secondaryAction: "Preview dashboard",
    highlights: [
      { title: "Academic direction", detail: "Record intended majors, target universities, and study destinations." },
      { title: "Preparation baseline", detail: "Add exam levels, essay confidence, and current education status." },
      { title: "Personal priorities", detail: "Shape recommendations around scholarships, activities, research, and careers." }
    ]
  },
  universities: {
    eyebrow: "Evidence-aware research",
    title: "Compare universities using published facts, not invented odds.",
    description:
      "Search institutions across initial target countries and trace requirements, testing ranges, and scholarships to official sources.",
    primaryAction: "Browse universities",
    secondaryAction: "View roadmap",
    secondaryHref: "/roadmap",
    highlights: [
      { title: "Official data sources", detail: "Keep admissions, program, and scholarship source records visible." },
      { title: "Published-range comparison", detail: "Use clear categories when official ranges are available." },
      { title: "Shortlist with purpose", detail: "Connect university research to deadlines and preparation tasks." }
    ],
    disclaimer: DISCLAIMERS.admissions
  },
  roadmap: {
    eyebrow: "Plan with sequence",
    title: "Turn a broad ambition into visible milestones and deadlines.",
    description:
      "Organize exams, essays, research, activities, university research, and events into a roadmap you can actually maintain.",
    primaryAction: "Create roadmap",
    secondaryAction: "Open dashboard",
    highlights: [
      { title: "Milestones", detail: "Group meaningful outcomes instead of collecting disconnected to-dos." },
      { title: "Deadline links", detail: "Connect event and university dates to the work needed beforehand." },
      { title: "Adaptable steps", detail: "Revise the plan when goals, evidence, or available time changes." }
    ]
  },
  essays: {
    eyebrow: "Feedback, not ghostwriting",
    title: "Strengthen your own voice with structured revision guidance.",
    description:
      "Review clarity, structure, authenticity, grammar, and rubric alignment while keeping authorship with the student.",
    primaryAction: "Start feedback",
    secondaryAction: "See policy",
    highlights: [
      { title: "Rubric-based review", detail: "Make strengths and weaknesses specific enough to revise." },
      { title: "Questions that unlock revision", detail: "Prompt deeper detail without inventing a student's story." },
      { title: "Private by design", detail: "Treat drafts as sensitive content with strict ownership controls." }
    ],
    disclaimer: DISCLAIMERS.essays
  },
  exams: {
    eyebrow: "Original practice",
    title: "Practice exam skills with transparent, original learning content.",
    description:
      "Build SAT, IELTS, and selected AP foundations using original questions aligned with public exam specifications.",
    primaryAction: "Choose an exam",
    secondaryAction: "View study roadmap",
    secondaryHref: "/roadmap",
    highlights: [
      { title: "Focused sections", detail: "Move between skills, lessons, timed practice, and explanations." },
      { title: "Original questions", detail: "Use content created for UniWay rather than copied proprietary banks." },
      { title: "Useful review", detail: "Understand mistakes and identify the next skill to practice." }
    ]
  },
  finance: {
    eyebrow: "Financial foundations",
    title: "Learn the concepts that make everyday money decisions less mysterious.",
    description:
      "Study budgeting, saving, inflation, banking, debt, risk, career income, and investing basics in an educational context.",
    primaryAction: "Browse lessons",
    secondaryAction: "Check learning plan",
    secondaryHref: "/roadmap",
    highlights: [
      { title: "Plain-language lessons", detail: "Start with concepts students can connect to real life." },
      { title: "Low-stakes simulations", detail: "Explore trade-offs without real money or trading instructions." },
      { title: "Clear boundaries", detail: "Separate education from personalized financial or legal advice." }
    ],
    disclaimer: DISCLAIMERS.finance
  },
  profile: {
    eyebrow: "Your academic context",
    title: "Keep goals, preparation, interests, and evidence in one place.",
    description:
      "Your profile should improve recommendations while remaining understandable, editable, and privacy-aware.",
    primaryAction: "Complete profile",
    secondaryAction: "Update onboarding",
    secondaryHref: "/onboarding",
    highlights: [
      { title: "Goals and preferences", detail: "Maintain destinations, majors, scholarships, and career interests." },
      { title: "Preparation record", detail: "Track exams, activities, essays, research, and important achievements." },
      { title: "Readiness explanation", detail: "Show why an area needs attention without reducing a student to one score." }
    ]
  },
  pricing: {
    eyebrow: "Simple plan boundaries",
    title: "Keep core discovery free and make paid limits understandable.",
    description:
      "Phase 0 models Free, $5, $10, and $25 plans without real payment integration or dark-pattern upgrades.",
    primaryAction: "Compare plans",
    secondaryAction: "Return to dashboard",
    highlights: [
      { title: "Free essentials", detail: "Event Map, university search, profile basics, and core learning remain available." },
      { title: "Visible usage limits", detail: "Show AI and essay allowances before a user reaches a limit." },
      { title: "Payments later", detail: "Choose regional and global providers only after product validation." }
    ]
  },
  activities: {
    eyebrow: "Depth over collecting",
    title: "Turn activities, MUN, and debate into meaningful development.",
    description:
      "Plan preparation, record genuine contributions, and reflect on skills rather than chasing an artificial activity count.",
    primaryAction: "Add an activity",
    secondaryAction: "Find events",
    secondaryHref: "/events",
    highlights: [
      { title: "Preparation workflows", detail: "Organize MUN research, resolutions, arguments, and practice." },
      { title: "Evidence of contribution", detail: "Record responsibilities, outcomes, and lessons honestly." },
      { title: "Profile connection", detail: "Understand how activities support interests and future study." }
    ]
  },
  research: {
    eyebrow: "Research guidance",
    title: "Move from curiosity to a responsible, manageable research plan.",
    description:
      "Develop questions, methods, timelines, reading lists, and mentor outreach without fabricating credentials or results.",
    primaryAction: "Start a research plan",
    secondaryAction: "Explore opportunities",
    secondaryHref: "/events",
    highlights: [
      { title: "Question development", detail: "Narrow broad interests into researchable student-level questions." },
      { title: "Method and timeline", detail: "Plan ethical steps, sources, milestones, and realistic deliverables." },
      { title: "Mentor outreach guidance", detail: "Prepare respectful, accurate communication and relevant context." }
    ]
  }
} satisfies Record<string, ModuleScreenProps>;
