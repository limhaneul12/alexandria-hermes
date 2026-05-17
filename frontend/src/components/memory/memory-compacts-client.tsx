"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookMarked, CalendarRange, Filter, ScrollText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { fetchCurrentMemoryCompact, fetchMemoryCompacts } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import {
  MEMORY_COMPACT_STATUSES,
  type MemoryCompactDTO,
  type MemoryCompactStatus,
} from "@/types/library";

function previewMarkdown(markdown: string) {
  return markdown.replace(/[#>*_`-]/g, "").split("\n").filter(Boolean).slice(0, 3).join(" ");
}

function MemoryCompactCard({ compact }: { compact: MemoryCompactDTO }) {
  return (
    <Card className="archive-paper-card overflow-hidden">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <Badge>{compact.status}</Badge>
            {compact.project ? <Badge>{compact.project}</Badge> : <Badge>Default Project</Badge>}
            <Badge>{compact.sourceRefs.length} refs</Badge>
          </div>
          <span className="text-xs tabular-nums uppercase tracking-[0.18em] text-[#6f6a60]">
            {formatDate(compact.updatedAt)}
          </span>
        </div>
        <CardTitle className="flex items-center gap-2">
          <BookMarked className="h-5 w-5" aria-hidden="true" /> Memory Compact
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[#6f6a60]">
          <CalendarRange className="h-4 w-4" aria-hidden="true" />
          {formatDate(compact.coveredFrom)} — {formatDate(compact.coveredTo)}
        </p>
        <p className="line-clamp-4 rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-sm leading-6 text-[#36322d]">
          {previewMarkdown(compact.markdownBody)}
        </p>
        <div className="flex flex-wrap gap-2">
          {compact.sourceRefs.slice(0, 3).map((ref) => (
            <Badge key={ref.id}>{ref.sourceType}: {ref.title}</Badge>
          ))}
        </div>
        <Button asChild size="sm">
          <Link href={`/memory-compacts/${encodeURIComponent(compact.id)}`}>Open Compact</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

export function MemoryCompactsClient() {
  const [project, setProject] = useState("");
  const [status, setStatus] = useState<MemoryCompactStatus | "ALL">("ALL");
  const [currentProject, setCurrentProject] = useState<string | null>(null);

  const params = useMemo(() => {
    const searchParams = new URLSearchParams({ limit: "60" });
    if (project.trim()) searchParams.set("project", project.trim());
    if (status !== "ALL") searchParams.set("status", status);
    return searchParams;
  }, [project, status]);

  const compactsQuery = useQuery({
    queryKey: ["memory-compacts", params.toString()],
    queryFn: () => fetchMemoryCompacts(params),
  });

  const currentQuery = useQuery({
    queryKey: ["memory-compact-current", currentProject],
    queryFn: () => fetchCurrentMemoryCompact(currentProject),
    enabled: currentProject !== null,
    retry: false,
  });

  function loadCurrentCompact() {
    setCurrentProject(project.trim() || "");
  }

  const currentCompact = currentQuery.data;

  return (
    <div className="archive-document-page space-y-7 px-8 py-10 md:px-14 xl:px-16">
      <section className="border-b border-[#cfc8b8] pb-8">
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#161616]">
          Memory Compacts
        </p>
        <h1 className="mt-4 text-balance font-serif text-6xl tracking-[-0.04em] text-[#070707] md:text-7xl">
          Durable Project Memory
        </h1>
        <p className="mt-5 max-w-3xl text-sm leading-7 text-[#36322d]">
          Browse the curated long-running Memory Compact artifacts that agents can
          cite, lazy-load, and hand to the Librarian without stuffing full context
          into every prompt.
        </p>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" aria-hidden="true" /> Compact Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
            <label className="space-y-2 text-sm font-semibold text-[#28241f]">
              Project
              <Input
                name="compact-project"
                autoComplete="off"
                value={project}
                onChange={(event) => setProject(event.target.value)}
                placeholder="e.g. alexandria-hermes…"
              />
            </label>
            <Button type="button" className="self-end" onClick={loadCurrentCompact}>
              Load Current Compact
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={status === "ALL" ? "default" : "outline"}
              onClick={() => setStatus("ALL")}
            >
              All
            </Button>
            {MEMORY_COMPACT_STATUSES.map((item) => (
              <Button
                key={item}
                type="button"
                variant={status === item ? "default" : "outline"}
                onClick={() => setStatus(item)}
              >
                {item}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {currentQuery.isError ? (
        <Card className="p-4 text-sm text-[#8f5037]">
          No current Memory Compact was found for that project.
        </Card>
      ) : currentCompact ? (
        <section className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-[#161616]">
            Current Compact
          </p>
          <MemoryCompactCard compact={currentCompact} />
        </section>
      ) : null}

      {compactsQuery.isLoading ? (
        <Card className="p-6 text-sm text-[#514c44]">Opening Memory Compacts…</Card>
      ) : compactsQuery.isError ? (
        <Card className="p-6 text-sm text-[#8f5037]">
          Memory Compacts could not be loaded. Check the backend connection and try again.
        </Card>
      ) : compactsQuery.data?.items.length ? (
        <section className="grid gap-5 xl:grid-cols-2">
          {compactsQuery.data.items.map((compact) => (
            <MemoryCompactCard key={compact.id} compact={compact} />
          ))}
        </section>
      ) : (
        <Card className="p-8 text-center">
          <ScrollText className="mx-auto h-8 w-8 text-[#6f6a60]" aria-hidden="true" />
          <p className="mt-3 font-serif text-2xl text-[#111111]">No Memory Compacts Yet</p>
          <p className="mt-2 text-sm text-[#6f6a60]">
            Create or mark a compact current from the backend/CLI to populate this archive shelf.
          </p>
        </Card>
      )}
    </div>
  );
}
