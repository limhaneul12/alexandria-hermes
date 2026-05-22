"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { archiveHarness, fetchHarnesses, requestErrorMessage } from "@/lib/api";
import { t, type Language } from "@/lib/i18n";
import { formatDate } from "@/lib/utils";
import { useLibraryStore } from "@/store/library-store";
import type { HarnessContextDTO } from "@/types/library";

function preview(content: string): string {
  return content.replace(/[#>*_`-]/g, "").split("\n").filter(Boolean).slice(0, 2).join(" ");
}

function HarnessCard({ harness, language, onArchive }: { harness: HarnessContextDTO; language: Language; onArchive: (contextId: string) => void }) {
  const [confirmingArchive, setConfirmingArchive] = useState(false);
  const metadata = harness.harness;
  const counts = [
    [t(language, "harnessSteps"), metadata.steps.length],
    [t(language, "harnessCommands"), metadata.commands.length],
    [t(language, "harnessTests"), metadata.tests.length],
    [t(language, "harnessFixes"), metadata.fixes.length],
  ];

  function requestArchive() {
    if (!confirmingArchive) {
      setConfirmingArchive(true);
      return;
    }
    setConfirmingArchive(false);
    onArchive(harness.id);
  }

  return (
    <Card className="book-cover book-cover-list overflow-hidden p-5">
      <div className="book-corner book-corner-tl" aria-hidden="true" />
      <div className="relative z-10 space-y-4 pl-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <Badge>HARNESS</Badge>
            <Badge>{harness.status}</Badge>
            {harness.project ? <Badge>{harness.project}</Badge> : null}
          </div>
          <span className="text-xs uppercase tracking-[0.18em] text-[#6f6a60]">{formatDate(harness.updatedAt)}</span>
        </div>
        <div>
          <h3 className="font-serif text-3xl leading-tight">{metadata.taskGoal ?? harness.title}</h3>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-[#514c44]">{harness.summary || preview(harness.content)}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {counts.map(([label, count]) => (
            <div key={label} className="rounded-lg border border-[#d8d3c7] bg-white/50 px-3 py-2">
              <p className="text-[11px] uppercase tracking-[0.16em] text-[#6f6a60]">{label}</p>
              <p className="font-serif text-2xl text-[#111111]">{count}</p>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {metadata.recallKeywords.map((keyword) => <Badge key={keyword}>{keyword}</Badge>)}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm"><Link href={`/harnesses/${encodeURIComponent(harness.id)}`}>{t(language, "harnessOpenFieldManual")}</Link></Button>
          {!harness.isArchived ? <Button type="button" size="sm" variant="outline" onClick={requestArchive}><Archive className="h-4 w-4" aria-hidden="true" /> {confirmingArchive ? t(language, "confirmArchive") : t(language, "archive")}</Button> : null}
        </div>
      </div>
    </Card>
  );
}

export function HarnessGuidebookClient() {
  const queryClient = useQueryClient();
  const language = useLibraryStore((state) => state.language);
  const [project, setProject] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const params = useMemo(() => {
    const searchParams = new URLSearchParams({ limit: "60" });
    if (project.trim()) searchParams.set("project", project.trim());
    if (includeArchived) searchParams.set("include_archived", "true");
    return searchParams;
  }, [includeArchived, project]);
  const harnessesQuery = useQuery({ queryKey: ["harnesses", params.toString()], queryFn: () => fetchHarnesses(params) });
  const archiveMutation = useMutation({
    mutationFn: archiveHarness,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["harnesses"] }),
  });
  const items = harnessesQuery.data?.items ?? [];

  return (
    <div className="archive-document-page archive-document-grid gap-8 px-8 py-10 md:px-14 xl:px-16">
      <main className="space-y-7">
        <section className="border-b border-[#cfc8b8] pb-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#161616]">{t(language, "harnessGuidebook")}</p>
          <h1 className="mt-4 text-balance font-serif text-6xl tracking-[-0.04em] text-[#070707] md:text-7xl">{t(language, "harnessReusableFieldManuals")}</h1>
          <p className="mt-5 max-w-3xl text-sm leading-7 text-[#36322d]">{t(language, "harnessGuidebookDescription")}</p>
        </section>
        <Card className="archive-paper-card p-4">
          <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-center">
            <Input value={project} onChange={(event) => setProject(event.target.value)} placeholder={t(language, "harnessFilterProject")} />
            <Button type="button" variant="secondary" onClick={() => setIncludeArchived((value) => !value)}>{includeArchived ? t(language, "harnessHideArchived") : t(language, "harnessIncludeArchived")}</Button>
          </div>
        </Card>
        <div className="grid gap-4">
          {harnessesQuery.isLoading ? <p className="text-sm text-[#514c44]">{t(language, "harnessOpeningShelf")}</p> : null}
          {items.map((harness) => <HarnessCard key={harness.id} harness={harness} language={language} onArchive={(id) => archiveMutation.mutate(id)} />)}
          {!harnessesQuery.isLoading && items.length === 0 ? <Card className="archive-paper-card p-6 text-sm text-[#6f6a60]">{t(language, "harnessEmpty")}</Card> : null}
          {archiveMutation.isError ? <p className="text-sm text-[#8f5037]">{requestErrorMessage(archiveMutation.error, t(language, "harnessActionFailed"))}</p> : null}
        </div>
      </main>
      <aside className="archive-right-rail space-y-5 p-5">
        <Card className="archive-paper-card p-5"><p className="font-serif text-2xl text-[#111111]">{t(language, "harnessWhatIs")}</p><p className="mt-3 text-sm leading-6 text-[#514c44]">{t(language, "harnessWhatIsBody")}</p></Card>
      </aside>
    </div>
  );
}
