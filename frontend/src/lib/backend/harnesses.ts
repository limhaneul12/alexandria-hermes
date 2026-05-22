import { backendFetch } from "@/lib/backend/client";
import type {
  HarnessContextDTO,
  HarnessExecutionMetadataDTO,
  HarnessListDTO,
} from "@/types/library";

type BackendHarnessContext = {
  id: string;
  kind: "HARNESS";
  title: string;
  summary: string;
  content: string;
  content_format: string;
  project: string | null;
  source_agent: string;
  source_type: HarnessContextDTO["sourceType"];
  importance: HarnessContextDTO["importance"];
  tags: string[];
  status: HarnessContextDTO["status"];
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

type BackendHarnessList = {
  items: BackendHarnessContext[];
  total: number;
};

function stringValue(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function harnessMetadata(metadata: Record<string, unknown>): HarnessExecutionMetadataDTO {
  const raw = metadata.harness;
  const harness = raw && typeof raw === "object" && !Array.isArray(raw) ? raw as Record<string, unknown> : {};
  return {
    taskGoal: stringValue(harness.task_goal),
    environment: stringValue(harness.environment),
    triggerContext: stringValue(harness.trigger_context),
    steps: stringList(harness.steps),
    commands: stringList(harness.commands),
    tests: stringList(harness.tests),
    failures: stringList(harness.failures),
    fixes: stringList(harness.fixes),
    artifacts: stringList(harness.artifacts),
    reusableProcedure: stringValue(harness.reusable_procedure),
    recallKeywords: stringList(harness.recall_keywords),
    safetyNotes: stringList(harness.safety_notes),
  };
}

function toHarnessDTO(context: BackendHarnessContext): HarnessContextDTO {
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
    harness: harnessMetadata(context.metadata),
  };
}


export async function loadHarnessesFromBackend(searchParams: URLSearchParams): Promise<HarnessListDTO> {
  const query = searchParams.toString();
  const result = await backendFetch<BackendHarnessList>(`/memory/contexts/harnesses${query ? `?${query}` : ""}`);
  return { items: result.items.map(toHarnessDTO), total: result.total };
}

export async function loadHarnessFromBackend(contextId: string): Promise<HarnessContextDTO> {
  const context = await backendFetch<BackendHarnessContext>(`/memory/contexts/harnesses/${encodeURIComponent(contextId)}`);
  return toHarnessDTO(context);
}

export async function archiveHarnessInBackend(contextId: string): Promise<HarnessContextDTO> {
  const context = await backendFetch<BackendHarnessContext>(`/memory/contexts/harnesses/${encodeURIComponent(contextId)}/archive`, {
    method: "POST",
  });
  return toHarnessDTO(context);
}
