import { backendFetch } from "@/lib/backend/client";
import { askLibrarianInBackend } from "@/lib/backend/librarians";
import {
  createMemoryCompactInBackend,
  loadMemoryCompactsFromBackend,
} from "@/lib/backend/memory-compacts";
import {
  loadContextsFromBackend,
  prepareCompactInBackend,
  searchContextsInBackend,
} from "@/lib/backend/contexts";
import type {
  ContextDTO,
  ItemStatus,
  ItemType,
  LibrarianChatRequestDTO,
  LibrarianChatResponseDTO,
  LibrarianDirectHitDTO,
  LibrarianSourceRefDTO,
  MemoryCompactCreateSourceRefDTO,
  MemoryCompactDTO,
} from "@/types/library";

type BackendSearchHit = {
  id: string;
  item_type: ItemType;
  title: string;
  summary: string | null;
  tags: string[];
  status: ItemStatus;
  category_id: string | null;
  score: number;
  why_matched: string[];
  highlights: string[];
  details_preview: Record<string, unknown>;
  content_char_count: number;
  updated_at: string;
};

type BackendSearchResponse = {
  items: BackendSearchHit[];
  total: number;
  limit: number;
  offset: number;
};

type BackendCategory = {
  id: string;
  name: string;
};

type DirectSearchBucket = {
  hits: LibrarianDirectHitDTO[];
  totalCount: number;
};

const EMPTY_DIRECT_SEARCH_BUCKET: DirectSearchBucket = {
  hits: [],
  totalCount: 0,
};

const LIBRARIAN_ACTION_PROJECT = "alexandria-hermes";

const PLATFORM_TOOL_INSTRUCTIONS = [
  "You are connected to Alexandria-Hermes.",
  "Use the provided direct search hits and source refs first.",
  "If a user asks count/list/inventory questions, answer with the total count first and show only the top 5 representative items by default.",
  "Do not expose raw API routes, backend endpoints, frontend paths, headers, or implementation-only identifiers unless the user explicitly asks for API details.",
  "Guide continuation in natural product language, such as asking to show more results or opening the relevant library view.",
  "If additional lookup is needed, use available Alexandria CLI/MCP/search tools where exposed by the runtime.",
  "Do not claim there is no platform access unless a tool/search call failed.",
  "Report which search targets and queries were used without exposing raw routes.",
].join("\n");

function clampLimit(value: number) {
  return Math.min(Math.max(Math.trunc(value || 5), 1), 10);
}

function toSourceType(itemType: ItemType): LibrarianSourceRefDTO["sourceType"] {
  if (itemType === "PROMPT") return "PROMPT";
  if (itemType === "SKILL") return "SKILL";
  return "LIBRARY_ITEM";
}

function sourceRefFromHit(hit: LibrarianDirectHitDTO): LibrarianSourceRefDTO {
  return {
    sourceType: hit.sourceType,
    sourceId: hit.id,
    title: hit.title,
    detailPath: hit.detailPath,
    preview: hit.preview,
  };
}

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9가-힣]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

async function categorySlugForHit(
  hit: BackendSearchHit,
  categorySlugCache: Map<string, Promise<string>>,
): Promise<string> {
  if (!hit.category_id) return "uncategorized";
  const cached = categorySlugCache.get(hit.category_id);
  if (cached) return cached;
  const slugPromise = backendFetch<BackendCategory>(`/library/categories/${encodeURIComponent(hit.category_id)}`)
    .then((category) => {
      const slug = slugify(category.name);
      return slug ? `${slug}-${category.id.slice(0, 8)}` : category.id;
    })
    .catch(() => "uncategorized");
  categorySlugCache.set(hit.category_id, slugPromise);
  return slugPromise;
}

