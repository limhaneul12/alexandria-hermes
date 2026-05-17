export const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export const HEALTH_ENDPOINT = `${BACKEND_BASE_URL}/health/live`;
export const BACKEND_OPERATOR_API_KEY = process.env.ALEXANDRIA_OPERATOR_API_KEY ?? "";
export const BACKEND_OPERATOR_API_KEY_HEADER = "x-operator-api-key";
