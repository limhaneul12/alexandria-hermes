"use client";

import { useQuery } from "@tanstack/react-query";
import { Archive, BookOpen, LibraryBig, ScrollText, Sparkles } from "lucide-react";
import Link from "next/link";

import { SkillCard } from "@/components/library/skill-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchDashboard } from "@/lib/api";

function EmptyPanel({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-6 text-sm text-stone-400">
      <p className="font-serif text-xl text-gold-100">{title}</p>
      <p className="mt-2 leading-6">{description}</p>
    </div>
  );
}

export function DashboardClient() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  if (isLoading) {
    return <div className="rounded-2xl border border-white/10 p-10 text-stone-400">대시보드를 여는 중입니다...</div>;
  }

  if (isError || !data) {
    return <div className="rounded-2xl border border-white/10 p-10 text-stone-400">아카이브 상태를 불러오지 못했습니다.</div>;
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-3xl border border-gold-300/20 bg-[radial-gradient(circle_at_20%_10%,rgba(214,173,69,0.16),transparent_30%),linear-gradient(135deg,rgba(29,24,16,0.96),rgba(8,8,8,0.98))] shadow-gold">
        <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          <div className="p-7 md:p-9">
            <p className="text-xs uppercase tracking-[0.34em] text-gold-300">Grand Archive</p>
            <h2 className="mt-5 font-serif text-4xl leading-tight text-gold-50 md:text-5xl">AI 에이전트를 위한 기술 지식 아카이브</h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
              분류, 탐색, 기록, 추천을 중심으로 필요한 스킬과 지식 문서를 빠르게 다시 꺼내 쓰는 디지털 도서관입니다.
            </p>
          </div>
          <div className="min-h-52 border-t border-white/10 bg-[radial-gradient(circle_at_30%_20%,rgba(214,173,69,0.22),transparent_26%),linear-gradient(135deg,rgba(214,173,69,0.08),transparent)] lg:border-l lg:border-t-0" />
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {data.stats.map((stat) => (
          <Card key={stat.label} className="p-5">
            <div className="flex items-start gap-3">
              <Archive className="mt-1 h-5 w-5 text-gold-300" />
              <div>
                <p className="text-xs text-stone-500">{stat.label}</p>
                <p className="mt-2 font-serif text-3xl text-gold-100">{stat.value.toLocaleString()}</p>
                <p className="mt-1 text-xs text-stone-500">{stat.hint}</p>
              </div>
            </div>
          </Card>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <Card id="recent">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" /> 최근에 가져간 스킬
            </CardTitle>
            <Link href="/library" className="text-sm text-gold-100 hover:text-gold-200">전체 보기</Link>
          </CardHeader>
          <CardContent>
            {data.recentlyUsed.length === 0 ? (
              <EmptyPanel title="아직 가져간 스킬이 없습니다" description="서재에 실제 항목이 들어오면 최근에 열람한 스킬이 여기에 표시됩니다." />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {data.recentlyUsed.slice(0, 4).map((skill) => (
                  <SkillCard key={skill.id} skill={skill} view="list" />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card id="recommended">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" /> 추천 아카이브
            </CardTitle>
            <Link href="/library" className="text-sm text-gold-100 hover:text-gold-200">전체 보기</Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.recommendations.length === 0 ? (
              <EmptyPanel title="추천할 기록이 없습니다" description="사용 기록과 카테고리 신호가 쌓이면 추천 항목을 보여줍니다." />
            ) : (
              data.recommendations.slice(0, 4).map((item) => (
                <div key={item.id} className="rounded-xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-serif text-lg text-gold-100">{item.title}</p>
                    <span className="rounded-full bg-gold-300/10 px-2 py-1 text-[11px] text-gold-100">{item.type}</span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-400">{item.description}</p>
                  <p className="mt-3 text-xs text-stone-500">{item.usageCount.toLocaleString()}회 사용</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>

      <section id="usage" className="grid gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LibraryBig className="h-5 w-5" /> 카테고리 활동
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.categoryActivity.length === 0 ? (
              <EmptyPanel title="카테고리 활동 없음" description="카테고리별 항목과 사용 기록이 생기면 활동량을 보여줍니다." />
            ) : (
              data.categoryActivity.map((category) => (
                <div key={category.name} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-parchment">{category.name}</span>
                    <span className="text-stone-400">{category.value.toLocaleString()}</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div className="h-2 rounded-full bg-gold-300" style={{ width: `${Math.min(100, category.value)}%` }} />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ScrollText className="h-5 w-5" /> 최근 7일 사용 추이
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.usageTrend.length === 0 ? (
              <EmptyPanel title="사용 추이 없음" description="아카이브를 사용하기 시작하면 날짜별 사용 흐름이 표시됩니다." />
            ) : (
              <div className="flex h-56 items-end gap-3 border-b border-white/10 px-2 pb-2">
                {data.usageTrend.map((point) => (
                  <div key={point.day} className="flex flex-1 flex-col items-center gap-2">
                    <div className="w-full rounded-t bg-gold-300/70" style={{ height: `${Math.max(8, Math.min(100, point.usage))}%` }} />
                    <span className="text-[10px] text-stone-500">{point.day}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
