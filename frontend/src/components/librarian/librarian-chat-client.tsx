"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bot, Loader2, Send, SlidersHorizontal } from "lucide-react";

import { ContentViewer } from "@/components/content/content-viewer";
import { Button } from "@/components/ui/button";
import { chatWithLibrarian, fetchAgents, fetchLibrarianProviders } from "@/lib/api";
import type {
  AgentDTO,
  LibrarianChatResponseDTO,
  LibrarianProviderDTO,
  LibrarianSourceRefDTO,
} from "@/types/library";

function sourceRefLabel(sourceType: LibrarianSourceRefDTO["sourceType"]) {
  if (sourceType === "SKILL") return "스킬";
  if (sourceType === "PROMPT") return "프롬프트";
  if (sourceType === "CONTEXT") return "장기기억";
  if (sourceType === "MEMORY_COMPACT") return "기억 요약본";
  return "라이브러리 항목";
}

function providerName(
  providers: LibrarianProviderDTO[] | undefined,
  providerId: string | null,
) {
  if (!providerId) return "provider 미지정";
  return providers?.find((provider) => provider.id === providerId)?.name ?? providerId;
}

function librarianOptionLabel(
  agent: AgentDTO,
  providers: LibrarianProviderDTO[] | undefined,
) {
  const model = agent.preferredLibrarianModel ?? "model unset";
  return `${agent.name} · ${providerName(providers, agent.preferredLibrarianProvider)} · ${model}`;
}

