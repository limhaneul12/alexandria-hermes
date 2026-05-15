import { backendFetch } from "@/lib/backend/client";
import type {
  ContextChunkDTO,
  ContextDTO,
  ContextKind,
  ContextLintRequestDTO,
  ContextLintResultDTO,
  ContextListDTO,
  ContextPackDTO,
  ContextPrepareCompactDTO,
  ContextSaveDTO,
  ContextSearchDTO,
  ContextSearchMatchDTO,
  ContextStorageStatus,
  RagStatusDTO,
  RagStrategy,
} from "@/types/library";

type BackendContext = {
  id: string;
  kind: ContextKind;
  title: string;
  summary: string;
  content: string;
  content_format: string;
  project: string | null;
  source_agent: string;
  source_type: ContextDTO["sourceType"];
  importance: ContextDTO["importance"];
  tags: string[];
  status: ContextStorageStatus;
  quality_score: number;
  warnings: string[];
  restore_prompt: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  last_accessed_at: string | null;
  expires_at: string | null;
  archived_at: string | null;
  access_count: number;
  is_archived: boolean;
};

type BackendContextChunk = {
  id: string;
  context_id: string;
  chunk_index: number;
  heading: string | null;
  content: string;
  token_count: number;
  content_hash: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

type BackendContextList = {
  items: BackendContext[];
  total: number;
};

type BackendLintResult = {
  ok: boolean;
  status: ContextStorageStatus;
  score: number;
  errors: string[];
  warnings: string[];
  suggestions: string[];
  redacted_content: string;
  normalized: Record<string, unknown>;
};

type BackendContextMatch = {
  context: BackendContext;
  chunk: BackendContextChunk;
  score: number;
  fts_score: number | null;
  vector_score: number | null;
  why_retrieved: string;
};

type BackendContextPack = {
  query: string;
  strategy: RagStrategy;
  effective_strategy: RagStrategy;
  warnings: string[];
  matches: BackendContextMatch[];
  context_pack: string;
};

type BackendRagStatus = {
  fts: RagStatusDTO["fts"];
  vector: RagStatusDTO["vector"];
  embedding: RagStatusDTO["embedding"];
  default_strategy: RagStrategy;
  model_name: string;
  dimensions: number;
  warnings: string[];
};

function toContextDTO(context: BackendContext): ContextDTO {
  return {
    id: context.id,
    kind: context.kind,
    title: context.title,
    summary: context.summary,
    content: context.content,
    contentFormat: context.content_format,
    project: context.project,
    sourceAgent: context.source_agent,
    sourceType: context.source_type,
    importance: context.importance,
    tags: context.tags,
    status: context.status,
    qualityScore: context.quality_score,
    warnings: context.warnings,
    restorePrompt: context.restore_prompt,
    metadata: context.metadata,
    createdAt: context.created_at,
    updatedAt: context.updated_at,
    lastAccessedAt: context.last_accessed_at,
    expiresAt: context.expires_at,
    archivedAt: context.archived_at,
    accessCount: context.access_count,
    isArchived: context.is_archived,
  };
}

function toContextChunkDTO(chunk: BackendContextChunk): ContextChunkDTO {
  return {
    id: chunk.id,
    contextId: chunk.context_id,
    chunkIndex: chunk.chunk_index,
    heading: chunk.heading,
    content: chunk.content,
    tokenCount: chunk.token_count,
    contentHash: chunk.content_hash,
    metadata: chunk.metadata,
    createdAt: chunk.created_at,
  };
}

function toLintResultDTO(result: BackendLintResult): ContextLintResultDTO {
  return {
    ok: result.ok,
    status: result.status,
    score: result.score,
    errors: result.errors,
    warnings: result.warnings,
    suggestions: result.suggestions,
    redactedContent: result.redacted_content,
    normalized: result.normalized,
  };
}

function toContextMatchDTO(match: BackendContextMatch): ContextSearchMatchDTO {
  return {
    context: toContextDTO(match.context),
    chunk: toContextChunkDTO(match.chunk),
    score: match.score,
    ftsScore: match.fts_score,
    vectorScore: match.vector_score,
    whyRetrieved: match.why_retrieved,
  };
}

function toContextPackDTO(pack: BackendContextPack): ContextPackDTO {
  return {
    query: pack.query,
    strategy: pack.strategy,
    effectiveStrategy: pack.effective_strategy,
    warnings: pack.warnings,
    matches: pack.matches.map(toContextMatchDTO),
    contextPack: pack.context_pack,
  };
}

function toRagStatusDTO(status: BackendRagStatus): RagStatusDTO {
  return {
    fts: status.fts,
    vector: status.vector,
    embedding: status.embedding,
    defaultStrategy: status.default_strategy,
    modelName: status.model_name,
    dimensions: status.dimensions,
    warnings: status.warnings,
  };
}

function contextBody(payload: ContextSaveDTO) {
  return {
    kind: payload.kind,
    title: payload.title,
    content: payload.content,
    summary: payload.summary,
    project: payload.project,
    source_agent: payload.sourceAgent,
    source_type: payload.sourceType,
    importance: payload.importance,
    tags: payload.tags,
    metadata: payload.metadata,
  };
}

function lintBody(payload: ContextLintRequestDTO) {
  return {
    kind: payload.kind,
    title: payload.title,
    content: payload.content,
    summary: payload.summary,
    project: payload.project,
    source_agent: payload.sourceAgent,
    tags: payload.tags,
  };
}

function searchBody(payload: ContextSearchDTO) {
  return {
    query: payload.query,
    strategy: payload.strategy,
    limit: payload.limit,
    project: payload.project,
    kind: payload.kind,
  };
}

function compactBody(payload: ContextPrepareCompactDTO) {
  return {
    project: payload.project,
    source_agent: payload.sourceAgent,
    current_goal: payload.currentGoal,
    completed: payload.completed,
    in_progress: payload.inProgress,
    key_decisions: payload.keyDecisions,
    next_actions: payload.nextActions,
    risks: payload.risks,
  };
}

export async function loadContextsFromBackend(searchParams: URLSearchParams): Promise<ContextListDTO> {
  const query = searchParams.toString();
  const result = await backendFetch<BackendContextList>(`/library/contexts${query ? `?${query}` : ""}`);
  return { items: result.items.map(toContextDTO), total: result.total };
}

export async function loadContextFromBackend(contextId: string): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>(`/library/contexts/${encodeURIComponent(contextId)}`);
  return toContextDTO(context);
}

