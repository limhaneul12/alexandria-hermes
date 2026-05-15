import { NextResponse } from "next/server";

import { askLibrarianInBackend } from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../_shared/backend-error-response";
import type { LibrarianAskRequestDTO } from "@/types/library";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

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
    return NextResponse.json({ message: "질문 내용을 다시 확인하세요." }, { status: 400 });
  }
  if (!isRecord(rawBody)) {
    return NextResponse.json({ message: "질문 내용을 다시 확인하세요." }, { status: 400 });
  }
  const prompt = typeof rawBody.prompt === "string" ? rawBody.prompt.trim() : "";
  if (!prompt) {
    return NextResponse.json({ message: "질문 내용을 입력하세요." }, { status: 400 });
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
    return backendFailureResponse(error, "사서가 질문을 처리하지 못했습니다.");
  }
}
