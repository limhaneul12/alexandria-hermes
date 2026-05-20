import { backendFetch } from "@/lib/backend/client";
import { askLibrarianInBackend } from "@/lib/backend/librarians";
import {
  loadCurrentMemoryCompactFromBackend,
  loadMemoryCompactsFromBackend,
} from "@/lib/backend/memory-compacts";
import {
  loadContextsFromBackend,
  searchContextsInBackend,
} from "@/lib/backend/contexts";
import type {
  ItemStatus,
  ItemType,
  LibrarianChatRequestDTO,
  LibrarianChatResponseDTO,
  LibrarianDirectHitDTO,
  LibrarianSourceRefDTO,
  MemoryCompactDTO,
} from "@/types/library";

type LibrarianChatTarget = NonNullable<LibrarianChatRequestDTO["targets"]>[number];

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
  compacts?: MemoryCompactDTO[];
};

const EMPTY_DIRECT_SEARCH_BUCKET: DirectSearchBucket = {
  hits: [],
  totalCount: 0,
};

const LIBRARIAN_ACTION_PROJECT = "alexandria-hermes";
const DEFAULT_LIBRARIAN_CHAT_MODE = "SEARCH_AND_DELEGATE";
const DEFAULT_LIBRARIAN_CHAT_TARGETS: LibrarianChatTarget[] = [
  "SKILL",
  "PROMPT",
  "CONTEXT",
  "MEMORY_COMPACT",
];

const PLATFORM_TOOL_INSTRUCTIONS = [
  "You are connected to Alexandria-Hermes.",
  "Use the provided direct search hits and source refs first.",
  "The backend injects the current Memory Compact into the librarian knowledge packet when available; prefer it before broad recall.",
  "If a user asks count/list/inventory questions, answer with the total count first and show only the top 5 representative items by default.",
  "Do not expose raw API routes, backend endpoints, frontend paths, headers, or implementation-only identifiers unless the user explicitly asks for API details.",
  "Guide continuation in natural product language, such as asking to show more results or opening the relevant library view.",
  "If additional lookup is needed, use available Alexandria CLI/MCP/search tools where exposed by the runtime.",
  "Do not claim there is no platform access unless a tool/search call failed.",
  "Do not claim a durable platform action was saved unless a completed action result is provided.",
  "Report automatic evidence collection in natural product language without exposing raw routes.",
].join("\n");

const INVENTORY_QUESTION_PATTERN =
  /몇\s*개|몇\s*건|개수|건수|총\s*몇|전체\s*몇|목록|리스트|대표\s*목록|얼마나|현황|상태|inventory|count|how many|list|status/;
const MEMORY_STATUS_TERM_PATTERN =
  /장기\s*기억|기억|메모리|memory|memory\s*compact|compact|compacts|컨텍스트|context\s*vault/i;

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

function directHitKey(hit: Pick<LibrarianDirectHitDTO, "id" | "sourceType">): string {
  return `${hit.sourceType}:${hit.id}`;
}

function uniqueDirectHits(hits: LibrarianDirectHitDTO[]): LibrarianDirectHitDTO[] {
  const seen = new Set<string>();
  return hits.filter((hit) => {
    const key = directHitKey(hit);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
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
  targets: LibrarianChatTarget[],
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
  return INVENTORY_QUESTION_PATTERN.test(normalized);
}

function isMemoryStatusQuestion(prompt: string): boolean {
  return MEMORY_STATUS_TERM_PATTERN.test(prompt) && isInventoryQuestion(prompt);
}

async function searchContextTargets(
  prompt: string,
  targets: LibrarianChatTarget[],
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
  targets: LibrarianChatTarget[],
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
  return { hits, totalCount: compacts.total, compacts: compacts.items };
}

function sourceTypeLabel(sourceType: LibrarianDirectHitDTO["sourceType"]): string {
  if (sourceType === "SKILL") return "스킬";
  if (sourceType === "PROMPT") return "프롬프트";
  if (sourceType === "CONTEXT") return "컨텍스트";
  if (sourceType === "MEMORY_COMPACT") return "기억 요약본";
  return "라이브러리 항목";
}

function targetLabel(target: LibrarianChatTarget): string {
  if (target === "SKILL") return "스킬";
  if (target === "PROMPT") return "프롬프트";
  if (target === "CONTEXT") return "컨텍스트";
  if (target === "MEMORY_COMPACT") return "기억 요약본";
  return "라이브러리 항목";
}

function modeLabel(mode: NonNullable<LibrarianChatRequestDTO["mode"]>): string {
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
    return `# 사서 검색 결과\n\n질문: ${prompt}\n\n직접 검색 후보를 찾지 못했습니다. 사서에게 더 넓은 근거 수집을 맡겨 보세요.`;
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

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Seoul",
  }).format(new Date(value));
}