export async function loadContextChunksFromBackend(contextId: string): Promise<ContextChunkDTO[]> {
  const chunks = await backendFetch<BackendContextChunk[]>(`/library/contexts/${encodeURIComponent(contextId)}/chunks`);
  return chunks.map(toContextChunkDTO);
}

export async function lintContextInBackend(payload: ContextLintRequestDTO): Promise<ContextLintResultDTO> {
  const result = await backendFetch<BackendLintResult>("/library/contexts/lint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(lintBody(payload)),
  });
  return toLintResultDTO(result);
}

export async function saveContextInBackend(payload: ContextSaveDTO): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>("/library/contexts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(contextBody(payload)),
  });
  return toContextDTO(context);
}

export async function captureContextInBackend(payload: ContextSaveDTO): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>("/library/contexts/capture", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(contextBody(payload)),
  });
  return toContextDTO(context);
}

export async function prepareCompactInBackend(payload: ContextPrepareCompactDTO): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>("/library/contexts/prepare-compact", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(compactBody(payload)),
  });
  return toContextDTO(context);
}

export async function searchContextsInBackend(payload: ContextSearchDTO): Promise<ContextPackDTO> {
  const pack = await backendFetch<BackendContextPack>("/library/contexts/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(searchBody(payload)),
  });
  return toContextPackDTO(pack);
}

export async function archiveContextInBackend(contextId: string): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>(`/library/contexts/${encodeURIComponent(contextId)}/archive`, {
    method: "POST",
  });
  return toContextDTO(context);
}

export async function accessContextInBackend(contextId: string): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>(`/library/contexts/${encodeURIComponent(contextId)}/access`, {
    method: "POST",
  });
  return toContextDTO(context);
}

export async function loadRagStatusFromBackend(): Promise<RagStatusDTO> {
  const status = await backendFetch<BackendRagStatus>("/library/contexts/rag/status");
  return toRagStatusDTO(status);
}
