"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Grid2X2, List, Search, X } from "lucide-react";
import { motion } from "framer-motion";

import { CategoryTree } from "@/components/library/category-tree";
import { SkillCard } from "@/components/library/skill-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { fetchLibrary } from "@/lib/api";
import { useLibraryStore } from "@/store/library-store";
import { isItemType } from "@/types/library";

export function LibraryClient({ initialCategory }: { initialCategory?: string }) {
  const {
    searchQuery,
    categorySlug,
    tag,
    type,
    sort,
    viewMode,
    setSearchQuery,
    setCategorySlug,
    setTag,
    setType,
    setSort,
    setViewMode,
    clearFilters,
  } = useLibraryStore();
  const [draftQuery, setDraftQuery] = useState(searchQuery);

  useEffect(() => {
    setCategorySlug(initialCategory ?? null);
  }, [initialCategory, setCategorySlug]);

  useEffect(() => {
    setDraftQuery(searchQuery);
  }, [searchQuery]);

  useEffect(() => {
    if (draftQuery === searchQuery) return undefined;
    const timeout = window.setTimeout(() => setSearchQuery(draftQuery), 250);
    return () => window.clearTimeout(timeout);
  }, [draftQuery, searchQuery, setSearchQuery]);

  const params = useMemo(() => {
    const next = new URLSearchParams();
    if (searchQuery) next.set("q", searchQuery);
    if (categorySlug) next.set("category", categorySlug);
    if (tag) next.set("tag", tag);
    if (type) next.set("type", type);
    next.set("sort", sort);
    next.set("limit", "48");
    return next;
  }, [categorySlug, searchQuery, sort, tag, type]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["library", params.toString()],
    queryFn: () => fetchLibrary(params),
  });

  return (
    <div className="grid gap-6 xl:grid-cols-[250px_minmax(0,1fr)]">
      <aside className="space-y-4">
        <Card className="sticky top-24 p-4">
          <p className="mb-4 font-serif text-2xl text-gold-100">서재</p>
          {data ? (
            <CategoryTree categories={data.categories} activeSlug={categorySlug} />
          ) : (
            <p className="text-sm text-stone-500">카테고리를 불러오는 중입니다...</p>
          )}
        </Card>
      </aside>

      <section className="space-y-5">
        <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-bronze">Library</p>
              <h2 className="font-serif text-4xl text-gold-50">{categorySlug ?? "전체 서재"}</h2>
              <p className="mt-2 text-sm text-stone-400">필요한 스킬, 워크플로우, 지식 문서를 카드로 탐색합니다.</p>
            </div>
            <p className="text-sm text-stone-500">총 {data?.total ?? 0}개의 아이템</p>
          </div>

          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_150px_150px_150px_auto]">
            <label className="relative block">
              <span className="sr-only">아이템 검색</span>
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
              <Input
                value={draftQuery}
                onChange={(event) => setDraftQuery(event.target.value)}
                placeholder="아이템 검색..."
                className="pl-9"
              />
            </label>

            <label className="relative block">
              <span className="sr-only">유형 선택</span>
              <select
                value={type ?? ""}
                onChange={(event) => {
                  const nextType = event.target.value;
                  setType(nextType && isItemType(nextType) ? nextType : null);
                }}
                className="archive-select appearance-none pr-8"
              >
                <option value="">전체 유형</option>
                <option value="SKILL">스킬</option>
                <option value="WORKFLOW">워크플로우</option>
                <option value="KNOWLEDGE">지식 문서</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
            </label>

            <label className="relative block">
              <span className="sr-only">태그 선택</span>
              <select value={tag ?? ""} onChange={(event) => setTag(event.target.value || null)} className="archive-select appearance-none pr-8">
                <option value="">전체 태그</option>
                {data?.tags.map((tagName) => (
                  <option key={tagName} value={tagName}>{tagName}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
            </label>

            <label className="relative block">
              <span className="sr-only">정렬 선택</span>
              <select value={sort} onChange={(event) => setSort(event.target.value as "recent" | "popular" | "title")} className="archive-select appearance-none pr-8">
                <option value="popular">신뢰 높은순</option>
                <option value="recent">최근 사용순</option>
                <option value="title">이름순</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
            </label>

            <div className="flex items-center gap-2">
              <Button variant={viewMode === "grid" ? "default" : "secondary"} size="icon" onClick={() => setViewMode("grid")} aria-label="격자 보기">
                <Grid2X2 className="h-4 w-4" />
              </Button>
              <Button variant={viewMode === "list" ? "default" : "secondary"} size="icon" onClick={() => setViewMode("list")} aria-label="목록 보기">
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {(searchQuery || categorySlug || tag || type) && (
            <div className="mt-4">
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <X className="h-3.5 w-3.5" /> 필터 지우기
              </Button>
            </div>
          )}
        </div>

        {isLoading && <div className="rounded-2xl border border-white/10 p-10 text-stone-400">서재를 펼치는 중입니다...</div>}
        {isError && <div className="rounded-2xl border border-white/10 p-10 text-stone-400">서재를 불러오지 못했습니다.</div>}
        {!isLoading && !isError && data?.items.length === 0 && (
          <div className="rounded-2xl border border-white/10 bg-black/20 p-10 text-stone-400">
            <p className="font-serif text-2xl text-gold-100">아직 등록된 아이템이 없습니다</p>
            <p className="mt-2 text-sm">실제 아카이브 항목이 들어오면 여기에 표시됩니다.</p>
          </div>
        )}

        <motion.div layout className={viewMode === "grid" ? "grid gap-4 md:grid-cols-2 2xl:grid-cols-4" : "grid gap-3"}>
          {data?.items.map((skill) => <SkillCard key={skill.id} skill={skill} view={viewMode} />)}
        </motion.div>
      </section>
    </div>
  );
}
