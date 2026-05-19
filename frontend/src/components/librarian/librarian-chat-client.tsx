"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bot, Loader2, Search, Send } from "lucide-react";

import { ContentViewer } from "@/components/content/content-viewer";
import { Button } from "@/components/ui/button";
import { chatWithLibrarian } from "@/lib/api";
import type {
  LibrarianChatMode,
  LibrarianChatResponseDTO,
  LibrarianChatTarget,
  LibrarianSourceRefDTO,
} from "@/types/library";

const TARGETS: Array<{ value: LibrarianChatTarget; label: string; description: string }> = [
  { value: "SKILL", label: "스킬", description: "실행 가능한 agent capability" },
  { value: "PROMPT", label: "프롬프트", description: "재사용 가능한 지시문" },
  { value: "CONTEXT", label: "장기기억", description: "Context Vault recall" },
  { value: "MEMORY_COMPACT", label: "Memory Compact", description: "요약된 durable memory" },
];

function modeLabel(mode: LibrarianChatMode) {
  if (mode === "DIRECT_SEARCH") return "직접 검색 먼저";
  if (mode === "DELEGATE") return "사서에게 위임";
  return "둘 다";
}

function sourceRefLabel(sourceType: LibrarianSourceRefDTO["sourceType"]) {
  if (sourceType === "SKILL") return "스킬";
  if (sourceType === "PROMPT") return "프롬프트";
  if (sourceType === "CONTEXT") return "장기기억";
  if (sourceType === "MEMORY_COMPACT") return "기억 요약본";
  return "라이브러리 항목";
}

export function LibrarianChatClient() {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<LibrarianChatMode>("SEARCH_AND_DELEGATE");
  const [targets, setTargets] = useState<LibrarianChatTarget[]>(["SKILL", "PROMPT", "CONTEXT", "MEMORY_COMPACT"]);
  const [response, setResponse] = useState<LibrarianChatResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  const modeOptions = useMemo(
    () => (["SEARCH_AND_DELEGATE", "DIRECT_SEARCH", "DELEGATE"] as const).map((item) => ({ value: item, label: modeLabel(item) })),
    [],
  );

  const chatMutation = useMutation({
    mutationFn: () => chatWithLibrarian({ prompt: prompt.trim(), mode, targets, limit: 5 }),
    onMutate: () => {
      setResponse(null);
      setError(null);
    },
    onSuccess: setResponse,
    onError: () => setError("사서 대화를 처리하지 못했습니다. 직접 검색 결과가 필요하면 모드를 바꿔 다시 시도하세요."),
  });

  function toggleTarget(target: LibrarianChatTarget) {
    setTargets((current) => {
      if (current.includes(target)) {
        const next = current.filter((item) => item !== target);
        return next.length ? next : current;
      }
      return [...current, target];
    });
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
          질문을 입력하면 Alexandria가 먼저 직접 검색 후보와 source ref를 구성하고, 필요하면 사서 delegate에 budgeted packet으로 전달합니다.
        </p>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="space-y-5">
          <form onSubmit={submit} className="rounded-2xl border border-[#d8d3c7] bg-white/65 p-5">
            <label className="block text-sm font-semibold text-[#28241f]">
              질문 입력
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                rows={5}
                className="mt-2 w-full rounded-xl border border-[#cfc8b8] bg-white/80 px-4 py-3 text-sm leading-6 text-[#111111] outline-none focus-visible:ring-2 focus-visible:ring-black/15"
                placeholder="예: OAuth 검토에 맞는 스킬과 관련 장기기억을 찾아줘"
              />
            </label>
            <div className="mt-4 grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-end">
              <label className="block text-sm font-semibold text-[#28241f]">
                실행 모드
                <select
                  value={mode}
                  onChange={(event) => setMode(event.target.value as LibrarianChatMode)}
                  className="mt-2 w-full rounded-xl border border-[#cfc8b8] bg-white/85 px-3 py-2 text-sm text-[#111111] outline-none focus-visible:ring-2 focus-visible:ring-black/15"
                >
                  {modeOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">검색 대상</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {TARGETS.map((target) => (
                    <label key={target.value} className="flex cursor-pointer gap-3 rounded-xl border border-[#d8d3c7] bg-white/70 p-3 text-sm text-[#36322d]">
                      <input type="checkbox" checked={targets.includes(target.value)} onChange={() => toggleTarget(target.value)} className="mt-1 h-4 w-4 accent-black" />
                      <span>
                        <span className="block font-semibold text-[#111111]">{target.label}</span>
                        <span className="block text-xs leading-5 text-[#6f6a60]">{target.description}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
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
            <h2 className="flex items-center gap-2 font-serif text-2xl font-bold text-[#111111]"><Search className="h-5 w-5" /> 실행/CLI 요약</h2>
            {response?.executionSummary.length ? (
              <ul className="mt-4 space-y-2 text-sm text-[#514c44]">
                {response.executionSummary.map((item) => <li key={item} className="rounded-lg border border-[#d8d3c7] bg-white/70 px-3 py-2">{item}</li>)}
              </ul>
            ) : <p className="mt-3 text-sm text-[#625c52]">검색 대상과 실행 모드가 기록됩니다.</p>}
          </section>
          <section className="rounded-xl border border-[#d8d3c7] bg-white/62 p-4">
            <h2 className="font-serif text-2xl font-bold text-[#111111]">Source refs</h2>
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
            ) : <p className="mt-3 text-sm text-[#625c52]">답변에 사용할 source ref가 여기에 표시됩니다.</p>}
          </section>
        </aside>
      </div>
    </div>
  );
}
