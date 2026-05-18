import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const chatBackend = readFileSync(new URL("../src/lib/backend/librarian-chat.ts", import.meta.url), "utf8");
const chatRoute = readFileSync(new URL("../src/app/api/librarians/chat/route.ts", import.meta.url), "utf8");
const chatClient = readFileSync(new URL("../src/components/librarian/librarian-chat-client.tsx", import.meta.url), "utf8");

assert.match(
  chatRoute,
  /chatWithLibrarianInBackend/,
  "/api/librarians/chat must use the server-side chat orchestrator",
);
assert.match(
  chatBackend,
  /response\.status === "COMPLETED"[\s\S]*delegate\.status === "COMPLETED"/,
  "chat orchestration must require a completed top-level ask and completed delegate",
);
assert.match(
  chatBackend,
  /delegatedJobId:\s*null/,
  "chat orchestration must not expose a delegated job id when delegation did not complete",
);
assert.match(
  chatBackend,
  /delegateFailureAnswer/,
  "chat orchestration must surface skipped delegate evidence to the UI",
);
assert.match(
  chatBackend,
  /function isInventoryQuestion/,
  "chat orchestration must distinguish inventory/count questions from semantic search questions",
);
assert.match(
  chatBackend,
  /if \(inventoryMode\) \{[\s\S]*loadContextsFromBackend\(new URLSearchParams/,
  "context inventory/count answers must preserve the backend context list total",
);
assert.match(
  chatBackend,
  /if \(inventoryMode\) \{[\s\S]*const hits = contextList\.items\.map/,
  "context inventory/count representative items must come from the same list source as the total",
);
assert.match(
  chatBackend,
  /searchContextsInBackend\(\{[\s\S]*query: prompt/,
  "ordinary context search must still use prompt-based retrieval",
);
assert.match(
  chatBackend,
  /searchContextTargets\(request\.prompt, targets, limit, inventoryMode\)/,
  "chat orchestration must pass inventory mode explicitly into context search",
);
assert.match(
  chatBackend,
  /return \{ hits, totalCount: contextList\.total \};/,
  "context inventory/count answers must derive totals from the list response total",
);
assert.doesNotMatch(
  chatBackend,
  /direct_total_count|direct_hits|delegated_job|delegation_status|query=|targets=/,
  "ordinary librarian execution summaries must not expose raw implementation identifiers",
);
assert.match(
  chatBackend,
  /directTotalCount = searchBuckets\.reduce/,
  "direct librarian search answers must aggregate real total counts across buckets",
);
assert.match(
  chatBackend,
  /검색된 직접 후보는 총 \$\{totalCount\}개/,
  "direct librarian search answers must show the real total count",
);
assert.doesNotMatch(
  chatBackend,
  /검색된 직접 후보는 총 \$\{hits\.length\}개/,
  "direct librarian search answers must not treat visible hits as the total count",
);
assert.match(
  chatBackend,
  /hits\.slice\(0, 5\)/,
  "direct librarian search answers must show only five items by default",
);
assert.match(
  chatBackend,
  /상위 5개만 먼저 보여드릴게요/,
  "direct librarian search answers must explain the five-item preview in user language",
);
assert.doesNotMatch(
  chatBackend,
  /limit을 높이거나/,
  "ordinary librarian answers must not expose parameter/endpoint language",
);
assert.match(
  chatBackend,
  /관련 라이브러리에서 검색 결과를 더 펼쳐/,
  "direct librarian search answers must guide continuation in natural product language",
);
assert.match(
  chatBackend,
  /## 목록/,
  "direct librarian search answers must include a visible result list",
);
assert.match(
  chatBackend,
  /function delegateInventoryContext/,
  "delegated librarian answers must receive an inventory context builder",
);
assert.match(
  chatBackend,
  /Direct search inventory total count:\s*\$\{totalCount\}/,
  "delegated librarian answers must receive the real total count",
);
assert.match(
  chatBackend,
  /Visible top 5 representative items for count\/list\/inventory answers/,
  "delegated librarian answers must receive the top-five representative list",
);
assert.match(
  chatBackend,
  /taskSummary:\s*`\$\{request\.prompt\}\\n\\n\$\{inventoryContext\}`/,
  "delegated librarian task summary must include total-count and top-five context",
);
assert.doesNotMatch(
  chatBackend,
  /Direct search hits: \$\{directHits\.length\}/,
  "delegated librarian task summary must not treat visible hits as total count",
);
assert.match(
  chatBackend,
  /Do not expose raw API routes/,
  "delegated librarian prompts must hide raw implementation routes from ordinary answers",
);

assert.doesNotMatch(
  chatClient,
  /\{ref\.detailPath\}/,
  "ordinary source-ref UI must not print raw frontend/backend paths",
);
assert.doesNotMatch(
  chatClient,
  /\{ref\.sourceType\} · \{ref\.sourceId\}/,
  "ordinary source-ref UI must not print implementation source ids",
);
assert.match(
  chatClient,
  /function sourceRefLabel/,
  "ordinary source-ref UI must map source types to natural labels",
);
assert.match(
  chatClient,
  /sourceRefLabel\(hit\.sourceType\)/,
  "direct-hit UI must render natural source-type labels",
);
assert.match(
  chatClient,
  /sourceRefLabel\(ref\.sourceType\)/,
  "source-ref UI must render natural source-type labels",
);
assert.doesNotMatch(
  chatClient,
  />\{hit\.sourceType\}</,
  "direct-hit UI must not print enum-like source types",
);
assert.doesNotMatch(
  chatClient,
  />\{ref\.sourceType\}</,
  "source-ref UI must not print enum-like source types",
);

console.log("librarian chat delegation contract ok");
