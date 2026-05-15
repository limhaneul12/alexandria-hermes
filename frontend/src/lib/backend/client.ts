import {
  BACKEND_BASE_URL,
  BACKEND_OPERATOR_API_KEY,
  BACKEND_OPERATOR_API_KEY_HEADER,
} from "@/lib/backend/config";

export class BackendRequestError extends Error {
  constructor(
    public readonly status: number,
    path: string,
    public readonly payload: unknown,
  ) {
    super(`Backend request failed: ${status} ${path}`);
    this.name = "BackendRequestError";
  }
}

export async function backendFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { headers, ...restInit } = init;
  const requestHeaders = new Headers(headers);
  if (!requestHeaders.has("Accept")) {
    requestHeaders.set("Accept", "application/json");
  }
  if (BACKEND_OPERATOR_API_KEY) {
    requestHeaders.set(BACKEND_OPERATOR_API_KEY_HEADER, BACKEND_OPERATOR_API_KEY);
  }
  const response = await fetch(`${BACKEND_BASE_URL}${path}`, {
    cache: "no-store",
    ...restInit,
    headers: requestHeaders,
  });

  if (!response.ok) {
    throw new BackendRequestError(response.status, path, await readErrorPayload(response));
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function readErrorPayload(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return undefined;
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}
