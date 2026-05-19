import type {
  AgentDTO,
  AgentCreateDTO,
  AgentUpdateDTO,
  CategoryCreateDTO,
  CategoryDTO,
  ContextChunkDTO,
  ContextDTO,
  ContextAccessEventCreateDTO,
  ContextAccessEventDTO,
  ContextListDTO,
  ContextPrepareCompactDTO,
  DashboardDTO,
  LibrarianOAuthStartDTO,
  LibrarianOAuthStatusDTO,
  LibrarianAskRequestDTO,
  LibrarianAskResponseDTO,
  LibrarianChatRequestDTO,
  LibrarianChatResponseDTO,
  LibrarianProviderCreateDTO,
  LibrarianProviderDTO,
  LibrarianProviderTestDTO,
  LibrarianProviderUpdateDTO,
  LibraryDTO,
  LibraryItemDetailDTO,
  LibraryUsageRecordCreateDTO,
  LibraryUsageRecordDTO,
  MemoryCompactDTO,
  MemoryCompactListDTO,
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

export function deleteLibrarianProvider(providerId: string) {
  return fetchJson<void>(
    `/api/librarians/${encodeURIComponent(providerId)}`,
    { method: "DELETE" },
  );
}

export function testLibrarianProvider(providerId: string, testQuery: string) {
  return fetchJson<LibrarianProviderTestDTO>(
    `/api/librarians/${encodeURIComponent(providerId)}/test`,
    jsonInit("POST", { testQuery }),
  );
}

export function startLibrarianOAuth(providerId: string) {
  return fetchJson<LibrarianOAuthStartDTO>(
    `/api/librarians/${encodeURIComponent(providerId)}/oauth/start`,
    { method: "POST" },
  );
}

export function pollLibrarianOAuth(providerId: string) {
  return fetchJson<LibrarianOAuthStatusDTO>(
    `/api/librarians/${encodeURIComponent(providerId)}/oauth/poll`,
    { method: "POST" },
  );
}

export function fetchLibrarianOAuthStatus(providerId: string) {
  return fetchJson<LibrarianOAuthStatusDTO>(
    `/api/librarians/${encodeURIComponent(providerId)}/oauth/status`,
  );
}

export function refreshLibrarianOAuth(providerId: string) {
  return fetchJson<LibrarianOAuthStatusDTO>(
    `/api/librarians/${encodeURIComponent(providerId)}/oauth/refresh`,
    { method: "POST" },
  );
}

export function askLibrarian(payload: LibrarianAskRequestDTO) {
  return fetchJson<LibrarianAskResponseDTO>(
    "/api/librarians/ask",
    jsonInit("POST", payload),
  );
}

export function chatWithLibrarian(payload: LibrarianChatRequestDTO) {
  return fetchJson<LibrarianChatResponseDTO>(
    "/api/librarians/chat",
    jsonInit("POST", payload),
  );
}


export function fetchAgents() {
  return fetchJson<AgentDTO[]>("/api/agents");
}

export function createAgent(payload: AgentCreateDTO) {
  return fetchJson<AgentDTO>("/api/agents", jsonInit("POST", payload));
}

export function fetchAgent(agentId: string) {
  return fetchJson<AgentDTO>(`/api/agents/${encodeURIComponent(agentId)}`);
}

export function updateAgent(agentId: string, payload: AgentUpdateDTO) {
  return fetchJson<AgentDTO>(
    `/api/agents/${encodeURIComponent(agentId)}`,
    jsonInit("PATCH", payload),
  );
}

export function deleteAgent(agentId: string) {
  return fetchJson<void>(
    `/api/agents/${encodeURIComponent(agentId)}`,
    { method: "DELETE" },
  );
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


export function prepareCompact(payload: ContextPrepareCompactDTO) {
  return fetchJson<ContextDTO>(
    "/api/library/contexts/prepare-compact",
    jsonInit("POST", payload),
  );
}

export function archiveContext(contextId: string) {
  return fetchJson<ContextDTO>(
    `/api/library/contexts/${encodeURIComponent(contextId)}/archive`,
    jsonInit("POST", {}),
  );
}

export function fetchMemoryCompacts(params: URLSearchParams) {
  const query = params.toString();
  return fetchJson<MemoryCompactListDTO>(
    `/api/library/compacts${query ? `?${query}` : ""}`,
  );
}

export function fetchCurrentMemoryCompact(project: string | null) {
  const query = project ? `?project=${encodeURIComponent(project)}` : "";
  return fetchJson<MemoryCompactDTO>(`/api/library/compacts/current${query}`);
}

export function fetchMemoryCompact(compactId: string) {
  return fetchJson<MemoryCompactDTO>(
    `/api/library/compacts/${encodeURIComponent(compactId)}`,
  );
}

export function accessContext(contextId: string) {
  return fetchJson<ContextDTO>(
    `/api/library/contexts/${encodeURIComponent(contextId)}/access`,
    jsonInit("POST", {}),
  );
}

export function recordContextAccessEvent(
  contextId: string,
  payload: ContextAccessEventCreateDTO,
) {
  return fetchJson<ContextAccessEventDTO>(
    `/api/library/contexts/${encodeURIComponent(contextId)}/access-events`,
    jsonInit("POST", payload),
  );
}

export function fetchContextAccessEvents(contextId: string, limit = 5) {
  const boundedLimit = Math.min(Math.max(limit, 1), 5);
  return fetchJson<ContextAccessEventDTO[]>(
    `/api/library/contexts/${encodeURIComponent(contextId)}/access-events?limit=${boundedLimit}`,
  );
}

export function recordLibraryUsage(payload: LibraryUsageRecordCreateDTO) {
  return fetchJson<LibraryUsageRecordDTO>(
    "/api/library/usage",
    jsonInit("POST", payload),
  );
}

export function fetchRagStatus() {
  return fetchJson<RagStatusDTO>("/api/library/contexts/rag/status");
}