async function searchLibraryTargets(
  prompt: string,
  targets: LibrarianChatRequestDTO["targets"],
  limit: number,
): Promise<DirectSearchBucket> {
  const itemTypes = targets.filter((target) => target === "SKILL" || target === "PROMPT");
  if (itemTypes.length === 0) return EMPTY_DIRECT_SEARCH_BUCKET;
  const params = new URLSearchParams({
    q: prompt,
    limit: String(limit),
    offset: "0",
    content_mode: "candidate",
  });
  for (const itemType of itemTypes) params.append("item_types", itemType);
  const response = await backendFetch<BackendSearchResponse>(`/library/search?${params.toString()}`);
  const categorySlugCache = new Map<string, Promise<string>>();
  const hits = await Promise.all(
    response.items.map(async (hit) => {
      const categorySlug = await categorySlugForHit(hit, categorySlugCache);
      return {
        id: hit.id,
        sourceType: toSourceType(hit.item_type),
        title: hit.title,
        preview: hit.summary ?? hit.highlights[0] ?? "No preview available.",
        detailPath: `/library/${categorySlug}/${encodeURIComponent(hit.id)}`,
        score: hit.score,
      };
    }),
  );
  return { hits, totalCount: response.total };
}

function isInventoryQuestion(prompt: string): boolean {
  const normalized = prompt.toLowerCase();
  return /몇\s*개|개수|총\s*몇|전체\s*몇|목록|리스트|대표\s*목록|inventory|count|how many|list/.test(normalized);
}

async function searchContextTargets(
  prompt: string,
  targets: LibrarianChatRequestDTO["targets"],
  limit: number,
  inventoryMode: boolean,
): Promise<DirectSearchBucket> {
  if (!targets.includes("CONTEXT")) return EMPTY_DIRECT_SEARCH_BUCKET;
  if (inventoryMode) {
    const contextList = await loadContextsFromBackend(new URLSearchParams({ limit: String(limit), offset: "0" }));
    const hits = contextList.items.map((context) => ({
      id: context.id,
      sourceType: "CONTEXT" as const,
      title: context.title,
      preview: context.summary,
      detailPath: `/memory/contexts/${context.id}`,
      score: 1,
    }));
    return { hits, totalCount: contextList.total };
  }
  const contextPack = await searchContextsInBackend({
    query: prompt,
    strategy: "HYBRID",
    limit,
    project: null,
    kind: null,
  });
  const hits = contextPack.matches.map((match) => ({
    id: match.context.id,
    sourceType: "CONTEXT" as const,
    title: match.context.title,
    preview: match.context.summary || match.chunk.content.slice(0, 240),
    detailPath: `/memory/contexts/${match.context.id}`,
    score: match.score,
  }));
  return { hits, totalCount: hits.length };
}

async function searchMemoryCompactTargets(
  targets: LibrarianChatRequestDTO["targets"],
  limit: number,
): Promise<DirectSearchBucket> {
  if (!targets.includes("MEMORY_COMPACT")) return EMPTY_DIRECT_SEARCH_BUCKET;
  const compacts = await loadMemoryCompactsFromBackend(new URLSearchParams({ limit: String(limit) }));
  const hits = compacts.items.map((compact) => ({
    id: compact.id,
    sourceType: "MEMORY_COMPACT" as const,
    title: compact.project ? `Memory Compact · ${compact.project}` : "Memory Compact · default",
    preview: compact.markdownBody.slice(0, 240),
    detailPath: `/memory/compacts/${compact.id}`,
    score: compact.status === "CURRENT" ? 1 : 0.5,
  }));
  return { hits, totalCount: compacts.total };
}

function sourceTypeLabel(sourceType: LibrarianDirectHitDTO["sourceType"]): string {
  if (sourceType === "SKILL") return "스킬";
  if (sourceType === "PROMPT") return "프롬프트";
  if (sourceType === "CONTEXT") return "컨텍스트";
  if (sourceType === "MEMORY_COMPACT") return "기억 요약본";
  return "라이브러리 항목";
}

function targetLabel(target: LibrarianChatRequestDTO["targets"][number]): string {
  if (target === "SKILL") return "스킬";
  if (target === "PROMPT") return "프롬프트";
  if (target === "CONTEXT") return "컨텍스트";
  if (target === "MEMORY_COMPACT") return "기억 요약본";
  return "라이브러리 항목";
}

function modeLabel(mode: LibrarianChatRequestDTO["mode"]): string {
  if (mode === "DIRECT_SEARCH") return "직접 검색";
  if (mode === "DELEGATE") return "사서 위임";
  return "검색 후 사서 위임";
}

