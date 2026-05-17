"use client";

import { LibraryClient } from "@/components/library/library-client";
import type { VisibleItemType } from "@/types/library";

export function LibraryItemListClient({ type }: { type: VisibleItemType }) {
  return (
    <LibraryClient
      forcedType={type}
      flatList
      title={type === "SKILL" ? "내 스킬" : "내 프롬프트"}
      description={type === "SKILL" ? "폴더 경로와 무관하게 모든 스킬을 flat list로 검색하고 정렬합니다." : "폴더 경로와 무관하게 모든 프롬프트를 flat list로 검색하고 정렬합니다."}
    />
  );
}
