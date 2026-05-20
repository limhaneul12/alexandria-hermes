import { HarnessDetailClient } from "@/components/harness/harness-detail-client";

type HarnessPageProps = {
  params: Promise<{ contextId: string }>;
};

export default async function HarnessPage({ params }: HarnessPageProps) {
  const { contextId } = await params;
  return <HarnessDetailClient contextId={decodeURIComponent(contextId)} />;
}
