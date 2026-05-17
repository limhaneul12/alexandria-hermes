"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Bot, Loader2, Search, Send, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { askLibrarian } from "@/lib/api";
import {
  OPEN_LIBRARIAN_ASK_EVENT,
  type OpenLibrarianAskEventDetail,
} from "@/lib/librarian/ask-events";
import { t, type Language } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";
import type { LibrarianAskResponseDTO } from "@/types/library";

type AskCopy = {
  title: string;
  kicker: string;
  body: string;
  promptLabel: string;
  placeholder: string;
  send: string;
  sending: string;
  result: string;
  route: string;
  delegates: string;
  status: string;
  job: string;
  closePanel: string;
  error: string;
  quickPrompts: Array<{ label: string; prompt: string }>;
};

function copyFor(language: Language): AskCopy {
  if (language === "ko") {
    return {
      title: "사서에게 묻기",
      kicker: "도움이 필요하신가요?",
      body: "스킬, 프롬프트, 맥락 회수, 후보 작성 경로를 바로 물어보세요.",
      promptLabel: "질문",
      placeholder: "예: OAuth 검토에 맞는 스킬을 찾아줘",
      send: "보내기",
      sending: "보내는 중",
      result: "추천",
      route: "라우팅 미리보기",
      delegates: "사서 delegate",
      status: "상태",
      job: "작업",
      closePanel: "닫기",
      error: "사서에게 질문하지 못했습니다. 잠시 뒤 다시 시도하세요.",
      quickPrompts: [
        {
          label: "스킬 찾기",
          prompt: "이 작업에 맞는 스킬을 찾고 왜 적합한지 설명해줘.",
        },
        {
          label: "프롬프트 추천",
          prompt: "이 작업에 재사용할 수 있는 프롬프트를 추천해줘.",
        },
        {
          label: "맥락 회수",
          prompt: "시작하기 전에 관련 프로젝트 맥락을 찾아줘.",
        },
        {
          label: "후보 초안",
          prompt: "라이브러리에 추가할 수 있는 스킬 후보 초안을 작성해줘.",
        },
      ],
    };
  }
  return {
    title: "Ask the Librarian",
    kicker: "Need Help?",
    body: "Ask for a skill, prompt, context recall, or candidate drafting route.",
    promptLabel: "Question",
    placeholder: "e.g. Find a skill for reviewing OAuth flows",
    send: "Send",
    sending: "Sending",
    result: "Recommendation",
    route: "Route preview",
    delegates: "Delegates",
    status: "Status",
    job: "Job",
    closePanel: "Close librarian question panel",
    error: "The librarian could not answer yet. Try again shortly.",
    quickPrompts: [
      {
        label: "Find a skill",
        prompt: "Find a skill for this task and explain why it fits.",
      },
      {
        label: "Recommend prompt",
        prompt: "Recommend a reusable prompt for this task.",
      },
      {
        label: "Recall context",
        prompt: "Recall related project context before I start.",
      },
      {
        label: "Draft candidate",
        prompt: "Draft a skill candidate that could be added to the library.",
      },
    ],
  };
}

function isOpenEvent(event: Event): event is CustomEvent<OpenLibrarianAskEventDetail> {
  return event.type === OPEN_LIBRARIAN_ASK_EVENT;
}

