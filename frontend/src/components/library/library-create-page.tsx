"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { LibraryItemCreatePanel } from "@/components/library/library-forms";
import { Card } from "@/components/ui/card";
import { createPrompt, createSkill, fetchLibrary } from "@/lib/api";
import {
  buildPromptCreatePayload,
  buildSkillCreatePayload,
  flattenCategoryOptions,
  initialPromptDraft,
  initialSkillDraft,
  type PromptDraft,
  type SkillDraft,
} from "@/lib/library/forms";
import { t } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";

type CreateMode = "SKILL" | "PROMPT";

export function LibraryCreatePage({ mode }: { mode: CreateMode }) {
  const language = useLibraryStore((state) => state.language);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [skillDraft, setSkillDraft] = useState<SkillDraft>(() => initialSkillDraft());
  const [promptDraft, setPromptDraft] = useState<PromptDraft>(() => initialPromptDraft());
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const libraryQuery = useQuery({
    queryKey: ["library", "create-options"],
    queryFn: () => fetchLibrary(new URLSearchParams({ limit: "1" })),
  });
  const categoryOptions = useMemo(
    () => flattenCategoryOptions(libraryQuery.data?.categories ?? []),
    [libraryQuery.data?.categories],
  );

  const createItemMutation = useMutation({
    mutationFn: () => mode === "SKILL"
      ? createSkill(buildSkillCreatePayload(skillDraft))
      : createPrompt(buildPromptCreatePayload(promptDraft)),
    onSuccess: () => {
      setSkillDraft(initialSkillDraft());
      setPromptDraft(initialPromptDraft());
      void queryClient.invalidateQueries({ queryKey: ["library"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      router.push(mode === "SKILL" ? "/library/skills" : "/library/prompts", { scroll: false });
    },
    onError: () => setStatusMessage(mode === "SKILL" ? t(language, "skillCreateFailed") : t(language, "promptCreateFailed")),
  });

  function handleCreateItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createItemMutation.mutate();
  }

  function handleSkillFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const content = typeof reader.result === "string" ? reader.result : "";
      const titleFromFile = file.name.replace(/\.(md|markdown|txt)$/i, "").replace(/[-_]+/g, " ").trim();
      setSkillDraft((draft) => ({
        ...draft,
        title: draft.title || titleFromFile,
        summary: draft.summary || content.split("\n").find((line) => line.trim() && !line.trim().startsWith("#"))?.trim() || "",
        purpose: draft.purpose || titleFromFile,
        content,
      }));
    };
    reader.readAsText(file);
  }

  function switchMode(nextMode: CreateMode) {
    if (nextMode !== mode) {
      router.push(nextMode === "SKILL" ? "/library/skills/new" : "/library/prompts/new", { scroll: false });
    }
  }

  return (
    <div className="archive-document-page min-h-[calc(100vh-74px)] px-8 py-10 md:px-14 xl:px-16">
      <section className="mb-7 border-b border-[#cfc8b8] pb-7">
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#161616]">{mode === "SKILL" ? "New Skill" : "New Prompt"}</p>
        <h1 className="mt-4 font-serif text-6xl font-bold leading-none tracking-[-0.055em] text-[#050505] md:text-7xl">
          {mode === "SKILL" ? t(language, "createSkill") : t(language, "createPrompt")}
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-[#36322d]">
          생성 상태는 이 전용 route에만 보관됩니다. 내 서재·내 스킬·내 프롬프트로 이동하면 draft UI가 남지 않습니다.
        </p>
      </section>

      {libraryQuery.isError ? (
        <Card className="mb-6 p-5 text-sm text-[#8f5037]">서재 폴더 정보를 불러오지 못했습니다.</Card>
      ) : null}
      {statusMessage ? <p className="archive-inline-status mb-6">{statusMessage}</p> : null}

      <LibraryItemCreatePanel
        mode={mode}
        skillDraft={skillDraft}
        promptDraft={promptDraft}
        options={categoryOptions}
        isPending={createItemMutation.isPending || libraryQuery.isLoading}
        onModeChange={switchMode}
        onSkillDraftChange={(patch) => setSkillDraft((draft) => ({ ...draft, ...patch }))}
        onPromptDraftChange={(patch) => setPromptDraft((draft) => ({ ...draft, ...patch }))}
        onSkillFileSelect={handleSkillFile}
        onSubmit={handleCreateItem}
      />
    </div>
  );
}
