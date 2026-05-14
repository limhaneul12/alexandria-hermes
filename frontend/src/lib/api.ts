import type {
  AgentDTO,
  CategoryCreateDTO,
  CategoryDTO,
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