function selectedLibrarianLabel(request: LibrarianChatRequestDTO): string {
  if (request.librarianProfileName) return `선택 사서: ${request.librarianProfileName}`;
  if (request.librarianProfileId) return `선택 사서: ${request.librarianProfileId}`;
  if (request.providerId) return `선택 provider: ${request.providerId}`;
  return "선택 사서: 자동 라우팅";
}

function selectedLibrarianRolePrompt(request: LibrarianChatRequestDTO): string {
  const profilePrompt = request.librarianRolePrompt?.trim();
  if (!profilePrompt) return PLATFORM_TOOL_INSTRUCTIONS;
  return [profilePrompt, PLATFORM_TOOL_INSTRUCTIONS].join("\n\n");
}

function summarizeHitCounts(hits: LibrarianDirectHitDTO[]): string {
  const counts = hits.reduce<Record<string, number>>((accumulator, hit) => {
    const label = sourceTypeLabel(hit.sourceType);
    accumulator[label] = (accumulator[label] ?? 0) + 1;
    return accumulator;
  }, {});
  return Object.entries(counts)
    .map(([sourceType, count]) => `${sourceType} ${count}`)
    .join(", ");
}

function directSearchAnswer(hits: LibrarianDirectHitDTO[], totalCount: number, prompt: string) {
  if (totalCount === 0) {
    return `# 사서 검색 결과\n\n질문: ${prompt}\n\n직접 검색 후보를 찾지 못했습니다. 검색어를 바꾸거나 사서 위임 모드를 사용하세요.`;
  }
  const visibleHits = hits.slice(0, 5);
  const hiddenCount = Math.max(totalCount - visibleHits.length, 0);
  return [
    "# 사서 검색 결과",
    "",
    `질문: ${prompt}`,
    "",
    `## 답변\n검색된 직접 후보는 총 ${totalCount}개입니다. (상위 후보 기준: ${summarizeHitCounts(hits)})`,
    "",
    "상위 5개만 먼저 보여드릴게요.",
    "",
    "## 목록",
    ...visibleHits.map((hit, index) => `${index + 1}. **${hit.title}** (${sourceTypeLabel(hit.sourceType)}) — ${hit.preview}`),
    ...(hiddenCount > 0 ? ["", `나머지 ${hiddenCount}개는 관련 라이브러리에서 검색 결과를 더 펼쳐 확인할 수 있어요. 원하면 “전체 목록 보여줘”라고 말해 주세요.`] : []),
  ].join("\n");
}

function delegateInventoryContext(hits: LibrarianDirectHitDTO[], totalCount: number): string {
  if (totalCount === 0) {
    return "Direct search inventory: total 0 candidates.";
  }
  const visibleHits = hits.slice(0, 5);
  const lines = [
    `Direct search inventory total count: ${totalCount}.`,
    "Visible top 5 representative items for count/list/inventory answers:",
    ...visibleHits.map(
      (hit, index) => `${index + 1}. ${hit.title} (${sourceTypeLabel(hit.sourceType)}) — ${hit.preview}`,
    ),
  ];
  const hiddenCount = Math.max(totalCount - visibleHits.length, 0);
  if (hiddenCount > 0) {
    lines.push(
      `Remaining candidates not shown: ${hiddenCount}. Guide the user in natural product language to expand the relevant library results; do not expose routes or endpoints.`,
    );
  }
  return lines.join("\n");
}

function isMemoryCompactAction(prompt: string): boolean {
  const normalized = prompt.toLowerCase();
  const mentionsCompact = /(?:memory|메모리|장기기억)(?:\s*(?:memory|메모리))?\s*comp(?:act|ect)|메모리\s*(?:컴팩트|컴팩|압축|요약)|장기기억\s*(?:컴팩트|컴팩|압축|요약)/.test(normalized);
  const hasActionVerb = /해줘|해주세요|만들|생성|저장|압축|요약|create|save|prepare|run|execute/.test(normalized);
  return mentionsCompact && hasActionVerb;
}

function compactCoverageWindow() {
  const coveredTo = new Date();
  const coveredFrom = new Date(coveredTo.getTime() - 60_000);
  return {
    coveredFrom: coveredFrom.toISOString(),
    coveredTo: coveredTo.toISOString(),
  };
}

