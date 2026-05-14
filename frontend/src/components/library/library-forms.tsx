"use client";

import type { ChangeEvent, FormEventHandler, ReactNode } from "react";
import { AlertTriangle, FileText, FolderPlus, ScrollText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { t } from "@/lib/i18n";
import type { CategoryOption, PromptDraft, SkillDraft } from "@/lib/library/forms";
import { useLibraryStore } from "@/store/library-store";
import { PROMPT_CONTENT_FORMATS, PROMPT_DOMAINS, PROMPT_KINDS, PROMPT_TASK_TYPES } from "@/types/library";

type CreateMode = "SKILL" | "PROMPT";

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function markdownPreview(value: string) {
  return escapeHtml(value || "Preview will appear here.")
    .replace(/^### (.*)$/gm, "<h4>$1</h4>")
    .replace(/^## (.*)$/gm, "<h3>$1</h3>")
    .replace(/^# (.*)$/gm, "<h2>$1</h2>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br />");
}

function promptWarnings(draft: PromptDraft): string[] {
  const warnings: string[] = [];
  if (!draft.title.trim()) warnings.push("제목이 비어 있습니다.");
  if (!draft.content.trim()) warnings.push("본문이 비어 있습니다.");
  if (draft.contentFormat === "JSON") {
    try { JSON.parse(draft.content); } catch { warnings.push("JSON 문법을 확인하세요."); }
  }
  if (draft.contentFormat === "XML" && draft.content.trim() && !/^<[^>]+>[\s\S]*<\/[^>]+>$/.test(draft.content.trim())) {
    warnings.push("XML은 여는 태그와 닫는 태그가 필요합니다.");
  }
  const variableNames = draft.variables.split(",").map((item) => item.split(":")[0]?.trim()).filter(Boolean);
  if (new Set(variableNames).size !== variableNames.length) warnings.push("중복된 변수명이 있습니다.");
  return warnings;
}

export function CategorySelect({
  label,
  value,
  options,
  emptyLabel,
  name,
  onChange,
}: {
  label: string;
  value: string;
  options: CategoryOption[];
  emptyLabel: string;
  name: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">
      {label}
      <select
        name={name}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="archive-select mt-2"
      >
        <option value="">{emptyLabel}</option>
        {options.map((category) => (
          <option key={category.id} value={category.id}>{category.label}</option>
        ))}
      </select>
    </label>
  );
}

export function FolderCreateForm({
  name,
  parentId,
  options,
  isPending,
  onNameChange,
  onParentChange,
  onSubmit,
}: {
  name: string;
  parentId: string;
  options: CategoryOption[];
  isPending: boolean;
  onNameChange: (value: string) => void;
  onParentChange: (value: string) => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
}) {
  const language = useLibraryStore((state) => state.language);

  return (
    <form onSubmit={onSubmit} className="archive-paper-card mb-6 space-y-4 p-5">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.22em] text-[#111111]">{t(language, "newFolder")}</p>
        <p className="mt-1 text-sm text-[#6f6a60]">{t(language, "folderCreateHelper")}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">
          {t(language, "folderName")}
          <Input name="folderName" autoComplete="off" value={name} onChange={(event) => onNameChange(event.target.value)} placeholder={t(language, "folderNamePlaceholder")} required className="mt-2" />
        </label>
        <CategorySelect label={t(language, "parentFolder")} name="parentFolder" value={parentId} options={options} emptyLabel={t(language, "rootFolder")} onChange={onParentChange} />
      </div>
      <Button type="submit" size="sm" disabled={isPending || !name.trim()}>
        <FolderPlus className="h-3.5 w-3.5" aria-hidden="true" /> {t(language, "createFolder")}
      </Button>
    </form>
  );
}

function FieldLabel({ children }: { children: ReactNode }) {
  return <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">{children}</span>;
}

function SkillFields({ draft, options, onDraftChange, onFileSelect }: {
  draft: SkillDraft;
  options: CategoryOption[];
  onDraftChange: (patch: Partial<SkillDraft>) => void;
  onFileSelect: (file: File) => void;
}) {
  const language = useLibraryStore((state) => state.language);
  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    onFileSelect(file);
    event.target.value = "";
  }
  return (
    <>
      <div className="archive-form-section lg:col-span-2">
        <p className="archive-form-section-title">01 · {t(language, "createBasics")}</p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <label className="block"><FieldLabel>{t(language, "skillTitle")}</FieldLabel><Input name="skillTitle" autoComplete="off" value={draft.title} onChange={(event) => onDraftChange({ title: event.target.value })} required className="mt-2" /></label>
          <CategorySelect label={t(language, "skillFolder")} name="skillFolder" value={draft.categoryId} options={options} emptyLabel={t(language, "uncategorized")} onChange={(categoryId) => onDraftChange({ categoryId })} />
          <label className="block lg:col-span-2"><FieldLabel>{t(language, "summary")}</FieldLabel><Input name="skillSummary" autoComplete="off" value={draft.summary} onChange={(event) => onDraftChange({ summary: event.target.value })} className="mt-2" /></label>
          <label className="block lg:col-span-2"><FieldLabel>{t(language, "purpose")}</FieldLabel><Input name="skillPurpose" autoComplete="off" value={draft.purpose} onChange={(event) => onDraftChange({ purpose: event.target.value })} required className="mt-2" /></label>
        </div>
      </div>
      <div className="archive-form-section lg:col-span-2">
        <p className="archive-form-section-title">02 · {t(language, "createContent")}</p>
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
          <label className="block"><FieldLabel>{t(language, "body")}</FieldLabel><textarea name="skillBody" value={draft.content} onChange={(event) => onDraftChange({ content: event.target.value })} required rows={12} className="mt-2 w-full rounded-md border border-[#cfc8b8] bg-white/70 px-3 py-2 text-sm text-[#111111] outline-none focus-visible:ring-2 focus-visible:ring-black/15" /></label>
          <div className="space-y-4">
            <label className="flex cursor-pointer flex-col gap-2 rounded-xl border border-dashed border-[#bfb6a8] bg-[#fbf8f0] p-4 text-sm text-[#514c44] transition-colors hover:border-[#111111]">
              <span className="flex items-center gap-2 font-semibold text-[#111111]"><FileText className="h-4 w-4" aria-hidden="true" /> {t(language, "uploadSkillFile")}</span>
              <span className="text-xs leading-5 text-[#6f6a60]">{t(language, "uploadSkillHint")}</span>
              <input name="skillFile" type="file" accept=".md,.markdown,.txt,text/markdown,text/plain" className="sr-only" onChange={handleFileChange} />
            </label>
            <label className="block"><FieldLabel>{t(language, "tags")}</FieldLabel><Input name="skillTags" autoComplete="off" value={draft.tags} onChange={(event) => onDraftChange({ tags: event.target.value })} placeholder="agent, backend" className="mt-2" /></label>
            <label className="flex items-center gap-2 text-sm text-[#36322d]"><input name="activateSkill" type="checkbox" checked={draft.activate} onChange={(event) => onDraftChange({ activate: event.target.checked })} className="h-4 w-4 accent-black" />{t(language, "activateImmediately")}</label>
          </div>
        </div>
      </div>
    </>
  );
}

function PromptFields({ draft, options, onDraftChange }: {
  draft: PromptDraft;
  options: CategoryOption[];
  onDraftChange: (patch: Partial<PromptDraft>) => void;
}) {
  const language = useLibraryStore((state) => state.language);
  const warnings = promptWarnings(draft);
  return (
    <>
      <div className="archive-form-section lg:col-span-2">
        <p className="archive-form-section-title">01 · {t(language, "createBasics")}</p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <label className="block"><FieldLabel>{t(language, "promptTitle")}</FieldLabel><Input name="promptTitle" autoComplete="off" value={draft.title} onChange={(event) => onDraftChange({ title: event.target.value })} required className="mt-2" /></label>
          <CategorySelect label={t(language, "skillFolder")} name="promptFolder" value={draft.categoryId} options={options} emptyLabel={t(language, "uncategorized")} onChange={(categoryId) => onDraftChange({ categoryId })} />
          <label className="block lg:col-span-2"><FieldLabel>{t(language, "summary")}</FieldLabel><Input name="promptSummary" autoComplete="off" value={draft.summary} onChange={(event) => onDraftChange({ summary: event.target.value })} className="mt-2" /></label>
        </div>
      </div>
      <div className="archive-form-section lg:col-span-2">
        <p className="archive-form-section-title">02 · {t(language, "promptMetadata")}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SelectField label={t(language, "promptKind")} value={draft.promptKind} values={PROMPT_KINDS} onChange={(value) => onDraftChange({ promptKind: value as PromptDraft["promptKind"] })} />
          <SelectField label={t(language, "contentFormat")} value={draft.contentFormat} values={PROMPT_CONTENT_FORMATS} onChange={(value) => onDraftChange({ contentFormat: value as PromptDraft["contentFormat"] })} />
          <SelectField label={t(language, "promptDomain")} value={draft.promptDomain} values={PROMPT_DOMAINS} onChange={(value) => onDraftChange({ promptDomain: value as PromptDraft["promptDomain"] })} />
          <SelectField label={t(language, "promptTaskType")} value={draft.promptTaskType} values={PROMPT_TASK_TYPES} onChange={(value) => onDraftChange({ promptTaskType: value as PromptDraft["promptTaskType"] })} />
          <label className="block"><FieldLabel>{t(language, "inputVariables")}</FieldLabel><Input name="promptVariables" autoComplete="off" value={draft.variables} onChange={(event) => onDraftChange({ variables: event.target.value })} placeholder="diff:required, context:optional" className="mt-2" /></label>
          <label className="block"><FieldLabel>{t(language, "targetActor")}</FieldLabel><Input name="targetActor" autoComplete="off" value={draft.targetActor} onChange={(event) => onDraftChange({ targetActor: event.target.value })} placeholder="Backend Agent" className="mt-2" /></label>
          <label className="block"><FieldLabel>{t(language, "outputFormat")}</FieldLabel><Input name="outputFormat" autoComplete="off" value={draft.outputFormat} onChange={(event) => onDraftChange({ outputFormat: event.target.value })} placeholder="bullet review" className="mt-2" /></label>
          <label className="block"><FieldLabel>{t(language, "targetModel")}</FieldLabel><Input name="targetModel" autoComplete="off" value={draft.targetModelFamily} onChange={(event) => onDraftChange({ targetModelFamily: event.target.value })} placeholder="OpenAI" className="mt-2" /></label>
        </div>
      </div>
      <div className="archive-form-section lg:col-span-2">
        <p className="archive-form-section-title">03 · {t(language, "createContent")}</p>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <label className="block"><FieldLabel>{t(language, "body")}</FieldLabel><textarea name="promptBody" value={draft.content} onChange={(event) => onDraftChange({ content: event.target.value })} required rows={14} className="mt-2 w-full rounded-md border border-[#cfc8b8] bg-white/70 px-3 py-2 font-mono text-sm text-[#111111] outline-none focus-visible:ring-2 focus-visible:ring-black/15" /></label>
          <div className="rounded-xl border border-[#d8d3c7] bg-[#fbf8f0] p-4 text-sm text-[#36322d]">
            <p className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[#111111]"><ScrollText className="h-4 w-4" aria-hidden="true" /> {t(language, "previewLint")}</p>
            {warnings.length > 0 ? <ul className="mb-4 space-y-1 text-xs text-[#8f5037]" aria-live="polite">{warnings.map((warning) => <li key={warning} className="flex gap-2"><AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />{warning}</li>)}</ul> : <p className="mb-4 text-xs text-[#2f6b44]" aria-live="polite">{t(language, "noSyntaxWarnings")}</p>}
            <div className="prose max-w-none text-[#36322d]" dangerouslySetInnerHTML={{ __html: markdownPreview(draft.content) }} />
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <label className="block"><FieldLabel>{t(language, "tags")}</FieldLabel><Input name="promptTags" autoComplete="off" value={draft.tags} onChange={(event) => onDraftChange({ tags: event.target.value })} placeholder="prompt, review" className="mt-2" /></label>
          <label className="block"><FieldLabel>{t(language, "createdBy")}</FieldLabel><Input name="promptCreatedBy" autoComplete="off" value={draft.createdByName} onChange={(event) => onDraftChange({ createdByName: event.target.value })} className="mt-2" /></label>
          <label className="mt-6 flex items-center gap-2 text-sm text-[#36322d]"><input name="activatePrompt" type="checkbox" checked={draft.activate} onChange={(event) => onDraftChange({ activate: event.target.checked })} className="h-4 w-4 accent-black" />{t(language, "activateImmediately")}</label>
        </div>
      </div>
    </>
  );
}

function SelectField({ label, value, values, onChange }: { label: string; value: string; values: readonly string[]; onChange: (value: string) => void }) {
  return (
    <label className="block"><FieldLabel>{label}</FieldLabel><select value={value} onChange={(event) => onChange(event.target.value)} className="archive-select mt-2">{values.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
  );
}

export function LibraryItemCreatePanel({
  mode,
  skillDraft,
  promptDraft,
  options,
  isPending,
  onModeChange,
  onSkillDraftChange,
  onPromptDraftChange,
  onSkillFileSelect,
  onSubmit,
}: {
  mode: CreateMode;
  skillDraft: SkillDraft;
  promptDraft: PromptDraft;
  options: CategoryOption[];
  isPending: boolean;
  onModeChange: (mode: CreateMode) => void;
  onSkillDraftChange: (patch: Partial<SkillDraft>) => void;
  onPromptDraftChange: (patch: Partial<PromptDraft>) => void;
  onSkillFileSelect: (file: File) => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
}) {
  const language = useLibraryStore((state) => state.language);
  const disabled = mode === "SKILL"
    ? !skillDraft.title.trim() || !skillDraft.content.trim() || !skillDraft.purpose.trim()
    : !promptDraft.title.trim() || !promptDraft.content.trim();
  return (
    <form onSubmit={onSubmit} className="archive-create-panel mb-6 overflow-hidden rounded-xl border border-[#cfc8b8] bg-[#f9f6ef]">
      <div className="grid border-b border-[#d8d3c7] lg:grid-cols-[270px_minmax(0,1fr)]">
        <aside className="border-b border-[#d8d3c7] bg-[#f0ebe1] p-6 lg:border-b-0 lg:border-r">
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-[#111111]">{t(language, "newAcquisition")}</p>
          <h2 className="mt-3 font-serif text-4xl leading-none text-[#111111]">{t(language, "newItem")}</h2>
          <p className="mt-4 text-sm leading-6 text-[#514c44]">{t(language, "createPanelDescription")}</p>
          <div className="mt-6 grid gap-2">
            {(["SKILL", "PROMPT"] as const).map((item) => (
              <button key={item} type="button" onClick={() => onModeChange(item)} className={`rounded-md border px-4 py-3 text-left text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/20 ${mode === item ? "border-[#111111] bg-[#111111] text-white" : "border-[#cfc8b8] bg-white/55 text-[#111111] hover:bg-white"}`}>{item === "SKILL" ? t(language, "skill") : t(language, "prompt")}</button>
            ))}
          </div>
        </aside>
        <div className="grid gap-5 p-6 lg:grid-cols-2">
          {mode === "SKILL" ? <SkillFields draft={skillDraft} options={options} onDraftChange={onSkillDraftChange} onFileSelect={onSkillFileSelect} /> : <PromptFields draft={promptDraft} options={options} onDraftChange={onPromptDraftChange} />}
        </div>
      </div>
      <div className="flex flex-col gap-3 bg-[#eee9df] px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-[#6f6a60]">{mode === "SKILL" ? t(language, "skillSaveHint") : t(language, "promptSaveHint")}</p>
        <Button type="submit" disabled={isPending || disabled}>{isPending ? t(language, "saving") : mode === "SKILL" ? t(language, "saveSkill") : t(language, "savePrompt")}</Button>
      </div>
    </form>
  );
}

export const SkillCreateForm = LibraryItemCreatePanel;
