import { Suspense } from "react";

import { ContextVaultClient } from "@/components/context/context-vault-client";

export default function ContextsPage() {
  return (
    <Suspense fallback={null}>
      <ContextVaultClient />
    </Suspense>
  );
}
