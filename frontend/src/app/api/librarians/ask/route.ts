import { NextResponse } from "next/server";

import { askLibrarianInBackend } from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../_shared/backend-error-response";
import { routeErrorPayload } from "@/lib/backend/route-errors";
import { isRecord } from "../../_shared/request-parsing";
import type { LibrarianAskRequestDTO } from "@/types/library";

function optionalString(value: unknown): string | null | undefined {
  if (value === null) return null;
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function optionalDelegateLimit(value: unknown): number | null | undefined {
  if (value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) return undefined;
  return Math.min(Math.max(Math.trunc(value), 1), 6);
}

function optionalStringList(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const values = value
    .filter((item): item is string => typeof item === "string")
    .map((item) => item.trim())
    .filter(Boolean);
  return values;
}

export async function POST(request: Request) {
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json(routeErrorPayload("INVALID_LIBRARIAN_ASK_PAYLOAD", "Invalid librarian ask payload."), { status: 400 });
  }
  if (!isRecord(rawBody)) {
    return NextResponse.json(routeErrorPayload("INVALID_LIBRARIAN_ASK_PAYLOAD", "Invalid librarian ask payload."), { status: 400 });
  }
  const prompt = typeof rawBody.prompt === "string" ? rawBody.prompt.trim() : "";
  if (!prompt) {
    return NextResponse.json(routeErrorPayload("REQUIRED_LIBRARIAN_ASK_PROMPT", "Prompt is required."), { status: 400 });
  }

  const payload: LibrarianAskRequestDTO = {
    prompt,
    agentName: optionalString(rawBody.agentName) ?? "Hermes",
    delegateToLibrarian:
      typeof rawBody.delegateToLibrarian === "boolean"
        ? rawBody.delegateToLibrarian
        : false,
  };
  const project = optionalString(rawBody.project);
  if (project !== undefined) payload.project = project;
  const taskSummary = optionalString(rawBody.taskSummary);
  if (taskSummary !== undefined) payload.taskSummary = taskSummary;
  const providerId = optionalString(rawBody.providerId);
  if (providerId !== undefined) payload.providerId = providerId;
  const librarianProfileId = optionalString(rawBody.librarianProfileId);
  if (librarianProfileId !== undefined) {
    payload.librarianProfileId = librarianProfileId;
  }
  const librarianModel = optionalString(rawBody.librarianModel);
  if (librarianModel !== undefined) payload.librarianModel = librarianModel;
  const librarianRolePrompt = optionalString(rawBody.librarianRolePrompt);
  if (librarianRolePrompt !== undefined) {
    payload.librarianRolePrompt = librarianRolePrompt;
  }
  const maxLibrarianAgents = optionalDelegateLimit(rawBody.maxLibrarianAgents);
  if (maxLibrarianAgents !== undefined) {
    payload.maxLibrarianAgents = maxLibrarianAgents;
  }
  const routingSpecialties = optionalStringList(rawBody.routingSpecialties);
  if (routingSpecialties !== undefined) {
    payload.routingSpecialties = routingSpecialties;
  }

  try {
    return NextResponse.json(await askLibrarianInBackend(payload));
  } catch (error) {
    return backendFailureResponse(error, "Librarian ask failed", "LIBRARIAN_ASK_FAILED");
  }
}
