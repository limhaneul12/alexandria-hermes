import { Suspense } from "react";

import { LibraryItemListClient } from "@/components/library/library-item-list-client";

export default function PromptsLibraryPage() {
  return (
    <Suspense fallback={null}>
      <LibraryItemListClient type="PROMPT" />
    </Suspense>
  );
}
