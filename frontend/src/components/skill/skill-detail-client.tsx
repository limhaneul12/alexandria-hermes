"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BookOpen, Clock3, Code2, History, Table2 } from "lucide-react";

import { fetchSkillDetail } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, formatRelative } from "@/lib/utils";

export function SkillDetailClient({ skillId }: { skillId: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["skill", skillId], queryFn: () => fetchSkillDetail(skillId) });

  if (isLoading || !data) return <div className="rounded-2xl border border-white/10 p-10 text-stone-400">Opening archive volume...</div>;

  return (
    <div className="grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)_260px]">
      <aside className="hidden xl:block">
        <Card className="sticky top-28 p-4">
          <Link href={`/library/${data.category.slug}`} className="mb-4 flex items-center gap-2 text-sm text-gold-100 hover:text-gold-200">
            <ArrowLeft className="h-4 w-4" /> Back to shelf
          </Link>
          <p className="mb-3 text-xs uppercase tracking-[0.28em] text-bronze">Metadata</p>
          <div className="space-y-3 text-sm text-stone-400">
            <p><span className="text-stone-500">Version</span><br />{data.version}</p>
            <p><span className="text-stone-500">Created by</span><br />{data.author}</p>
            <p><span className="text-stone-500">Last used</span><br />{formatRelative(data.lastAccessedAt)}</p>
            <p><span className="text-stone-500">Shelf</span><br />{data.category.name}</p>
          </div>
        </Card>
      </aside>

      <article className="space-y-6">
        <Card className="p-8">
          <div className="flex flex-wrap gap-2">
            <Badge>{data.type}</Badge>
            {data.tags.map((tag) => <Badge key={tag} className="bg-white/[0.04] text-stone-300">{tag}</Badge>)}
          </div>
          <h2 className="mt-5 font-serif text-5xl leading-tight text-gold-50">{data.title}</h2>
          <p className="mt-4 max-w-3xl text-lg leading-8 text-stone-300">{data.description}</p>
          <div className="mt-6 grid gap-3 text-sm text-stone-400 md:grid-cols-4">
            <span><Clock3 className="mb-1 h-4 w-4 text-gold-300" />Updated {formatDate(data.updatedAt)}</span>
            <span><BookOpen className="mb-1 h-4 w-4 text-gold-300" />{data.usageCount} usages</span>
            <span>Version<br /><strong className="text-parchment">{data.version}</strong></span>
            <span>Author<br /><strong className="text-parchment">{data.author}</strong></span>
          </div>
        </Card>

        <Card id="overview">
          <CardHeader><CardTitle>Overview</CardTitle></CardHeader>
          <CardContent>
            <p className="whitespace-pre-line leading-8 text-stone-300">{data.content.replace(/```[\s\S]*?```/g, "").trim()}</p>
          </CardContent>
        </Card>

        <Card id="usage-guide">
          <CardHeader><CardTitle className="flex items-center gap-2"><Table2 className="h-5 w-5" /> Usage Guide</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-xl border border-white/10">
              <table className="w-full text-left text-sm">
                <tbody className="divide-y divide-white/10">
                  <tr><th className="w-44 bg-white/[0.03] p-3 text-stone-500">Capability type</th><td className="p-3 text-parchment">{data.type}</td></tr>
                  <tr><th className="bg-white/[0.03] p-3 text-stone-500">Recommended agent</th><td className="p-3 text-parchment">Hermes Librarian</td></tr>
                  <tr><th className="bg-white/[0.03] p-3 text-stone-500">Access pattern</th><td className="p-3 text-parchment">Search → inspect metadata → execute procedure → record usage</td></tr>
                  <tr><th className="bg-white/[0.03] p-3 text-stone-500">Governance</th><td className="p-3 text-parchment">Versioned, tagged, category-owned</td></tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card id="examples">
          <CardHeader><CardTitle className="flex items-center gap-2"><Code2 className="h-5 w-5" /> Code Examples</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {data.codeExamples.map((example) => (
              <div key={`${example.title}-${example.language}`} className="overflow-hidden rounded-xl border border-white/10 bg-black/40">
                <div className="border-b border-white/10 px-4 py-2 text-xs uppercase tracking-[0.22em] text-bronze">{example.title} · {example.language}</div>
                <pre className="overflow-x-auto p-4 text-sm leading-6 text-gold-100"><code>{example.code}</code></pre>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card id="history">
          <CardHeader><CardTitle className="flex items-center gap-2"><History className="h-5 w-5" /> Recent Usage History</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data.usageHistory.map((usage) => (
                <div key={usage.id} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] p-3 text-sm">
                  <div>
                    <p className="text-parchment">{usage.agentName}</p>
                    <p className="text-stone-500">{usage.accessMethod}</p>
                  </div>
                  <p className="text-stone-400">{formatRelative(usage.accessedAt)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </article>

      <aside className="hidden xl:block">
        <Card className="sticky top-28 p-4">
          <p className="mb-3 text-xs uppercase tracking-[0.28em] text-bronze">On this volume</p>
          <nav className="space-y-1">
            {data.tableOfContents.map((item) => (
              <a key={item.id} href={`#${item.id}`} className="block rounded-lg px-3 py-2 text-sm text-stone-400 hover:bg-white/[0.05] hover:text-gold-100">
                {item.label}
              </a>
            ))}
          </nav>
        </Card>
      </aside>
    </div>
  );
}
