"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Grid2X2, List, Search, X } from "lucide-react";
import { motion } from "framer-motion";

import { fetchLibrary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { CategoryTree } from "@/components/library/category-tree";
import { SkillCard } from "@/components/library/skill-card";
import { useLibraryStore } from "@/store/library-store";

export function LibraryClient({ initialCategory }: { initialCategory?: string }) {
  const {
    searchQuery,
    categorySlug,
    tag,
    type,
    sort,
    viewMode,
    recentSearches,
    addRecentSearch,
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
    const timeout = window.setTimeout(() => {
      setSearchQuery(draftQuery);
      if (draftQuery.trim()) addRecentSearch(draftQuery);
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [addRecentSearch, draftQuery, searchQuery, setSearchQuery]);

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

  const { data, isLoading } = useQuery({
    queryKey: ["library", params.toString()],
    queryFn: () => fetchLibrary(params),
  });

  return (
    <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="space-y-4">
        <Card className="p-4">
          <p className="mb-3 text-xs uppercase tracking-[0.28em] text-bronze">Shelves</p>
          {data ? <CategoryTree categories={data.categories} activeSlug={categorySlug} /> : <p className="text-sm text-stone-500">Loading categories...</p>}
        </Card>
        <Card className="p-4">
          <p className="mb-3 text-xs uppercase tracking-[0.28em] text-bronze">Recent Searches</p>
          <div className="flex flex-wrap gap-2">
            {recentSearches.length === 0 && <span className="text-sm text-stone-500">No searches yet</span>}
            {recentSearches.map((item) => (
              <button key={item} onClick={() => setSearchQuery(item)} className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-stone-300 hover:border-gold-300/40">
                {item}
              </button>
            ))}
          </div>
        </Card>
      </aside>

      <section className="space-y-5">
        <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-bronze">Library Explorer</p>
              <h2 className="font-serif text-4xl text-gold-50">Capability stacks and operational books</h2>
            </div>
            <div className="flex items-center gap-2">
              <Button variant={viewMode === "grid" ? "default" : "secondary"} size="icon" onClick={() => setViewMode("grid")} aria-label="Grid view">
                <Grid2X2 className="h-4 w-4" />
              </Button>
              <Button variant={viewMode === "list" ? "default" : "secondary"} size="icon" onClick={() => setViewMode("list")} aria-label="List view">
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-[1fr_180px_180px_180px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
              <Input value={draftQuery} onChange={(event) => setDraftQuery(event.target.value)} placeholder="Keyword search" className="pl-9" />
            </div>
            <select value={type ?? ""} onChange={(event) => setType(event.target.value || null)} className="archive-select">
              <option value="">All types</option>
              <option value="SKILL">Skills</option>
              <option value="WORKFLOW">Workflows</option>
              <option value="KNOWLEDGE">Knowledge</option>
              <option value="CHECKLIST">Checklists</option>
            </select>
            <select value={tag ?? ""} onChange={(event) => setTag(event.target.value || null)} className="archive-select">
              <option value="">All tags</option>
              {data?.tags.map((tagName) => (
                <option key={tagName} value={tagName}>{tagName}</option>
              ))}
            </select>
            <select value={sort} onChange={(event) => setSort(event.target.value as "recent" | "popular" | "title")} className="archive-select">
              <option value="recent">Recently used</option>
              <option value="popular">Most popular</option>
              <option value="title">Title</option>
            </select>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-stone-500">
            <span>{data?.total ?? 0} matching archives</span>
            {(searchQuery || categorySlug || tag || type) && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <X className="h-3.5 w-3.5" /> Clear filters
              </Button>
            )}
          </div>
        </div>

        {isLoading && <div className="rounded-2xl border border-white/10 p-10 text-stone-400">Consulting the catalog...</div>}
        {!isLoading && data?.items.length === 0 && <div className="rounded-2xl border border-white/10 p-10 text-stone-400">No matching archive entries.</div>}
        <motion.div layout className={viewMode === "grid" ? "grid gap-4 md:grid-cols-2 2xl:grid-cols-3" : "grid gap-3"}>
          {data?.items.map((skill) => <SkillCard key={skill.id} skill={skill} view={viewMode} />)}
        </motion.div>
      </section>
    </div>
  );
}
