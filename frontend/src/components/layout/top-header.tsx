"use client";

import { useEffect, useState } from "react";
import { BookOpen, Search } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { t } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";

export function TopHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsString = searchParams.toString();
  const addRecentSearch = useLibraryStore((state) => state.addRecentSearch);
  const language = useLibraryStore((state) => state.language);
  const [localQuery, setLocalQuery] = useState(searchParams.get("q") ?? "");

  useEffect(() => setLocalQuery(searchParams.get("q") ?? ""), [searchParams]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const trimmed = localQuery.trim();
      if (trimmed) addRecentSearch(trimmed);
      const next = new URLSearchParams(searchParamsString);
      if (trimmed) next.set("q", trimmed); else next.delete("q");
      const query = next.toString();
      if (pathname.startsWith("/library")) {
        if (query !== searchParamsString) router.replace(`${pathname}${query ? `?${query}` : ""}`, { scroll: false });
      } else if (trimmed) {
        router.push(`/library${query ? `?${query}` : ""}`);
      }
    }, 220);
    return () => window.clearTimeout(timeout);
  }, [addRecentSearch, localQuery, pathname, router, searchParamsString]);

  return (
    <header className="sticky top-0 z-30 h-[74px] border-b border-[#ded9cd] bg-[#fffdfa]/96 text-[#111111] backdrop-blur">
      <div className="flex h-full items-center justify-between gap-6 px-8">
        <label className="relative w-full max-w-[620px]">
          <span className="sr-only">{t(language, "searchItems")}</span>
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#625c52]" aria-hidden="true" />
          <input
            name="globalSearch"
            autoComplete="off"
            value={localQuery}
            onChange={(event) => setLocalQuery(event.target.value)}
            placeholder={t(language, "globalSearchPlaceholder")}
            className="h-11 w-full rounded-lg border border-[#d8d3c7] bg-white px-11 pr-16 text-sm text-[#111111] outline-none placeholder:text-[#7b7368] focus-visible:border-[#111111]/40 focus-visible:ring-2 focus-visible:ring-black/10"
          />
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 rounded border border-[#d8d3c7] bg-[#f2eee5] px-2 py-1 text-xs text-[#514c44]">⌘ K</kbd>
        </label>
        <nav className="flex items-center gap-5 text-sm" aria-label="Global">
          <Link href="/library" className="flex items-center gap-2 font-medium text-[#111111] hover:text-[#514c44] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15">
            <BookOpen className="h-4 w-4" aria-hidden="true" /> {t(language, "library")}
          </Link>
        </nav>
      </div>
    </header>
  );
}
