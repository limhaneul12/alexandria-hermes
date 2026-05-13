"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, FolderPlus, Grid2X2, List, Plus, Search, X } from "lucide-react";
import { motion } from "framer-motion";

import { CategoryTree } from "@/components/library/category-tree";
import { SkillCard } from "@/components/library/skill-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createCategory, createSkill, fetchLibrary } from "@/lib/api";
import { useLibraryStore } from "@/store/library-store";
import { isItemType, type CategoryNode } from "@/types/library";

type CategoryOption = {
  id: string;
  label: string;
};

function flattenCategoryOptions(categories: CategoryNode[], depth = 0): CategoryOption[] {
  return categories.flatMap((category) => [
    { id: category.id, label: `${"　".repeat(depth)}${category.name}` },
    ...flattenCategoryOptions(category.children, depth + 1),
  ]);
}

function commaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

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
  const queryClient = useQueryClient();
  const [draftQuery, setDraftQuery] = useState(searchQuery);
  const [showFolderForm, setShowFolderForm] = useState(false);
  const [showSkillForm, setShowSkillForm] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [folderParentId, setFolderParentId] = useState("");
  const [skillTitle, setSkillTitle] = useState("");
  const [skillSummary, setSkillSummary] = useState("");
  const [skillContent, setSkillContent] = useState("");
  const [skillPurpose, setSkillPurpose] = useState("");
  const [skillCategoryId, setSkillCategoryId] = useState("");
  const [skillTags, setSkillTags] = useState("");
  const [skillActivate, setSkillActivate] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

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
  const categoryOptions = useMemo(
    () => flattenCategoryOptions(data?.categories ?? []),
    [data?.categories],
  );

  const folderMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["library"] });
      setFolderName("");
      setFolderParentId("");
      setShowFolderForm(false);
      setNotice("새 폴더가 생성됐습니다.");
    },
    onError: () => setNotice("폴더를 만들지 못했습니다."),
  });

  const skillMutation = useMutation({
    mutationFn: createSkill,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["library"] });
      setSkillTitle("");
      setSkillSummary("");
      setSkillContent("");
      setSkillPurpose("");
      setSkillCategoryId("");
      setSkillTags("");
      setSkillActivate(false);
      setShowSkillForm(false);
      setNotice("스킬이 등록됐습니다.");
    },
    onError: () => setNotice("스킬을 등록하지 못했습니다."),
  });

  function handleCreateFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    folderMutation.mutate({ name: folderName.trim(), parentId: folderParentId || null });
  }

  function handleCreateSkill(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    skillMutation.mutate({
      title: skillTitle.trim(),
      summary: skillSummary.trim() || null,
      content: skillContent.trim(),
      categoryId: skillCategoryId || null,
      tags: commaList(skillTags),
      purpose: skillPurpose.trim(),
      usageExample: null,
      requiredTools: [],
      riskLevel: "LOW",
      version: "1.0.0",
      createdByName: "library-user",
      status: skillActivate ? "ACTIVE" : "DRAFT",
    });
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[250px_minmax(0,1fr)]">
      <aside className="space-y-4">
        <Card className="sticky top-24 p-4">
          <div className="mb-4 flex items-center justify-between gap-2">
            <p className="font-serif text-2xl text-gold-100">서재</p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowFolderForm((current) => !current)}
              type="button"
            >
              <FolderPlus className="h-3.5 w-3.5" /> 새 폴더
            </Button>
          </div>
          {showFolderForm && (
            <form onSubmit={handleCreateFolder} className="mb-4 space-y-2 rounded-xl border border-white/10 bg-black/20 p-3">
              <label className="block text-xs text-stone-400">
                폴더 이름
                <Input
                  value={folderName}
                  onChange={(event) => setFolderName(event.target.value)}
                  placeholder="예: Backend"
                  required
                  className="mt-1"
                />
              </label>
              <label className="block text-xs text-stone-400">
                상위 폴더
                <select
                  value={folderParentId}
                  onChange={(event) => setFolderParentId(event.target.value)}
                  className="archive-select mt-1"
                >
                  <option value="">최상위</option>
                  {categoryOptions.map((category) => (
                    <option key={category.id} value={category.id}>{category.label}</option>
                  ))}
                </select>
              </label>
              <Button type="submit" size="sm" disabled={folderMutation.isPending || !folderName.trim()}>
                폴더 생성
              </Button>
            </form>
          )}
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
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm text-stone-500">총 {data?.total ?? 0}개의 아이템</p>
              <Button type="button" onClick={() => setShowSkillForm((current) => !current)}>
                <Plus className="h-4 w-4" /> 스킬 등록
              </Button>
            </div>
          </div>

          {notice && <div className="mb-4 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-stone-300">{notice}</div>}

          {showSkillForm && (
            <form onSubmit={handleCreateSkill} className="mb-5 grid gap-3 rounded-2xl border border-white/10 bg-black/20 p-4 lg:grid-cols-2">
              <label className="block text-xs text-stone-400">
                스킬 제목
                <Input value={skillTitle} onChange={(event) => setSkillTitle(event.target.value)} required className="mt-1" />
              </label>
              <label className="block text-xs text-stone-400">
                배치할 폴더
                <select value={skillCategoryId} onChange={(event) => setSkillCategoryId(event.target.value)} className="archive-select mt-1">
                  <option value="">미분류</option>
                  {categoryOptions.map((category) => (
                    <option key={category.id} value={category.id}>{category.label}</option>
                  ))}
                </select>
              </label>
              <label className="block text-xs text-stone-400 lg:col-span-2">
                요약
                <Input value={skillSummary} onChange={(event) => setSkillSummary(event.target.value)} className="mt-1" />
              </label>
              <label className="block text-xs text-stone-400 lg:col-span-2">
                목적
                <Input value={skillPurpose} onChange={(event) => setSkillPurpose(event.target.value)} required className="mt-1" />
              </label>
              <label className="block text-xs text-stone-400 lg:col-span-2">
                본문
                <textarea
                  value={skillContent}
                  onChange={(event) => setSkillContent(event.target.value)}
                  required
                  rows={5}
                  className="mt-1 w-full rounded-md border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-parchment outline-none focus:border-gold-300/60"
                />
              </label>
              <label className="block text-xs text-stone-400">
                태그
                <Input value={skillTags} onChange={(event) => setSkillTags(event.target.value)} placeholder="fastapi, testing" className="mt-1" />
              </label>
              <label className="flex items-center gap-2 self-end text-xs text-stone-400">
                <input type="checkbox" checked={skillActivate} onChange={(event) => setSkillActivate(event.target.checked)} />
                바로 활성화
              </label>
              <div className="flex gap-2 lg:col-span-2">
                <Button
                  type="submit"
                  disabled={skillMutation.isPending || !skillTitle.trim() || !skillContent.trim() || !skillPurpose.trim()}
                >
                  스킬 저장
                </Button>
                <Button type="button" variant="secondary" onClick={() => setShowSkillForm(false)}>
                  닫기
                </Button>
              </div>
            </form>
          )}

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