export function AskLibrarianWidget() {
  const language = useLibraryStore((state) => state.language);
  const copy = useMemo(() => copyFor(language), [language]);
  const [isOpen, setIsOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState<LibrarianAskResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    function handleOpen(event: Event) {
      if (!isOpenEvent(event)) return;
      setIsOpen(true);
      if (event.detail.prompt) setPrompt(event.detail.prompt);
    }
    window.addEventListener(OPEN_LIBRARIAN_ASK_EVENT, handleOpen);
    return () => window.removeEventListener(OPEN_LIBRARIAN_ASK_EVENT, handleOpen);
  }, []);

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    setResponse(null);
    try {
      const result = await askLibrarian({
        prompt: trimmedPrompt,
        agentName: "Alexandria UI",
        delegateToLibrarian: true,
        taskSummary: trimmedPrompt,
      });
      setResponse(result);
    } catch {
      setError(copy.error);
      setResponse(null);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3 print:hidden">
      {isOpen ? (
        <section className="w-[min(calc(100vw-2rem),420px)] rounded-2xl border border-[#cfc8b8] bg-[#fbfaf6] p-4 shadow-2xl shadow-black/20">
          <div className="flex items-start justify-between gap-4 border-b border-[#d8d3c7] pb-3">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#6f6a60]">
                {copy.kicker}
              </p>
              <h2 className="mt-1 flex items-center gap-2 font-serif text-2xl font-bold text-[#111111]">
                <Bot className="h-5 w-5" aria-hidden="true" /> {copy.title}
              </h2>
              <p className="mt-2 text-sm leading-6 text-[#514c44]">{copy.body}</p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={copy.closePanel}
              onClick={() => setIsOpen(false)}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {copy.quickPrompts.map((quickPrompt) => (
              <button
                key={quickPrompt.label}
                type="button"
                className="rounded-full border border-[#d8d3c7] bg-white px-3 py-1.5 text-xs font-semibold text-[#28241f] transition hover:bg-[#f6f3ec] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15"
                onClick={() => setPrompt(quickPrompt.prompt)}
              >
                {quickPrompt.label}
              </button>
            ))}
          </div>

          <form className="mt-4 space-y-3" onSubmit={submitQuestion}>
            <label className="block text-sm font-semibold text-[#28241f]">
              {copy.promptLabel}
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder={copy.placeholder}
                className="mt-2 min-h-28 w-full rounded-xl border border-[#cfc8b8] bg-white px-3 py-2 text-sm text-[#111111] outline-none transition focus-visible:border-[#111111] focus-visible:ring-2 focus-visible:ring-black/10"
              />
            </label>
            <Button type="submit" disabled={isSubmitting || !prompt.trim()} className="w-full">
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="h-4 w-4" aria-hidden="true" />
              )}
              {isSubmitting ? copy.sending : copy.send}
            </Button>
          </form>

          <div className="mt-4" aria-live="polite">
            {error ? <p className="rounded-xl border border-[#e6c8bd] bg-[#fff2ee] p-3 text-sm text-[#8a4331]">{error}</p> : null}
            {response ? (
              <div className="space-y-3 rounded-xl border border-[#d8d3c7] bg-white/70 p-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6f6a60]">
                    {copy.result}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-[#28241f]">
                    {response.recommendation}
                  </p>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="rounded-lg border border-[#e2ddd2] bg-[#fbfaf6] p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#6f6a60]">
                      {copy.status}
                    </p>
                    <p className="mt-1 text-sm font-semibold text-[#111111]">
                      {response.decision}
                    </p>
                  </div>
                  <div className="rounded-lg border border-[#e2ddd2] bg-[#fbfaf6] p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#6f6a60]">
                      {copy.job}
                    </p>
                    <p className="mt-1 truncate text-sm font-semibold text-[#111111]">
                      {response.jobId}
                    </p>
                  </div>
                </div>
                {response.routePreview.length > 0 ? (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6f6a60]">
                      {copy.route}
                    </p>
                    <ol className="mt-2 space-y-1 text-sm leading-6 text-[#514c44]">
                      {response.routePreview.slice(0, 5).map((step) => (
                        <li key={step} className="flex gap-2">
                          <Sparkles className="mt-1 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}
                {response.delegates.length > 0 ? (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6f6a60]">
                      {copy.delegates}
                    </p>
                    <ul className="mt-2 space-y-1 text-sm leading-6 text-[#514c44]">
                      {response.delegates.map((delegate) => (
                        <li key={`${delegate.profileId}-${delegate.delegateType}`}>
                          <span className="font-semibold text-[#28241f]">
                            {delegate.delegateType}
                          </span>
                          : {delegate.summary}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </section>
      ) : null}
      <Button
        type="button"
        size="lg"
        className="rounded-full shadow-lg shadow-black/20"
        onClick={() => setIsOpen((value) => !value)}
      >
        <Search className="h-4 w-4" aria-hidden="true" /> {t(language, "askQuestion")}
      </Button>
    </div>
  );
}
