import { backendFetch } from "@/lib/backend/client";
import type {
  ContextChunkDTO,
  ContextDTO,
  ContextAccessEventCreateDTO,
  ContextAccessEventDTO,
  ContextAccessActorType,
  ContextAccessMethod,
  ContextKind,
  ContextListDTO,
  ContextPackDTO,
  ContextPrepareCompactDTO,
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

type BackendContextAccessEvent = {
  id: string;
  context_id: string;
  accessed_at: string;
  actor_name: string;
  actor_type: ContextAccessActorType;
  access_method: ContextAccessMethod;
  source_surface: string | null;
};

type BackendContextList = {
  items: BackendContext[];
  total: number;
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

function toContextAccessEventDTO(event: BackendContextAccessEvent): ContextAccessEventDTO {
  return {
    id: event.id,
    contextId: event.context_id,
    accessedAt: event.accessed_at,
    actorName: event.actor_name,
    actorType: event.actor_type,
    accessMethod: event.access_method,
    sourceSurface: event.source_surface,
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
  const result = await backendFetch<BackendContextList>(`/memory/contexts${query ? `?${query}` : ""}`);
  return { items: result.items.map(toContextDTO), total: result.total };
}

export async function loadContextFromBackend(contextId: string): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>(`/memory/contexts/${encodeURIComponent(contextId)}`);
  return toContextDTO(context);
}

export async function loadContextChunksFromBackend(contextId: string): Promise<ContextChunkDTO[]> {
  const chunks = await backendFetch<BackendContextChunk[]>(`/memory/contexts/${encodeURIComponent(contextId)}/chunks`);
  return chunks.map(toContextChunkDTO);
}

export async function prepareCompactInBackend(payload: ContextPrepareCompactDTO): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>("/memory/contexts/prepare-compact", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(compactBody(payload)),
  });
  return toContextDTO(context);
}

export async function searchContextsInBackend(payload: ContextSearchDTO): Promise<ContextPackDTO> {
  const pack = await backendFetch<BackendContextPack>("/memory/contexts/retrieval/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(searchBody(payload)),
  });
  return toContextPackDTO(pack);
}

export async function archiveContextInBackend(contextId: string): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>(`/memory/contexts/${encodeURIComponent(contextId)}/archive`, {
    method: "POST",
  });
  return toContextDTO(context);
}

export async function accessContextInBackend(contextId: string): Promise<ContextDTO> {
  const context = await backendFetch<BackendContext>(`/memory/contexts/${encodeURIComponent(contextId)}/access`, {
    method: "POST",
  });
  return toContextDTO(context);
}

export async function recordContextAccessEventInBackend(
  contextId: string,
  payload: ContextAccessEventCreateDTO,
): Promise<ContextAccessEventDTO> {
  const event = await backendFetch<BackendContextAccessEvent>(
    `/memory/contexts/${encodeURIComponent(contextId)}/access-events`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor_name: payload.actorName,
        actor_type: payload.actorType,
        access_method: payload.accessMethod,
        source_surface: payload.sourceSurface,
      }),
    },
  );
  return toContextAccessEventDTO(event);
}

export async function loadContextAccessEventsFromBackend(
  contextId: string,
  limit = 5,
): Promise<ContextAccessEventDTO[]> {
  const boundedLimit = Math.min(Math.max(limit, 1), 5);
  const events = await backendFetch<BackendContextAccessEvent[]>(
    `/memory/contexts/${encodeURIComponent(contextId)}/access-events?limit=${boundedLimit}`,
  );
  return events.map(toContextAccessEventDTO);
}

export async function loadRagStatusFromBackend(): Promise<RagStatusDTO> {
  const status = await backendFetch<BackendRagStatus>("/memory/contexts/rag/status");
  return toRagStatusDTO(status);
}
