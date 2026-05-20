import { Suspense } from "react";

import { HarnessGuidebookClient } from "@/components/harness/harness-guidebook-client";

export default function HarnessesPage() {
  return (
    <Suspense fallback={null}>
      <HarnessGuidebookClient />
    </Suspense>
  );
}
