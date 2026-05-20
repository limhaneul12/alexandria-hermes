"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Code2, FolderPlus, Search, ScrollText, SlidersHorizontal, X } from "lucide-react";

import { LibraryFolderBrowser, findCategoryPath, flattenCategories } from "@/components/library/library-folder-browser";
import { FolderCreateForm } from "@/components/library/library-forms";
import { LibraryItemCard } from "@/components/library/library-item-card";
import { Button } from "@/components/ui/button";
import {
  FilterChipGroup,
  type FilterChipChoice,
} from "@/components/ui/filter-chip-group";
import { Input } from "@/components/ui/input";
import { createCategory, deleteCategory, fetchLibrary } from "@/lib/api";
import { dateInputValue, toUtcDateBoundaryIso } from "@/lib/filter-utils";
import { t, tx } from "@/lib/i18n";
import { buildCategoryCreatePayload, flattenCategoryOptions } from "@/lib/library/forms";
import { useLibraryStore } from "@/store/library-store";
import { isItemType, type CategoryNode, type VisibleItemType } from "@/types/library";

type LibraryClientProps = {
  initialCategory?: string;
  forcedType?: VisibleItemType;
  flatList?: boolean;
  title?: string;
  description?: string;
};

function latestTimestamp(item: { lastAccessedAt: string | null; updatedAt: string }) {
  return new Date(item.lastAccessedAt ?? item.updatedAt).getTime();
}

function routeForType(type: VisibleItemType) {
  return type === "SKILL" ? "/library/skills" : "/library/prompts";
}