function relativeAge(value: string): string {
  const diffMs = Math.max(Date.now() - new Date(value).getTime(), 0);
  const minuteMs = 60 * 1000;
  const hourMs = 60 * minuteMs;
  const dayMs = 24 * hourMs;
  if (diffMs < hourMs) return `${Math.max(Math.floor(diffMs / minuteMs), 0)}분 전`;
  if (diffMs < dayMs) return `${Math.floor(diffMs / hourMs)}시간 전`;
  return `${Math.floor(diffMs / dayMs)}일 전`;
}

function compactStatusLabel(status: MemoryCompactDTO["status"]): string {
  if (status === "CURRENT") return "현재 사용 중";
  if (status === "ARCHIVED") return "보관됨";
  return "이전 버전";
}

function compactSummaryLine(compact: MemoryCompactDTO): string {
  const project = compact.project ?? "default";
  return [
    `- 현재 compact: ${compactStatusLabel(compact.status)} · ${project}`,
    `- coverage: ${formatDateTime(compact.coveredFrom)} ~ ${formatDateTime(compact.coveredTo)}`,
    `- 마지막 업데이트: ${formatDateTime(compact.updatedAt)} (${relativeAge(compact.updatedAt)})`,
    `- source refs: ${compact.sourceRefs.length}개`,
  ].join("\n");
}

function representativeCurrentCompact(
  currentCompact: MemoryCompactDTO | null,
  compactBucket: DirectSearchBucket,
): MemoryCompactDTO | null {
  return currentCompact
    ?? compactBucket.compacts?.find((compact) => compact.status === "CURRENT")
    ?? compactBucket.compacts?.[0]
    ?? null;
}

