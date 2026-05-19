"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BookOpen, CheckCircle2, Clipboard, ExternalLink, History, ScrollText, ShieldCheck, Table2, Trash2, XCircle } from "lucide-react";

import { RecentActivityList } from "@/components/activity/recent-activity-list";
import { ContentViewer } from "@/components/content/content-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteLibraryItem, fetchLibraryItemDetail, recordLibraryUsage } from "@/lib/api";
import { t, tx, type Language } from "@/lib/i18n";
import { formatDate, formatRelative } from "@/lib/utils";
import { useLibraryStore } from "@/store/library-store";
import type { LibraryItemDetailDTO } from "@/types/library";

function EmptySection({ message }: { message: string }) {
  return <p className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4 text-sm text-[#514c44]">{message}</p>;
}

function renderPrompt(content: string, variables: Record<string, string>) {
  return content.replace(/\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g, (_match, name: string) => variables[name] ?? `{{${name}}}`);
}

function ArchiveControls({ data, language, onDelete, pending, failed }: { data: LibraryItemDetailDTO; language: Language; onDelete: () => void; pending: boolean; failed: boolean }) {
  const [confirming, setConfirming] = useState(false);

  function requestDelete() {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    onDelete();
  }

  return (
    <Card id="archive-controls" className="archive-paper-card scroll-mt-24 p-4">
      <p className="font-serif text-xl text-[#111111]">{t(language, "archiveControls")}</p>
      <dl className="mt-4 space-y-3 text-sm">
        <div className="flex justify-between gap-4"><dt className="text-[#6f6a60]">{t(language, "status")}</dt><dd className="text-[#111111]">ACTIVE/DRAFT</dd></div>
        <div className="flex justify-between gap-4"><dt className="text-[#6f6a60]">{t(language, "version")}</dt><dd className="text-[#111111]">{data.version}</dd></div>
        <div className="flex justify-between gap-4"><dt className="text-[#6f6a60]">{t(language, "updated")}</dt><dd className="text-[#111111]">{formatDate(data.updatedAt)}</dd></div>
      </dl>
      <div className="mt-5 rounded-xl border border-[#c88a72] bg-[#fff4ef] p-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8f5037]">{t(language, "removalPanel")}</p>
        <p className="mt-2 text-xs leading-5 text-[#6f6a60]">{t(language, "removalPanelDescription")}</p>
        {confirming ? (
          <div className="mt-3 rounded-lg border border-[#d9b4a3] bg-white/70 p-3">
            <p className="text-sm font-semibold text-[#111111]">{tx(language, "deleteItemConfirm", { title: data.title })}</p>
            <div className="mt-3 flex gap-2">
              <Button type="button" variant="secondary" onClick={() => setConfirming(false)} disabled={pending} className="flex-1">{t(language, "cancel")}</Button>
              <Button type="button" onClick={requestDelete} disabled={pending} className="flex-1 bg-[#8f5037] text-white hover:bg-[#7d412c]">
                <Trash2 className="h-4 w-4" /> {pending ? t(language, "deletingSkill") : t(language, "deleteProvider")}
              </Button>
            </div>
          </div>
        ) : (
          <Button type="button" variant="secondary" onClick={requestDelete} disabled={pending} className="mt-3 w-full border-[#c88a72] text-[#8f5037] hover:bg-[#ffe8dd]">
            <Trash2 className="h-4 w-4" /> {pending ? t(language, "deletingSkill") : tx(language, "deleteItemByType", { type: data.type })}
          </Button>
        )}
        {failed ? <p className="mt-2 text-xs text-[#8f5037]">{t(language, "skillDeleteFailed")}</p> : null}
      </div>
    </Card>
  );
}

function PromptBody({ data, language }: { data: LibraryItemDetailDTO; language: Language }) {
  const [variables, setVariables] = useState<Record<string, string>>({});
  const rendered = useMemo(() => renderPrompt(data.content, variables), [data.content, variables]);
  const prompt = data.prompt;
  return (
    <>
      <Card id="overview" className="scroll-mt-24">
        <CardHeader><CardTitle className="flex items-center gap-2"><ScrollText className="h-5 w-5" /> {t(language, "promptBody")}</CardTitle></CardHeader>
        <CardContent>
          <ContentViewer content={data.content} />
        </CardContent>
      </Card>
      <Card id="variables" className="scroll-mt-24">
        <CardHeader><CardTitle>{t(language, "fillVariables")}</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {prompt?.inputVariables.length ? prompt.inputVariables.map((variable) => (
            <label key={variable.name} className="block text-xs text-[#514c44]">
              {variable.name}{variable.required ? " *" : ""}
              <textarea value={variables[variable.name] ?? ""} onChange={(event) => setVariables((current) => ({ ...current, [variable.name]: event.target.value }))} rows={3} className="mt-1 w-full rounded-md border border-[#d8d3c7] bg-white/60 px-3 py-2 text-sm text-[#111111] outline-none focus:border-gold-300/60" />
            </label>
          )) : <EmptySection message={t(language, "noPromptVariables")} />}
          <pre className="max-h-80 overflow-auto rounded-xl border border-gold-300/15 bg-white/60 p-4 text-sm leading-7 text-[#36322d]"><code>{rendered}</code></pre>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void navigator.clipboard.writeText(data.content)}><Clipboard className="h-4 w-4" /> {t(language, "copyPrompt")}</Button>
            <Button type="button" variant="secondary" onClick={() => void navigator.clipboard.writeText(rendered)}><Clipboard className="h-4 w-4" /> {t(language, "copyRenderedPrompt")}</Button>
          </div>
        </CardContent>
      </Card>
    </>
  );
}

