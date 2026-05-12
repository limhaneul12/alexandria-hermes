import type { DashboardDTO, LibraryDTO, SkillDetailDTO } from "@/types/library";

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export function fetchDashboard() {
  return fetchJson<DashboardDTO>("/api/dashboard");
}

export function fetchLibrary(params: URLSearchParams) {
  const query = params.toString();
  return fetchJson<LibraryDTO>(`/api/library${query ? `?${query}` : ""}`);
}

export function fetchSkillDetail(skillId: number | string) {
  return fetchJson<SkillDetailDTO>(`/api/skills/${skillId}`);
}
