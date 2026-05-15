import { ContextDetailClient } from "@/components/context/context-detail-client";

type ContextDetailPageProps = {
  params: Promise<{ contextId: string }>;
};

export default async function ContextDetailPage({ params }: ContextDetailPageProps) {
  const { contextId } = await params;
  return <ContextDetailClient contextId={decodeURIComponent(contextId)} />;
}
