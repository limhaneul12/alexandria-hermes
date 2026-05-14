"use client";

import Link from "next/link";
import { Code2, ScrollText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { t, tx, type Language } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";
import type { LibraryItemCardDTO } from "@/types/library";

function formatLibraryRelative(language: Language, value?: string | null) {
  if (!value) return t(language, "noHistory");
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.round(diff / 60_000));
  if (minutes < 60) return minutes === 1 ? t(language, "minuteAgo") : tx(language, "minutesAgo", { count: minutes });
  const hours = Math.round(minutes / 60);
  if (hours < 24) return tx(language, "hoursAgo", { count: hours });
  return tx(language, "daysAgo", { count: Math.round(hours / 24) });
}

export function LibraryItemCard({ item, view = "grid" }: { item: LibraryItemCardDTO; view?: "grid" | "compact" | "list" }) {
  const language = useLibraryStore((state) => state.language);
  const href = `/library/${item.category.slug}/${item.id}`;
  const relative = formatLibraryRelative(language, item.lastAccessedAt ?? item.updatedAt);
  const isPrompt = item.type === "PROMPT";
  const Icon = isPrompt ? ScrollText : Code2;

  if (view === "list") {
    return (
      <Link href={href} className="archive-explore-item-card grid gap-4 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15 md:grid-cols-[52px_minmax(0,1fr)_auto] md:items-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#ddd8cd] bg-white text-[#111111]"><Icon className="h-7 w-7" aria-hidden="true" /></span>
        <span className="min-w-0">
          <span className="block text-base font-bold text-[#111111]">{item.title}</span>
          <span className="mt-1 line-clamp-2 block text-sm leading-6 text-[#514c44]">{item.description}</span>
        </span>
        <span className="text-sm font-medium text-[#625c52]">{relative}</span>
      </Link>
    );
  }

  return (
    <Link href={href} aria-label={tx(language, "openSkill", { title: item.title })} className="archive-explore-item-card flex min-h-[230px] flex-col focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15">
      <div className="mb-4 flex items-start justify-between gap-4">
        <span className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#ddd8cd] bg-white text-[#111111]"><Icon className="h-7 w-7" aria-hidden="true" /></span>
        <Badge className="rounded-md uppercase tracking-[0.08em]">{isPrompt ? t(language, "prompt") : t(language, "skill")}</Badge>
      </div>
      <h3 className="text-base font-bold leading-6 text-[#111111]">{item.title}</h3>
      <p className="mt-4 line-clamp-3 flex-1 text-sm leading-6 text-[#514c44]">{item.description}</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {item.tags.slice(0, 3).map((tag) => <span key={tag} className="rounded border border-[#ddd8cd] bg-[#f6f3ec] px-2 py-1 text-[11px] text-[#514c44]">{tag}</span>)}
      </div>
      <p className="mt-5 text-xs font-medium text-[#625c52]">{relative}</p>
    </Link>
  );
}
