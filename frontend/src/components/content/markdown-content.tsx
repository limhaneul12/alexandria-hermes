import type { ReactNode } from "react";

type Block =
  | { type: "heading"; level: 1 | 2 | 3; text: string }
  | { type: "paragraph"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "code"; language: string; code: string };

function safeHref(value: string) {
  const trimmed = value.trim();
  if (/^(https?:|mailto:|#)/i.test(trimmed)) return trimmed;
  return "#";
}

function inlineNodes(text: string, keyPrefix: string): ReactNode[] {
  const pattern = /(\[[^\]]+\]\([^\s)]+\)|`[^`]+`)/g;
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let index = 0;
  for (const match of text.matchAll(pattern)) {
    const matched = match[0];
    const offset = match.index ?? 0;
    if (offset > cursor) nodes.push(text.slice(cursor, offset));
    if (matched.startsWith("`")) {
      nodes.push(
        <code key={`${keyPrefix}-code-${index}`} className="rounded border border-[#cfc8b8] bg-[#eee9df] px-1 py-0.5 text-[0.92em] text-[#111111]">
          {matched.slice(1, -1)}
        </code>,
      );
    } else {
      const link = matched.match(/^\[([^\]]+)\]\(([^\s)]+)\)$/);
      if (link) {
        nodes.push(
          <a key={`${keyPrefix}-link-${index}`} href={safeHref(link[2])} className="font-semibold underline decoration-[#9c6f3b]/50 underline-offset-4" target={link[2].startsWith("#") ? undefined : "_blank"} rel={link[2].startsWith("#") ? undefined : "noreferrer"}>
            {link[1]}
          </a>,
        );
      }
    }
    cursor = offset + matched.length;
    index += 1;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

function parseMarkdown(content: string): Block[] {
  const blocks: Block[] = [];
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.match(/^```\s*([\w-]+)?\s*$/);
    if (fence) {
      const language = fence[1] ?? "text";
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !/^```\s*$/.test(lines[index] ?? "")) {
        codeLines.push(lines[index] ?? "");
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push({ type: "code", language, code: codeLines.join("\n") });
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length as 1 | 2 | 3, text: heading[2].trim() });
      index += 1;
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index] ?? "")) {
        items.push((lines[index] ?? "").replace(/^[-*]\s+/, "").trim());
        index += 1;
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index] ?? "")) {
        items.push((lines[index] ?? "").replace(/^\d+\.\s+/, "").trim());
        index += 1;
      }
      blocks.push({ type: "ol", items });
      continue;
    }

    const paragraph: string[] = [];
    while (
      index < lines.length &&
      lines[index]?.trim() &&
      !/^```/.test(lines[index] ?? "") &&
      !/^(#{1,3})\s+/.test(lines[index] ?? "") &&
      !/^[-*]\s+/.test(lines[index] ?? "") &&
      !/^\d+\.\s+/.test(lines[index] ?? "")
    ) {
      paragraph.push((lines[index] ?? "").trim());
      index += 1;
    }
    blocks.push({ type: "paragraph", text: paragraph.join(" ") });
  }

  return blocks;
}

export function MarkdownContent({ content, emptyLabel }: { content: string; emptyLabel: string }) {
  const blocks = parseMarkdown(content);
  if (!blocks.length) return <p className="text-sm text-[#6f6a60]">{emptyLabel}</p>;

  return (
    <div className="space-y-4 text-sm leading-7 text-[#36322d]">
      {blocks.map((block, index) => {
        const key = `${block.type}-${index}`;
        if (block.type === "heading") {
          const className = block.level === 1
            ? "font-serif text-3xl font-bold leading-tight text-[#111111]"
            : block.level === 2
              ? "font-serif text-2xl font-bold leading-tight text-[#111111]"
              : "text-lg font-bold text-[#111111]";
          const Heading = `h${block.level}` as "h1" | "h2" | "h3";
          return <Heading key={key} className={className}>{inlineNodes(block.text, key)}</Heading>;
        }
        if (block.type === "code") {
          return (
            <pre key={key} className="overflow-auto rounded-xl border border-[#d8d3c7] bg-[#111111] p-4 text-sm leading-6 text-[#f6f3ec]">
              <code data-language={block.language}>{block.code}</code>
            </pre>
          );
        }
        if (block.type === "ul") {
          return <ul key={key} className="list-disc space-y-2 pl-6">{block.items.map((item, itemIndex) => <li key={`${key}-${itemIndex}`}>{inlineNodes(item, `${key}-${itemIndex}`)}</li>)}</ul>;
        }
        if (block.type === "ol") {
          return <ol key={key} className="list-decimal space-y-2 pl-6">{block.items.map((item, itemIndex) => <li key={`${key}-${itemIndex}`}>{inlineNodes(item, `${key}-${itemIndex}`)}</li>)}</ol>;
        }
        return <p key={key}>{inlineNodes(block.text, key)}</p>;
      })}
    </div>
  );
}
