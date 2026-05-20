"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookMarked, CalendarRange, ScrollText, SlidersHorizontal } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FilterChipGroup } from "@/components/ui/filter-chip-group";
import { Input } from "@/components/ui/input";
import { fetchCurrentMemoryCompact, fetchMemoryCompacts } from "@/lib/api";
import {
  countFilterChoices,
  humanizeFilterLabel,
  toUtcDateBoundaryIso,
} from "@/lib/filter-utils";
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
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [currentProject, setCurrentProject] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const filterOptionParams = useMemo(
    () => new URLSearchParams({ limit: "200" }),
    [],
  );

  const params = useMemo(() => {
    const searchParams = new URLSearchParams({ limit: "60" });
    if (project.trim()) searchParams.set("project", project.trim());
    if (status !== "ALL") searchParams.set("status", status);
    const fromValue = toUtcDateBoundaryIso(dateFrom, "start");
    const toValue = toUtcDateBoundaryIso(dateTo, "end");
    if (fromValue) {
      searchParams.set("covered_after", fromValue);
    }
    if (toValue) {
      searchParams.set("covered_before", toValue);
    }
    return searchParams;
  }, [dateFrom, dateTo, project, status]);

  const compactsQuery = useQuery({
    queryKey: ["memory-compacts", params.toString()],
    queryFn: () => fetchMemoryCompacts(params),
  });

  const filterOptionsQuery = useQuery({
    queryKey: ["memory-compacts", "filter-options"],
    queryFn: () => fetchMemoryCompacts(filterOptionParams),
    staleTime: 60_000,
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
  const filterSource = filterOptionsQuery.data?.items ?? compactsQuery.data?.items;
  const projectChoices = useMemo(
    () =>
      countFilterChoices(
        (filterSource ?? []).flatMap((compact) =>
          compact.project ? [compact.project] : [],
        ),
      ),
    [filterSource],
  );
  const statusCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const compact of filterSource ?? []) {
      counts.set(compact.status, (counts.get(compact.status) ?? 0) + 1);
    }
    return counts;
  }, [filterSource]);
  const statusChoices = useMemo(
    () =>
      MEMORY_COMPACT_STATUSES.map((item) => ({
        value: item,
        label: humanizeFilterLabel(item),
        count: statusCounts.get(item) ?? 0,
      })),
    [statusCounts],
  );
  const hasActiveFilters =
    project !== "" || status !== "ALL" || dateFrom !== "" || dateTo !== "";
  const advancedFilterCount = [
    project !== "",
    dateFrom !== "" || dateTo !== "",
  ].filter(Boolean).length;
  const displayedCount = compactsQuery.data?.total ?? compactsQuery.data?.items.length ?? 0;

  function clearFilters() {
    setProject("");
    setStatus("ALL");
    setDateFrom("");
    setDateTo("");
    setCurrentProject(null);
  }

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

      <Card className="p-4">
        <div className="space-y-4">
          <FilterChipGroup
            name="compact-status"
            label="Status"
            value={status}
            onChange={(value) => setStatus(value as MemoryCompactStatus | "ALL")}
            allLabel="All"
            choices={statusChoices}
            showCounts={false}
            variant="toolbar"
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-semibold text-[#514c44]">
              Displaying {displayedCount} results
            </p>
            <Button
              type="button"
              variant="secondary"
              className="h-9 w-full rounded-full border-[#cfc8b8] bg-[#fbfaf6] px-4 text-sm font-semibold text-[#36322d] hover:bg-[#eee9df] sm:w-auto"
              aria-expanded={filtersOpen}
              onClick={() => setFiltersOpen((current) => !current)}
            >
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              Filters ({advancedFilterCount})
            </Button>
          </div>

          {filtersOpen ? (
            <div className="space-y-4 rounded-2xl border border-[#d8d3c7] bg-white/45 p-4">
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
                <FilterChipGroup
                  name="compact-project"
                  label="Project"
                  value={project || "ALL"}
                  onChange={(value) => setProject(value === "ALL" ? "" : value)}
                  allLabel="All Projects"
                  choices={projectChoices}
                  emptyLabel="No project filters yet"
                />
                <Button type="button" className="self-end" onClick={loadCurrentCompact}>
                  Load Current Compact
                </Button>
              </div>
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_160px_auto] md:items-end">
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">
                    Summary Period
                  </p>
                  <p className="rounded-xl border border-[#d8d3c7] bg-white/55 px-3 py-2 text-xs leading-5 text-[#514c44]">
                    Filter by the dates included in the memory compact.
                  </p>
                </div>
                <label className="space-y-2 text-sm font-semibold text-[#28241f]">
                  From
                  <Input
                    name="compact-date-from"
                    type="date"
                    value={dateFrom}
                    onChange={(event) => setDateFrom(event.target.value)}
                  />
                </label>
                <label className="space-y-2 text-sm font-semibold text-[#28241f]">
                  To
                  <Input
                    name="compact-date-to"
                    type="date"
                    value={dateTo}
                    onChange={(event) => setDateTo(event.target.value)}
                  />
                </label>
                <Button
                  type="button"
                  variant="secondary"
                  className="self-end"
                  disabled={!hasActiveFilters}
                  onClick={clearFilters}
                >
                  Clear Filters
                </Button>
              </div>
            </div>
          ) : null}
        </div>
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