function sourceRefFromContext(context: ContextDTO): LibrarianSourceRefDTO {
  return {
    sourceType: "CONTEXT",
    sourceId: context.id,
    title: context.title,
    detailPath: `/memory/contexts/${context.id}`,
    preview: context.summary,
  };
}

function sourceRefFromCompact(compact: MemoryCompactDTO): LibrarianSourceRefDTO {
  return {
    sourceType: "MEMORY_COMPACT",
    sourceId: compact.id,
    title: compact.project ? `Memory Compact · ${compact.project}` : "Memory Compact · default",
    detailPath: `/memory/compacts/${compact.id}`,
    preview: compact.markdownBody.slice(0, 240),
  };
}

function directHitFromCompact(compact: MemoryCompactDTO): LibrarianDirectHitDTO {
  const ref = sourceRefFromCompact(compact);
  return {
    id: compact.id,
    sourceType: "MEMORY_COMPACT",
    title: ref.title,
    preview: ref.preview ?? "Memory Compact created by AI Librarian action.",
    detailPath: ref.detailPath,
    score: 1,
  };
}

function compactCreateSourceRefs(
  sourceRefs: LibrarianSourceRefDTO[],
): MemoryCompactCreateSourceRefDTO[] {
  const uniqueRefs = new Map<string, MemoryCompactCreateSourceRefDTO>();
  for (const ref of sourceRefs) {
    const key = `${ref.sourceType}:${ref.sourceId}`;
    if (uniqueRefs.has(key)) continue;
    uniqueRefs.set(key, {
      sourceType: ref.sourceType,
      sourceId: ref.sourceId,
      title: ref.title,
      detailPath: ref.detailPath,
    });
  }
  return [...uniqueRefs.values()];
}

function memoryCompactActionAnswer({
  prompt,
  compact,
  compactContext,
  totalCount,
  visibleHits,
}: {
  prompt: string;
  compact: MemoryCompactDTO;
  compactContext: ContextDTO;
  totalCount: number;
  visibleHits: LibrarianDirectHitDTO[];
}) {
  return [
    "# 사서 작업 완료",
    "",
    `질문/명령: ${prompt}`,
    "",
    "## 수행한 기능",
    "- 장기기억 Compact Context를 생성했습니다.",
    "- 생성된 내용을 Memory Compact로 저장했습니다.",
    `- Memory Compact 상태를 **${compact.status}**로 설정했습니다.`,
    "",
    "## 생성 결과",
    `- Memory Compact: **${compact.project ? `Memory Compact · ${compact.project}` : "Memory Compact · default"}**`,
    `- 연결된 source refs: **${compact.sourceRefs.length}개**`,
    `- Compact Context: **${compactContext.title}**`,
    "",
    "## 포함한 근거",
    `직접 검색으로 확인한 후보 총계는 ${totalCount}개입니다.`,
    ...(visibleHits.length
      ? [
          "",
          "상위 근거:",
          ...visibleHits.map(
            (hit, index) => `${index + 1}. **${hit.title}** (${sourceTypeLabel(hit.sourceType)}) — ${hit.preview}`,
          ),
        ]
      : ["", "직접 검색 후보가 없어 이번 실행 기록 자체를 source ref로 묶었습니다."]),
    "",
    "이제 Memory Compacts 화면에서 방금 만든 요약본을 열어 확인할 수 있어요.",
  ].join("\n");
}

function memoryCompactActionFailureAnswer(prompt: string) {
  return [
    "# 사서 작업 실패",
    "",
    `질문/명령: ${prompt}`,
    "",
    "Memory Compact 생성 작업을 실행했지만 저장까지 완료하지 못했습니다.",
    "잠시 후 다시 실행하거나, 장기기억/Memory Compact 저장소 상태를 확인해 주세요.",
  ].join("\n");
}

