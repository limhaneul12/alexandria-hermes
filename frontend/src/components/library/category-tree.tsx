"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";
import type { CategoryNode } from "@/types/library";

export function CategoryTree({ categories, activeSlug }: { categories: CategoryNode[]; activeSlug?: string | null }) {
  return (
    <div className="space-y-1">
      {categories.map((category) => (
        <CategoryBranch key={category.id} category={category} activeSlug={activeSlug} level={0} />
      ))}
    </div>
  );
}

function CategoryBranch({ category, activeSlug, level }: { category: CategoryNode; activeSlug?: string | null; level: number }) {
  const active = activeSlug === category.slug;
  return (
    <div>
      <Link
        href={`/library/${category.slug}`}
        className={cn(
          "flex items-center justify-between rounded-lg px-3 py-2 text-sm transition hover:bg-white/[0.05]",
          active ? "bg-gold-300/10 text-gold-100" : "text-stone-400",
        )}
        style={{ paddingLeft: `${12 + level * 14}px` }}
      >
        <span className="flex items-center gap-2">
          <ChevronRight className={cn("h-3.5 w-3.5", category.children.length === 0 && "opacity-0")} />
          {category.name}
        </span>
        <span className="text-xs text-stone-600">{category.skillCount}</span>
      </Link>
      {category.children.length > 0 && (
        <div className="mt-1 space-y-1">
          {category.children.map((child) => (
            <CategoryBranch key={child.id} category={child} activeSlug={activeSlug} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
