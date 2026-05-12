"use client";

import { useEffect, useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useLibraryStore } from "@/store/library-store";

export function TopHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const searchQuery = useLibraryStore((state) => state.searchQuery);
  const setSearchQuery = useLibraryStore((state) => state.setSearchQuery);
  const addRecentSearch = useLibraryStore((state) => state.addRecentSearch);
  const [localQuery, setLocalQuery] = useState(searchQuery);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setSearchQuery(localQuery);
      if (localQuery.trim()) addRecentSearch(localQuery);
      if (!pathname.startsWith("/library") && localQuery.trim()) router.push("/library");
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [addRecentSearch, localQuery, pathname, router, setSearchQuery]);

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-archive-950/80 px-4 py-4 backdrop-blur-xl lg:px-8">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-bronze">AI Agent Capability Library</p>
          <h1 className="font-serif text-2xl text-parchment md:text-3xl">ALEXANDRIA-HERMES</h1>
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-3 xl:max-w-2xl">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
            <Input
              value={localQuery}
              onChange={(event) => setLocalQuery(event.target.value)}
              placeholder="Search capabilities, workflows, knowledge..."
              className="pl-9"
            />
          </div>
          <Button variant="secondary" size="icon" aria-label="Open filters">
            <SlidersHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