async function runMemoryCompactAction({
  prompt,
  directHits,
  sourceRefs,
  totalCount,
}: {
  prompt: string;
  directHits: LibrarianDirectHitDTO[];
  sourceRefs: LibrarianSourceRefDTO[];
  totalCount: number;
}) {
  const visibleHits = directHits.slice(0, 5);
  const compactContext = await prepareCompactInBackend({
    project: LIBRARIAN_ACTION_PROJECT,
    sourceAgent: "Alexandria UI Librarian",
    currentGoal: `사서 실행형 요청: ${prompt}`,
    completed: [
      "사용자 요청을 실행형 Memory Compact 작업으로 분류했습니다.",
      `직접 검색 후보 ${totalCount}개를 확인했습니다.`,
      ...visibleHits.map(
        (hit, index) => `근거 ${index + 1}: ${hit.title} (${sourceTypeLabel(hit.sourceType)})`,
      ),
    ],
    inProgress: ["AI Librarian chat action에서 Memory Compact 저장을 수행했습니다."],
    keyDecisions: [
      "사서는 단순 답변뿐 아니라 명시적 실행형 요청을 안전한 플랫폼 작업으로 수행합니다.",
      "생성된 Compact Context를 Memory Compact의 source ref로 연결합니다.",
    ],
    nextActions: ["Memory Compacts 화면에서 생성된 요약본을 검토합니다."],
    risks: visibleHits.length
      ? []
      : ["직접 검색 후보가 없어 실행 기록 Context만 source ref로 연결했습니다."],
  });
  const compactContextRef = sourceRefFromContext(compactContext);
  const sourceRefPayload = compactCreateSourceRefs([
    compactContextRef,
    ...sourceRefs,
  ]);
  const coverage = compactCoverageWindow();
  const compact = await createMemoryCompactInBackend({
    project: LIBRARIAN_ACTION_PROJECT,
    coveredFrom: coverage.coveredFrom,
    coveredTo: coverage.coveredTo,
    markdownBody: compactContext.content,
    status: "CURRENT",
    sourceRefs: sourceRefPayload,
  });
  return {
    answer: memoryCompactActionAnswer({
      prompt,
      compact,
      compactContext,
      totalCount,
      visibleHits,
    }),
    compact,
    compactContext,
    directHit: directHitFromCompact(compact),
    sourceRefs: [sourceRefFromCompact(compact), compactContextRef],
    executionSummary: [
      "작업 실행: Memory Compact 생성 완료",
      `생성된 Memory Compact source refs: ${compact.sourceRefs.length}개`,
    ],
  };
}

function delegationCompleted(response: NonNullable<LibrarianChatResponseDTO["askResponse"]>) {
  return response.status === "COMPLETED"
    && response.delegates.some((delegate) => delegate.status === "COMPLETED");
}

function delegateFailureAnswer(response: NonNullable<LibrarianChatResponseDTO["askResponse"]>) {
  const delegateEvidence = response.delegates.length
    ? response.delegates
        .map((delegate) => `- ${delegate.status}: ${delegate.summary}`)
        .join("\n")
    : "- No delegate lanes returned.";
  return [
    "# 사서 delegate 미완료",
    "",
    response.recommendation,
    "",
    "## Delegate evidence",
    delegateEvidence,
  ].join("\n");
}

function delegateCompletedAnswer(
  response: NonNullable<LibrarianChatResponseDTO["askResponse"]>,
  hits: LibrarianDirectHitDTO[],
  totalCount: number,
  prompt: string,
) {
  const completedSummaries = response.delegates
    .filter((delegate) => delegate.status === "COMPLETED")
    .map((delegate) => delegate.summary.trim())
    .filter(Boolean);
  const visibleHits = hits.slice(0, 5);
  const hiddenCount = Math.max(totalCount - visibleHits.length, 0);
  const answerLines = completedSummaries.length
    ? completedSummaries.flatMap((summary, index) => (
        completedSummaries.length === 1
          ? [summary]
          : [`### 사서 ${index + 1}`, summary]
      ))
    : [response.recommendation];
  return [
    "# 사서 답변",
    "",
    `질문: ${prompt}`,
    "",
    ...answerLines,
    "",
    "## 직접 검색 근거",
    `검색된 후보 총계: ${totalCount}개입니다.`,
    ...(visibleHits.length
      ? [
          "",
          "상위 후보 5개:",
          ...visibleHits.map(
            (hit, index) => `${index + 1}. **${hit.title}** (${sourceTypeLabel(hit.sourceType)}) — ${hit.preview}`,
          ),
        ]
      : ["", "직접 검색 후보는 없습니다."]),
    ...(hiddenCount > 0
      ? [
          "",
          `나머지 ${hiddenCount}개는 관련 라이브러리에서 더 펼쳐 확인할 수 있어요.`,
        ]
      : []),
  ].join("\n");
}

