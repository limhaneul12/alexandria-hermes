import {
  LIBRARIAN_AUTH_TYPES,
  PROVIDER_TYPES,
  type LibrarianProviderCredentialMode,
  type ProviderType,
} from "@/types/library";

const OPENAI_CODEX_CONFIG_KEYS = [
  "device_authorization_url",
  "device_token_url",
  "issuer",
  "redirect_uri",
  "token_url",
  "verification_uri",
  "client_id",
  "scope",
] as const;

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isProviderType(value: unknown): value is ProviderType {
  return typeof value === "string" && (PROVIDER_TYPES as readonly string[]).includes(value);
}

export function isCredentialMode(
  value: unknown,
): value is LibrarianProviderCredentialMode {
  return (
    typeof value === "string" &&
    (LIBRARIAN_AUTH_TYPES as readonly string[]).includes(value)
  );
}

export function safeLibrarianProviderConfig(
  value: unknown,
  providerType: ProviderType,
): Record<string, unknown> {
  if (!isRecord(value)) return {};
  const config: Record<string, unknown> = {};
  if (providerType === "OPENAI_CODEX") {
    for (const key of OPENAI_CODEX_CONFIG_KEYS) {
      const rawValue = value[key];
      if (typeof rawValue === "string" && rawValue.trim()) {
        config[key] = rawValue.trim();
      }
    }
    return config;
  }
  if (typeof value.model === "string" && value.model.trim()) {
    config.model = value.model.trim();
  }
  if (typeof value.base_url === "string" && value.base_url.trim()) {
    config.base_url = value.base_url.trim();
  }
  return config;
}