function platformInventoryAnswer(
  prompt: string,
  libraryBucket: DirectSearchBucket,
  contextBucket: DirectSearchBucket,
  compactBucket: DirectSearchBucket,
  currentCompact: MemoryCompactDTO | null,
  directHits: LibrarianDirectHitDTO[],
): string {
  const visibleHits = directHits.slice(0, 5);
  const hiddenCount = Math.max(
    libraryBucket.totalCount + contextBucket.totalCount + compactBucket.totalCount
      - visibleHits.length,
    0,
  );
  const compact = representativeCurrentCompact(currentCompact, compactBucket);
  return [
    "# 사서 답변",
    "",
    `질문: ${prompt}`,
    "",
    "플랫폼에서 바로 확인한 기억 현황입니다.",
    "",
    "## 현재 기억 현황",
    `- Context Vault 장기기억: ${contextBucket.totalCount}건`,
    `- Memory Compacts: ${compactBucket.totalCount}건`,
    `- Library skill/prompt 후보: ${libraryBucket.totalCount}건`,
    "",
    "## Current Memory Compact",
    compact
      ? compactSummaryLine(compact)
      : "- 현재 compact를 찾지 못했습니다. 아직 CURRENT compact가 없을 수 있습니다.",
    ...(visibleHits.length
      ? [
          "",
          "## 대표 항목",
          ...visibleHits.map(
            (hit, index) => `${index + 1}. **${hit.title}** (${sourceTypeLabel(hit.sourceType)}) — ${hit.preview}`,
          ),
        ]
      : []),
    ...(hiddenCount > 0
      ? [
          "",
          `나머지 ${hiddenCount}개는 관련 기억/라이브러리 화면에서 더 펼쳐 확인할 수 있어요.`,
        ]
      : []),
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

function sourceRefFromCompact(compact: MemoryCompactDTO): LibrarianSourceRefDTO {
  return {
    sourceType: "MEMORY_COMPACT",
    sourceId: compact.id,
    title: compact.project ? `Memory Compact · ${compact.project}` : "Memory Compact · default",
    detailPath: `/memory/compacts/${compact.id}`,
    preview: compact.markdownBody.slice(0, 240),
  };
}

function toLibrarianSourceType(
  sourceType: string,
): LibrarianSourceRefDTO["sourceType"] | null {
  if (
    sourceType === "CONTEXT" ||
    sourceType === "MEMORY_COMPACT" ||
    sourceType === "LIBRARY_ITEM" ||
    sourceType === "SKILL" ||
    sourceType === "PROMPT"
  ) {
    return sourceType;
  }
  return null;
}

function sourceRefFromCompactSourceRef(
  ref: MemoryCompactDTO["sourceRefs"][number],
): LibrarianSourceRefDTO | null {
  const sourceType = toLibrarianSourceType(ref.sourceType);
  if (!sourceType) return null;
  return {
    sourceType,
    sourceId: ref.sourceId,
    title: ref.title,
    detailPath: ref.detailPath,
    preview: null,
  };
}

async function loadCurrentMemoryCompactForLibrarian(): Promise<MemoryCompactDTO | null> {
  try {
    return await loadCurrentMemoryCompactFromBackend(LIBRARIAN_ACTION_PROJECT);
  } catch {
    return null;
  }
}

function currentCompactSourceRefs(
  compact: MemoryCompactDTO,
  sourceRefs: LibrarianSourceRefDTO[],
): LibrarianSourceRefDTO[] {
  return [
    sourceRefFromCompact(compact),
    ...compact.sourceRefs.flatMap((ref) => {
      const sourceRef = sourceRefFromCompactSourceRef(ref);
      return sourceRef ? [sourceRef] : [];
    }),
    ...sourceRefs,
  ];
}

function uniqueSourceRefs(sourceRefs: LibrarianSourceRefDTO[]): LibrarianSourceRefDTO[] {
  const seen = new Set<string>();
  return sourceRefs.filter((ref) => {
    const key = `${ref.sourceType}:${ref.sourceId}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function delegationCompleted(response: NonNullable<LibrarianChatResponseDTO["askResponse"]>) {
  return response.status === "COMPLETED"
    && response.delegates.some((delegate) => delegate.status === "COMPLETED");
}

function delegateStatusLabel(status: string): string {
  if (status === "COMPLETED") return "완료";
  if (status === "SKIPPED") return "건너뜀";
  if (status === "FAILED") return "실패";
  return "확인 필요";
}

function delegateFailureAnswer(response: NonNullable<LibrarianChatResponseDTO["askResponse"]>) {
  const delegateEvidence = response.delegates.length
    ? response.delegates
        .map((delegate) => `- ${delegateStatusLabel(delegate.status)}: ${delegate.summary}`)
        .join("\n")
    : "- 완료된 사서 위임 결과가 없습니다. 필요한 플랫폼 기억 조회는 직접 검색 결과로 답할 수 있습니다.";
  return [
    "# 사서 위임 결과 없음",
    "",
    response.recommendation,
    "",
    "## 확인한 내용",
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
  const mode = request.mode ?? DEFAULT_LIBRARIAN_CHAT_MODE;
  const targets = request.targets?.length
    ? request.targets
    : DEFAULT_LIBRARIAN_CHAT_TARGETS;
  const executionSummary = [
    `질문: ${request.prompt}`,
    `실행 방식: ${modeLabel(mode)}`,
    `근거 수집: 자동 (${targets.map(targetLabel).join(", ")})`,
    selectedLibrarianLabel(request),
  ];
  const inventoryMode = isInventoryQuestion(request.prompt);
  const memoryStatusMode = isMemoryStatusQuestion(request.prompt);
  const [libraryBucket, contextBucket, memoryCompactBucket] = await Promise.all([
    searchLibraryTargets(request.prompt, targets, limit),
    searchContextTargets(request.prompt, targets, limit, inventoryMode),
    searchMemoryCompactTargets(targets, limit),
  ]);
  const searchBuckets = [libraryBucket, contextBucket, memoryCompactBucket];
  const directTotalCount = searchBuckets.reduce(
    (total, bucket) => total + bucket.totalCount,
    0,
  );
  const directHits = uniqueDirectHits(
    searchBuckets.flatMap((bucket) => bucket.hits),
  ).slice(0, limit * Math.max(1, targets.length));
  executionSummary.push(`표시 후보: ${directHits.length}개`);
  executionSummary.push(`검색된 후보 총계: ${directTotalCount}개`);
  let sourceRefs = uniqueSourceRefs(directHits.map(sourceRefFromHit));
  const currentCompact = await loadCurrentMemoryCompactForLibrarian();
  if (currentCompact) {
    executionSummary.push("현재 Memory Compact를 사서 knowledge packet에 포함했습니다.");
    sourceRefs = uniqueSourceRefs(currentCompactSourceRefs(currentCompact, sourceRefs));
  }

  if (mode === "DIRECT_SEARCH") {
    return {
      answer: directSearchAnswer(directHits, directTotalCount, request.prompt),
      directHits,
      delegatedJobId: null,
      sourceRefs,
      executionSummary,
      askResponse: null,
    };
  }

  if (memoryStatusMode || inventoryMode) {
    executionSummary.push("플랫폼 기억 현황 질문으로 직접 답변했습니다.");
    return {
      answer: platformInventoryAnswer(
        request.prompt,
        libraryBucket,
        contextBucket,
        memoryCompactBucket,
        currentCompact,
        directHits,
      ),
      directHits,
      delegatedJobId: null,
      sourceRefs,
      executionSummary,
      askResponse: null,
    };
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
    contextCompact: currentCompact
      ? {
          markdownBody: currentCompact.markdownBody,
          sourceRefs: currentCompactSourceRefs(currentCompact, []),
        }
      : null,
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
