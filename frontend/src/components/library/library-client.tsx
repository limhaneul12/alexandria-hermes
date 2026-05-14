"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Bot,
  Code2,
  Folder,
  FolderPlus,
  Plus,
  Search,
  ScrollText,
  Tags,
  Trash2,
  X,
  type LucideIcon,
} from "lucide-react";

import { FolderCreateForm, LibraryItemCreatePanel } from "@/components/library/library-forms";
import { LibraryItemCard } from "@/components/library/library-item-card";
import { Button } from "@/components/ui/button";
import { createCategory, createPrompt, createSkill, deleteCategory, fetchLibrary } from "@/lib/api";
import { t, type Language } from "@/lib/i18n";
import {
  buildCategoryCreatePayload,
  buildPromptCreatePayload,
  buildSkillCreatePayload,
  flattenCategoryOptions,
  initialPromptDraft,
  initialSkillDraft,
  type PromptDraft,
  type SkillDraft,
} from "@/lib/library/forms";
import { useLibraryStore } from "@/store/library-store";
import { isItemType, type CategoryNode, type LibraryItemCardDTO } from "@/types/library";

function findCategoryPath(categories: CategoryNode[], slug: string | null): CategoryNode[] {
  if (!slug) return [];
  for (const category of categories) {
    if (category.slug === slug) return [category];
    const childPath = findCategoryPath(category.children, slug);
    if (childPath.length > 0) return [category, ...childPath];
  }
  return [];
}

function flattenCategories(categories: CategoryNode[]): CategoryNode[] {
  return categories.flatMap((category) => [category, ...flattenCategories(category.children)]);
}

function latestTimestamp(item: LibraryItemCardDTO) {
  return new Date(item.lastAccessedAt ?? item.updatedAt).getTime();
}

