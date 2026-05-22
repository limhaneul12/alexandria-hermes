"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArrowLeft, Clipboard, ScrollText } from "lucide-react";

import { ContentViewer } from "@/components/content/content-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { archiveHarness, fetchHarness, recordContextAccessEvent, requestErrorMessage } from "@/lib/api";
import { t, type Language } from "@/lib/i18n";
import { formatDate } from "@/lib/utils";
import { useLibraryStore } from "@/store/library-store";

type PanelProps = { title: string; items: string[]; language: Language };

function ListPanel({ title, items, language }: PanelProps) {
  return (
    <Card className="archive-paper-card p-4">
      <p className="font-serif text-xl text-[#111111]">{title}</p>
      {items.length ? <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-[#36322d]">{items.map((item) => <li key={item}>{item}</li>)}</ol> : <p className="mt-3 text-sm text-[#6f6a60]">{t(language, "harnessNoEntries")}</p>}
    </Card>
  );
}

export function HarnessDetailClient({ contextId }: { contextId: string }) {
  const queryClient = useQueryClient();
  const language = useLibraryStore((state) => state.language);
  const harnessQuery = useQuery({ queryKey: ["harness", contextId], queryFn: () => fetchHarness(contextId) });
  const archiveMutation = useMutation({
    mutationFn: archiveHarness,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["harness", contextId] });
      void queryClient.invalidateQueries({ queryKey: ["harnesses"] });
    },
  });

  useEffect(() => {
    void recordContextAccessEvent(contextId, {
      actorName: "Alexandria UI",
      actorType: "UI",
      accessMethod: "DETAIL_VIEW",
      sourceSurface: "harness-detail",
    }).catch(() => undefined);
  }, [contextId]);

  if (harnessQuery.isLoading) return <div className="archive-document-page p-10 text-sm text-[#514c44]">{t(language, "harnessOpening")}</div>;
  if (harnessQuery.isError || !harnessQuery.data) return <div className="archive-document-page p-10 text-sm text-[#8f5037]">{requestErrorMessage(harnessQuery.error, t(language, "harnessNotFound"))}</div>;

  const harness = harnessQuery.data;
  const meta = harness.harness;
  return (
    <div className="archive-document-page grid gap-8 px-8 py-10 md:px-14 xl:grid-cols-[250px_minmax(0,1fr)] xl:px-16">
      <aside className="hidden xl:block">
        <Card className="sticky top-24 p-4">
          <Link href="/harnesses" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[#36322d] hover:bg-[#e9e4da]"><ArrowLeft className="h-4 w-4" aria-hidden="true" /> {t(language, "harnessGuidebook")}</Link>
          <div className="mt-4 space-y-2 border-t border-[#d8d3c7] pt-4 text-sm text-[#6f6a60]"><p>{harness.project ?? t(language, "noProject")}</p><p>{formatDate(harness.updatedAt)}</p><p>{harness.sourceAgent}</p></div>
        </Card>
      </aside>
      <article className="space-y-5">
        <p className="text-xs font-bold uppercase tracking-[0.32em] text-[#111111]">{t(language, "harnessFieldManual")}</p>
        <Card className="book-cover p-6">
          <div className="book-corner book-corner-tl" aria-hidden="true" />
          <div className="relative z-10 pl-5">
            <div className="flex flex-wrap gap-2"><Badge>HARNESS</Badge><Badge>{harness.status}</Badge><Badge>{harness.importance}</Badge>{meta.recallKeywords.map((keyword) => <Badge key={keyword}>{keyword}</Badge>)}</div>
            <h1 className="mt-4 text-balance font-serif text-5xl leading-tight tracking-[-0.03em] md:text-6xl">{meta.taskGoal ?? harness.title}</h1>
            <p className="mt-4 max-w-3xl text-sm leading-7">{harness.summary}</p>
            <div className="mt-5 flex flex-wrap gap-2"><Button type="button" onClick={() => void navigator.clipboard.writeText(harness.content)}><Clipboard className="h-4 w-4" aria-hidden="true" /> {t(language, "harnessCopyManual")}</Button>{!harness.isArchived ? <Button type="button" variant="outline" onClick={() => archiveMutation.mutate(harness.id)}><Archive className="h-4 w-4" aria-hidden="true" /> {t(language, "archive")}</Button> : null}</div>
            {archiveMutation.isError ? <p className="mt-3 text-sm text-[#8f5037]">{requestErrorMessage(archiveMutation.error, t(language, "harnessActionFailed"))}</p> : null}
          </div>
        </Card>
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-5">
            <Card><CardHeader><CardTitle className="flex items-center gap-2"><ScrollText className="h-5 w-5" aria-hidden="true" /> {t(language, "harnessReusableProcedure")}</CardTitle></CardHeader><CardContent><ContentViewer content={meta.reusableProcedure ?? harness.content} /></CardContent></Card>
            <div className="grid gap-4 md:grid-cols-2"><ListPanel title={t(language, "harnessSteps")} items={meta.steps} language={language} /><ListPanel title={t(language, "harnessCommands")} items={meta.commands} language={language} /><ListPanel title={t(language, "harnessTests")} items={meta.tests} language={language} /><ListPanel title={t(language, "harnessArtifacts")} items={meta.artifacts} language={language} /></div>
            <div className="grid gap-4 md:grid-cols-2"><ListPanel title={t(language, "harnessFailures")} items={meta.failures} language={language} /><ListPanel title={t(language, "harnessFixes")} items={meta.fixes} language={language} /></div>
          </div>
          <aside className="space-y-5"><Card className="archive-paper-card p-4"><p className="font-serif text-xl">{t(language, "harnessRecallSignals")}</p><div className="mt-3 flex flex-wrap gap-2">{meta.recallKeywords.map((keyword) => <Badge key={keyword}>{keyword}</Badge>)}</div></Card><ListPanel title={t(language, "harnessSafetyNotes")} items={meta.safetyNotes} language={language} /><Card className="archive-paper-card p-4"><p className="font-serif text-xl">{t(language, "harnessTriggerEnvironment")}</p><p className="mt-3 text-sm leading-6 text-[#36322d]">{meta.triggerContext ?? t(language, "harnessNoTrigger")}</p><p className="mt-3 text-sm leading-6 text-[#6f6a60]">{meta.environment ?? t(language, "harnessNoEnvironment")}</p></Card></aside>
        </div>
      </article>
    </div>
  );
}
