import { isRecord } from "../../_shared/request-parsing";
import type { ContextScope, HarnessCaptureDTO } from "@/types/library";

const contextScopes = new Set<ContextScope>(["GLOBAL", "PROJECT", "AGENT", "SESSION", "USER"]);

export type HarnessCaptureParseResult =
  | { ok: true; payload: HarnessCaptureDTO }
  | {
      ok: false;
      code:
        | "INVALID_HARNESS_PAYLOAD"
        | "REQUIRED_HARNESS_FIELDS"
        | "INVALID_HARNESS_SCOPE";
      message: string;
    };

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

function optionalStringList(value: unknown): string[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value)) return undefined;
  return value
    .filter((item): item is string => typeof item === "string")
    .map((item) => item.trim())
    .filter(Boolean);
}

function optionalScope(value: unknown): ContextScope | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "string") return undefined;
  return contextScopes.has(value as ContextScope) ? value as ContextScope : undefined;
}

export function parseHarnessCaptureBody(rawBody: unknown): HarnessCaptureParseResult {
  if (!isRecord(rawBody)) {
    return {
      ok: false,
      code: "INVALID_HARNESS_PAYLOAD",
      message: "Invalid harness payload.",
    };
  }

  const taskGoal = requiredText(rawBody.taskGoal);
  const reusableProcedure = requiredText(rawBody.reusableProcedure);
  if (!taskGoal || !reusableProcedure) {
    return {
      ok: false,
      code: "REQUIRED_HARNESS_FIELDS",
      message: "Task goal and reusable procedure are required.",
    };
  }

  const scope = optionalScope(rawBody.scope);
  if (rawBody.scope !== undefined && scope === undefined) {
    return {
      ok: false,
      code: "INVALID_HARNESS_SCOPE",
      message: "Invalid harness scope.",
    };
  }

  const payload: HarnessCaptureDTO = {
    taskGoal,
    reusableProcedure,
    summary: optionalText(rawBody.summary) ?? null,
    project: optionalText(rawBody.project) ?? null,
    scope: scope ?? "PROJECT",
    sourceAgent: optionalText(rawBody.sourceAgent) ?? "Hermes",
    environment: optionalText(rawBody.environment) ?? null,
    triggerContext: optionalText(rawBody.triggerContext) ?? null,
    steps: optionalStringList(rawBody.steps) ?? [],
    commands: optionalStringList(rawBody.commands) ?? [],
    tests: optionalStringList(rawBody.tests) ?? [],
    failures: optionalStringList(rawBody.failures) ?? [],
    fixes: optionalStringList(rawBody.fixes) ?? [],
    artifacts: optionalStringList(rawBody.artifacts) ?? [],
    recallKeywords: optionalStringList(rawBody.recallKeywords) ?? [],
    safetyNotes: optionalStringList(rawBody.safetyNotes) ?? [],
  };
  return { ok: true, payload };
}
