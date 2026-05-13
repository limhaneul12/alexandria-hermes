"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Bot, BrainCircuit, CheckCircle2, Clock3, ScrollText, ShieldCheck, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchAgents, fetchLibrarianProviders, updateAgentLibrarianProvider } from "@/lib/api";

const queue = [
  "새 서재 규칙을 에이전트가 찾기 쉬운 책장에 정리",
  "긴 목록을 넘기는 서재 탐색 정책 검토",
  "복구 워크플로우를 추천 서가로 승격",
];

const selectClassName =
  "mt-3 h-10 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-parchment outline-none transition focus:border-gold-300/50 focus:ring-1 focus:ring-gold-300/30";

export default function AgentsPage() {
  const queryClient = useQueryClient();
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const agentsQuery = useQuery({ queryKey: ["agents"], queryFn: fetchAgents });
  const providersQuery = useQuery({
    queryKey: ["librarian-providers"],
    queryFn: fetchLibrarianProviders,
  });

  const providersById = useMemo(
    () => new Map((providersQuery.data ?? []).map((provider) => [provider.id, provider])),
    [providersQuery.data],
  );
  const enabledProviders = useMemo(
    () => (providersQuery.data ?? []).filter((provider) => provider.enabled),
    [providersQuery.data],
  );

  const assignMutation = useMutation({
    mutationFn: ({ agentId, providerId }: { agentId: string; providerId: string | null }) =>
      updateAgentLibrarianProvider(agentId, providerId),
    onSuccess: async (agent) => {
      const providerName = agent.preferredLibrarianProvider
        ? providersById.get(agent.preferredLibrarianProvider)?.name ?? agent.preferredLibrarianProvider
        : "지정 없음";
      setStatusMessage(`${agent.name}의 서재 관리 사서를 ${providerName}(으)로 배정했습니다.`);
      await queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: () => setStatusMessage("에이전트 사서 배정 저장에 실패했습니다."),
  });

  return (
    <div className="space-y-7">
      <section className="rounded-3xl border border-gold-300/20 bg-[radial-gradient(circle_at_15%_10%,rgba(214,173,69,0.18),transparent_28%),linear-gradient(135deg,rgba(22,22,22,0.95),rgba(9,8,7,0.98))] p-8 shadow-gold">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.34em] text-bronze">Agents</p>
            <h2 className="mt-3 font-serif text-5xl text-gold-50">에이전트별 서재 관리 사서 배정</h2>
            <p className="mt-4 text-base leading-7 text-stone-300">
              에이전트별 서재 역할을 확인하고 사용할 서재 관리 사서를 지정합니다.
            </p>
          </div>
          <div className="rounded-2xl border border-gold-300/20 bg-black/30 p-5 text-sm text-stone-400">
            <div className="flex items-center gap-2 text-gold-100">
              <ShieldCheck className="h-4 w-4" /> 서재 관리 준비됨
            </div>
            <p className="mt-2">검토된 스킬 · 정리된 워크플로우 · 재사용 가능한 지식</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {agentsQuery.isLoading ? (
          <Card className="p-5 xl:col-span-3">
            <p className="text-sm text-stone-400">에이전트 프로필을 불러오는 중입니다.</p>
          </Card>
        ) : agentsQuery.isError ? (
          <Card className="p-5 xl:col-span-3">
            <p className="text-sm text-red-300">에이전트 목록을 불러오지 못했습니다.</p>
          </Card>
        ) : agentsQuery.data?.length ? (
          agentsQuery.data.map((agent) => {
            const currentProvider = agent.preferredLibrarianProvider
              ? providersById.get(agent.preferredLibrarianProvider)
              : null;
            const hasMissingCurrentProvider =
              Boolean(agent.preferredLibrarianProvider) && !currentProvider;

            return (
              <Card key={agent.id} className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-gold-300/25 bg-gold-300/10 text-gold-100">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="font-serif text-2xl text-gold-100">{agent.name}</h3>
                      <p className="text-sm text-stone-400">{agent.provider}</p>
                    </div>
                  </div>
                  <Badge className={currentProvider?.enabled ? "bg-emerald-500/10 text-emerald-200" : undefined}>
                    {currentProvider?.enabled ? "배정됨" : "사서 배정 필요"}
                  </Badge>
                </div>
                <p className="mt-5 text-sm leading-6 text-stone-300">
                  {agent.description ?? "설명 없이 등록된 에이전트입니다."}
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  {agent.capabilities.map((capability) => (
                    <span key={capability} className="rounded-full bg-white/[0.05] px-2.5 py-1 text-xs text-stone-300">
                      {capability}
                    </span>
                  ))}
                </div>
                <label className="mt-5 block text-sm text-stone-400">
                  서재 관리 사서
                  <select
                    className={selectClassName}
                    value={agent.preferredLibrarianProvider ?? ""}
                    disabled={enabledProviders.length === 0 || assignMutation.isPending}
                    onChange={(event) => {
                      assignMutation.mutate({
                        agentId: agent.id,
                        providerId: event.target.value || null,
                      });
                    }}
                  >
                    <option value="">지정 없음</option>
                    {hasMissingCurrentProvider ? (
                      <option value={agent.preferredLibrarianProvider ?? ""}>
                        현재 사서: {agent.preferredLibrarianProvider}
                      </option>
                    ) : null}
                    {enabledProviders.map((provider) => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name} · {provider.providerType} · {provider.authType}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="mt-3 text-xs text-stone-500">
                  현재 선택: {currentProvider?.name ?? agent.preferredLibrarianProvider ?? "지정 없음"}
                </p>
              </Card>
            );
          })
        ) : (
          <Card className="p-5 xl:col-span-3">
            <p className="text-sm text-stone-400">등록된 에이전트 프로필이 없습니다.</p>
          </Card>
        )}
      </section>

      {enabledProviders.length === 0 ? (
        <Card className="p-5">
          <p className="text-sm text-stone-300">
            배정 가능한 서재 관리 사서가 없습니다. 설정에서 API key 기반 사서 인증을 먼저 추가하세요.
          </p>
          <Link href="/settings#librarians" className="mt-3 inline-flex text-sm text-gold-100 hover:text-gold-50">
            사서 인증 설정으로 이동
          </Link>
        </Card>
      ) : null}
      {statusMessage ? <p className="text-sm text-gold-100">{statusMessage}</p> : null}

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><BrainCircuit className="h-5 w-5" /> 사서 정리 대기열</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {queue.map((item, index) => (
              <div key={item} className="flex gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gold-300/10 text-xs text-gold-100">{index + 1}</span>
                <p className="text-sm leading-6 text-stone-300">{item}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5" /> 서재 운영 신호</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {[
              { icon: Sparkles, label: "추천 상태", value: "준비됨" },
              { icon: ScrollText, label: "최근 정리", value: "역량 접수" },
              { icon: Clock3, label: "검토 주기", value: "매일 검토" },
              { icon: CheckCircle2, label: "열람 정책", value: "버전별 열람" },
            ].map((signal) => {
              const Icon = signal.icon;
              return (
                <div key={signal.label} className="rounded-xl border border-white/10 bg-black/25 p-4">
                  <Icon className="h-5 w-5 text-gold-300" />
                  <p className="mt-3 text-xs uppercase tracking-[0.22em] text-stone-500">{signal.label}</p>
                  <p className="mt-1 font-serif text-xl text-parchment">{signal.value}</p>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
