import { UniversityDetailScreen } from "@/screens/universities/university-detail";

export default async function Page({
  params
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <UniversityDetailScreen slug={slug} />;
}
