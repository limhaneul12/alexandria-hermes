"use client";

import Link from "next/link";
import { ArrowUp, Folder, Trash2 } from "lucide-react";

import { LibraryBreadcrumb } from "@/components/library/library-breadcrumb";
import { Button } from "@/components/ui/button";
import { t, type Language } from "@/lib/i18n";
import type { CategoryNode } from "@/types/library";

export function findCategoryPath(categories: CategoryNode[], slug: string | null): CategoryNode[] {
  if (!slug) return [];
  for (const category of categories) {
    if (category.slug === slug) return [category];
    const childPath = findCategoryPath(category.children, slug);
    if (childPath.length > 0) return [category, ...childPath];
  }
  return [];
}

export function flattenCategories(categories: CategoryNode[]): CategoryNode[] {
  return categories.flatMap((category) => [category, ...flattenCategories(category.children)]);
}

function visibleFolders(categories: CategoryNode[], activePath: CategoryNode[]) {
  if (activePath.length === 0) return categories;
  return activePath.at(-1)?.children ?? [];
}

function CategoryBrowseCard({
  category,
  language,
  onDelete,
  deleting,
}: {
  category: CategoryNode;
  language: Language;
  onDelete: (category: CategoryNode) => void;
  deleting: boolean;
}) {
  return (
    <div className="archive-explore-card group/category grid grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-4 p-4">
      <Link href={`/library/${category.slug}`} className="contents focus-visible:outline-none">
        <span className="flex h-11 w-11 items-center justify-center rounded-lg border border-[#ddd8cd] bg-white text-[#111111]">
          <Folder className="h-6 w-6" aria-hidden="true" />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-base font-bold text-[#111111]">{category.name}</span>
          <span className="text-sm text-[#625c52]">{category.skillCount} items</span>
        </span>
      </Link>
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

export function LibraryFolderBrowser({
  categories,
  activePath,
  language,
  deletingCategoryId,
  onDelete,
}: {
  categories: CategoryNode[];
  activePath: CategoryNode[];
  language: Language;
  deletingCategoryId: string | null;
  onDelete: (category: CategoryNode) => void;
}) {
  const folders = visibleFolders(categories, activePath);
  const parent = activePath.length > 1 ? activePath.at(-2) : null;

  return (
    <section className="mb-9" aria-labelledby="folder-browser-heading">
      <LibraryBreadcrumb path={activePath} />
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 id="folder-browser-heading" className="font-serif text-3xl font-bold text-[#111111]">하위 폴더</h2>
          <p className="mt-1 text-sm text-[#625c52]">폴더를 먼저 탐색하고, 선택한 shelf의 항목만 아래에서 확인합니다.</p>
        </div>
        {activePath.length > 0 ? (
          <Button asChild variant="secondary" size="sm">
            <Link href={parent ? `/library/${parent.slug}` : "/library"}>
              <ArrowUp className="h-4 w-4" aria-hidden="true" /> 상위 폴더로
            </Link>
          </Button>
        ) : null}
      </div>
      {folders.length === 0 ? (
        <div className="archive-explore-card p-6 text-sm text-[#625c52]">{t(language, "noCategories")}</div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {folders.map((category) => (
            <CategoryBrowseCard key={category.id} category={category} language={language} deleting={deletingCategoryId === category.id} onDelete={onDelete} />
          ))}
        </div>
      )}
    </section>
  );
}
