"use client";

import { type FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Clipboard, Search, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { fetchRagStatus, searchContexts } from "@/lib/api";
import { RAG_STRATEGIES, type RagStrategy } from "@/types/library";

const selectClassName =
  "h-10 rounded-md border border-[#cfc8b8] bg-white/80 px-3 py-2 text-sm font-medium text-[#111111] outline-none focus-visible:border-[#111111] focus-visible:ring-2 focus-visible:ring-[#111111]/10";

export function RagInspectorClient() {
  const [query, setQuery] = useState("context handoff");
  const [strategy, setStrategy] = useState<RagStrategy>("HYBRID");
  const statusQuery = useQuery({ queryKey: ["rag-status"], queryFn: fetchRagStatus });
  const searchMutation = useMutation({ mutationFn: searchContexts });
  const vectorReady = statusQuery.data?.vector === "HEALTHY" && statusQuery.data?.embedding === "HEALTHY";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    searchMutation.mutate({ query: trimmed, strategy, limit: 6, project: null, kind: null });
  }

  return (
    <div className="archive-document-page space-y-7 px-8 py-10 md:px-14 xl:px-16">
      <section className="border-b border-[#cfc8b8] pb-8">
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#161616]">RAG Inspector</p>
        <h1 className="mt-4 text-balance font-serif text-6xl tracking-[-0.04em] text-[#070707] md:text-7xl">Context Pack Workbench</h1>
        <p className="mt-5 max-w-3xl text-sm leading-7 text-[#36322d]">Inspect retrieved chunks, scores, reasons, and the final Context Pack before an agent uses it.</p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {["fts", "vector", "embedding"].map((key) => (
          <Card key={key} className="p-5">
            <div className="flex items-center justify-between gap-3"><p className="font-serif text-xl capitalize text-[#111111]">{key}</p><ShieldCheck className="h-5 w-5 text-[#6f6a60]" aria-hidden="true" /></div>
            <p className="mt-3 text-sm text-[#514c44]">{statusQuery.data ? String(statusQuery.data[key as "fts" | "vector" | "embedding"]) : "Checking…"}</p>
          </Card>
        ))}
      </section>

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Search className="h-5 w-5" aria-hidden="true" /> Query</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_auto]">
            <Input name="rag-query" autoComplete="off" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. context handoff…" />
            <select name="rag-strategy" value={strategy} onChange={(event) => setStrategy(event.target.value as RagStrategy)} className={selectClassName}>{RAG_STRATEGIES.map((item) => <option key={item} value={item} disabled={item === "VECTOR_ONLY" && !vectorReady}>{item === "VECTOR_ONLY" && !vectorReady ? "VECTOR_ONLY (degraded)" : item}</option>)}</select>
            <Button type="submit" disabled={searchMutation.isPending}>{searchMutation.isPending ? "Searching…" : "Inspect"}</Button>
          </form>
        </CardContent>
      </Card>

      {searchMutation.data ? (
        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-4">
            {searchMutation.data.matches.map((match) => (
              <Card key={match.chunk.id}>
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>{match.context.title}</CardTitle><Badge>{match.context.kind}</Badge></div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs tabular-nums uppercase tracking-[0.18em] text-[#6f6a60]">Final {match.score.toFixed(4)} · FTS {match.ftsScore?.toFixed(4) ?? "-"} · Vector {match.vectorScore?.toFixed(4) ?? "-"}</p>
                  <p className="rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-sm text-[#514c44]">{match.whyRetrieved}</p>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-[#36322d]">{match.chunk.content}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          <Card className="h-fit p-4">
            <div className="flex items-center justify-between gap-3"><p className="font-serif text-xl text-[#111111]">Context Pack</p><Button type="button" size="sm" variant="secondary" onClick={() => void navigator.clipboard.writeText(searchMutation.data?.contextPack ?? "")}><Clipboard className="h-4 w-4" aria-hidden="true" /> Copy</Button></div>
            <p className="mt-3 text-xs text-[#6f6a60]">Requested strategy: {searchMutation.data.strategy} · Effective strategy: {searchMutation.data.effectiveStrategy}</p>
            {searchMutation.data.warnings.length ? <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-[#8f5037]">{searchMutation.data.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
            <pre className="mt-4 max-h-[620px] overflow-auto whitespace-pre-wrap rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-xs leading-5 text-[#36322d]">{searchMutation.data.contextPack}</pre>
          </Card>
        </section>
      ) : null}
    </div>
  );
}
