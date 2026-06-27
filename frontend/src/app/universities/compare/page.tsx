import { UniversityCompareScreen } from "@/screens/universities/university-compare";

export default async function Page({
  searchParams
}: {
  searchParams: Promise<{ ids?: string }>;
}) {
  const { ids } = await searchParams;
  return <UniversityCompareScreen ids={ids ?? ""} />;
}
