"use client";

import Link from "next/link";

import type { CategoryNode } from "@/types/library";

export function LibraryBreadcrumb({ path }: { path: CategoryNode[] }) {
  return (
    <nav aria-label="Library breadcrumb" className="mb-4 flex flex-wrap items-center gap-2 text-sm text-[#625c52]">
      <Link href="/library" className="font-semibold text-[#111111] hover:underline">내 서재</Link>
      {path.map((category, index) => (
        <span key={category.id} className="flex items-center gap-2">
          <span aria-hidden="true">/</span>
          {index === path.length - 1 ? (
            <span className="font-semibold text-[#111111]">{category.name}</span>
          ) : (
            <Link href={`/library/${category.slug}`} className="hover:underline">{category.name}</Link>
          )}
        </span>
      ))}
    </nav>
  );
}
