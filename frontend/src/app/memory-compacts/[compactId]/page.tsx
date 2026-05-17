import { MemoryCompactDetailClient } from "@/components/memory/memory-compact-detail-client";

type MemoryCompactDetailPageProps = {
  params: Promise<{ compactId: string }>;
};

export default async function MemoryCompactDetailPage({
  params,
}: MemoryCompactDetailPageProps) {
  const { compactId } = await params;
  return <MemoryCompactDetailClient compactId={decodeURIComponent(compactId)} />;
}
