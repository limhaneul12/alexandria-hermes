"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BookOpen, Copy, History, MoreHorizontal, Star, Table2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchSkillDetail } from "@/lib/api";
import { formatDate, formatRelative } from "@/lib/utils";

function EmptySection({ message }: { message: string }) {
  return <p className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-stone-400">{message}</p>;
}

export function SkillDetailClient({ skillId }: { skillId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["skill", skillId],
    queryFn: () => fetchSkillDetail(skillId),
  });

  if (isLoading) {
    return <div className="rounded-2xl border border-white/10 p-10 text-stone-400">스킬 상세 열람을 준비하는 중입니다...</div>;
  }

  if (isError || !data) {
    return <div className="rounded-2xl border border-white/10 p-10 text-stone-400">해당 항목을 찾지 못했습니다.</div>;
  }

  const overview = data.content.replace(/```[\s\S]*?```/g, "").trim();

  return (
    <div className="grid gap-6 xl:grid-cols-[250px_minmax(0,1fr)]">
      <aside className="hidden xl:block">
        <Card className="sticky top-24 p-4">
          <p className="mb-4 font-serif text-lg text-gold-100">서재</p>
          <Link href={`/library/${data.category.slug}`} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-stone-300 hover:bg-white/[0.04] hover:text-gold-100">
            <ArrowLeft className="h-4 w-4" /> {data.category.name}
          </Link>
          <div className="mt-4 space-y-2 border-t border-white/10 pt-4 text-sm text-stone-400">
            <p>Computer Science</p>
            <p className="pl-3 text-gold-100">{data.category.name}</p>
          </div>
        </Card>
      </aside>

      <article className="space-y-5">
        <p className="text-xs uppercase tracking-[0.32em] text-bronze">스킬 상세 열람</p>
        <Card className="p-6">
          <div className="grid gap-6 lg:grid-cols-[150px_minmax(0,1fr)]">
            <div className="book-cover flex min-h-48 items-center justify-center rounded-xl border border-gold-300/20 p-5 text-center font-serif text-xl leading-tight text-gold-100">
              {data.title}
            </div>
            <div>
              <div className="flex flex-wrap gap-2">
                <Badge>{data.type}</Badge>
                {data.tags.map((tag) => <Badge key={tag} className="bg-white/[0.04] text-stone-300">{tag}</Badge>)}
              </div>
              <h2 className="mt-4 font-serif text-4xl leading-tight text-gold-50 md:text-5xl">{data.title}</h2>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-stone-300">{data.description}</p>
              <div className="mt-5 flex flex-wrap gap-2">
                <Button asChild>
                  <a href="#usage-guide"><BookOpen className="h-4 w-4" /> 사용 가이드 열기</a>
                </Button>
                <Button variant="secondary"><Star className="h-4 w-4" /> 즐겨찾기</Button>
                <Button variant="secondary"><Copy className="h-4 w-4" /> 복제하기</Button>
                <Button variant="ghost" size="icon" aria-label="더보기"><MoreHorizontal className="h-4 w-4" /></Button>
              </div>
            </div>
          </div>
        </Card>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_280px]">
          <div className="space-y-5">
            <Card>
              <CardHeader><CardTitle>기본 정보</CardTitle></CardHeader>
              <CardContent>
                <dl className="grid gap-3 text-sm md:grid-cols-2">
                  <div><dt className="text-stone-500">ID</dt><dd className="break-all text-parchment">{data.id}</dd></div>
                  <div><dt className="text-stone-500">Type</dt><dd className="text-parchment">{data.type}</dd></div>
                  <div><dt className="text-stone-500">Category</dt><dd className="text-parchment">{data.category.name}</dd></div>
                  <div><dt className="text-stone-500">Created By</dt><dd className="text-parchment">{data.author}</dd></div>
                  <div><dt className="text-stone-500">Created At</dt><dd className="text-parchment">{formatDate(data.updatedAt)}</dd></div>
                  <div><dt className="text-stone-500">Last Accessed</dt><dd className="text-parchment">{formatRelative(data.lastAccessedAt)}</dd></div>
                  <div><dt className="text-stone-500">Version</dt><dd className="text-parchment">{data.version}</dd></div>
                  <div><dt className="text-stone-500">Tags</dt><dd className="text-parchment">{data.tags.join(", ") || "-"}</dd></div>
                </dl>
              </CardContent>
            </Card>

            <Card id="usage-guide">
              <CardHeader><CardTitle className="flex items-center gap-2"><Table2 className="h-5 w-5" /> 사용 가이드</CardTitle></CardHeader>
              <CardContent>
                {overview ? <p className="whitespace-pre-line leading-8 text-stone-300">{overview}</p> : <EmptySection message="아직 작성된 사용 가이드가 없습니다." />}
              </CardContent>
            </Card>

            <Card id="history">
              <CardHeader><CardTitle className="flex items-center gap-2"><History className="h-5 w-5" /> 최근 사용 이력</CardTitle></CardHeader>
              <CardContent>
                {data.usageHistory.length === 0 ? (
                  <EmptySection message="아직 사용 이력이 없습니다." />
                ) : (
                  <div className="overflow-hidden rounded-xl border border-white/10">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-white/[0.03] text-stone-500">
                        <tr>
                          <th className="p-3">사용일시</th>
                          <th className="p-3">에이전트</th>
                          <th className="p-3">사용 방법</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/10">
                        {data.usageHistory.map((usage) => (
                          <tr key={usage.id}>
                            <td className="p-3 text-stone-400">{formatDate(usage.accessedAt)}</td>
                            <td className="p-3 text-parchment">{usage.agentName}</td>
                            <td className="p-3 text-stone-400">{usage.accessMethod}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <aside className="space-y-5">
            <Card className="p-4">
              <p className="mb-3 font-serif text-xl text-gold-100">목차</p>
              <nav className="space-y-1">
                {(data.tableOfContents.length > 0 ? data.tableOfContents : [{ id: "usage-guide", label: "사용 가이드" }, { id: "history", label: "최근 사용 이력" }]).map((item, index) => (
                  <a key={item.id} href={`#${item.id}`} className="flex gap-3 rounded-lg px-3 py-2 text-sm text-stone-400 hover:bg-white/[0.05] hover:text-gold-100">
                    <span className="text-stone-600">{index + 1}.</span> {item.label}
                  </a>
                ))}
              </nav>
            </Card>
          </aside>
        </div>
      </article>
    </div>
  );
}
