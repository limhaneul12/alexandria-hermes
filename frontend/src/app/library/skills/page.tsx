import { Suspense } from "react";

import { LibraryItemListClient } from "@/components/library/library-item-list-client";

export default function SkillsLibraryPage() {
  return (
    <Suspense fallback={null}>
      <LibraryItemListClient type="SKILL" />
    </Suspense>
  );
}
