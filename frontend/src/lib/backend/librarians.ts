import { backendFetch } from "@/lib/backend/client";
import type {
  AgentDTO,
  AuthType,
  LibrarianProviderCreateDTO,
  LibrarianProviderDTO,
  LibrarianProviderTestDTO,
  LibrarianProviderUpdateDTO,
  ProviderType,
} from "@/types/library";

type BackendLibrarianProvider = {
  id: string;
  name: string;
  provider_type: ProviderType;
  auth_type: AuthType;
  enabled: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

type BackendLibrarianProviderTest = {
  provider_id: string;
  ok: boolean;
  message: string;
};

type BackendAgent = {
  id: string;
  name: string;
  provider: string;
  description: string | null;
  capabilities: string[];
  created_at: string;
  updated_at: string;
};

function jsonInit(method: "POST" | "PATCH", body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

function toSafeProviderConfig(
  config: Record<string, unknown>,
  providerType: ProviderType,
): Record<string, unknown> {
  const safeConfig: Record<string, unknown> = {};
  if (providerType === "MINIO") {
    if (typeof config.endpoint === "string" && config.endpoint.trim()) {
      safeConfig.endpoint = config.endpoint.trim();
    }
    if (typeof config.bucket === "string" && config.bucket.trim()) {
      safeConfig.bucket = config.bucket.trim();
    }
    if (typeof config.prefix === "string") {
      safeConfig.prefix = config.prefix.trim();
    }
    if (typeof config.region === "string" && config.region.trim()) {
      safeConfig.region = config.region.trim();
    }
    if (typeof config.use_ssl === "boolean") {
      safeConfig.use_ssl = config.use_ssl;
    }
  } else {
    if (typeof config.model === "string" && config.model.trim()) {
      safeConfig.model = config.model.trim();
    }
    if (typeof config.base_url === "string" && config.base_url.trim()) {
      safeConfig.base_url = config.base_url.trim();
    }
  }
  return safeConfig;
}

function toBackendProviderPayload(
  payload: LibrarianProviderCreateDTO | LibrarianProviderUpdateDTO,
) {
  const body: Record<string, unknown> = {};
  if (payload.name !== undefined) body.name = payload.name;
  if (payload.providerType !== undefined) body.provider_type = payload.providerType;
  if (payload.authType !== undefined) body.auth_type = payload.authType;
  if (payload.enabled !== undefined) body.enabled = payload.enabled;
  const providerType = payload.providerType;
  if (payload.config !== undefined && providerType !== undefined) {
    body.config = toSafeProviderConfig(payload.config, providerType);
  }
  if (payload.credential !== undefined) {
    body.api_key = payload.credential;
  }
  return body;
}

function toProviderDTO(provider: BackendLibrarianProvider): LibrarianProviderDTO {
  return {
    id: provider.id,
    name: provider.name,
    providerType: provider.provider_type,
    authType: provider.auth_type,
    enabled: provider.enabled,
    config: toSafeProviderConfig(provider.config, provider.provider_type),
    createdAt: provider.created_at,
    updatedAt: provider.updated_at,
  };
}

function toProviderTestDTO(result: BackendLibrarianProviderTest): LibrarianProviderTestDTO {
  return {
    providerId: result.provider_id,
    ok: result.ok,
    message: result.ok
      ? "사서 인증 검증에 성공했습니다."
      : "사서 인증 검증에 실패했습니다. 설정을 확인하세요.",
  };
}

function toAgentDTO(agent: BackendAgent): AgentDTO {
  return {
    id: agent.id,
    name: agent.name,
    provider: agent.provider,
    description: agent.description,
    capabilities: agent.capabilities,
    createdAt: agent.created_at,
    updatedAt: agent.updated_at,
  };
}

export async function loadLibrarianProvidersFromBackend(): Promise<LibrarianProviderDTO[]> {
  const providers = await backendFetch<BackendLibrarianProvider[]>("/settings/librarians");
  return providers.map(toProviderDTO);
}

export async function createLibrarianProviderInBackend(
  payload: LibrarianProviderCreateDTO,
): Promise<LibrarianProviderDTO> {
  const provider = await backendFetch<BackendLibrarianProvider>(
    "/settings/librarians",
    jsonInit("POST", toBackendProviderPayload(payload)),
  );
  return toProviderDTO(provider);
}

export async function updateLibrarianProviderInBackend(
  providerId: string,
  payload: LibrarianProviderUpdateDTO,
): Promise<LibrarianProviderDTO> {
  const provider = await backendFetch<BackendLibrarianProvider>(
    `/settings/librarians/${encodeURIComponent(providerId)}`,
    jsonInit("PATCH", toBackendProviderPayload(payload)),
  );
  return toProviderDTO(provider);
}

export async function testLibrarianProviderInBackend(
  providerId: string,
  testQuery: string,
): Promise<LibrarianProviderTestDTO> {
  const result = await backendFetch<BackendLibrarianProviderTest>(
    `/settings/librarians/${encodeURIComponent(providerId)}/test`,
    jsonInit("POST", { test_query: testQuery }),
  );
  return toProviderTestDTO(result);
}

export async function loadAgentsFromBackend(): Promise<AgentDTO[]> {
  const agents = await backendFetch<BackendAgent[]>("/agents");
  return agents.map(toAgentDTO);
}
