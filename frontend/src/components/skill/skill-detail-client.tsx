"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BookOpen, Clipboard, History, ScrollText, Table2, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteLibraryItem, fetchLibraryItemDetail } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatDate, formatRelative } from "@/lib/utils";
import { useLibraryStore } from "@/store/library-store";
import type { LibraryItemDetailDTO } from "@/types/library";

function EmptySection({ message }: { message: string }) {
  return <p className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4 text-sm text-[#514c44]">{message}</p>;
}

function renderPrompt(content: string, variables: Record<string, string>) {
  return content.replace(/\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g, (_match, name: string) => variables[name] ?? `{{${name}}}`);
}

function ArchiveControls({ data, onDelete, pending, failed }: { data: LibraryItemDetailDTO; onDelete: () => void; pending: boolean; failed: boolean }) {
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
      <p className="font-serif text-xl text-[#111111]">Archive Controls</p>
      <dl className="mt-4 space-y-3 text-sm">
        <div className="flex justify-between gap-4"><dt className="text-[#6f6a60]">Status</dt><dd className="text-[#111111]">ACTIVE/DRAFT</dd></div>
        <div className="flex justify-between gap-4"><dt className="text-[#6f6a60]">Version</dt><dd className="text-[#111111]">{data.version}</dd></div>
        <div className="flex justify-between gap-4"><dt className="text-[#6f6a60]">Updated</dt><dd className="text-[#111111]">{formatDate(data.updatedAt)}</dd></div>
      </dl>
      <div className="mt-5 rounded-xl border border-[#c88a72] bg-[#fff4ef] p-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8f5037]">Removal panel</p>
        <p className="mt-2 text-xs leading-5 text-[#6f6a60]">삭제 확인은 브라우저 팝업 없이 이 카드 안에서 처리합니다.</p>
        {confirming ? (
          <div className="mt-3 rounded-lg border border-[#d9b4a3] bg-white/70 p-3">
            <p className="text-sm font-semibold text-[#111111]">{data.title} 자료를 삭제할까요?</p>
            <div className="mt-3 flex gap-2">
              <Button type="button" variant="secondary" onClick={() => setConfirming(false)} disabled={pending} className="flex-1">취소</Button>
              <Button type="button" onClick={requestDelete} disabled={pending} className="flex-1 bg-[#8f5037] text-white hover:bg-[#7d412c]">
                <Trash2 className="h-4 w-4" /> {pending ? "삭제 중" : "삭제"}
              </Button>
            </div>
          </div>
        ) : (
          <Button type="button" variant="secondary" onClick={requestDelete} disabled={pending} className="mt-3 w-full border-[#c88a72] text-[#8f5037] hover:bg-[#ffe8dd]">
            <Trash2 className="h-4 w-4" /> {pending ? "삭제 중" : `${data.type} 삭제`}
          </Button>
        )}
        {failed ? <p className="mt-2 text-xs text-[#8f5037]">삭제하지 못했습니다.</p> : null}
      </div>
    </Card>
  );
}

function PromptBody({ data }: { data: LibraryItemDetailDTO }) {
  const [variables, setVariables] = useState<Record<string, string>>({});
  const rendered = useMemo(() => renderPrompt(data.content, variables), [data.content, variables]);
  const prompt = data.prompt;
  return (
    <>
      <Card id="overview" className="scroll-mt-24">
        <CardHeader><CardTitle className="flex items-center gap-2"><ScrollText className="h-5 w-5" /> Prompt Body</CardTitle></CardHeader>
        <CardContent>
          <pre className="max-h-[520px] overflow-auto rounded-xl border border-[#d8d3c7] bg-white/60 p-4 text-sm leading-7 text-[#36322d]"><code>{data.content}</code></pre>
        </CardContent>
      </Card>
      <Card id="variables" className="scroll-mt-24">
        <CardHeader><CardTitle>Fill Variables</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {prompt?.inputVariables.length ? prompt.inputVariables.map((variable) => (
            <label key={variable.name} className="block text-xs text-[#514c44]">
              {variable.name}{variable.required ? " *" : ""}
              <textarea value={variables[variable.name] ?? ""} onChange={(event) => setVariables((current) => ({ ...current, [variable.name]: event.target.value }))} rows={3} className="mt-1 w-full rounded-md border border-[#d8d3c7] bg-white/60 px-3 py-2 text-sm text-[#111111] outline-none focus:border-gold-300/60" />
            </label>
          )) : <EmptySection message="등록된 변수가 없습니다." />}
          <pre className="max-h-80 overflow-auto rounded-xl border border-gold-300/15 bg-white/60 p-4 text-sm leading-7 text-[#36322d]"><code>{rendered}</code></pre>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void navigator.clipboard.writeText(data.content)}><Clipboard className="h-4 w-4" /> Copy Prompt</Button>
            <Button type="button" variant="secondary" onClick={() => void navigator.clipboard.writeText(rendered)}><Clipboard className="h-4 w-4" /> Copy Rendered Prompt</Button>
          </div>
        </CardContent>
      </Card>
    </>
  );
}

