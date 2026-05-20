import { isRecord } from "../../_shared/request-parsing";
import type {
  LibrarianChatMode,
  LibrarianChatRequestDTO,
  LibrarianChatTarget,
} from "@/types/library";

const chatModes = new Set<LibrarianChatMode>([
  "DIRECT_SEARCH",
  "DELEGATE",
  "SEARCH_AND_DELEGATE",
]);
const chatTargets = new Set<LibrarianChatTarget>([
  "SKILL",
  "PROMPT",
  "CONTEXT",
  "MEMORY_COMPACT",
]);

type LibrarianChatErrorCode =
  | "INVALID_LIBRARIAN_CHAT_PAYLOAD"
  | "REQUIRED_LIBRARIAN_CHAT_PROMPT"
  | "INVALID_LIBRARIAN_CHAT_MODE"
  | "INVALID_LIBRARIAN_CHAT_TARGETS"
  | "INVALID_LIBRARIAN_CHAT_LIMIT";

export type LibrarianChatParseResult =
  | { ok: true; payload: LibrarianChatRequestDTO }
  | { ok: false; code: LibrarianChatErrorCode; message: string };

function requiredText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function optionalText(value: unknown): string | null | undefined {
  if (value === null) return null;
  if (value === undefined) return undefined;
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function chatMode(value: unknown): LibrarianChatMode | null | undefined {
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "string") return null;
  return chatModes.has(value as LibrarianChatMode)
    ? value as LibrarianChatMode
    : null;
}

function targetList(value: unknown): LibrarianChatTarget[] | null | undefined {
  if (value === undefined || value === null) return undefined;
  if (!Array.isArray(value)) return null;
  const targets: LibrarianChatTarget[] = [];
  for (const item of value) {
    if (typeof item !== "string" || !chatTargets.has(item as LibrarianChatTarget)) {
      return null;
    }
    const target = item as LibrarianChatTarget;
    if (!targets.includes(target)) targets.push(target);
  }
  return targets.length ? targets : undefined;
}

function chatLimit(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.min(Math.max(Math.trunc(value), 1), 10);
}

function delegateLimit(value: unknown): number | null | undefined {
  if (value === null) return null;
  if (value === undefined) return undefined;
  if (typeof value !== "number" || !Number.isFinite(value)) return undefined;
  return Math.min(Math.max(Math.trunc(value), 1), 6);
}

export function parseLibrarianChatBody(rawBody: unknown): LibrarianChatParseResult {
  if (!isRecord(rawBody)) {
    return {
      ok: false,
      code: "INVALID_LIBRARIAN_CHAT_PAYLOAD",
      message: "Invalid librarian chat payload.",
    };
  }

  const prompt = requiredText(rawBody.prompt);
  if (!prompt) {
    return {
      ok: false,
      code: "REQUIRED_LIBRARIAN_CHAT_PROMPT",
      message: "Prompt is required.",
    };
  }

  const mode = chatMode(rawBody.mode);
  if (mode === null) {
    return {
      ok: false,
      code: "INVALID_LIBRARIAN_CHAT_MODE",
      message: "Invalid librarian chat mode.",
    };
  }

  const targets = targetList(rawBody.targets);
  if (targets === null) {
    return {
      ok: false,
      code: "INVALID_LIBRARIAN_CHAT_TARGETS",
      message: "Invalid librarian chat targets.",
    };
  }

  const limit = chatLimit(rawBody.limit);
  if (limit === null) {
    return {
      ok: false,
      code: "INVALID_LIBRARIAN_CHAT_LIMIT",
      message: "Invalid librarian chat limit.",
    };
  }

  const payload: LibrarianChatRequestDTO = { prompt, limit };
  if (mode !== undefined) payload.mode = mode;
  if (targets !== undefined) payload.targets = targets;
  const providerId = optionalText(rawBody.providerId);
  if (providerId !== undefined) payload.providerId = providerId;
  const librarianProfileId = optionalText(rawBody.librarianProfileId);
  if (librarianProfileId !== undefined) payload.librarianProfileId = librarianProfileId;
  const librarianProfileName = optionalText(rawBody.librarianProfileName);
  if (librarianProfileName !== undefined) {
    payload.librarianProfileName = librarianProfileName;
  }
  const librarianModel = optionalText(rawBody.librarianModel);
  if (librarianModel !== undefined) payload.librarianModel = librarianModel;
  const librarianRolePrompt = optionalText(rawBody.librarianRolePrompt);
  if (librarianRolePrompt !== undefined) {
    payload.librarianRolePrompt = librarianRolePrompt;
  }
  const maxLibrarianAgents = delegateLimit(rawBody.maxLibrarianAgents);
  if (maxLibrarianAgents !== undefined) {
    payload.maxLibrarianAgents = maxLibrarianAgents;
  }
  return { ok: true, payload };
}
