"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArrowLeft, Clipboard, ScrollText } from "lucide-react";

import { RecentActivityList } from "@/components/activity/recent-activity-list";
import { ContentViewer } from "@/components/content/content-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { archiveContext, fetchContext, fetchContextAccessEvents, fetchContextChunks, recordContextAccessEvent } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export function ContextDetailClient({ contextId }: { contextId: string }) {
  const queryClient = useQueryClient();
  const [confirmingArchive, setConfirmingArchive] = useState(false);
  const contextQuery = useQuery({ queryKey: ["context", contextId], queryFn: () => fetchContext(contextId) });
  const chunksQuery = useQuery({ queryKey: ["context-chunks", contextId], queryFn: () => fetchContextChunks(contextId) });
  const accessEventsQuery = useQuery({ queryKey: ["context-access-events", contextId], queryFn: () => fetchContextAccessEvents(contextId, 5) });
  const archiveMutation = useMutation({
    mutationFn: archiveContext,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["context", contextId] });
      void queryClient.invalidateQueries({ queryKey: ["contexts"] });
    },
  });

  useEffect(() => {
    void recordContextAccessEvent(contextId, {
      actorName: "Alexandria UI",
      actorType: "UI",
      accessMethod: "DETAIL_VIEW",
      sourceSurface: "context-detail",
    })
      .then(() => {
        void queryClient.invalidateQueries({ queryKey: ["context", contextId] });
        void queryClient.invalidateQueries({ queryKey: ["context-access-events", contextId] });
      })
      .catch(() => undefined);
  }, [contextId, queryClient]);

  if (contextQuery.isLoading) return <div className="archive-document-page p-10 text-sm text-[#514c44]">Opening context…</div>;
  if (contextQuery.isError || !contextQuery.data) return <div className="archive-document-page p-10 text-sm text-[#8f5037]">Context not found. Return to Context Vault and choose another entry.</div>;

  const context = contextQuery.data;
  function requestArchive() {
    if (!confirmingArchive) {
      setConfirmingArchive(true);
      return;
    }
    setConfirmingArchive(false);
    archiveMutation.mutate(context.id);
  }

  return (
    <div className="archive-document-page grid gap-8 px-8 py-10 md:px-14 xl:grid-cols-[250px_minmax(0,1fr)] xl:px-16">
      <aside className="hidden xl:block">
        <Card className="sticky top-24 p-4">
          <Link href="/contexts" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[#36322d] hover:bg-[#e9e4da]"><ArrowLeft className="h-4 w-4" aria-hidden="true" /> Context Vault</Link>
          <div className="mt-4 space-y-2 border-t border-[#d8d3c7] pt-4 text-sm text-[#6f6a60]">
            <p>{context.kind}</p>
            <p>{context.project ?? "No project"}</p>
            <p>{formatDate(context.updatedAt)}</p>
          </div>
        </Card>
      </aside>
      <article className="space-y-5">
        <p className="text-xs font-bold uppercase tracking-[0.32em] text-[#111111]">Context Reading Room</p>
        <Card className="archive-paper-card p-6">
          <div className="flex flex-wrap gap-2">
            <Badge>{context.kind}</Badge><Badge>{context.status}</Badge><Badge>{context.importance}</Badge>
            {context.tags.map((tag) => <Badge key={tag}>{tag}</Badge>)}
          </div>
          <h1 className="mt-4 text-balance font-serif text-5xl leading-tight tracking-[-0.03em] text-[#070707] md:text-6xl">{context.title}</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[#36322d]">{context.summary}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button type="button" onClick={() => void navigator.clipboard.writeText(context.content)}><Clipboard className="h-4 w-4" aria-hidden="true" /> Copy Content</Button>
            {context.restorePrompt ? <Button type="button" variant="secondary" onClick={() => void navigator.clipboard.writeText(context.restorePrompt ?? "")}><Clipboard className="h-4 w-4" aria-hidden="true" /> Copy Restore Prompt</Button> : null}
            {!context.isArchived ? <Button type="button" variant="outline" onClick={requestArchive} disabled={archiveMutation.isPending}><Archive className="h-4 w-4" aria-hidden="true" /> {confirmingArchive ? "Confirm Archive" : "Archive"}</Button> : null}
          </div>
          {confirmingArchive ? (
            <div className="archive-inline-confirm mt-4" role="status" aria-live="polite">
              <p className="text-sm text-[#8f5037]">Archive this context? It remains available when archived entries are included.</p>
              <Button type="button" variant="secondary" onClick={() => setConfirmingArchive(false)} disabled={archiveMutation.isPending}>Cancel</Button>
            </div>
          ) : null}
        </Card>
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
          <div className="space-y-5">
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><ScrollText className="h-5 w-5" aria-hidden="true" /> Markdown Preview</CardTitle></CardHeader>
              <CardContent><ContentViewer content={context.content} /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Retrieved Chunks</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {chunksQuery.data?.map((chunk) => (
                  <div key={chunk.id} className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4">
                    <p className="text-xs tabular-nums uppercase tracking-[0.18em] text-[#6f6a60]">#{chunk.chunkIndex} · {chunk.heading ?? "Untitled"} · {chunk.tokenCount} tokens</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#36322d]">{chunk.content}</p>
                  </div>
                )) ?? <p className="text-sm text-[#6f6a60]">Loading chunks…</p>}
              </CardContent>
            </Card>
          </div>
          <aside className="space-y-5">
            <Card className="p-4"><p className="font-serif text-xl text-[#111111]">Recall Stats</p><dl className="mt-4 space-y-3 text-sm"><div className="flex justify-between"><dt>Quality</dt><dd className="tabular-nums">{context.qualityScore}</dd></div><div className="flex justify-between"><dt>Accesses</dt><dd className="tabular-nums">{context.accessCount}</dd></div><div className="flex justify-between"><dt>Source</dt><dd>{context.sourceAgent}</dd></div></dl></Card>
            <Card className="p-4"><p className="font-serif text-xl text-[#111111]">최근 조회/사용</p><div className="mt-4"><RecentActivityList items={(accessEventsQuery.data ?? []).slice(0, 5).map((event) => ({ id: event.id, occurredAt: event.accessedAt, actorName: event.actorName, method: event.accessMethod, sourceSurface: event.sourceSurface }))} /></div></Card>
            <Card className="p-4"><p className="font-serif text-xl text-[#111111]">Warnings</p>{context.warnings.length ? <ul className="mt-3 list-disc space-y-1 pl-4 text-sm text-[#8f5037]">{context.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : <p className="mt-3 text-sm text-[#6f6a60]">No warnings recorded.</p>}</Card>
          </aside>
        </div>
      </article>
    </div>
  );
}
