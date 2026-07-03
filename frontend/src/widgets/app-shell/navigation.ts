import {
  BookOpenCheck,
  CalendarDays,
  CalendarPlus,
  CircleUserRound,
  ClipboardList,
  Compass,
  Database,
  FlaskConical,
  GraduationCap,
  LayoutDashboard,
  LogIn,
  Map,
  MessageSquareWarning,
  Tickets,
  UserPlus,
  Route,
  ScrollText,
  ShieldCheck,
  Shapes,
  WalletCards
} from "lucide-react";

import type { NavigationItem } from "@/shared/types/navigation";

export const primaryNavigation: NavigationItem[] = [
  { href: "/dashboard", labelKey: "navigation.dashboard", icon: LayoutDashboard },
  { href: "/profile", labelKey: "navigation.profile", icon: CircleUserRound },
  { href: "/events", labelKey: "navigation.eventMap", icon: Map },
  { href: "/events/my", labelKey: "navigation.myEvents", icon: Tickets },
  { href: "/universities", labelKey: "navigation.universities", icon: GraduationCap },
  { href: "/recommendations", labelKey: "navigation.recommendations", icon: Compass },
  { href: "/roadmap", labelKey: "navigation.roadmap", icon: Route },
  { href: "/essays", labelKey: "navigation.essays", icon: ScrollText },
  { href: "/applications", labelKey: "navigation.applications", icon: ClipboardList },
  { href: "/exams", labelKey: "navigation.exams", icon: BookOpenCheck },
  { href: "/finance", labelKey: "navigation.finance", icon: WalletCards },
  { href: "/activities", labelKey: "navigation.activities", icon: CalendarDays },
  { href: "/research", labelKey: "navigation.research", icon: FlaskConical },
  { href: "/pricing", labelKey: "navigation.plans", icon: Shapes }
];

export const authenticatedAccountNavigation: NavigationItem[] = [];

export const organizerNavigation: NavigationItem[] = [
  {
    href: "/organizer/events",
    labelKey: "navigation.organizerEvents",
    icon: CalendarPlus
  }
];

export const adminNavigation: NavigationItem[] = [
  {
    href: "/admin/university-import",
    labelKey: "navigation.universityImport",
    icon: Database
  },
  {
    href: "/admin/events/moderation",
    labelKey: "navigation.eventModeration",
    icon: ShieldCheck
  },
  {
    href: "/admin/feedback",
    labelKey: "navigation.feedbackInbox",
    icon: MessageSquareWarning
  }
];

export const guestAccountNavigation: NavigationItem[] = [
  { href: "/login", labelKey: "navigation.login", icon: LogIn },
  { href: "/register", labelKey: "navigation.register", icon: UserPlus }
];
