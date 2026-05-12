"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

type ViewMode = "grid" | "list";
type ThemeMode = "dark" | "ember";

type LibraryState = {
  sidebarCollapsed: boolean;
  selectedSkillId: number | null;
  searchQuery: string;
  categorySlug: string | null;
  tag: string | null;
  type: string | null;
  sort: "recent" | "popular" | "title";
  viewMode: ViewMode;
  theme: ThemeMode;
  recentSearches: string[];
  setSidebarCollapsed: (value: boolean) => void;
  setSelectedSkillId: (id: number | null) => void;
  setSearchQuery: (query: string) => void;
  setCategorySlug: (slug: string | null) => void;
  setTag: (tag: string | null) => void;
  setType: (type: string | null) => void;
  setSort: (sort: LibraryState["sort"]) => void;
  setViewMode: (mode: ViewMode) => void;
  setTheme: (theme: ThemeMode) => void;
  addRecentSearch: (query: string) => void;
  clearFilters: () => void;
};

export const useLibraryStore = create<LibraryState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      selectedSkillId: null,
      searchQuery: "",
      categorySlug: null,
      tag: null,
      type: null,
      sort: "recent",
      viewMode: "grid",
      theme: "dark",
      recentSearches: [],
      setSidebarCollapsed: (value) => set({ sidebarCollapsed: value }),
      setSelectedSkillId: (id) => set({ selectedSkillId: id }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      setCategorySlug: (slug) => set({ categorySlug: slug }),
      setTag: (tag) => set({ tag }),
      setType: (type) => set({ type }),
      setSort: (sort) => set({ sort }),
      setViewMode: (mode) => set({ viewMode: mode }),
      setTheme: (theme) => set({ theme }),
      addRecentSearch: (query) =>
        set((state) => {
          const normalized = query.trim();
          if (!normalized) return state;
          return {
            recentSearches: [
              normalized,
              ...state.recentSearches.filter((item) => item !== normalized),
            ].slice(0, 6),
          };
        }),
      clearFilters: () =>
        set({ searchQuery: "", categorySlug: null, tag: null, type: null, sort: "recent" }),
    }),
    { name: "alexandria-hermes-library" },
  ),
);