export async function chatWithLibrarianInBackend(
  request: LibrarianChatRequestDTO,
): Promise<LibrarianChatResponseDTO> {
  const limit = clampLimit(request.limit);
  const targets: LibrarianChatRequestDTO["targets"] = request.targets.length
    ? request.targets
    : ["SKILL", "PROMPT", "CONTEXT"];
  const executionSummary = [
    `질문: ${request.prompt}`,
    `실행 방식: ${modeLabel(request.mode)}`,
    `검색 대상: ${targets.map(targetLabel).join(", ")}`,
    selectedLibrarianLabel(request),
  ];
  const inventoryMode = isInventoryQuestion(request.prompt);
  const searchBuckets = await Promise.all([
    searchLibraryTargets(request.prompt, targets, limit),
    searchContextTargets(request.prompt, targets, limit, inventoryMode),
    searchMemoryCompactTargets(targets, limit),
  ]);
  const directTotalCount = searchBuckets.reduce(
    (total, bucket) => total + bucket.totalCount,
    0,
  );
  let directHits = searchBuckets
    .flatMap((bucket) => bucket.hits)
    .slice(0, limit * Math.max(1, targets.length));
  executionSummary.push(`표시 후보: ${directHits.length}개`);
  executionSummary.push(`검색된 후보 총계: ${directTotalCount}개`);
  let sourceRefs = directHits.map(sourceRefFromHit);

  if (request.mode === "DIRECT_SEARCH") {
    return {
      answer: directSearchAnswer(directHits, directTotalCount, request.prompt),
      directHits,
      delegatedJobId: null,
      sourceRefs,
      executionSummary,
      askResponse: null,
    };
  }

  if (isMemoryCompactAction(request.prompt)) {
    try {
      const actionResult = await runMemoryCompactAction({
        prompt: request.prompt,
        directHits,
        sourceRefs,
        totalCount: directTotalCount,
      });
      directHits = [
        actionResult.directHit,
        ...directHits,
      ].slice(0, limit * Math.max(1, targets.length) + 1);
      sourceRefs = [
        ...actionResult.sourceRefs,
        ...sourceRefs,
      ];
      executionSummary.push(...actionResult.executionSummary);
      return {
        answer: actionResult.answer,
        directHits,
        delegatedJobId: null,
        sourceRefs,
        executionSummary,
        askResponse: null,
      };
    } catch {
      executionSummary.push("작업 실행 실패: Memory Compact 생성");
      return {
        answer: memoryCompactActionFailureAnswer(request.prompt),
        directHits,
        delegatedJobId: null,
        sourceRefs,
        executionSummary,
        askResponse: null,
      };
    }
  }

  const inventoryContext = delegateInventoryContext(directHits, directTotalCount);
  const askResponse = await askLibrarianInBackend({
    prompt: request.prompt,
    agentName: "Alexandria UI",
    delegateToLibrarian: true,
    providerId: request.providerId,
    librarianProfileId: request.librarianProfileId,
    librarianModel: request.librarianModel,
    maxLibrarianAgents: request.maxLibrarianAgents,
    taskSummary: `${request.prompt}\n\n${inventoryContext}`,
    librarianRolePrompt: selectedLibrarianRolePrompt(request),
    sourceRefs,
  });
  if (!delegationCompleted(askResponse)) {
    executionSummary.push("사서 위임이 완료되지 않았습니다.");
    return {
      answer: delegateFailureAnswer(askResponse),
      directHits,
      delegatedJobId: null,
      sourceRefs,
      executionSummary,
      askResponse,
    };
  }
  executionSummary.push("사서 위임 완료");

  return {
    answer: delegateCompletedAnswer(
      askResponse,
      directHits,
      directTotalCount,
      request.prompt,
    ),
    directHits,
    delegatedJobId: askResponse.jobId,
    sourceRefs,
    executionSummary,
    askResponse,
  };
}
