import { BACKEND_BASE_URL } from "@/lib/backend/config";

export class BackendRequestError extends Error {
  constructor(
    public readonly status: number,
    path: string,
  ) {
    super(`Backend request failed: ${status} ${path}`);
    this.name = "BackendRequestError";
  }
}

export async function backendFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { headers, ...restInit } = init;
  const response = await fetch(`${BACKEND_BASE_URL}${path}`, {
    cache: "no-store",
    ...restInit,
    headers: { Accept: "application/json", ...headers },
  });

  if (!response.ok) {
    throw new BackendRequestError(response.status, path);
  }

  return response.json() as Promise<T>;
}
