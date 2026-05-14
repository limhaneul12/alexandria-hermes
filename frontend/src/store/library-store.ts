"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Language } from "@/lib/i18n";
import type { ItemType } from "@/types/library";

type ViewMode = "grid" | "compact" | "list";
type ThemeMode = "default" | "marble";

type LibraryState = {
  sidebarCollapsed: boolean;
  selectedSkillId: string | null;
  searchQuery: string;
  categorySlug: string | null;
  tag: string | null;
  type: ItemType | null;
  sort: "recent" | "popular" | "title";
  viewMode: ViewMode;
  theme: ThemeMode;
  language: Language;
  recentSearches: string[];
  setSidebarCollapsed: (value: boolean) => void;
  setSelectedSkillId: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  setCategorySlug: (slug: string | null) => void;
  setTag: (tag: string | null) => void;
  setType: (type: ItemType | null) => void;
  setSort: (sort: LibraryState["sort"]) => void;
  setViewMode: (mode: ViewMode) => void;
  setTheme: (theme: ThemeMode) => void;
  setLanguage: (language: Language) => void;
  addRecentSearch: (query: string) => void;
  clearFilters: () => void;
};

type PersistedLibraryState = Pick<
  LibraryState,
  "sidebarCollapsed" | "sort" | "viewMode" | "theme" | "language" | "recentSearches"
>;

const libraryStoreVersion = 1;

function normalizeSort(value: unknown): LibraryState["sort"] | undefined {
  return value === "recent" || value === "popular" || value === "title" ? value : undefined;
}

function normalizeViewMode(value: unknown): ViewMode | undefined {
  return value === "grid" || value === "compact" || value === "list" ? value : undefined;
}

function normalizeTheme(value: unknown): ThemeMode | undefined {
  if (value === "marble") return "marble";
  if (value === "default" || value === "dark" || value === "ember") return "default";
  return undefined;
}

function normalizeLanguage(value: unknown): Language | undefined {
  return value === "ko" || value === "en" ? value : undefined;
}

function normalizeRecentSearches(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  return value.filter((item): item is string => typeof item === "string").slice(0, 6);
}

function migrateLibraryStore(persistedState: unknown): Partial<LibraryState> {
  if (!persistedState || typeof persistedState !== "object") return {};

  const state = persistedState as Partial<PersistedLibraryState>;
  return {
    sidebarCollapsed: typeof state.sidebarCollapsed === "boolean" ? state.sidebarCollapsed : undefined,
    sort: normalizeSort(state.sort),
    viewMode: normalizeViewMode(state.viewMode),
    theme: normalizeTheme(state.theme),
    language: normalizeLanguage(state.language),
    recentSearches: normalizeRecentSearches(state.recentSearches),
  };
}

export const useLibraryStore = create<LibraryState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      selectedSkillId: null,
      searchQuery: "",
      categorySlug: null,
      tag: null,
      type: null,
      sort: "popular",
      viewMode: "grid",
      theme: "default",
      language: "ko",
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
      setLanguage: (language) => set({ language }),
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
        set({ searchQuery: "", categorySlug: null, tag: null, type: null, sort: "popular" }),
    }),
    {
      name: "alexandria-hermes-library",
      version: libraryStoreVersion,
      migrate: migrateLibraryStore,
      partialize: (state): PersistedLibraryState => ({
        sidebarCollapsed: state.sidebarCollapsed,
        sort: state.sort,
        viewMode: state.viewMode,
        theme: state.theme,
        language: state.language,
        recentSearches: state.recentSearches,
      }),
    },
  ),
);