export function SkillDetailClient({ skillId }: { skillId: string }) {
  const language = useLibraryStore((state) => state.language);
  const router = useRouter();
  const queryClient = useQueryClient();
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

  if (isLoading) return <div className="rounded-2xl border border-[#d8d3c7] p-10 text-[#514c44]">{t(language, "preparingSkillDetail")}</div>;
  if (isError || !data) return <div className="rounded-2xl border border-[#d8d3c7] p-10 text-[#514c44]">{t(language, "skillNotFound")}</div>;

  const item = data;
  const isPrompt = item.type === "PROMPT";
  const overview = item.content.replace(/```[\s\S]*?```/g, "").trim();

  function handleDelete() {
    if (deleteMutation.isPending) return;
    deleteMutation.mutate();
  }

  return (
    <div className="archive-document-page grid gap-8 px-8 py-10 md:px-14 xl:grid-cols-[250px_minmax(0,1fr)] xl:px-16">
      <aside className="hidden xl:block">
        <Card className="archive-paper-card sticky top-24 p-4">
          <p className="mb-4 font-serif text-lg text-[#111111]">서재</p>
          <Link href={`/library/${item.category.slug}`} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[#36322d] hover:bg-[#e9e4da]"><ArrowLeft className="h-4 w-4" /> {item.category.name}</Link>
          <div className="mt-4 space-y-2 border-t border-[#d8d3c7] pt-4 text-sm text-[#6f6a60]"><p>Computer Science</p><p className="pl-3 text-[#111111]">{item.category.name}</p></div>
        </Card>
      </aside>

      <article className="space-y-5">
        <p className="text-xs font-bold uppercase tracking-[0.32em] text-[#111111]">{isPrompt ? "Prompt Reading Room" : t(language, "skillDetailKicker")}</p>
        <Card className="archive-paper-card overflow-hidden p-6">
          <div className="grid gap-7 lg:grid-cols-[190px_minmax(0,1fr)]">
            <div className={`book-cover ${isPrompt ? "prompt-card" : ""} flex min-h-64 items-center justify-center rounded-xl border border-gold-300/20 p-5 text-center font-serif text-xl leading-tight text-[#111111]`}>{item.title}</div>
            <div>
              <div className="flex flex-wrap gap-2"><Badge>{item.type}</Badge>{isPrompt && item.prompt ? <><Badge>{item.prompt.promptKind}</Badge><Badge>{item.prompt.contentFormat}</Badge></> : null}{item.tags.map((tag) => <Badge key={tag} className="border-[#cfc8b8] bg-[#f6f3ec] text-[#36322d]">{tag}</Badge>)}</div>
              <h1 className="mt-4 text-balance font-serif text-5xl leading-tight tracking-[-0.03em] text-[#070707] md:text-6xl">{item.title}</h1>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-[#36322d]">{item.description}</p>
              <div className="mt-5 flex flex-wrap gap-2">
                {isPrompt ? <><Button type="button" onClick={() => void navigator.clipboard.writeText(item.content)}><Clipboard className="h-4 w-4" /> Copy Prompt</Button><Button asChild variant="secondary"><a href="#variables">Fill Variables</a></Button></> : <Button asChild><a href="#usage-guide"><BookOpen className="h-4 w-4" /> {t(language, "openUsageGuide")}</a></Button>}
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
                  ...(isPrompt && item.prompt ? [["Prompt Domain", item.prompt.promptDomain], ["Task", item.prompt.promptTaskType], ["Variables", String(item.prompt.inputVariables.length)]] : []),
                ].map(([label, value]) => <tr key={label}><th className="w-40 bg-[#eee9df] px-4 py-3 align-top font-medium text-[#6f6a60]">{label}</th><td className="break-words px-4 py-3 text-[#111111]">{value}</td></tr>)}
              </tbody></table></CardContent>
            </Card>

            {isPrompt ? <PromptBody data={data} /> : (
              <Card id="usage-guide" className="scroll-mt-24"><CardHeader><CardTitle className="flex items-center gap-2"><Table2 className="h-5 w-5" /> {t(language, "usageGuide")}</CardTitle></CardHeader><CardContent>{overview ? <p className="whitespace-pre-line leading-8 text-[#36322d]">{overview}</p> : <EmptySection message={t(language, "usageGuideEmpty")} />}</CardContent></Card>
            )}

            <Card id="history" className="scroll-mt-24"><CardHeader><CardTitle className="flex items-center gap-2"><History className="h-5 w-5" /> {t(language, "recentUsageHistory")}</CardTitle></CardHeader><CardContent>{item.usageHistory.length === 0 ? <EmptySection message={t(language, "usageHistoryEmpty")} /> : <div className="overflow-hidden rounded-xl border border-[#d8d3c7]"><table className="w-full text-left text-sm"><thead className="bg-white/[0.03] text-[#6f6a60]"><tr><th className="p-3">{t(language, "usedAt")}</th><th className="p-3">{t(language, "agent")}</th><th className="p-3">{t(language, "accessMethod")}</th></tr></thead><tbody className="divide-y divide-[#d8d3c7]">{item.usageHistory.map((usage) => <tr key={usage.id}><td className="p-3 text-[#514c44]">{formatDate(usage.accessedAt)}</td><td className="p-3 text-[#111111]">{usage.agentName}</td><td className="p-3 text-[#514c44]">{usage.accessMethod}</td></tr>)}</tbody></table></div>}</CardContent></Card>
          </div>

          <aside className="space-y-5">
            <Card className="p-4"><p className="mb-3 font-serif text-xl text-[#111111]">{t(language, "tableOfContents")}</p><nav className="space-y-1">{item.tableOfContents.map((item, index) => <a key={item.id} href={`#${item.id}`} className="flex gap-3 rounded-lg px-3 py-2 text-sm text-[#514c44] hover:bg-white/[0.05] hover:text-[#111111]"><span className="text-[#958c7e]">{index + 1}.</span> {item.label}</a>)}</nav></Card>
            <ArchiveControls data={data} onDelete={handleDelete} pending={deleteMutation.isPending} failed={deleteMutation.isError} />
          </aside>
        </div>
      </article>
    </div>
  );
}
