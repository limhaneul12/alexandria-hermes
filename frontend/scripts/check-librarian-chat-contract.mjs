import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const chatBackend = readFileSync(new URL("../src/lib/backend/librarian-chat.ts", import.meta.url), "utf8");
const chatRoute = readFileSync(new URL("../src/app/api/librarians/chat/route.ts", import.meta.url), "utf8");
const chatClient = readFileSync(new URL("../src/components/librarian/librarian-chat-client.tsx", import.meta.url), "utf8");
const libraryTypes = readFileSync(new URL("../src/types/library.ts", import.meta.url), "utf8");

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
  /function delegateCompletedAnswer/,
  "chat orchestration must build the visible answer from completed delegate summaries",
);
assert.match(
  chatBackend,
  /filter\(\(delegate\) => delegate\.status === "COMPLETED"\)[\s\S]*delegate\.summary\.trim\(\)/,
  "completed librarian chat answers must surface completed delegate summaries",
);
assert.doesNotMatch(
  chatBackend,
  /answer:\s*askResponse\.recommendation/,
  "completed librarian chat answers must not show only the generic recommendation",
);
assert.match(
  chatBackend,
  /검색된 후보 총계:\s*\$\{totalCount\}개입니다/,
  "completed librarian chat answers must include the real direct-search total as evidence",
);
assert.match(
  chatBackend,
  /function isInventoryQuestion/,
  "chat orchestration must distinguish inventory/count questions from semantic search questions",
);
assert.match(
  chatBackend,
  /function isMemoryStatusQuestion/,
  "chat orchestration must distinguish memory status questions from delegate requests",
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
assert.match(
  chatBackend,
  /function platformInventoryAnswer/,
  "librarian chat must answer platform inventory questions directly",
);
assert.match(
  chatBackend,
  /if \(memoryStatusMode \|\| inventoryMode\)/,
  "inventory and memory-status questions must bypass librarian delegation",
);
assert.match(
  chatBackend,
  /Context Vault 장기기억: \$\{contextBucket\.totalCount\}건/,
  "memory inventory answers must report Context Vault totals",
);
assert.match(
  chatBackend,
  /Memory Compacts: \$\{compactBucket\.totalCount\}건/,
  "memory inventory answers must report Memory Compact totals",
);
assert.match(
  chatBackend,
  /current Memory Compact/,
  "memory inventory answers must include current compact context",
);
assert.doesNotMatch(
  chatBackend,
  /No delegate lanes returned|사서 delegate 미완료|Delegate evidence/,
  "librarian chat must not expose raw delegate failure wording",
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
  /function uniqueDirectHits/,
  "librarian chat must collapse duplicate direct hits before the UI renders React keys",
);
assert.match(
  chatBackend,
  /const directHits = uniqueDirectHits\([\s\S]*flatMap\(\(bucket\) => bucket\.hits\)[\s\S]*\)\.slice/,
  "direct librarian search visible hits must be deduplicated before slicing",
);
assert.match(
  chatBackend,
  /sourceRefs = uniqueSourceRefs\(directHits\.map\(sourceRefFromHit\)\)/,
  "source refs must be deduplicated even when no current compact is available",
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
assert.match(
  libraryTypes,
  /type LibrarianChatRequestDTO[\s\S]*librarianProfileId\?: string \| null/,
  "librarian chat requests must carry an optional selected librarian profile",
);
assert.match(
  chatClient,
  /fetchAgents/,
  "librarian chat UI must load saved librarian profiles for selection",
);
assert.match(
  chatClient,
  /사서 선택/,
  "librarian chat UI must expose a natural librarian selector",
);
assert.match(
  chatClient,
  /플랫폼 기억과 근거/,
  "librarian chat UI must describe the librarian as using platform memory",
);
assert.match(
  chatClient,
  /aria-label="사서 선택"/,
  "librarian chat UI must keep only the librarian selector as the user-facing control",
);
assert.match(
  chatClient,
  /SlidersHorizontal/,
  "librarian chat selector group must use the shared selection affordance icon",
);
assert.match(
  chatClient,
  /선택 초기화/,
  "librarian chat selector must support resetting the selected librarian",
);
assert.doesNotMatch(
  chatClient,
  /검색 대상|실행 모드|필터링|필터 초기화|targets:/,
  "librarian chat UI must not expose mode or search-target filters",
);
assert.doesNotMatch(
  chatClient,
  /실행\/CLI 요약|executionSummary\.map|backend orchestration/,
  "librarian chat UI must not expose internal execution summaries",
);
assert.match(
  chatClient,
  /librarianProfileId: selectedLibrarian\?\.id/,
  "librarian chat UI must submit the selected librarian profile id",
);
assert.match(
  chatBackend,
  /librarianProfileId: request\.librarianProfileId/,
  "chat orchestration must forward the selected librarian profile to backend ask",
);
assert.match(
  chatBackend,
  /selectedLibrarianRolePrompt/,
  "chat orchestration must preserve selected profile role prompt while appending platform guardrails",
);
assert.doesNotMatch(
  chatBackend,
  /function isMemoryCompactAction/,
  "librarian chat must not use frontend/server-adapter regexes for memory compact action detection",
);
assert.doesNotMatch(
  chatBackend,
  /prepareCompactInBackend/,
  "memory compact actions must not create compact contexts in the frontend server adapter",
);
assert.doesNotMatch(
  chatBackend,
  /createMemoryCompactInBackend/,
  "memory compact actions must not save artifacts from the frontend server adapter",
);
assert.match(
  chatBackend,
  /contextCompact:\s*currentCompact/,
  "librarian chat must pass current Memory Compact through the backend librarian knowledge packet",
);
assert.match(
  chatBackend,
  /loadCurrentMemoryCompactForLibrarian/,
  "librarian chat must load the current compact as evidence instead of compacting locally",
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
