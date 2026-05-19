"use client";

import { LibraryClient } from "@/components/library/library-client";
import { t } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";
import type { VisibleItemType } from "@/types/library";

export function LibraryItemListClient({ type }: { type: VisibleItemType }) {
  const language = useLibraryStore((state) => state.language);
  return (
    <LibraryClient
      forcedType={type}
      flatList
      title={type === "SKILL" ? t(language, "mySkills") : t(language, "myPrompts")}
      description={type === "SKILL" ? t(language, "flatSkillsDescription") : t(language, "flatPromptsDescription")}
    />
  );
}