export function LibraryClient({
  initialCategory,
  forcedType,
  flatList = false,
  title,
  description,
}: LibraryClientProps) {
  const queryClient = useQueryClient();
  const language = useLibraryStore((state) => state.language);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const searchQuery = searchParams.get("q") ?? "";
  const categorySlug = flatList ? null : initialCategory ?? null;
  const tag = searchParams.get("tag");
  const typeParam = searchParams.get("type");
  const type = forcedType ?? (typeParam && isItemType(typeParam) ? typeParam : null);
  const sortParam = searchParams.get("sort");
  const sort = sortParam === "recent" || sortParam === "title" ? sortParam : "popular";
  const updatedAfter = searchParams.get("updated_after");
  const updatedBefore = searchParams.get("updated_before");

  const [inlineSearch, setInlineSearch] = useState(searchQuery);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [showFolderForm, setShowFolderForm] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [folderParentId, setFolderParentId] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [deletingCategoryId, setDeletingCategoryId] = useState<string | null>(null);
  const [pendingCategoryDelete, setPendingCategoryDelete] = useState<CategoryNode | null>(null);

  useEffect(() => setInlineSearch(searchQuery), [searchQuery]);


  const params = useMemo(() => {
    const next = new URLSearchParams();
    if (searchQuery) next.set("q", searchQuery);
    if (categorySlug) next.set("category", categorySlug);
    if (tag) next.set("tag", tag);
    if (type) next.set("type", type);
    if (updatedAfter) next.set("updated_after", updatedAfter);
    if (updatedBefore) next.set("updated_before", updatedBefore);
    next.set("sort", sort);
    next.set("limit", "48");
    return next;
  }, [categorySlug, searchQuery, sort, tag, type, updatedAfter, updatedBefore]);

  const libraryQuery = useQuery({
    queryKey: ["library", params.toString()],
    queryFn: () => fetchLibrary(params),
  });

  const data = libraryQuery.data;
  const categoryOptions = useMemo(
    () => flattenCategoryOptions(data?.categories ?? []),
    [data?.categories],
  );
  const flatCategories = useMemo(() => flattenCategories(data?.categories ?? []), [data?.categories]);
  const activePath = useMemo(
    () => findCategoryPath(data?.categories ?? [], categorySlug),
    [categorySlug, data?.categories],
  );
  const pageTitle = title ?? activePath.at(-1)?.name ?? t(language, "myLibrary");
  const pageDescription = description ?? t(language, flatList && forcedType === "SKILL" ? "flatSkillsDescription" : flatList && forcedType === "PROMPT" ? "flatPromptsDescription" : "libraryDefaultDescription");
  const hasFilters = Boolean(
    searchQuery ||
    categorySlug ||
    tag ||
    (!forcedType && type) ||
    updatedAfter ||
    updatedBefore,
  );
  const activeFilterCount = [
    !forcedType && type,
    !flatList && categorySlug,
    tag,
    updatedAfter || updatedBefore,
  ].filter(Boolean).length;
  const visibleItems = useMemo(() => data?.items ?? [], [data?.items]);
  const sortedItems = useMemo(() => {
    const items = [...visibleItems];
    items.sort((left, right) => {
      if (sort === "title") return left.title.localeCompare(right.title);
      if (sort === "recent") return latestTimestamp(right) - latestTimestamp(left);
      return right.usageCount - left.usageCount || latestTimestamp(right) - latestTimestamp(left);
    });
    return items;
  }, [sort, visibleItems]);

  const createCategoryMutation = useMutation({
    mutationFn: () => createCategory(buildCategoryCreatePayload(folderName, folderParentId)),
    onSuccess: () => {
      setFolderName("");
      setFolderParentId("");
      setShowFolderForm(false);
      setStatusMessage(t(language, "folderCreated"));
      void queryClient.invalidateQueries({ queryKey: ["library"] });
    },
    onError: () => setStatusMessage(t(language, "folderCreateFailed")),
  });

  const deleteCategoryMutation = useMutation({
    mutationFn: (category: CategoryNode) => deleteCategory(category.id),
    onMutate: (category) => setDeletingCategoryId(category.id),
    onSuccess: (_result, deletedCategory) => {
      setPendingCategoryDelete(null);
      setStatusMessage(t(language, "folderDeleted"));
      if (activePath.some((category) => category.id === deletedCategory.id)) {
        router.push("/library", { scroll: false });
      }
      void queryClient.invalidateQueries({ queryKey: ["library"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => setStatusMessage(t(language, "folderDeleteFailed")),
    onSettled: () => setDeletingCategoryId(null),
  });

  function replaceLibraryQuery(updates: Record<string, string | null>) {
    const nextParams = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value) nextParams.set(key, value);
      else nextParams.delete(key);
    }
    const query = nextParams.toString();
    router.replace(`${pathname}${query ? `?${query}` : ""}`, { scroll: false });
  }

  function clearLibraryFilters() {
    router.push(forcedType ? routeForType(forcedType) : "/library", { scroll: false });
  }

  function handleInlineSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    replaceLibraryQuery({ q: inlineSearch.trim() || null });
  }

  function pushCategoryFilter(value: string) {
    const nextParams = new URLSearchParams(searchParams.toString());
    const query = nextParams.toString();
    const targetPath = value === "ALL" ? "/library" : `/library/${value}`;
    router.push(`${targetPath}${query ? `?${query}` : ""}`, { scroll: false });
  }

  function updateDateFilter(value: string, boundary: "start" | "end") {
    replaceLibraryQuery({
      [boundary === "start" ? "updated_after" : "updated_before"]: toUtcDateBoundaryIso(
        value,
        boundary,
      ),
    });
  }

  function handleCreateCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createCategoryMutation.mutate();
  }

  function confirmDeleteCategory() {
    if (!pendingCategoryDelete || deleteCategoryMutation.isPending) return;
    deleteCategoryMutation.mutate(pendingCategoryDelete);
  }

  const typeChoices: FilterChipChoice[] = [
    { value: "SKILL", label: t(language, "skill") },
    { value: "PROMPT", label: t(language, "prompt") },
  ];
  const categoryChoices: FilterChipChoice[] = [
    ...flatCategories.map((category) => ({ value: category.slug, label: category.name })),
  ];
  const tagChoices: FilterChipChoice[] = [
    ...(data?.tags ?? []).map((tagName) => ({ value: tagName, label: tagName })),
  ];
  const sortChoices: FilterChipChoice[] = [
    { value: "popular", label: t(language, "popular") },
    { value: "recent", label: t(language, "newest") },
    { value: "title", label: t(language, "titleSort") },
  ];

  return (
    <div className="archive-document-page min-h-[calc(100vh-74px)] px-8 py-10 md:px-14 xl:px-16">
      <section className="mb-7 border-b border-[#cfc8b8] pb-7">
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#161616]">{flatList ? t(language, "flatLibraryList") : t(language, "shelfBrowser")}</p>
        <h1 className="mt-4 font-serif text-6xl font-bold leading-none tracking-[-0.055em] text-[#050505] md:text-7xl">{pageTitle}</h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-[#111111]">{pageDescription}</p>
      </section>

      <div className="archive-filter-panel mb-8">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <form onSubmit={handleInlineSearch} className="relative max-w-[560px] xl:flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6f6a60]" aria-hidden="true" />
            <input
              value={inlineSearch}
              onChange={(event) => setInlineSearch(event.target.value)}
              placeholder={t(language, "librarySearchPlaceholder")}
              className="h-10 w-full rounded-full border border-[#cfc8b8] bg-[#fbfaf6] pl-10 pr-4 text-sm text-[#111111] outline-none focus-visible:ring-2 focus-visible:ring-black/15"
            />
          </form>

          <div className="flex flex-wrap items-center gap-2">
            {!flatList ? (
              <Button
                type="button"
                variant="secondary"
                className="h-9 rounded-full border-[#cfc8b8] bg-[#fbfaf6] px-4 text-sm font-semibold text-[#36322d] hover:bg-[#eee9df]"
                onClick={() => setShowFolderForm((value) => !value)}
              >
                <FolderPlus className="h-4 w-4" /> {t(language, "folder")}
              </Button>
            ) : null}
            <Button
              type="button"
              variant="secondary"
              className="h-9 rounded-full border-[#cfc8b8] bg-[#fbfaf6] px-4 text-sm font-semibold text-[#36322d] hover:bg-[#eee9df]"
              aria-expanded={filtersOpen}
              onClick={() => setFiltersOpen((current) => !current)}
            >
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              {t(language, "filters")} ({activeFilterCount})
            </Button>
          </div>
        </div>

        {filtersOpen ? (
          <div className="mt-4 space-y-4 rounded-2xl border border-[#d8d3c7] bg-white/45 p-4">
            <div className="grid gap-4 lg:grid-cols-2">
              {forcedType ? null : (
                <FilterChipGroup
                  name="library-type"
                  label={t(language, "typeFilter")}
                  value={type ?? "ALL"}
                  onChange={(value) => replaceLibraryQuery({ type: value === "ALL" ? null : value })}
                  allLabel={t(language, "allTypes")}
                  choices={typeChoices}
                />
              )}
              {!flatList ? (
                <FilterChipGroup
                  name="library-category"
                  label={t(language, "categoryFilter")}
                  value={categorySlug ?? "ALL"}
                  onChange={pushCategoryFilter}
                  allLabel={t(language, "allCategories")}
                  choices={categoryChoices}
                  emptyLabel={t(language, "noCategories")}
                />
              ) : null}
              <FilterChipGroup
                name="library-tag"
                label={t(language, "tagsFilter")}
                value={tag ?? "ALL"}
                onChange={(value) => replaceLibraryQuery({ tag: value === "ALL" ? null : value })}
                allLabel={t(language, "allTags")}
                choices={tagChoices}
                emptyLabel={t(language, "allTags")}
              />
              <FilterChipGroup
                name="library-sort"
                label={t(language, "sortBy")}
                value={sort}
                onChange={(value) => replaceLibraryQuery({ sort: value })}
                allLabel={null}
                choices={sortChoices}
              />
            </div>
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_160px] md:items-end">
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">
                  {t(language, "updatedRange")}
                </p>
                <p className="rounded-xl border border-[#d8d3c7] bg-white/55 px-3 py-2 text-xs leading-5 text-[#514c44]">
                  {t(language, "updatedDateFilterHelper")}
                </p>
              </div>
              <label className="space-y-2 text-sm font-semibold text-[#28241f]">
                {t(language, "fromDate")}
                <Input
                  name="library-updated-from"
                  type="date"
                  value={dateInputValue(updatedAfter)}
                  onChange={(event) => updateDateFilter(event.target.value, "start")}
                />
              </label>
              <label className="space-y-2 text-sm font-semibold text-[#28241f]">
                {t(language, "toDate")}
                <Input
                  name="library-updated-to"
                  type="date"
                  value={dateInputValue(updatedBefore)}
                  onChange={(event) => updateDateFilter(event.target.value, "end")}
                />
              </label>
            </div>
          </div>
        ) : null}
      </div>

      {showFolderForm && !flatList ? (
        <FolderCreateForm
          name={folderName}
          parentId={folderParentId}
          options={categoryOptions}
          isPending={createCategoryMutation.isPending}
          onNameChange={setFolderName}
          onParentChange={setFolderParentId}
          onSubmit={handleCreateCategory}
        />
      ) : null}

      {statusMessage ? <p className="archive-inline-status mb-6">{statusMessage}</p> : null}

      {pendingCategoryDelete ? (
        <div className="archive-inline-confirm mb-6" role="status" aria-live="polite">
          <div>
            <p className="font-semibold text-[#111111]">{tx(language, "deleteCategoryInlineConfirm", { name: pendingCategoryDelete.name })}</p>
            <p className="mt-1 text-sm text-[#6f6a60]">{t(language, "inlineDeleteConfirmation")}</p>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={() => setPendingCategoryDelete(null)} disabled={deleteCategoryMutation.isPending}>{t(language, "cancel")}</Button>
            <Button type="button" onClick={confirmDeleteCategory} disabled={deleteCategoryMutation.isPending}>
              {deleteCategoryMutation.isPending ? t(language, "deleting") : t(language, "deleteAction")}
            </Button>
          </div>
        </div>
      ) : null}

      {hasFilters ? (
        <div className="mb-6">
          <Button variant="ghost" size="sm" onClick={clearLibraryFilters}>
            <X className="h-3.5 w-3.5" /> {t(language, "clearFilters")}
          </Button>
        </div>
      ) : null}

      {!flatList ? (
        <LibraryFolderBrowser
          categories={data?.categories ?? []}
          activePath={activePath}
          language={language}
          deletingCategoryId={deletingCategoryId}
          onDelete={setPendingCategoryDelete}
        />
      ) : null}

      <section aria-labelledby="library-items-heading">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 id="library-items-heading" className="font-serif text-3xl font-bold text-[#111111]">
              {flatList ? pageTitle : t(language, "libraryItemsHeading")}
            </h2>
            <p className="mt-1 text-sm text-[#625c52]">{tx(language, "archiveCandidateCount", { count: data?.total ?? sortedItems.length })}</p>
          </div>
          <div className="flex gap-2">
            <Button asChild variant="secondary" size="sm"><Link href="/library/skills"><Code2 className="h-4 w-4" /> {t(language, "mySkills")}</Link></Button>
            <Button asChild variant="secondary" size="sm"><Link href="/library/prompts"><ScrollText className="h-4 w-4" /> {t(language, "myPrompts")}</Link></Button>
          </div>
        </div>

        {libraryQuery.isLoading ? (
          <div className="archive-explore-card p-8 text-[#625c52]">{t(language, "loadingLibrary")}</div>
        ) : libraryQuery.isError ? (
          <div className="archive-explore-card p-8 text-[#625c52]">{t(language, "libraryLoadFailed")}</div>
        ) : sortedItems.length === 0 ? (
          <div className="archive-explore-card p-8 text-[#625c52]">
            <p className="font-serif text-2xl text-[#111111]">{t(language, "noItemsTitle")}</p>
            <p className="mt-2 text-sm">{t(language, "emptyItemsDescription")}</p>
          </div>
        ) : (
          <div className={flatList ? "grid gap-3" : "grid gap-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"}>
            {sortedItems.map((item) => <LibraryItemCard key={item.id} item={item} view={flatList ? "list" : "grid"} />)}
          </div>
        )}
      </section>
    </div>
  );
}
