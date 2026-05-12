import { SkillDetailClient } from "@/components/skill/skill-detail-client";

type SkillDetailPageProps = {
  params: Promise<{ category: string; skillId: string }>;
};

export default async function SkillDetailPage({ params }: SkillDetailPageProps) {
  const { skillId } = await params;
  return <SkillDetailClient skillId={decodeURIComponent(skillId)} />;
}