export function LibrarianChatClient() {
  const [prompt, setPrompt] = useState("");
  const [selectedLibrarianId, setSelectedLibrarianId] = useState("");
  const [response, setResponse] = useState<LibrarianChatResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  const agentsQuery = useQuery({
    queryKey: ["agents", "librarian-chat"],
    queryFn: fetchAgents,
    staleTime: 60_000,
  });

  const providersQuery = useQuery({
    queryKey: ["librarian-providers", "librarian-chat"],
    queryFn: fetchLibrarianProviders,
    staleTime: 60_000,
  });

  const librarianProfiles = useMemo(
    () =>
      (agentsQuery.data ?? []).filter(
        (agent) =>
          agent.librarianEnabled &&
          (
            agent.provider === "OPENAI_CODEX" ||
            agent.preferredLibrarianProvider !== null
          ),
      ),
    [agentsQuery.data],
  );

  const selectedLibrarian = useMemo(
    () =>
      librarianProfiles.find((agent) => agent.id === selectedLibrarianId) ??
      null,
    [librarianProfiles, selectedLibrarianId],
  );
  const activeSelectionCount = [
    selectedLibrarianId !== "",
  ].filter(Boolean).length;

  const chatMutation = useMutation({
    mutationFn: () => chatWithLibrarian({
      prompt: prompt.trim(),
      limit: 5,
      providerId: selectedLibrarian?.preferredLibrarianProvider ?? null,
      librarianProfileId: selectedLibrarian?.id ?? null,
      librarianProfileName: selectedLibrarian?.name ?? null,
      librarianModel: selectedLibrarian?.preferredLibrarianModel ?? null,
      librarianRolePrompt: selectedLibrarian?.librarianRolePrompt ?? null,
      maxLibrarianAgents: selectedLibrarian ? 1 : null,
    }),
    onMutate: () => {
      setResponse(null);
      setError(null);
    },
    onSuccess: setResponse,
    onError: () => setError("사서 대화를 처리하지 못했습니다. 잠시 후 다시 시도하세요."),
  });

  function resetSelection() {
    setSelectedLibrarianId("");
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim() || chatMutation.isPending) return;
    chatMutation.mutate();
  }

  return (
    <div className="archive-document-page min-h-[calc(100vh-74px)] px-8 py-10 md:px-14 xl:px-16">
      <section className="mb-8 border-b border-[#cfc8b8] pb-8">
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#161616]">AI Librarian</p>
        <h1 className="mt-4 text-balance font-serif text-6xl tracking-[-0.04em] text-[#070707] md:text-7xl">사서와 얘기하기</h1>
        <p className="mt-5 max-w-3xl text-sm leading-7 text-[#36322d]">
          질문이나 실행 명령을 입력하면 Alexandria가 먼저 플랫폼 기억과 근거를 확인하고, 필요하면 선택한 사서에게 위임하거나 안전한 플랫폼 작업으로 실행합니다.
        </p>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="space-y-5">
          <form onSubmit={submit} className="rounded-2xl border border-[#d8d3c7] bg-white/65 p-5">
            <label className="block text-sm font-semibold text-[#28241f]">
              질문/명령 입력
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                rows={5}
                className="mt-2 w-full rounded-xl border border-[#cfc8b8] bg-white/80 px-4 py-3 text-sm leading-6 text-[#111111] outline-none focus-visible:ring-2 focus-visible:ring-black/15"
                placeholder="예: OAuth 검토에 맞는 사서를 찾아줘 / Summarize today's project memory"
              />
            </label>
            <section
              aria-label="사서 선택"
              className="mt-4 rounded-2xl border border-[#d8d3c7] bg-[#fbfaf6]/75 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="flex items-center gap-2 text-sm font-semibold text-[#111111]">
                    <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                    사서 선택
                    <span className="rounded-full bg-[#eee9df] px-2 py-0.5 text-xs text-[#625c52]">
                      {activeSelectionCount}
                    </span>
                  </p>
                  <p className="mt-1 text-xs leading-5 text-[#6f6a60]">
                    필요하면 특정 사서만 고르세요.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={resetSelection}
                  disabled={activeSelectionCount === 0}
                >
                  선택 초기화
                </Button>
              </div>
              <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)] xl:items-start">
                <label className="block text-sm font-semibold text-[#28241f]">
                  사서 선택
                  <select
                    value={selectedLibrarianId}
                    onChange={(event) => setSelectedLibrarianId(event.target.value)}
                    disabled={agentsQuery.isLoading || librarianProfiles.length === 0}
                    className="mt-2 w-full rounded-xl border border-[#cfc8b8] bg-white/85 px-3 py-2 text-sm text-[#111111] outline-none focus-visible:ring-2 focus-visible:ring-black/15 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="">자동 선택</option>
                    {librarianProfiles.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {librarianOptionLabel(agent, providersQuery.data)}
                      </option>
                    ))}
                  </select>
                  <span className="mt-1 block text-xs leading-5 text-[#6f6a60]">
                    {agentsQuery.isLoading
                      ? "사서 목록을 불러오는 중입니다."
                      : librarianProfiles.length
                        ? "특정 사서를 고르면 해당 사서에게 우선 답변을 요청합니다."
                        : "저장된 사서가 없으면 자동으로 가능한 답변 경로를 사용합니다."}
                  </span>
                </label>
              </div>
            </section>
            <div className="mt-5 flex justify-end">
              <Button type="submit" disabled={!prompt.trim() || chatMutation.isPending}>
                {chatMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} 보내기
              </Button>
            </div>
          </form>

          {error ? <div className="rounded-xl border border-[#d9b4a3] bg-[#fff4ef] p-4 text-sm text-[#8f5037]">{error}</div> : null}

          {response ? (
            <div className="space-y-5">
              <ContentViewer title="사서 답변" content={response.answer} />
              <section className="rounded-xl border border-[#d8d3c7] bg-white/62 p-4">
                <h2 className="font-serif text-2xl font-bold text-[#111111]">직접 검색 후보</h2>
                {response.directHits.length ? (
                  <div className="mt-4 grid gap-3">
                    {response.directHits.map((hit) => (
                      <a key={`${hit.sourceType}-${hit.id}`} href={hit.detailPath.replace(/^\/memory\/contexts/, "/contexts").replace(/^\/memory\/compacts/, "/memory-compacts")} className="rounded-xl border border-[#d8d3c7] bg-white/70 p-4 transition hover:bg-white">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <span className="font-semibold text-[#111111]">{hit.title}</span>
                          <span className="rounded border border-[#cfc8b8] px-2 py-1 text-[11px] text-[#625c52]">{sourceRefLabel(hit.sourceType)}</span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-[#514c44]">{hit.preview}</p>
                      </a>
                    ))}
                  </div>
                ) : <p className="mt-3 text-sm text-[#625c52]">직접 검색 후보가 없습니다.</p>}
              </section>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-[#cfc8b8] bg-white/45 p-8 text-center text-[#625c52]">
              <Bot className="mx-auto h-10 w-10" aria-hidden="true" />
              <p className="mt-3 font-serif text-2xl text-[#111111]">질문을 보내면 검색 후보와 사서 답변이 여기에 표시됩니다.</p>
            </div>
          )}
        </section>

        <aside className="space-y-5">
          <section className="rounded-xl border border-[#d8d3c7] bg-white/62 p-4">
            <h2 className="font-serif text-2xl font-bold text-[#111111]">근거</h2>
            {response?.sourceRefs.length ? (
              <ul className="mt-4 space-y-2 text-sm text-[#514c44]">
                {response.sourceRefs.map((ref) => (
                  <li key={`${ref.sourceType}-${ref.sourceId}`} className="rounded-lg border border-[#d8d3c7] bg-white/70 p-3">
                    <p className="font-semibold text-[#111111]">{ref.title}</p>
                    <p className="mt-1 text-xs text-[#6f6a60]">{sourceRefLabel(ref.sourceType)}</p>
                    <p className="mt-1 text-xs text-[#6f6a60]">{ref.preview}</p>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        </aside>
      </div>
    </div>
  );
}
