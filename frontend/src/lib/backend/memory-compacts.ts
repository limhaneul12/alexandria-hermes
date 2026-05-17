import { backendFetch } from "@/lib/backend/client";
import type {
  MemoryCompactDTO,
  MemoryCompactListDTO,
  MemoryCompactSourceRefDTO,
  MemoryCompactStatus,
} from "@/types/library";

type BackendMemoryCompactSourceRef = {
  id: string;
  compact_id: string;
  source_type: string;
  source_id: string;
  title: string;
  detail_path: string;
};

type BackendMemoryCompact = {
  id: string;
  project: string | null;
  covered_from: string;
  covered_to: string;
  markdown_body: string;
  status: MemoryCompactStatus;
  source_refs: BackendMemoryCompactSourceRef[];
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

type BackendMemoryCompactList = {
  items: BackendMemoryCompact[];
  total: number;
};

function toSourceRefDTO(ref: BackendMemoryCompactSourceRef): MemoryCompactSourceRefDTO {
  return {
    id: ref.id,
    compactId: ref.compact_id,
    sourceType: ref.source_type,
    sourceId: ref.source_id,
    title: ref.title,
    detailPath: ref.detail_path,
  };
}

function toMemoryCompactDTO(compact: BackendMemoryCompact): MemoryCompactDTO {
  return {
    id: compact.id,
    project: compact.project,
    coveredFrom: compact.covered_from,
    coveredTo: compact.covered_to,
    markdownBody: compact.markdown_body,
    status: compact.status,
    sourceRefs: compact.source_refs.map(toSourceRefDTO),
    createdAt: compact.created_at,
    updatedAt: compact.updated_at,
    archivedAt: compact.archived_at,
  };
}

export async function loadMemoryCompactsFromBackend(
  searchParams: URLSearchParams,
): Promise<MemoryCompactListDTO> {
  const query = searchParams.toString();
  const result = await backendFetch<BackendMemoryCompactList>(
    `/memory/compacts${query ? `?${query}` : ""}`,
  );
  return { items: result.items.map(toMemoryCompactDTO), total: result.total };
}

export async function loadCurrentMemoryCompactFromBackend(
  project: string | null,
): Promise<MemoryCompactDTO> {
  const query = project ? `?project=${encodeURIComponent(project)}` : "";
  const result = await backendFetch<BackendMemoryCompact>(
    `/memory/compacts/current${query}`,
  );
  return toMemoryCompactDTO(result);
}

export async function loadMemoryCompactFromBackend(
  compactId: string,
): Promise<MemoryCompactDTO> {
  const result = await backendFetch<BackendMemoryCompact>(
    `/memory/compacts/${encodeURIComponent(compactId)}`,
  );
  return toMemoryCompactDTO(result);
}
