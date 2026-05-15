import type { AgentCreateDTO, AgentUpdateDTO } from "@/types/library";

type PayloadResult<T> =
  | { ok: true; payload: T }
  | { ok: false; message: string };

const invalidAgentMessage = "에이전트 설정을 확인하세요.";
const requiredAgentMessage = "에이전트 이름과 provider가 필요합니다.";
const agentPayloadFields = new Set([
  "name",
  "provider",
  "description",
  "capabilities",
  "preferredLibrarianProvider",
  "preferredLibrarianModel",
  "maxLibrarianAgents",
  "librarianRolePrompt",
  "librarianRole",
  "librarianSpecialties",
  "librarianRoutingPriority",
  "librarianEnabled",
]);
const librarianRoles = new Set([
  "DEFAULT_SEARCH",
  "SPECIALIST",
  "QUALITY_REVIEWER",
  "ARCHIVIST_CURATOR",
]);

export function isAgentRequestRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function createAgentPayload(body: Record<string, unknown>): PayloadResult<AgentCreateDTO> {
  if (!hasOnlyAgentPayloadFields(body)) {
    return { ok: false, message: invalidAgentMessage };
  }
  const name = requiredString(body.name);
  const provider = requiredString(body.provider);
  if (name === null || provider === null) {
    return { ok: false, message: requiredAgentMessage };
  }
  const capabilities = requiredStringList(body.capabilities);
  const maxLibrarianAgents = requiredBoundedAgentCount(body.maxLibrarianAgents);
  if (capabilities === null || maxLibrarianAgents === null) {
    return { ok: false, message: invalidAgentMessage };
  }
  const description = nullableString(body.description);
  const preferredLibrarianProvider = nullableString(body.preferredLibrarianProvider);
  const preferredLibrarianModel = nullableString(body.preferredLibrarianModel);
  const librarianRolePrompt = nullableString(body.librarianRolePrompt);
  const librarianRole = requiredRole(body.librarianRole);
  const librarianSpecialties = requiredStringList(body.librarianSpecialties);
  const librarianRoutingPriority = requiredRoutingPriority(body.librarianRoutingPriority);
  const librarianEnabled = requiredBoolean(body.librarianEnabled);
  if (
    description === undefined ||
    preferredLibrarianProvider === undefined ||
    preferredLibrarianModel === undefined ||
    librarianRolePrompt === undefined ||
    librarianRole === null ||
    librarianSpecialties === null ||
    librarianRoutingPriority === null ||
    librarianEnabled === null
  ) {
    return { ok: false, message: invalidAgentMessage };
  }
  return {
    ok: true,
    payload: {
      name,
      provider,
      description,
      capabilities,
      preferredLibrarianProvider,
      preferredLibrarianModel,
      maxLibrarianAgents,
      librarianRolePrompt,
      librarianRole,
      librarianSpecialties,
      librarianRoutingPriority,
      librarianEnabled,
    },
  };
}

export function updateAgentPayload(body: Record<string, unknown>): PayloadResult<AgentUpdateDTO> {
  if (!hasOnlyAgentPayloadFields(body)) {
    return { ok: false, message: invalidAgentMessage };
  }
  const payload: AgentUpdateDTO = {};
  let fieldCount = 0;

  if ("name" in body) {
    const name = requiredString(body.name);
    if (name === null) return { ok: false, message: invalidAgentMessage };
    payload.name = name;
    fieldCount += 1;
  }
  if ("provider" in body) {
    const provider = requiredString(body.provider);
    if (provider === null) return { ok: false, message: invalidAgentMessage };
    payload.provider = provider;
    fieldCount += 1;
  }
  if ("description" in body) {
    const description = nullableString(body.description);
    if (description === undefined) return { ok: false, message: invalidAgentMessage };
    payload.description = description;
    fieldCount += 1;
  }
  if ("capabilities" in body) {
    const capabilities = requiredStringList(body.capabilities);
    if (capabilities === null) return { ok: false, message: invalidAgentMessage };
    payload.capabilities = capabilities;
    fieldCount += 1;
  }
  if ("preferredLibrarianProvider" in body) {
    const providerId = nullableString(body.preferredLibrarianProvider);
    if (providerId === undefined) return { ok: false, message: invalidAgentMessage };
    payload.preferredLibrarianProvider = providerId;
    fieldCount += 1;
  }
  if ("preferredLibrarianModel" in body) {
    const model = nullableString(body.preferredLibrarianModel);
    if (model === undefined) return { ok: false, message: invalidAgentMessage };
    payload.preferredLibrarianModel = model;
    fieldCount += 1;
  }
  if ("maxLibrarianAgents" in body) {
    const maxAgents = requiredBoundedAgentCount(body.maxLibrarianAgents);
    if (maxAgents === null) return { ok: false, message: invalidAgentMessage };
    payload.maxLibrarianAgents = maxAgents;
    fieldCount += 1;
  }
  if ("librarianRolePrompt" in body) {
    const rolePrompt = nullableString(body.librarianRolePrompt);
    if (rolePrompt === undefined) return { ok: false, message: invalidAgentMessage };
    payload.librarianRolePrompt = rolePrompt;
    fieldCount += 1;
  }
  if ("librarianRole" in body) {
    const role = requiredRole(body.librarianRole);
    if (role === null) return { ok: false, message: invalidAgentMessage };
    payload.librarianRole = role;
    fieldCount += 1;
  }
  if ("librarianSpecialties" in body) {
    const specialties = requiredStringList(body.librarianSpecialties);
    if (specialties === null) return { ok: false, message: invalidAgentMessage };
    payload.librarianSpecialties = specialties;
    fieldCount += 1;
  }
  if ("librarianRoutingPriority" in body) {
    const priority = requiredRoutingPriority(body.librarianRoutingPriority);
    if (priority === null) return { ok: false, message: invalidAgentMessage };
    payload.librarianRoutingPriority = priority;
    fieldCount += 1;
  }
  if ("librarianEnabled" in body) {
    const enabled = requiredBoolean(body.librarianEnabled);
    if (enabled === null) return { ok: false, message: invalidAgentMessage };
    payload.librarianEnabled = enabled;
    fieldCount += 1;
  }

  if (fieldCount === 0) return { ok: false, message: invalidAgentMessage };
  return { ok: true, payload };
}

function requiredString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function hasOnlyAgentPayloadFields(body: Record<string, unknown>): boolean {
  return Object.keys(body).every((key) => agentPayloadFields.has(key));
}

function nullableString(value: unknown): string | null | undefined {
  if (value === undefined || value === null) return null;
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function requiredStringList(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  if (!value.every((item) => typeof item === "string")) return null;
  return value;
}

function requiredBoundedAgentCount(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isInteger(value)) return null;
  if (value < 1 || value > 6) return null;
  return value;
}

function requiredRoutingPriority(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isInteger(value)) return null;
  if (value < 0) return null;
  return value;
}

function requiredBoolean(value: unknown): boolean | null {
  if (typeof value !== "boolean") return null;
  return value;
}

function requiredRole(value: unknown): AgentCreateDTO["librarianRole"] | null {
  if (typeof value !== "string") return null;
  if (!librarianRoles.has(value)) return null;
  return value as AgentCreateDTO["librarianRole"];
}
