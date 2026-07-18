import type { Metadata } from "next";

import { LandingScreen } from "@/screens/landing";

export const metadata: Metadata = {
  title: "UniWay — A calm academic workspace for admissions",
  description:
    "Build your profile, discover universities, and track applications with UniWay — a calm, honest academic workspace for Central Asian students applying abroad."
};

export default function HomePage() {
  return <LandingScreen />;
}
