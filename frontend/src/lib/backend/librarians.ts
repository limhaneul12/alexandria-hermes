import { backendFetch } from "@/lib/backend/client";
import type {
  AgentDTO,
  AgentCreateDTO,
  AgentUpdateDTO,
  AuthType,
  LibrarianOAuthStartDTO,
  LibrarianOAuthStatusDTO,
  LibrarianAskRequestDTO,
  LibrarianAskResponseDTO,
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

type BackendLibrarianOAuthStart = {
  provider_id: string;
  status: string;
  user_code: string;
  verification_uri: string;
  verification_uri_complete: string | null;
  expires_at: string;
  interval_seconds: number;
};

type BackendLibrarianOAuthStatus = {
  provider_id: string;
  status: string;
  expires_at: string | null;
  refresh_required: boolean;
  message: string | null;
  [key: string]: unknown;
};

const OAUTH_AUTHORIZED_RESPONSE_KEY = "connected";

type BackendAgent = {
  id: string;
  name: string;
  provider: string;
  description: string | null;
  capabilities: string[];
  preferred_librarian_provider: string | null;
  preferred_librarian_model: string | null;
  max_librarian_agents: number;
  librarian_role_prompt: string | null;
  librarian_role: AgentDTO["librarianRole"];
  librarian_specialties: string[];
  librarian_routing_priority: number;
  librarian_enabled: boolean;
  created_at: string;
  updated_at: string;
};

type BackendLibrarianDelegate = {
  profile_id: string;
  provider_id: string | null;
  status: string;
  delegate_type: string;
  summary: string;
  matched_specialties: string[];
};

type BackendLibrarianAskResponse = {
  job_id: string;
  status: string;
  decision: string;
  librarian_available: boolean;
  self_acquisition_allowed: boolean;
  recommendation: string;
  provider_id: string | null;
  candidate_id: string | null;
  librarian_profile_id: string | null;
  librarian_model: string | null;
  librarian_role_prompt: string | null;
  max_librarian_agents: number | null;
  route_preview: string[];
  selected_profiles: string[];
  matched_specialties: string[];
  quality_review_added: boolean;
  routing_reason: string;
  delegates: BackendLibrarianDelegate[];
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
  } else if (providerType === "OPENAI_CODEX") {
    for (const key of ["device_authorization_url", "device_token_url", "issuer", "redirect_uri", "token_url", "verification_uri", "client_id", "scope"] as const) {
      if (typeof config[key] === "string" && config[key].trim()) {
        safeConfig[key] = config[key].trim();
      }
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
  if (payload.authType === "API_KEY" && payload.credential !== undefined) {
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

function toOAuthStartDTO(result: BackendLibrarianOAuthStart): LibrarianOAuthStartDTO {
  return {
    providerId: result.provider_id,
    status: result.status,
    userCode: result.user_code,
    verificationUri: result.verification_uri,
    verificationUriComplete: result.verification_uri_complete,
    expiresAt: result.expires_at,
    intervalSeconds: result.interval_seconds,
  };
}

function toOAuthStatusDTO(result: BackendLibrarianOAuthStatus): LibrarianOAuthStatusDTO {
  return {
    providerId: result.provider_id,
    status: result.status,
    authorized: result[OAUTH_AUTHORIZED_RESPONSE_KEY] === true,
    expiresAt: result.expires_at,
    refreshRequired: result.refresh_required,
    message: result.message,
  };
}

function toAgentDTO(agent: BackendAgent): AgentDTO {
  return {
    id: agent.id,
    name: agent.name,
    provider: agent.provider,
    description: agent.description,
    capabilities: agent.capabilities,
    preferredLibrarianProvider: agent.preferred_librarian_provider,
    preferredLibrarianModel: agent.preferred_librarian_model,
    maxLibrarianAgents: agent.max_librarian_agents,
    librarianRolePrompt: agent.librarian_role_prompt,
    librarianRole: agent.librarian_role,
    librarianSpecialties: agent.librarian_specialties,
    librarianRoutingPriority: agent.librarian_routing_priority,
    librarianEnabled: agent.librarian_enabled,
    createdAt: agent.created_at,
    updatedAt: agent.updated_at,
  };
}

function toBackendAgentPayload(payload: AgentCreateDTO): Record<string, unknown> {
  return {
    name: payload.name,
    provider: payload.provider,
    description: payload.description,
    capabilities: payload.capabilities,
    preferred_librarian_provider: payload.preferredLibrarianProvider,
    preferred_librarian_model: payload.preferredLibrarianModel,
    max_librarian_agents: payload.maxLibrarianAgents,
    librarian_role_prompt: payload.librarianRolePrompt,
    librarian_role: payload.librarianRole,
    librarian_specialties: payload.librarianSpecialties,
    librarian_routing_priority: payload.librarianRoutingPriority,
    librarian_enabled: payload.librarianEnabled,
  };
}

function toBackendAgentPatchPayload(payload: AgentUpdateDTO): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  if (payload.name !== undefined) body.name = payload.name;
  if (payload.provider !== undefined) body.provider = payload.provider;
  if (payload.description !== undefined) body.description = payload.description;
  if (payload.capabilities !== undefined) body.capabilities = payload.capabilities;
  if (payload.preferredLibrarianProvider !== undefined) {
    body.preferred_librarian_provider = payload.preferredLibrarianProvider;
  }
  if (payload.preferredLibrarianModel !== undefined) {
    body.preferred_librarian_model = payload.preferredLibrarianModel;
  }
  if (payload.maxLibrarianAgents !== undefined) {
    body.max_librarian_agents = payload.maxLibrarianAgents;
  }
  if (payload.librarianRolePrompt !== undefined) {
    body.librarian_role_prompt = payload.librarianRolePrompt;
  }
  if (payload.librarianRole !== undefined) body.librarian_role = payload.librarianRole;
  if (payload.librarianSpecialties !== undefined) {
    body.librarian_specialties = payload.librarianSpecialties;
  }
  if (payload.librarianRoutingPriority !== undefined) {
    body.librarian_routing_priority = payload.librarianRoutingPriority;
  }
  if (payload.librarianEnabled !== undefined) {
    body.librarian_enabled = payload.librarianEnabled;
  }
  return body;
}

function toBackendAskPayload(payload: LibrarianAskRequestDTO): Record<string, unknown> {
  const body: Record<string, unknown> = {
    prompt: payload.prompt,
    agent_name: payload.agentName ?? "Hermes",
    delegate_to_librarian: payload.delegateToLibrarian ?? false,
  };
  if (payload.project !== undefined) body.project = payload.project;
  if (payload.taskSummary !== undefined) body.task_summary = payload.taskSummary;
  if (payload.providerId !== undefined) body.provider_id = payload.providerId;
  if (payload.librarianProfileId !== undefined) {
    body.librarian_profile_id = payload.librarianProfileId;
  }
  if (payload.librarianModel !== undefined) body.librarian_model = payload.librarianModel;
  if (payload.librarianRolePrompt !== undefined) {
    body.librarian_role_prompt = payload.librarianRolePrompt;
  }
  if (payload.maxLibrarianAgents !== undefined) {
    body.max_librarian_agents = payload.maxLibrarianAgents;
  }
  if (payload.routingSpecialties !== undefined) {
    body.routing_specialties = payload.routingSpecialties;
  }
  return body;
}

function toLibrarianAskResponseDTO(
  response: BackendLibrarianAskResponse,
): LibrarianAskResponseDTO {
  return {
    jobId: response.job_id,
    status: response.status,
    decision: response.decision,
    librarianAvailable: response.librarian_available,
    selfAcquisitionAllowed: response.self_acquisition_allowed,
    recommendation: response.recommendation,
    providerId: response.provider_id,
    candidateId: response.candidate_id,
    librarianProfileId: response.librarian_profile_id,
    librarianModel: response.librarian_model,
    librarianRolePrompt: response.librarian_role_prompt,
    maxLibrarianAgents: response.max_librarian_agents,
    routePreview: response.route_preview,
    selectedProfiles: response.selected_profiles,
    matchedSpecialties: response.matched_specialties,
    qualityReviewAdded: response.quality_review_added,
    routingReason: response.routing_reason,
    delegates: response.delegates.map((delegate) => ({
      profileId: delegate.profile_id,
      providerId: delegate.provider_id,
      status: delegate.status,
      delegateType: delegate.delegate_type,
      summary: delegate.summary,
      matchedSpecialties: delegate.matched_specialties,
    })),
  };
}

export async function loadLibrarianProvidersFromBackend(): Promise<LibrarianProviderDTO[]> {
  const providers = await backendFetch<BackendLibrarianProvider[]>("/settings/connections");
  return providers.map(toProviderDTO);
}

export async function createLibrarianProviderInBackend(
  payload: LibrarianProviderCreateDTO,
): Promise<LibrarianProviderDTO> {
  const provider = await backendFetch<BackendLibrarianProvider>(
    "/settings/connections",
    jsonInit("POST", toBackendProviderPayload(payload)),
  );
  return toProviderDTO(provider);
}

export async function updateLibrarianProviderInBackend(
  providerId: string,
  payload: LibrarianProviderUpdateDTO,
): Promise<LibrarianProviderDTO> {
  const provider = await backendFetch<BackendLibrarianProvider>(
    `/settings/connections/${encodeURIComponent(providerId)}`,
    jsonInit("PATCH", toBackendProviderPayload(payload)),
  );
  return toProviderDTO(provider);
}

export async function deleteLibrarianProviderInBackend(
  providerId: string,
): Promise<void> {
  await backendFetch<void>(
    `/settings/connections/${encodeURIComponent(providerId)}`,
    { method: "DELETE" },
  );
}

export async function testLibrarianProviderInBackend(
  providerId: string,
  testQuery: string,
): Promise<LibrarianProviderTestDTO> {
  const result = await backendFetch<BackendLibrarianProviderTest>(
    `/settings/connections/${encodeURIComponent(providerId)}/test`,
    jsonInit("POST", { test_query: testQuery }),
  );
  return toProviderTestDTO(result);
}

export async function startLibrarianOAuthInBackend(
  providerId: string,
): Promise<LibrarianOAuthStartDTO> {
  const result = await backendFetch<BackendLibrarianOAuthStart>(
    `/settings/connections/${encodeURIComponent(providerId)}/oauth/start`,
    { method: "POST" },
  );
  return toOAuthStartDTO(result);
}

export async function pollLibrarianOAuthInBackend(
  providerId: string,
): Promise<LibrarianOAuthStatusDTO> {
  const result = await backendFetch<BackendLibrarianOAuthStatus>(
    `/settings/connections/${encodeURIComponent(providerId)}/oauth/poll`,
    { method: "POST" },
  );
  return toOAuthStatusDTO(result);
}

export async function loadLibrarianOAuthStatusFromBackend(
  providerId: string,
): Promise<LibrarianOAuthStatusDTO> {
  const result = await backendFetch<BackendLibrarianOAuthStatus>(
    `/settings/connections/${encodeURIComponent(providerId)}/oauth/status`,
  );
  return toOAuthStatusDTO(result);
}

export async function refreshLibrarianOAuthInBackend(
  providerId: string,
): Promise<LibrarianOAuthStatusDTO> {
  const result = await backendFetch<BackendLibrarianOAuthStatus>(
    `/settings/connections/${encodeURIComponent(providerId)}/oauth/refresh`,
    { method: "POST" },
  );
  return toOAuthStatusDTO(result);
}

export async function loadAgentsFromBackend(): Promise<AgentDTO[]> {
  const agents = await backendFetch<BackendAgent[]>("/librarians/profiles");
  return agents.map(toAgentDTO);
}

export async function createAgentInBackend(
  payload: AgentCreateDTO,
): Promise<AgentDTO> {
  const agent = await backendFetch<BackendAgent>(
    "/librarians/profiles",
    jsonInit("POST", toBackendAgentPayload(payload)),
  );
  return toAgentDTO(agent);
}

export async function loadAgentFromBackend(agentId: string): Promise<AgentDTO> {
  const agent = await backendFetch<BackendAgent>(
    `/librarians/profiles/${encodeURIComponent(agentId)}`,
  );
  return toAgentDTO(agent);
}

export async function updateAgentInBackend(
  agentId: string,
  payload: AgentUpdateDTO,
): Promise<AgentDTO> {
  const agent = await backendFetch<BackendAgent>(
    `/librarians/profiles/${encodeURIComponent(agentId)}`,
    jsonInit("PATCH", toBackendAgentPatchPayload(payload)),
  );
  return toAgentDTO(agent);
}

export async function deleteAgentInBackend(agentId: string): Promise<void> {
  await backendFetch<void>(
    `/librarians/profiles/${encodeURIComponent(agentId)}`,
    { method: "DELETE" },
  );
}

export async function askLibrarianInBackend(
  payload: LibrarianAskRequestDTO,
): Promise<LibrarianAskResponseDTO> {
  const response = await backendFetch<BackendLibrarianAskResponse>(
    "/librarians/ask",
    jsonInit("POST", toBackendAskPayload(payload)),
  );
  return toLibrarianAskResponseDTO(response);
}
