import { backendFetch } from "@/lib/backend/client";
import { askLibrarianInBackend } from "@/lib/backend/librarians";
import { loadMemoryCompactsFromBackend } from "@/lib/backend/memory-compacts";
import { searchContextsInBackend } from "@/lib/backend/contexts";
import type {
  ItemStatus,
  ItemType,
  LibrarianChatRequestDTO,
  LibrarianChatResponseDTO,
  LibrarianDirectHitDTO,
  LibrarianSourceRefDTO,
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

const PLATFORM_TOOL_INSTRUCTIONS = [
  "You are connected to Alexandria-Hermes.",
  "Use the provided direct search hits and source refs first.",
  "If additional lookup is needed, use available Alexandria CLI/MCP/search tools where exposed by the runtime.",
  "Do not claim there is no platform access unless a tool/search call failed.",
  "Report which search targets and queries were used.",
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
): Promise<LibrarianDirectHitDTO[]> {
  const itemTypes = targets.filter((target) => target === "SKILL" || target === "PROMPT");
  if (itemTypes.length === 0) return [];
  const params = new URLSearchParams({
    q: prompt,
    limit: String(limit),
    offset: "0",
    content_mode: "candidate",
  });
  for (const itemType of itemTypes) params.append("item_types", itemType);
  const response = await backendFetch<BackendSearchResponse>(`/library/search?${params.toString()}`);
  const categorySlugCache = new Map<string, Promise<string>>();
  return Promise.all(
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
}

async function searchContextTargets(
  prompt: string,
  targets: LibrarianChatRequestDTO["targets"],
  limit: number,
): Promise<LibrarianDirectHitDTO[]> {
  if (!targets.includes("CONTEXT")) return [];
  const pack = await searchContextsInBackend({
    query: prompt,
    strategy: "HYBRID",
    limit,
    project: null,
    kind: null,
  });
  return pack.matches.map((match) => ({
    id: match.context.id,
    sourceType: "CONTEXT",
    title: match.context.title,
    preview: match.whyRetrieved || match.context.summary,
    detailPath: `/memory/contexts/${match.context.id}`,
    score: match.score,
  }));
}

async function searchMemoryCompactTargets(
  targets: LibrarianChatRequestDTO["targets"],
  limit: number,
): Promise<LibrarianDirectHitDTO[]> {
  if (!targets.includes("MEMORY_COMPACT")) return [];
  const compacts = await loadMemoryCompactsFromBackend(new URLSearchParams({ limit: String(limit) }));
  return compacts.items.map((compact) => ({
    id: compact.id,
    sourceType: "MEMORY_COMPACT",
    title: compact.project ? `Memory Compact · ${compact.project}` : "Memory Compact · default",
    preview: compact.markdownBody.slice(0, 240),
    detailPath: `/memory/compacts/${compact.id}`,
    score: compact.status === "CURRENT" ? 1 : 0.5,
  }));
}

function directSearchAnswer(hits: LibrarianDirectHitDTO[], prompt: string) {
  if (hits.length === 0) {
    return `# 사서 검색 결과\n\n질문: ${prompt}\n\n직접 검색 후보를 찾지 못했습니다. 검색어를 바꾸거나 사서 위임 모드를 사용하세요.`;
  }
  return [
    "# 사서 검색 결과",
    "",
    `질문: ${prompt}`,
    "",
    "직접 검색 후보를 먼저 확인하세요.",
    "",
    ...hits.slice(0, 5).map((hit, index) => `${index + 1}. **${hit.title}** (${hit.sourceType}) — ${hit.preview}`),
  ].join("\n");
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

export async function chatWithLibrarianInBackend(
  request: LibrarianChatRequestDTO,
): Promise<LibrarianChatResponseDTO> {
  const limit = clampLimit(request.limit);
  const targets: LibrarianChatRequestDTO["targets"] = request.targets.length
    ? request.targets
    : ["SKILL", "PROMPT", "CONTEXT"];
  const executionSummary = [`query=${request.prompt}`, `mode=${request.mode}`, `targets=${targets.join(",")}`];
  const directHits = [
    ...(await searchLibraryTargets(request.prompt, targets, limit)),
    ...(await searchContextTargets(request.prompt, targets, limit)),
    ...(await searchMemoryCompactTargets(targets, limit)),
  ].slice(0, limit * Math.max(1, targets.length));
  executionSummary.push(`direct_hits=${directHits.length}`);
  const sourceRefs = directHits.map(sourceRefFromHit);

  if (request.mode === "DIRECT_SEARCH") {
    return {
      answer: directSearchAnswer(directHits, request.prompt),
      directHits,
      delegatedJobId: null,
      sourceRefs,
      executionSummary,
      askResponse: null,
    };
  }

  const askResponse = await askLibrarianInBackend({
    prompt: request.prompt,
    agentName: "Alexandria UI",
    delegateToLibrarian: true,
    taskSummary: `${request.prompt}\n\nDirect search hits: ${directHits.length}`,
    librarianRolePrompt: PLATFORM_TOOL_INSTRUCTIONS,
    sourceRefs,
  });
  if (!delegationCompleted(askResponse)) {
    executionSummary.push(`delegation_status=${askResponse.status}`);
    return {
      answer: delegateFailureAnswer(askResponse),
      directHits,
      delegatedJobId: null,
      sourceRefs,
      executionSummary,
      askResponse,
    };
  }
  executionSummary.push(`delegated_job=${askResponse.jobId}`);

  return {
    answer: askResponse.recommendation,
    directHits,
    delegatedJobId: askResponse.jobId,
    sourceRefs,
    executionSummary,
    askResponse,
  };
}
