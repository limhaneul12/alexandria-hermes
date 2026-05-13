import { backendFetch } from "@/lib/backend/client";

export type HealthStatus = "ok" | "offline";

export type HealthPayload = {
  status: HealthStatus;
  timestamp?: string;
};

export async function fetchBackendHealth(): Promise<HealthPayload> {
  return backendFetch<HealthPayload>("/health/live");
}