function formatShortAge(value?: string | null) {
  if (!value) return "New";
  const diff = Date.now() - new Date(value).getTime();
  const hours = Math.max(1, Math.round(diff / 3_600_000));
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function ItemMiniRow({ item }: { item: LibraryItemCardDTO }) {
  const Icon = item.type === "PROMPT" ? ScrollText : Code2;
  return (
    <a href={`/library/${item.category.slug}/${item.id}`} className="group grid grid-cols-[36px_minmax(0,1fr)] gap-3 rounded-lg p-2 transition-colors hover:bg-black/[0.035] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#ddd8cd] bg-white text-[#111111]">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-[#111111] group-hover:underline">{item.title}</span>
        <span className="mt-0.5 block text-xs text-[#625c52]">{item.type === "PROMPT" ? "Prompt" : "Skill"} · {formatShortAge(item.lastAccessedAt ?? item.updatedAt)}</span>
      </span>
    </a>
  );
}

function ExploreMetric({ icon: Icon, title, description, count, onClick }: { icon: LucideIcon; title: string; description: string; count: string; onClick?: () => void }) {
  const content = (
    <>
      <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg border border-[#ddd8cd] bg-white text-[#111111]">
        <Icon className="h-7 w-7" aria-hidden="true" />
      </span>
      <span>
        <span className="block text-lg font-bold text-[#111111]">{title}</span>
        <span className="mt-1 block text-sm leading-5 text-[#514c44]">{description}</span>
        <span className="mt-4 block text-sm font-bold text-[#111111]">{count}</span>
      </span>
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className="archive-explore-card grid min-h-36 grid-cols-[64px_minmax(0,1fr)] gap-4 text-left transition-colors hover:bg-white/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15">
        {content}
      </button>
    );
  }

  return <div className="archive-explore-card grid min-h-36 grid-cols-[64px_minmax(0,1fr)] gap-4">{content}</div>;
}

function CategoryBrowseCard({ category, language, onDelete, deleting }: { category: CategoryNode; language: Language; onDelete: (category: CategoryNode) => void; deleting: boolean }) {
  return (
    <div className="archive-explore-card group/category grid grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-4 p-4">
      <a href={`/library/${category.slug}`} className="contents focus-visible:outline-none">
        <span className="flex h-11 w-11 items-center justify-center rounded-lg border border-[#ddd8cd] bg-white text-[#111111]">
          <Folder className="h-6 w-6" aria-hidden="true" />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-base font-bold text-[#111111]">{category.name}</span>
          <span className="text-sm text-[#625c52]">{category.skillCount} items</span>
        </span>
      </a>
      <button
        type="button"
        disabled={deleting}
        onClick={() => onDelete(category)}
        className="rounded-md border border-transparent p-2 text-[#8a4331] opacity-70 transition hover:border-[#e0c3b8] hover:bg-[#fff2ee] hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15 disabled:opacity-40"
        aria-label={`${category.name} ${t(language, "deleteFolder")}`}
      >
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}

export function LibraryClient({ initialCategory }: { initialCategory?: string }) {
  const queryClient = useQueryClient();
  const language = useLibraryStore((state) => state.language);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const searchQuery = searchParams.get("q") ?? "";
  const categorySlug = initialCategory ?? null;
  const tag = searchParams.get("tag");
  const typeParam = searchParams.get("type");
  const type = typeParam && isItemType(typeParam) ? typeParam : null;
  const sortParam = searchParams.get("sort");
  const createParam = searchParams.get("create");
  const sort = sortParam === "recent" || sortParam === "title" ? sortParam : "popular";

  const [inlineSearch, setInlineSearch] = useState(searchQuery);
  const [showFolderForm, setShowFolderForm] = useState(false);
  const [showCreatePanel, setShowCreatePanel] = useState(false);
  const [createMode, setCreateMode] = useState<"SKILL" | "PROMPT">("SKILL");
  const [folderName, setFolderName] = useState("");
  const [folderParentId, setFolderParentId] = useState("");
  const [skillDraft, setSkillDraft] = useState<SkillDraft>(() => initialSkillDraft());
  const [promptDraft, setPromptDraft] = useState<PromptDraft>(() => initialPromptDraft());
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [deletingCategoryId, setDeletingCategoryId] = useState<string | null>(null);
  const [pendingCategoryDelete, setPendingCategoryDelete] = useState<CategoryNode | null>(null);

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
  const pageTitle = activePath.at(-1)?.name ?? t(language, "explore");
  const hasFilters = Boolean(searchQuery || categorySlug || tag || type);
  const visibleItems = useMemo(() => data?.items ?? [], [data?.items]);
  const skillCount = visibleItems.filter((item) => item.type === "SKILL").length;
  const promptCount = visibleItems.filter((item) => item.type === "PROMPT").length;
  const recentItems = useMemo(
    () => [...visibleItems].sort((left, right) => latestTimestamp(right) - latestTimestamp(left)).slice(0, 5),
    [visibleItems],
  );
  const recommendedItems = useMemo(
    () => [...visibleItems].sort((left, right) => right.usageCount - left.usageCount || latestTimestamp(right) - latestTimestamp(left)).slice(0, 4),
    [visibleItems],
  );
  const featuredItems = visibleItems.slice(0, 6);

  useEffect(() => setInlineSearch(searchQuery), [searchQuery]);

  useEffect(() => {
    if (createParam === "skill" || createParam === "prompt") {
      setCreateMode(createParam === "prompt" ? "PROMPT" : "SKILL");
      setShowCreatePanel(true);
    }
  }, [createParam]);

  function replaceLibraryQuery(updates: Record<string, string | null>) {
    const nextParams = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value) {
        nextParams.set(key, value);
      } else {
        nextParams.delete(key);
      }
    }
    const query = nextParams.toString();
    router.replace(`${pathname}${query ? `?${query}` : ""}`, { scroll: false });
  }

  function clearLibraryFilters() {
    router.push("/library", { scroll: false });
  }

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

  const createItemMutation = useMutation({
    mutationFn: () => createMode === "SKILL"
      ? createSkill(buildSkillCreatePayload(skillDraft))
      : createPrompt(buildPromptCreatePayload(promptDraft)),
    onSuccess: () => {
      setSkillDraft(initialSkillDraft());
      setPromptDraft(initialPromptDraft());
      setShowCreatePanel(false);
      setStatusMessage(createMode === "SKILL" ? t(language, "skillCreated") : t(language, "promptCreated"));
      void queryClient.invalidateQueries({ queryKey: ["library"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => setStatusMessage(createMode === "SKILL" ? t(language, "skillCreateFailed") : t(language, "promptCreateFailed")),
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

  function handleInlineSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    replaceLibraryQuery({ q: inlineSearch.trim() || null });
  }

  function handleCreateCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createCategoryMutation.mutate();
  }

  function handleCreateItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createItemMutation.mutate();
  }

  function handleDeleteCategory(category: CategoryNode) {
    setPendingCategoryDelete(category);
  }

  function confirmDeleteCategory() {
    if (!pendingCategoryDelete || deleteCategoryMutation.isPending) return;
    deleteCategoryMutation.mutate(pendingCategoryDelete);
  }

  function handleSkillFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const content = typeof reader.result === "string" ? reader.result : "";
      const titleFromFile = file.name.replace(/\.(md|markdown|txt)$/i, "").replace(/[-_]+/g, " ").trim();
      setSkillDraft((draft) => ({
        ...draft,
        title: draft.title || titleFromFile,
        summary: draft.summary || content.split("\n").find((line) => line.trim() && !line.trim().startsWith("#"))?.trim() || "",
        purpose: draft.purpose || titleFromFile,
        content,
      }));
    };
    reader.readAsText(file);
  }

  return (
    <div className="archive-document-page archive-explore-layout min-h-[calc(100vh-74px)]">
      <section className="px-8 py-10 md:px-14 xl:px-16">
        <div className="mb-7">
          <h1 className="font-serif text-6xl font-bold leading-none tracking-[-0.055em] text-[#050505] md:text-7xl">{pageTitle}</h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-[#111111]">
            Discover skills and prompts for your agents, then place them in the right folder when they are ready to use.
          </p>
        </div>

        <div className="archive-filter-panel mb-8">
          <form onSubmit={handleInlineSearch} className="relative max-w-[640px]">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6f6a60]" aria-hidden="true" />
            <input
              value={inlineSearch}
              onChange={(event) => setInlineSearch(event.target.value)}
              placeholder="What are you looking for?"
              className="h-12 w-full rounded-lg border border-[#d8d3c7] bg-white pl-11 pr-4 text-sm text-[#111111] outline-none focus-visible:ring-2 focus-visible:ring-black/15"
            />
          </form>

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_1fr_auto]">
            <label className="archive-field-box">
              <span>Type</span>
              <select value={type ?? ""} onChange={(event) => replaceLibraryQuery({ type: event.target.value || null })}>
                <option value="">All Types</option>
                <option value="SKILL">Skills</option>
                <option value="PROMPT">Prompts</option>
              </select>
            </label>
            <label className="archive-field-box">
              <span>Category</span>
              <select value={categorySlug ?? ""} onChange={(event) => router.push(event.target.value ? `/library/${event.target.value}` : "/library", { scroll: false })}>
                <option value="">All Categories</option>
                {flatCategories.map((category) => <option key={category.id} value={category.slug}>{category.name}</option>)}
              </select>
            </label>
            <label className="archive-field-box">
              <span>Tags</span>
              <select value={tag ?? ""} onChange={(event) => replaceLibraryQuery({ tag: event.target.value || null })}>
                <option value="">All Tags</option>
                {(data?.tags ?? []).map((tagName) => <option key={tagName} value={tagName}>{tagName}</option>)}
              </select>
            </label>
            <label className="archive-field-box">
              <span>Sort by</span>
              <select value={sort} onChange={(event) => replaceLibraryQuery({ sort: event.target.value })}>
                <option value="popular">Popular</option>
                <option value="recent">Newest</option>
                <option value="title">Title</option>
              </select>
            </label>
            <div className="flex items-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setShowFolderForm((value) => !value)}>
                <FolderPlus className="h-4 w-4" /> Folder
              </Button>
              <Button type="button" onClick={() => setShowCreatePanel((value) => !value)}>
                <Plus className="h-4 w-4" /> Add
              </Button>
            </div>
          </div>
        </div>

        {showFolderForm ? (
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

        {showCreatePanel ? (
          <LibraryItemCreatePanel
            mode={createMode}
            skillDraft={skillDraft}
            promptDraft={promptDraft}
            options={categoryOptions}
            isPending={createItemMutation.isPending}
            onModeChange={setCreateMode}
            onSkillDraftChange={(patch) => setSkillDraft((draft) => ({ ...draft, ...patch }))}
            onPromptDraftChange={(patch) => setPromptDraft((draft) => ({ ...draft, ...patch }))}
            onSkillFileSelect={handleSkillFile}
            onSubmit={handleCreateItem}
          />
        ) : null}

        {statusMessage ? <p className="archive-inline-status mb-6">{statusMessage}</p> : null}

        {pendingCategoryDelete ? (
          <div className="archive-inline-confirm mb-6" role="status" aria-live="polite">
            <div>
              <p className="font-semibold text-[#111111]">{pendingCategoryDelete.name} 폴더를 삭제할까요?</p>
              <p className="mt-1 text-sm text-[#6f6a60]">브라우저 팝업 대신 이 화면 안에서만 확인합니다.</p>
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="secondary" onClick={() => setPendingCategoryDelete(null)} disabled={deleteCategoryMutation.isPending}>취소</Button>
              <Button type="button" onClick={confirmDeleteCategory} disabled={deleteCategoryMutation.isPending}>
                {deleteCategoryMutation.isPending ? "삭제 중" : "삭제"}
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

        <section className="mb-9 grid gap-5 md:grid-cols-2 2xl:grid-cols-4" aria-label="Archive resource types">
          <ExploreMetric icon={Code2} title="Skills" description="Reusable capabilities your agent can perform." count={`${skillCount} items`} onClick={() => replaceLibraryQuery({ type: "SKILL" })} />
          <ExploreMetric icon={ScrollText} title="Prompts" description="Templates and instructions with tracked formats." count={`${promptCount} items`} onClick={() => replaceLibraryQuery({ type: "PROMPT" })} />
          <ExploreMetric icon={Folder} title="Folders" description="Shelves that keep related resources together." count={`${flatCategories.length} folders`} />
          <ExploreMetric icon={Tags} title="Tags" description="Fast labels for domains, tools, and use cases." count={`${data?.tags.length ?? 0} tags`} />
        </section>

        <section className="mb-9" aria-labelledby="popular-heading">
          <div className="mb-5 flex items-center justify-between gap-4">
            <h2 id="popular-heading" className="font-serif text-3xl font-bold text-[#111111]">Popular This Week</h2>
            <button type="button" onClick={() => replaceLibraryQuery({ sort: "popular" })} className="text-sm text-[#514c44] hover:text-[#111111]">View all</button>
          </div>
          {libraryQuery.isLoading ? (
            <div className="archive-explore-card p-8 text-[#625c52]">{t(language, "loadingLibrary")}</div>
          ) : libraryQuery.isError ? (
            <div className="archive-explore-card p-8 text-[#625c52]">{t(language, "libraryLoadFailed")}</div>
          ) : featuredItems.length === 0 ? (
            <div className="archive-explore-card p-8 text-[#625c52]">
              <p className="font-serif text-2xl text-[#111111]">{t(language, "noItemsTitle")}</p>
              <p className="mt-2 text-sm">Create a skill or prompt and it will appear in Explore.</p>
            </div>
          ) : (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
              {featuredItems.map((item) => <LibraryItemCard key={item.id} item={item} />)}
            </div>
          )}
        </section>

        <section id="categories" aria-labelledby="category-heading">
          <div className="mb-5 flex items-center justify-between gap-4">
            <h2 id="category-heading" className="font-serif text-3xl font-bold text-[#111111]">Browse by Category</h2>
            <button type="button" onClick={() => router.push("/library", { scroll: false })} className="text-sm text-[#514c44] hover:text-[#111111]">View all</button>
          </div>
          {flatCategories.length === 0 ? (
            <div className="archive-explore-card p-8 text-sm text-[#625c52]">{t(language, "noCategories")}</div>
          ) : (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {flatCategories.slice(0, 8).map((category) => (
                <CategoryBrowseCard key={category.id} category={category} language={language} deleting={deletingCategoryId === category.id} onDelete={handleDeleteCategory} />
              ))}
            </div>
          )}
        </section>
      </section>

      <aside className="archive-explore-rail hidden px-8 py-9 2xl:block">
        <div className="archive-rail-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2>Recently Accessed</h2>
            <span>See all</span>
          </div>
          <div className="space-y-2">
            {recentItems.length > 0 ? recentItems.map((item) => <ItemMiniRow key={item.id} item={item} />) : <p className="text-sm text-[#625c52]">No recent resources yet.</p>}
          </div>
        </div>

        <div className="archive-rail-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2>Recommended for You</h2>
            <span>See all</span>
          </div>
          <div className="space-y-2">
            {recommendedItems.length > 0 ? recommendedItems.map((item) => <ItemMiniRow key={item.id} item={item} />) : <p className="text-sm text-[#625c52]">Use resources to build better recommendations.</p>}
          </div>
        </div>

        <div className="archive-rail-card">
          <p className="mb-4 text-xs font-bold uppercase tracking-[0.14em] text-[#625c52]">Need Help?</p>
          <div className="grid grid-cols-[48px_minmax(0,1fr)] gap-4">
            <span className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#ddd8cd] bg-white text-[#111111]"><Bot className="h-7 w-7" aria-hidden="true" /></span>
            <div>
              <h2>Ask the Librarian</h2>
              <p className="mt-1 text-sm text-[#625c52]">Get help from your AI librarian.</p>
              <a href="/settings#librarians" className="mt-4 inline-flex items-center rounded border border-[#cfc8b8] bg-white px-4 py-2 text-sm font-semibold text-[#111111] hover:bg-[#f6f3ec]">Ask a Question</a>
            </div>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-[#d8d3c7] bg-white/55">
          <Image src="/librarian-archive.svg" alt="Librarian reading in the archive" width={420} height={420} className="h-auto w-full" />
          <div className="p-5">
            <h2 className="font-serif text-xl font-bold text-[#111111]">A Living Archive</h2>
            <p className="mt-2 text-sm leading-6 text-[#514c44]">New skills and prompts are added every day by contributors like you.</p>
          </div>
        </div>
      </aside>
    </div>
  );
}
