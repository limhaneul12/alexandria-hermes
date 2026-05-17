import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const viewer = readFileSync(new URL("../src/components/content/content-viewer.tsx", import.meta.url), "utf8");
const markdown = readFileSync(new URL("../src/components/content/markdown-content.tsx", import.meta.url), "utf8");
const contextDetail = readFileSync(new URL("../src/components/context/context-detail-client.tsx", import.meta.url), "utf8");
const skillDetail = readFileSync(new URL("../src/components/skill/skill-detail-client.tsx", import.meta.url), "utf8");

assert.match(viewer, /원본보기 Raw/, "ContentViewer must expose raw source label");
assert.match(viewer, /보기/, "ContentViewer must expose rendered label");
assert.doesNotMatch(`${viewer}\n${markdown}`, /dangerouslySetInnerHTML/, "ContentViewer must not use unsafe HTML injection");
assert.match(markdown, /```/, "MarkdownContent must parse fenced code blocks");
assert.match(markdown, /role|list-disc|list-decimal/, "MarkdownContent must render list-like markdown structures");
assert.match(contextDetail, /<ContentViewer content=\{context\.content\}/, "Context detail must use ContentViewer");
assert.match(skillDetail, /<ContentViewer content=\{item\.content\}/, "Skill detail must use ContentViewer");
assert.match(skillDetail, /<ContentViewer content=\{data\.content\}/, "Prompt detail must use ContentViewer");

console.log("content viewer contract ok");
