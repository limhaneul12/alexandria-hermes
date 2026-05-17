"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Clipboard, ScrollText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchMemoryCompact } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export function MemoryCompactDetailClient({ compactId }: { compactId: string }) {
  const compactQuery = useQuery({
    queryKey: ["memory-compact", compactId],
    queryFn: () => fetchMemoryCompact(compactId),
  });

  if (compactQuery.isLoading) {
    return (
      <div className="archive-document-page p-10 text-sm text-[#514c44]">
        Opening Memory Compact…
      </div>
    );
  }

  if (compactQuery.isError || !compactQuery.data) {
    return (
      <div className="archive-document-page p-10 text-sm text-[#8f5037]">
        Memory Compact not found. Return to the compact shelf and choose another entry.
      </div>
    );
  }

  const compact = compactQuery.data;

  return (
    <div className="archive-document-page grid gap-8 px-8 py-10 md:px-14 xl:grid-cols-[250px_minmax(0,1fr)] xl:px-16">
      <aside className="hidden xl:block">
        <Card className="sticky top-24 p-4">
          <Link
            href="/memory-compacts"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[#36322d] hover:bg-[#e9e4da]"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Memory Compacts
          </Link>
          <div className="mt-4 space-y-2 border-t border-[#d8d3c7] pt-4 text-sm text-[#6f6a60]">
            <p>{compact.status}</p>
            <p>{compact.project ?? "Default project"}</p>
            <p>{formatDate(compact.updatedAt)}</p>
          </div>
        </Card>
      </aside>
      <article className="space-y-5">
        <p className="text-xs font-bold uppercase tracking-[0.32em] text-[#111111]">
          Memory Compact Reading Room
        </p>
        <Card className="archive-paper-card p-6">
          <div className="flex flex-wrap gap-2">
            <Badge>{compact.status}</Badge>
            {compact.project ? <Badge>{compact.project}</Badge> : <Badge>Default Project</Badge>}
            <Badge>{compact.sourceRefs.length} source refs</Badge>
          </div>
          <h1 className="mt-4 text-balance font-serif text-5xl leading-tight tracking-[-0.03em] text-[#070707] md:text-6xl">
            Memory Compact
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[#36322d]">
            Covers {formatDate(compact.coveredFrom)} through {formatDate(compact.coveredTo)}.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={() => void navigator.clipboard.writeText(compact.markdownBody)}
            >
              <Clipboard className="h-4 w-4" aria-hidden="true" /> Copy Markdown
            </Button>
          </div>
        </Card>
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ScrollText className="h-5 w-5" aria-hidden="true" /> Markdown Body
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="max-h-[720px] overflow-auto rounded-xl border border-[#d8d3c7] bg-white/60 p-4 text-sm leading-7 text-[#36322d] whitespace-pre-wrap">
                {compact.markdownBody}
              </pre>
            </CardContent>
          </Card>
          <aside className="space-y-5">
            <Card className="p-4">
              <p className="font-serif text-xl text-[#111111]">Source References</p>
              {compact.sourceRefs.length ? (
                <ul className="mt-4 space-y-3 text-sm text-[#36322d]">
                  {compact.sourceRefs.map((ref) => (
                    <li key={ref.id} className="rounded-xl border border-[#d8d3c7] bg-white/60 p-3">
                      <p className="font-semibold text-[#111111]">{ref.title}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-[#6f6a60]">
                        {ref.sourceType} · {ref.sourceId}
                      </p>
                      <p className="mt-1 break-all text-xs text-[#6f6a60]">{ref.detailPath}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-[#6f6a60]">No source references recorded.</p>
              )}
            </Card>
          </aside>
        </div>
      </article>
    </div>
  );
}
