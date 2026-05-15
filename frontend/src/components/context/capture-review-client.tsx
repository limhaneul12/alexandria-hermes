"use client";

import { type FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { captureContext, lintContext } from "@/lib/api";
import { CONTEXT_KINDS, type ContextKind, type ContextSaveDTO } from "@/types/library";

const selectClassName =
  "h-10 rounded-md border border-[#cfc8b8] bg-white/80 px-3 py-2 text-sm font-medium text-[#111111] outline-none focus-visible:border-[#111111] focus-visible:ring-2 focus-visible:ring-[#111111]/10";

function contextPayload(kind: ContextKind, title: string, content: string, summary: string, project: string): ContextSaveDTO {
  return {
    kind,
    title,
    content,
    summary: summary.trim() || null,
    project: project.trim() || null,
    sourceAgent: "Hermes UI",
    sourceType: "AGENT",
    importance: "MEDIUM",
    tags: ["capture-review"],
    metadata: {},
  };
}

export function CaptureReviewClient() {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<ContextKind>("HANDOFF");
  const [title, setTitle] = useState("Sprint handoff");
  const [summary, setSummary] = useState("");
  const [project, setProject] = useState("alexandria-hermes");
  const [content, setContent] = useState("# Sprint handoff\n\n## Summary\n\n## Current State\n\n## Next Actions\n\n## Restore Prompt\n");

  const lintMutation = useMutation({ mutationFn: lintContext });
  const captureMutation = useMutation({
    mutationFn: captureContext,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["contexts"] });
    },
  });

  function handleLint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    lintMutation.mutate(contextPayload(kind, title, content, summary, project));
  }

  function handleCapture() {
    captureMutation.mutate(contextPayload(kind, title, content, summary, project));
  }

  return (
    <div className="archive-document-page space-y-7 px-8 py-10 md:px-14 xl:px-16">
      <section className="border-b border-[#cfc8b8] pb-8">
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#161616]">Capture Review</p>
        <h1 className="mt-4 text-balance font-serif text-6xl tracking-[-0.04em] text-[#070707] md:text-7xl">Lint Before Memory</h1>
        <p className="mt-5 max-w-3xl text-sm leading-7 text-[#36322d]">Review warnings, redaction output, and required headings before a context enters durable recall.</p>
      </section>

      <form onSubmit={handleLint} className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <CardHeader><CardTitle>Context Draft</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-2 text-sm font-semibold text-[#28241f]">Title<Input name="context-title" autoComplete="off" value={title} onChange={(event) => setTitle(event.target.value)} /></label>
              <label className="space-y-2 text-sm font-semibold text-[#28241f]">Kind<select name="context-kind" value={kind} onChange={(event) => setKind(event.target.value as ContextKind)} className={selectClassName}>{CONTEXT_KINDS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
              <label className="space-y-2 text-sm font-semibold text-[#28241f]">Summary<Input name="context-summary" autoComplete="off" value={summary} onChange={(event) => setSummary(event.target.value)} /></label>
              <label className="space-y-2 text-sm font-semibold text-[#28241f]">Project<Input name="context-project" autoComplete="off" value={project} onChange={(event) => setProject(event.target.value)} /></label>
            </div>
            <label className="space-y-2 text-sm font-semibold text-[#28241f]">Content<textarea name="context-content" value={content} onChange={(event) => setContent(event.target.value)} rows={16} className="w-full rounded-xl border border-[#cfc8b8] bg-white/80 p-4 text-sm leading-6 text-[#111111] outline-none focus-visible:border-[#111111] focus-visible:ring-2 focus-visible:ring-[#111111]/10" /></label>
            <div className="flex flex-wrap gap-2"><Button type="submit" disabled={lintMutation.isPending}><ClipboardCheck className="h-4 w-4" aria-hidden="true" /> {lintMutation.isPending ? "Checking…" : "Run Review"}</Button><Button type="button" variant="secondary" disabled={!lintMutation.data?.ok || captureMutation.isPending} onClick={handleCapture}><Save className="h-4 w-4" aria-hidden="true" /> {captureMutation.isPending ? "Saving…" : "Save Context"}</Button></div>
          </CardContent>
        </Card>
        <Card className="h-fit">
          <CardHeader><CardTitle>Review Result</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {lintMutation.data ? (
              <>
                <div className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4"><p className="font-serif text-2xl text-[#111111]">{lintMutation.data.status}</p><p className="mt-1 text-sm tabular-nums text-[#514c44]">Score {lintMutation.data.score} · {lintMutation.data.ok ? "Ready to Save" : "Needs Edits"}</p></div>
                {lintMutation.data.errors.length ? <div><p className="font-semibold text-[#8f5037]">Errors</p><ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-[#8f5037]">{lintMutation.data.errors.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
                {lintMutation.data.warnings.length ? <div><p className="font-semibold text-[#8f5037]">Warnings</p><ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-[#8f5037]">{lintMutation.data.warnings.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
                <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-xs leading-5 text-[#36322d]">{lintMutation.data.redactedContent}</pre>
              </>
            ) : <p className="text-sm text-[#6f6a60]">Run review to see warnings and redaction output.</p>}
            {captureMutation.data ? <p className="rounded-xl border border-[#d8d3c7] bg-[#f6f3ec] p-3 text-sm text-[#111111]">Saved Context {captureMutation.data.id}</p> : null}
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
