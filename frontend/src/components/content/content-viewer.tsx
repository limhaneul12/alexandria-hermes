"use client";

import { useState } from "react";

import { MarkdownContent } from "@/components/content/markdown-content";
import { Button } from "@/components/ui/button";
import { t } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";

type ContentViewerProps = {
  title?: string;
  content: string;
  defaultMode?: "rendered" | "raw";
  rawLabel?: string;
  renderedLabel?: string;
};

export function ContentViewer({
  title,
  content,
  defaultMode = "rendered",
  rawLabel,
  renderedLabel,
}: ContentViewerProps) {
  const language = useLibraryStore((state) => state.language);
  const [mode, setMode] = useState<"rendered" | "raw">(defaultMode);
  const resolvedRawLabel = rawLabel ?? t(language, "rawView");
  const resolvedRenderedLabel = renderedLabel ?? t(language, "renderedView");

  return (
    <section className="rounded-xl border border-[#d8d3c7] bg-white/62 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        {title ? <h2 className="font-serif text-2xl font-bold text-[#111111]">{title}</h2> : <span />}
        <div className="flex rounded-lg border border-[#d8d3c7] bg-[#eee9df] p-1">
          <Button type="button" size="sm" variant={mode === "rendered" ? "default" : "ghost"} onClick={() => setMode("rendered")}>
            {resolvedRenderedLabel}
          </Button>
          <Button type="button" size="sm" variant={mode === "raw" ? "default" : "ghost"} onClick={() => setMode("raw")}>
            {resolvedRawLabel}
          </Button>
        </div>
      </div>
      {mode === "raw" ? (
        <pre className="max-h-[620px] overflow-auto whitespace-pre-wrap rounded-xl border border-[#d8d3c7] bg-[#fbf8f0] p-4 text-sm leading-7 text-[#36322d]">
          <code>{content}</code>
        </pre>
      ) : (
        <MarkdownContent content={content} emptyLabel={t(language, "markdownContentEmpty")} />
      )}
    </section>
  );
}
