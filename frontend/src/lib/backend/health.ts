import { BACKEND_BASE_URL } from "@/lib/backend/config";

export type HealthStatus = "ok" | "offline";

export type HealthPayload = {
  status: HealthStatus;
  timestamp?: string;
};

export async function fetchBackendHealth(): Promise<HealthPayload> {
  const response = await fetch(`${BACKEND_BASE_URL}/health/live`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Backend health check failed: ${response.status}`);
  }

  const payload = await response.json();
  return payload as HealthPayload;
}
