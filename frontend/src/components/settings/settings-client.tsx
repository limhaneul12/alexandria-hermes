"use client";

import { Moon, PanelLeftClose, ScrollText, Settings2, SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLibraryStore } from "@/store/library-store";

export function SettingsClient() {
  const collapsed = useLibraryStore((state) => state.sidebarCollapsed);
  const setCollapsed = useLibraryStore((state) => state.setSidebarCollapsed);
  const theme = useLibraryStore((state) => state.theme);
  const setTheme = useLibraryStore((state) => state.setTheme);
  const viewMode = useLibraryStore((state) => state.viewMode);
  const setViewMode = useLibraryStore((state) => state.setViewMode);
  const clearFilters = useLibraryStore((state) => state.clearFilters);

  return (
    <div className="space-y-7">
      <section className="rounded-3xl border border-gold-300/20 bg-archive-panel p-8 shadow-gold">
        <p className="text-xs uppercase tracking-[0.34em] text-bronze">Settings</p>
        <h2 className="mt-3 font-serif text-5xl text-gold-50">Library operating controls.</h2>
        <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
          Tune local archive behavior, browsing preferences, and the visual density of the Alexandria-Hermes operating interface.
        </p>
      </section>

      <section id="library" className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><SlidersHorizontal className="h-5 w-5" /> Library Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-parchment">Default explorer view</p>
                <p className="text-sm text-stone-500">Choose book-cover grid or operational list mode.</p>
              </div>
              <div className="flex gap-2">
                <Button variant={viewMode === "grid" ? "default" : "secondary"} onClick={() => setViewMode("grid")}>Grid</Button>
                <Button variant={viewMode === "list" ? "default" : "secondary"} onClick={() => setViewMode("list")}>List</Button>
              </div>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-parchment">Reset filters</p>
                <p className="text-sm text-stone-500">Clears search, shelf, tag, type, and sort state.</p>
              </div>
              <Button variant="outline" onClick={clearFilters}>Reset archive filters</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Settings2 className="h-5 w-5" /> Interface</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-parchment">Sidebar state</p>
                <p className="text-sm text-stone-500">Collapse the grand archive navigation rail.</p>
              </div>
              <Button variant="secondary" onClick={() => setCollapsed(!collapsed)}>
                <PanelLeftClose className="h-4 w-4" /> {collapsed ? "Expand" : "Collapse"}
              </Button>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-parchment">Theme tone</p>
                <p className="text-sm text-stone-500">Dark archive is default; ember adds warmer accents.</p>
              </div>
              <div className="flex gap-2">
                <Button variant={theme === "dark" ? "default" : "secondary"} onClick={() => setTheme("dark")}><Moon className="h-4 w-4" /> Dark</Button>
                <Button variant={theme === "ember" ? "default" : "secondary"} onClick={() => setTheme("ember")}>Ember</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ScrollText className="h-5 w-5" /> Data Contract</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            {[
              ["Persistence", "SQLite via Prisma ORM"],
              ["Caching", "TanStack Query, 30s stale window"],
              ["Local state", "Zustand persisted preferences"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-white/10 bg-black/25 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{label}</p>
                <p className="mt-2 text-parchment">{value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
