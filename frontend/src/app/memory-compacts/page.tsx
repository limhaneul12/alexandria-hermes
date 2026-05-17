import { Suspense } from "react";

import { MemoryCompactsClient } from "@/components/memory/memory-compacts-client";

export default function MemoryCompactsPage() {
  return (
    <Suspense fallback={null}>
      <MemoryCompactsClient />
    </Suspense>
  );
}
