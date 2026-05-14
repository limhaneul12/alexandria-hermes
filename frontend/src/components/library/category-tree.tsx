"use client";

import Link from "next/link";
import { ChevronDown, Folder, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { useLibraryStore } from "@/store/library-store";
import type { CategoryNode } from "@/types/library";

function findCategoryIdBySlug(categories: CategoryNode[], slug: string): string | null {
  for (const category of categories) {
    if (category.slug === slug) return category.id;
    const childId = findCategoryIdBySlug(category.children, slug);
    if (childId) return childId;
  }
  return null;
}

export function CategoryTree({
  categories,
  activeSlug,
  deletingCategoryId,
  onDelete,
}: {
  categories: CategoryNode[];
  activeSlug?: string | null;
  deletingCategoryId?: string | null;
  onDelete?: (category: CategoryNode) => void;
}) {
  const language = useLibraryStore((state) => state.language);
  const activeId = activeSlug ? findCategoryIdBySlug(categories, activeSlug) : null;

  if (categories.length === 0) {
    return <p className="px-2 py-3 text-sm text-[#6f6a60]">{t(language, "noCategories")}</p>;
  }

  return (
    <nav className="space-y-1" aria-label={t(language, "categories")}>
      {categories.map((category) => (
        <CategoryBranch
          key={category.id}
          category={category}
          activeId={activeId}
          deletingCategoryId={deletingCategoryId}
          level={0}
          onDelete={onDelete}
        />
      ))}
    </nav>
  );
}

function CategoryBranch({
  category,
  activeId,
  deletingCategoryId,
  level,
  onDelete,
}: {
  category: CategoryNode;
  activeId?: string | null;
  deletingCategoryId?: string | null;
  level: number;
  onDelete?: (category: CategoryNode) => void;
}) {
  const language = useLibraryStore((state) => state.language);
  const active = activeId === category.id;
  const hasChildren = category.children.length > 0;
  const isDeleting = deletingCategoryId === category.id;

  return (
    <div className="relative">
      {level > 0 && <span className="absolute bottom-0 left-[18px] top-0 w-px bg-[#d8d3c7]" aria-hidden />}
      <div
        className={cn(
          "group/category-row relative flex items-center rounded-md border border-transparent text-sm transition duration-150 hover:border-[#cfc8b8] hover:bg-[#eee9df] hover:text-[#111111] focus-within:ring-2 focus-within:ring-gold-300/60",
          active
            ? "border-[#bfb6a8] bg-[#e9e4da] text-[#111111]"
            : "text-[#36322d]",
        )}
      >
        <Link
          href={`/library/${category.slug}`}
          className="flex min-w-0 flex-1 items-center justify-between gap-2 px-3 py-2 focus-visible:outline-none"
          style={{ paddingLeft: `${14 + level * 18}px` }}
          aria-current={active ? "page" : undefined}
        >
          <span className="flex min-w-0 items-center gap-2">
            {hasChildren ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-[#111111]" />
            ) : (
              <Folder className="h-3.5 w-3.5 shrink-0 text-[#514c44]" />
            )}
            <span className="truncate">{category.name}</span>
          </span>
          {category.skillCount > 0 && (
            <span className={cn("ml-2 text-xs transition", active ? "text-[#111111]" : "text-[#6f6a60] group-hover/category-row:text-[#36322d]")}>
              {category.skillCount}
            </span>
          )}
        </Link>
        {onDelete ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="mr-1 h-7 w-7 shrink-0 opacity-0 transition group-hover/category-row:opacity-100 focus:opacity-100"
            aria-label={`${category.name} ${t(language, "deleteFolder")}`}
            disabled={isDeleting}
            onClick={() => onDelete(category)}
          >
            <Trash2 className="h-3.5 w-3.5 text-[#8f5037] hover:text-[#7d412c]" />
          </Button>
        ) : null}
      </div>
      {hasChildren && (
        <div className="mt-1 space-y-1">
          {category.children.map((child) => (
            <CategoryBranch
              key={child.id}
              category={child}
              activeId={activeId}
              deletingCategoryId={deletingCategoryId}
              level={level + 1}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
