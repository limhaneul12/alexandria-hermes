import { isRecord } from "../../_shared/request-parsing";
import {
  MEMORY_COMPACT_STATUSES,
  type MemoryCompactCreateDTO,
  type MemoryCompactStatus,
} from "@/types/library";

const memoryCompactStatuses = new Set<MemoryCompactStatus>(MEMORY_COMPACT_STATUSES);

type MemoryCompactErrorCode =
  | "INVALID_MEMORY_COMPACT_PAYLOAD"
  | "REQUIRED_MEMORY_COMPACT_FIELDS"
  | "INVALID_MEMORY_COMPACT_DATE_RANGE"
  | "INVALID_MEMORY_COMPACT_STATUS"
  | "INVALID_MEMORY_COMPACT_SOURCE_REFS";

export type MemoryCompactParseResult =
  | { ok: true; payload: MemoryCompactCreateDTO }
  | { ok: false; code: MemoryCompactErrorCode; message: string };

function requiredText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function optionalText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function dateText(value: unknown): string | null {
  const text = requiredText(value);
  if (!text) return null;
  return Number.isNaN(Date.parse(text)) ? null : text;
}

function compactStatus(value: unknown): MemoryCompactStatus | null {
  if (typeof value !== "string") return null;
  return memoryCompactStatuses.has(value as MemoryCompactStatus)
    ? value as MemoryCompactStatus
    : null;
}

function sourceRefs(value: unknown): MemoryCompactCreateDTO["sourceRefs"] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;
  const refs: MemoryCompactCreateDTO["sourceRefs"] = [];
  for (const item of value) {
    if (!isRecord(item)) return null;
    const sourceType = requiredText(item.sourceType);
    const sourceId = requiredText(item.sourceId);
    const title = requiredText(item.title);
    const detailPath = requiredText(item.detailPath);
    if (!sourceType || !sourceId || !title || !detailPath) return null;
    refs.push({ sourceType, sourceId, title, detailPath });
  }
  return refs;
}

export function parseMemoryCompactCreateBody(
  rawBody: unknown,
): MemoryCompactParseResult {
  if (!isRecord(rawBody)) {
    return {
      ok: false,
      code: "INVALID_MEMORY_COMPACT_PAYLOAD",
      message: "Invalid Memory Compact payload.",
    };
  }

  const coveredFrom = dateText(rawBody.coveredFrom);
  const coveredTo = dateText(rawBody.coveredTo);
  const markdownBody = requiredText(rawBody.markdownBody);
  if (!coveredFrom || !coveredTo || !markdownBody) {
    return {
      ok: false,
      code: "REQUIRED_MEMORY_COMPACT_FIELDS",
      message: "Memory Compact date range and markdown body are required.",
    };
  }
  if (Date.parse(coveredFrom) > Date.parse(coveredTo)) {
    return {
      ok: false,
      code: "INVALID_MEMORY_COMPACT_DATE_RANGE",
      message: "Memory Compact date range is invalid.",
    };
  }

  const status = compactStatus(rawBody.status);
  if (!status) {
    return {
      ok: false,
      code: "INVALID_MEMORY_COMPACT_STATUS",
      message: "Invalid Memory Compact status.",
    };
  }

  const parsedSourceRefs = sourceRefs(rawBody.sourceRefs);
  if (parsedSourceRefs === null) {
    return {
      ok: false,
      code: "INVALID_MEMORY_COMPACT_SOURCE_REFS",
      message: "Invalid Memory Compact source refs.",
    };
  }

  return {
    ok: true,
    payload: {
      project: rawBody.project === null ? null : optionalText(rawBody.project),
      coveredFrom,
      coveredTo,
      markdownBody,
      status,
      sourceRefs: parsedSourceRefs,
    },
  };
}
