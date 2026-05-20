"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Clipboard, ScrollText, SlidersHorizontal } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FilterChipGroup } from "@/components/ui/filter-chip-group";
import { Input } from "@/components/ui/input";
import { archiveContext, fetchContexts } from "@/lib/api";
import {
  countFilterChoices,
  humanizeFilterLabel,
  toUtcDateBoundaryIso,
} from "@/lib/filter-utils";
import { formatDate } from "@/lib/utils";
import { CONTEXT_KINDS, type ContextDTO, type ContextKind } from "@/types/library";

type ContextDateField = "created" | "updated";

function preview(content: string) {
  return content.replace(/[#>*_`-]/g, "").split("\n").filter(Boolean).slice(0, 2).join(" ");
}

function ContextCard({ context, onArchive }: { context: ContextDTO; onArchive: (contextId: string) => void }) {
  const [confirmingArchive, setConfirmingArchive] = useState(false);

  function requestArchive() {
    if (!confirmingArchive) {
      setConfirmingArchive(true);
      return;
    }
    setConfirmingArchive(false);
    onArchive(context.id);
  }

  return (
    <Card className="archive-paper-card overflow-hidden">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <Badge>{context.kind}</Badge>
            <Badge className="border-[#cfc8b8] bg-[#f6f3ec] text-[#36322d]">{context.status}</Badge>
            {context.project ? <Badge>{context.project}</Badge> : null}
          </div>
          <span className="text-xs tabular-nums uppercase tracking-[0.18em] text-[#6f6a60]">{formatDate(context.updatedAt)}</span>
        </div>
        <CardTitle>{context.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-6 text-[#514c44]">{context.summary || preview(context.content)}</p>
        <p className="line-clamp-3 rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-sm leading-6 text-[#36322d]">
          {preview(context.content)}
        </p>
        <div className="flex flex-wrap gap-2">
          {context.tags.map((tag) => <Badge key={tag}>{tag}</Badge>)}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm"><Link href={`/contexts/${encodeURIComponent(context.id)}`}>Open Context</Link></Button>
          {context.restorePrompt ? (
            <Button type="button" size="sm" variant="secondary" onClick={() => void navigator.clipboard.writeText(context.restorePrompt ?? "")}>
              <Clipboard className="h-4 w-4" aria-hidden="true" /> Copy Restore Prompt
            </Button>
          ) : null}
          {!context.isArchived ? (
            <Button type="button" size="sm" variant="outline" onClick={requestArchive}>
              <Archive className="h-4 w-4" aria-hidden="true" /> {confirmingArchive ? "Confirm Archive" : "Archive"}
            </Button>
          ) : null}
        </div>
        {confirmingArchive ? (
          <div className="archive-inline-confirm" role="status" aria-live="polite">
            <p className="text-sm text-[#8f5037]">Archive this context? It remains available when Include Archived is enabled.</p>
            <Button type="button" size="sm" variant="secondary" onClick={() => setConfirmingArchive(false)}>Cancel</Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function ContextVaultClient() {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<ContextKind | "ALL">("ALL");
  const [project, setProject] = useState("");
  const [tag, setTag] = useState("");
  const [dateField, setDateField] = useState<ContextDateField>("updated");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const filterOptionParams = useMemo(
    () => new URLSearchParams({ limit: "200", include_archived: "true" }),
    [],
  );

  const params = useMemo(() => {
    const searchParams = new URLSearchParams({ limit: "60" });
    if (kind !== "ALL") searchParams.set("kind", kind);
    if (project.trim()) searchParams.set("project", project.trim());
    if (tag.trim()) searchParams.set("tag", tag.trim());
    const fromValue = toUtcDateBoundaryIso(dateFrom, "start");
    const toValue = toUtcDateBoundaryIso(dateTo, "end");
    if (fromValue) {
      searchParams.set(
        dateField === "created" ? "created_after" : "updated_after",
        fromValue,
      );
    }
    if (toValue) {
      searchParams.set(
        dateField === "created" ? "created_before" : "updated_before",
        toValue,
      );
    }
    if (includeArchived) searchParams.set("include_archived", "true");
    return searchParams;
  }, [dateField, dateFrom, dateTo, includeArchived, kind, project, tag]);

  const contextsQuery = useQuery({
    queryKey: ["contexts", params.toString()],
    queryFn: () => fetchContexts(params),
  });

  const filterOptionsQuery = useQuery({
    queryKey: ["contexts", "filter-options"],
    queryFn: () => fetchContexts(filterOptionParams),
    staleTime: 60_000,
  });

  const archiveMutation = useMutation({
    mutationFn: archiveContext,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["contexts"] });
    },
  });

  const filterSource = filterOptionsQuery.data?.items ?? contextsQuery.data?.items;
  const kindCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const context of filterSource ?? []) {
      counts.set(context.kind, (counts.get(context.kind) ?? 0) + 1);
    }
    return counts;
  }, [filterSource]);
  const kindChoices = useMemo(
    () =>
      CONTEXT_KINDS.map((item) => ({
        value: item,
        label: humanizeFilterLabel(item),
        count: kindCounts.get(item) ?? 0,
      })),
    [kindCounts],
  );
  const projectChoices = useMemo(
    () =>
      countFilterChoices(
        (filterSource ?? []).flatMap((context) =>
          context.project ? [context.project] : [],
        ),
      ),
    [filterSource],
  );
  const tagChoices = useMemo(
    () => countFilterChoices((filterSource ?? []).flatMap((context) => context.tags)),
    [filterSource],
  );
  const hasActiveFilters =
    kind !== "ALL" ||
    project !== "" ||
    tag !== "" ||
    dateFrom !== "" ||
    dateTo !== "" ||
    includeArchived;
  const advancedFilterCount = [
    project !== "",
    tag !== "",
    dateFrom !== "" || dateTo !== "",
    includeArchived,
  ].filter(Boolean).length;
  const displayedCount = contextsQuery.data?.total ?? contextsQuery.data?.items.length ?? 0;

  function clearFilters() {
    setKind("ALL");
    setProject("");
    setTag("");
    setDateField("updated");
    setDateFrom("");
    setDateTo("");
    setIncludeArchived(false);
  }

  return (
    <div className="archive-document-page space-y-7 px-8 py-10 md:px-14 xl:px-16">
      <section className="border-b border-[#cfc8b8] pb-8">
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#161616]">Context Vault</p>
        <h1 className="mt-4 text-balance font-serif text-6xl tracking-[-0.04em] text-[#070707] md:text-7xl">Durable Agent Memory</h1>
        <p className="mt-5 max-w-3xl text-sm leading-7 text-[#36322d]">
          Browse handoffs, compact summaries, decisions, bug root causes, and restore prompts captured for Alexandria-Hermes agents.
        </p>
      </section>

      <Card className="p-4">
        <div className="space-y-4">
          <FilterChipGroup
            name="context-kind"
            label="Kind"
            value={kind}
            onChange={(value) => setKind(value as ContextKind | "ALL")}
            allLabel="All"
            choices={kindChoices}
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
              <div className="grid gap-4 lg:grid-cols-2">
                <FilterChipGroup
                  name="context-project"
                  label="Project"
                  value={project || "ALL"}
                  onChange={(value) => setProject(value === "ALL" ? "" : value)}
                  allLabel="All Projects"
                  choices={projectChoices}
                  emptyLabel="No project filters yet"
                />
                <FilterChipGroup
                  name="context-tag"
                  label="Tag"
                  value={tag || "ALL"}
                  onChange={(value) => setTag(value === "ALL" ? "" : value)}
                  allLabel="All Tags"
                  choices={tagChoices}
                  emptyLabel="No tag filters yet"
                />
              </div>
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_160px] xl:grid-cols-[minmax(0,1fr)_160px_160px_220px_auto] xl:items-end">
                <FilterChipGroup
                  name="context-date-field"
                  label="Date Field"
                  value={dateField}
                  onChange={(value) => setDateField(value as ContextDateField)}
                  allLabel={null}
                  choices={[
                    { value: "created", label: "Created Date" },
                    { value: "updated", label: "Updated Date" },
                  ]}
                />
                <label className="space-y-2 text-sm font-semibold text-[#28241f]">
                  From
                  <Input
                    name="date-from"
                    type="date"
                    value={dateFrom}
                    onChange={(event) => setDateFrom(event.target.value)}
                  />
                </label>
                <label className="space-y-2 text-sm font-semibold text-[#28241f]">
                  To
                  <Input
                    name="date-to"
                    type="date"
                    value={dateTo}
                    onChange={(event) => setDateTo(event.target.value)}
                  />
                </label>
                <label className="flex items-center gap-3 self-end rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-sm font-medium text-[#28241f]">
                  <input
                    name="include-archived"
                    type="checkbox"
                    checked={includeArchived}
                    onChange={(event) => setIncludeArchived(event.target.checked)}
                  />
                  Include Archived
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

      {contextsQuery.isLoading ? (
        <Card className="p-6 text-sm text-[#514c44]">Opening Context Vault…</Card>
      ) : contextsQuery.isError ? (
        <Card className="p-6 text-sm text-[#8f5037]">Context Vault could not be loaded. Check the backend connection and try again.</Card>
      ) : contextsQuery.data?.items.length ? (
        <section className="grid gap-5 xl:grid-cols-2">
          {contextsQuery.data.items.map((context) => (
            <ContextCard key={context.id} context={context} onArchive={(contextId) => archiveMutation.mutate(contextId)} />
          ))}
        </section>
      ) : (
        <Card className="p-8 text-center">
          <ScrollText className="mx-auto h-8 w-8 text-[#6f6a60]" aria-hidden="true" />
          <p className="mt-3 font-serif text-2xl text-[#111111]">No Context Entries Yet</p>
          <p className="mt-2 text-sm text-[#6f6a60]">Capture a handoff or prepare a compact summary to populate this vault.</p>
        </Card>
      )}
    </div>
  );
}