function SelfAcquisitionCard({
  language,
  metadata,
}: {
  language: Language;
  metadata: NonNullable<LibraryItemDetailDTO["skillAcquisition"]>;
}) {
  const harness = metadata.harness;
  const passed = harness?.status === "PASSED";
  const statusLabel = harness ? harness.status.replace("_", " ") : "UNVERIFIED";
  return (
    <Card id="self-acquisition" className="archive-paper-card scroll-mt-24">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5" /> {t(language, "selfAcquisitionEvidence")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{metadata.acquisitionMethod.replace("_", " ")}</Badge>
            <Badge className={passed ? "border-[#9fbd8f] bg-[#f1f7ed] text-[#355b2e]" : "border-[#d9b4a3] bg-[#fff4ef] text-[#8f5037]"}>
              {passed ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />} {statusLabel}
            </Badge>
          </div>
          {metadata.sourceSummary ? <p className="mt-3 text-sm leading-6 text-[#36322d]">{metadata.sourceSummary}</p> : null}
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#6f6a60]">{t(language, "evidenceUrls")}</p>
          {metadata.evidenceUrls.length ? (
            <ul className="mt-2 space-y-2">
              {metadata.evidenceUrls.map((url) => (
                <li key={url}>
                  <a href={url} target="_blank" rel="noreferrer" className="inline-flex max-w-full items-center gap-2 rounded-lg border border-[#d8d3c7] bg-white/70 px-3 py-2 text-sm text-[#111111] hover:bg-[#f6f3ec]">
                    <ExternalLink className="h-4 w-4 shrink-0" />
                    <span className="truncate">{url}</span>
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <EmptySection message={t(language, "noEvidenceUrls")} />
          )}
        </div>

        {harness ? (
          <div className="overflow-hidden rounded-xl border border-[#d8d3c7]">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#eee9df] text-[#6f6a60]">
                <tr><th className="p-3">{t(language, "check")}</th><th className="p-3">{t(language, "result")}</th><th className="p-3">{t(language, "message")}</th></tr>
              </thead>
              <tbody className="divide-y divide-[#d8d3c7] bg-white/50">
                {harness.checks.map((check) => (
                  <tr key={check.name}>
                    <td className="p-3 font-medium text-[#111111]">{check.name.replaceAll("_", " ")}</td>
                    <td className="p-3 text-[#514c44]">{check.passed ? t(language, "pass") : t(language, "review")}</td>
                    <td className="p-3 text-[#514c44]">{check.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function SkillDetailClient({ skillId }: { skillId: string }) {
  const language = useLibraryStore((state) => state.language);
  const router = useRouter();
  const queryClient = useQueryClient();
  const viewRecordedRef = useRef(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["library-item", skillId],
    queryFn: () => fetchLibraryItemDetail(skillId),
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteLibraryItem(skillId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["library"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.removeQueries({ queryKey: ["library-item", skillId] });
      router.push("/library", { scroll: false });
    },
  });

  useEffect(() => {
    if (!data || viewRecordedRef.current) return;
    viewRecordedRef.current = true;
    void recordLibraryUsage({
      itemId: data.id,
      itemType: data.type,
      agentName: "Alexandria UI",
      selectionSource: "UI_VIEW",
      success: true,
      query: null,
      librarianProvider: null,
      feedback: { source_surface: "library-detail" },
    })
      .then(() => queryClient.invalidateQueries({ queryKey: ["library-item", skillId] }))
      .catch(() => undefined);
  }, [data, queryClient, skillId]);

  if (isLoading) return <div className="rounded-2xl border border-[#d8d3c7] p-10 text-[#514c44]">{t(language, "preparingSkillDetail")}</div>;
  if (isError || !data) return <div className="rounded-2xl border border-[#d8d3c7] p-10 text-[#514c44]">{t(language, "skillNotFound")}</div>;

  const item = data;
  const isPrompt = item.type === "PROMPT";

  function handleDelete() {
    if (deleteMutation.isPending) return;
    deleteMutation.mutate();
  }

  return (
    <div className="archive-document-page grid gap-8 px-8 py-10 md:px-14 xl:grid-cols-[250px_minmax(0,1fr)] xl:px-16">
      <aside className="hidden xl:block">
        <Card className="archive-paper-card sticky top-24 p-4">
          <p className="mb-4 font-serif text-lg text-[#111111]">{t(language, "library")}</p>
          <Link href={`/library/${item.category.slug}`} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[#36322d] hover:bg-[#e9e4da]"><ArrowLeft className="h-4 w-4" /> {item.category.name}</Link>
          <div className="mt-4 space-y-2 border-t border-[#d8d3c7] pt-4 text-sm text-[#6f6a60]"><p>{t(language, "category")}</p><p className="pl-3 text-[#111111]">{item.category.name}</p></div>
        </Card>
      </aside>

      <article className="space-y-5">
        <p className="text-xs font-bold uppercase tracking-[0.32em] text-[#111111]">{isPrompt ? t(language, "promptReadingRoom") : t(language, "skillDetailKicker")}</p>
        <Card className="archive-paper-card overflow-hidden p-6">
          <div className="grid gap-7 lg:grid-cols-[190px_minmax(0,1fr)]">
            <div className={`book-cover ${isPrompt ? "prompt-card" : ""} flex min-h-64 items-center justify-center rounded-xl border border-gold-300/20 p-5 text-center font-serif text-xl leading-tight text-[#111111]`}>{item.title}</div>
            <div>
              <div className="flex flex-wrap gap-2"><Badge>{item.type}</Badge>{isPrompt && item.prompt ? <><Badge>{item.prompt.promptKind}</Badge><Badge>{item.prompt.contentFormat}</Badge></> : null}{item.tags.map((tag) => <Badge key={tag} className="border-[#cfc8b8] bg-[#f6f3ec] text-[#36322d]">{tag}</Badge>)}</div>
              <h1 className="mt-4 text-balance font-serif text-5xl leading-tight tracking-[-0.03em] text-[#070707] md:text-6xl">{item.title}</h1>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-[#36322d]">{item.description}</p>
              <div className="mt-5 flex flex-wrap gap-2">
                {isPrompt ? <><Button type="button" onClick={() => void navigator.clipboard.writeText(item.content)}><Clipboard className="h-4 w-4" /> {t(language, "copyPrompt")}</Button><Button asChild variant="secondary"><a href="#variables">{t(language, "fillVariables")}</a></Button></> : <Button asChild><a href="#usage-guide"><BookOpen className="h-4 w-4" /> {t(language, "openUsageGuide")}</a></Button>}
              </div>
            </div>
          </div>
        </Card>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_280px]">
          <div className="space-y-5">
            <Card className="archive-paper-card overflow-hidden">
              <CardHeader><CardTitle>{t(language, "basicInfo")}</CardTitle></CardHeader>
              <CardContent className="p-0"><table className="w-full text-left text-sm"><tbody className="divide-y divide-[#d8d3c7]">
                {[
                  ["ID", item.id], [t(language, "type"), item.type], [t(language, "category"), item.category.name],
                  [t(language, "createdBy"), item.author], [t(language, "createdAt"), formatDate(item.updatedAt)],
                  [t(language, "lastAccessed"), formatRelative(item.lastAccessedAt)], [t(language, "version"), item.version],
                  [t(language, "tags"), item.tags.join(", ") || "-"],
                  ...(isPrompt && item.prompt ? [[t(language, "promptDomain"), item.prompt.promptDomain], [t(language, "promptTask"), item.prompt.promptTaskType], [t(language, "variables"), String(item.prompt.inputVariables.length)]] : []),
                ].map(([label, value]) => <tr key={label}><th className="w-40 bg-[#eee9df] px-4 py-3 align-top font-medium text-[#6f6a60]">{label}</th><td className="break-words px-4 py-3 text-[#111111]">{value}</td></tr>)}
              </tbody></table></CardContent>
            </Card>

            {isPrompt ? <PromptBody data={data} language={language} /> : (
              <>
                {item.skillAcquisition ? <SelfAcquisitionCard language={language} metadata={item.skillAcquisition} /> : null}
                <Card id="usage-guide" className="scroll-mt-24"><CardHeader><CardTitle className="flex items-center gap-2"><Table2 className="h-5 w-5" /> {t(language, "usageGuide")}</CardTitle></CardHeader><CardContent>{item.content.trim() ? <ContentViewer content={item.content} /> : <EmptySection message={t(language, "usageGuideEmpty")} />}</CardContent></Card>
              </>
            )}

            <Card id="history" className="scroll-mt-24"><CardHeader><CardTitle className="flex items-center gap-2"><History className="h-5 w-5" /> {t(language, "recentUsageHistory")}</CardTitle></CardHeader><CardContent><RecentActivityList emptyLabel={t(language, "usageHistoryEmpty")} items={item.usageHistory.slice(0, 5).map((usage) => ({ id: usage.id, occurredAt: usage.accessedAt, actorName: usage.agentName, method: usage.accessMethod, sourceSurface: null }))} /></CardContent></Card>
          </div>

          <aside className="space-y-5">
            <Card className="p-4"><p className="mb-3 font-serif text-xl text-[#111111]">{t(language, "tableOfContents")}</p><nav className="space-y-1">{item.tableOfContents.map((item, index) => <a key={item.id} href={`#${item.id}`} className="flex gap-3 rounded-lg px-3 py-2 text-sm text-[#514c44] hover:bg-white/[0.05] hover:text-[#111111]"><span className="text-[#958c7e]">{index + 1}.</span> {item.label}</a>)}</nav></Card>
            <ArchiveControls data={data} language={language} onDelete={handleDelete} pending={deleteMutation.isPending} failed={deleteMutation.isError} />
          </aside>
        </div>
      </article>
    </div>
  );
}
