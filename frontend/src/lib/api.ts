import type {
  AgentDTO,
  CategoryCreateDTO,
  CategoryDTO,
  ContextChunkDTO,
  ContextDTO,
  ContextLintRequestDTO,
  ContextLintResultDTO,
  ContextListDTO,
  ContextPackDTO,
  ContextPrepareCompactDTO,
  ContextSaveDTO,
  ContextSearchDTO,
  DashboardDTO,
  ExternalArchiveCandidateDTO,
  ExternalArchiveImportResultDTO,
  LibrarianProviderCreateDTO,
  LibrarianProviderDTO,
  LibrarianProviderTestDTO,
  LibrarianProviderUpdateDTO,
  LibraryDTO,
  LibraryItemDetailDTO,
  PromptCreateDTO,
  PromptCreateResultDTO,
  SkillCreateDTO,
  SkillCreateResultDTO,
  RagStatusDTO,
  SkillDetailDTO,
} from "@/types/library";

async function fetchJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { headers: { Accept: "application/json" }, ...init });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function jsonInit(method: "POST" | "PATCH", body: unknown): RequestInit {
  return {
    method,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function fetchDashboard() {
  return fetchJson<DashboardDTO>("/api/dashboard");
}

export function fetchLibrary(params: URLSearchParams) {
  const query = params.toString();
  return fetchJson<LibraryDTO>(`/api/library${query ? `?${query}` : ""}`);
}

export function fetchLibraryItemDetail(itemId: string) {
  return fetchJson<LibraryItemDetailDTO>(`/api/items/${encodeURIComponent(itemId)}`);
}

export function fetchSkillDetail(skillId: string) {
  return fetchJson<SkillDetailDTO>(`/api/skills/${encodeURIComponent(skillId)}`);
}

export function createCategory(payload: CategoryCreateDTO) {
  return fetchJson<CategoryDTO>("/api/categories", jsonInit("POST", payload));
}

export function deleteCategory(categoryId: string) {
  return fetchJson<void>(`/api/categories/${encodeURIComponent(categoryId)}`, { method: "DELETE" });
}

export function createSkill(payload: SkillCreateDTO) {
  return fetchJson<SkillCreateResultDTO>("/api/skills", jsonInit("POST", payload));
}

export function createPrompt(payload: PromptCreateDTO) {
  return fetchJson<PromptCreateResultDTO>("/api/prompts", jsonInit("POST", payload));
}

export function deleteLibraryItem(itemId: string) {
  return fetchJson<void>(`/api/items/${encodeURIComponent(itemId)}`, { method: "DELETE" });
}

export function deleteSkill(skillId: string) {
  return fetchJson<void>(`/api/skills/${encodeURIComponent(skillId)}`, { method: "DELETE" });
}

export function fetchLibrarianProviders() {
  return fetchJson<LibrarianProviderDTO[]>("/api/librarians");
}

export function createLibrarianProvider(payload: LibrarianProviderCreateDTO) {
  return fetchJson<LibrarianProviderDTO>("/api/librarians", jsonInit("POST", payload));
}

export function updateLibrarianProvider(
  providerId: string,
  payload: LibrarianProviderUpdateDTO,
) {
  return fetchJson<LibrarianProviderDTO>(
    `/api/librarians/${encodeURIComponent(providerId)}`,
    jsonInit("PATCH", payload),
  );
}

export function testLibrarianProvider(providerId: string, testQuery: string) {
  return fetchJson<LibrarianProviderTestDTO>(
    `/api/librarians/${encodeURIComponent(providerId)}/test`,
    jsonInit("POST", { testQuery }),
  );
}

export function fetchExternalArchiveCandidates(limit = 48) {
  const boundedLimit = Math.min(Math.max(limit, 1), 1000);
  return fetchJson<ExternalArchiveCandidateDTO[]>(
    `/api/storage/minio/import-candidates?limit=${boundedLimit}`,
  );
}

export function importExternalArchiveCandidates(limit = 48) {
  const boundedLimit = Math.min(Math.max(limit, 1), 1000);
  return fetchJson<ExternalArchiveImportResultDTO>(
    "/api/storage/minio/import",
    jsonInit("POST", { limit: boundedLimit }),
  );
}

export function fetchAgents() {
  return fetchJson<AgentDTO[]>("/api/agents");
}

export function fetchContexts(params: URLSearchParams) {
  const query = params.toString();
  return fetchJson<ContextListDTO>(`/api/library/contexts${query ? `?${query}` : ""}`);
}

export function fetchContext(contextId: string) {
  return fetchJson<ContextDTO>(`/api/library/contexts/${encodeURIComponent(contextId)}`);
}

export function fetchContextChunks(contextId: string) {
  return fetchJson<ContextChunkDTO[]>(
    `/api/library/contexts/${encodeURIComponent(contextId)}/chunks`,
  );
}

export function lintContext(payload: ContextLintRequestDTO) {
  return fetchJson<ContextLintResultDTO>(
    "/api/library/contexts/lint",
    jsonInit("POST", payload),
  );
}

export function saveContext(payload: ContextSaveDTO) {
  return fetchJson<ContextDTO>("/api/library/contexts", jsonInit("POST", payload));
}

export function captureContext(payload: ContextSaveDTO) {
  return fetchJson<ContextDTO>(
    "/api/library/contexts/capture",
    jsonInit("POST", payload),
  );
}

export function prepareCompact(payload: ContextPrepareCompactDTO) {
  return fetchJson<ContextDTO>(
    "/api/library/contexts/prepare-compact",
    jsonInit("POST", payload),
  );
}

export function searchContexts(payload: ContextSearchDTO) {
  return fetchJson<ContextPackDTO>(
    "/api/library/contexts/search",
    jsonInit("POST", payload),
  );
}

export function archiveContext(contextId: string) {
  return fetchJson<ContextDTO>(
    `/api/library/contexts/${encodeURIComponent(contextId)}/archive`,
    jsonInit("POST", {}),
  );
}

export function accessContext(contextId: string) {
  return fetchJson<ContextDTO>(
    `/api/library/contexts/${encodeURIComponent(contextId)}/access`,
    jsonInit("POST", {}),
  );
}

export function fetchRagStatus() {
  return fetchJson<RagStatusDTO>("/api/library/contexts/rag/status");
}
