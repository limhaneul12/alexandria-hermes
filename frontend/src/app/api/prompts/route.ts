import { NextResponse } from "next/server";

import { createPromptInBackend } from "@/lib/backend/archive";
import {
  PROMPT_CONTENT_FORMATS,
  PROMPT_DOMAINS,
  PROMPT_KINDS,
  PROMPT_TASK_TYPES,
  type CreatedByType,
  type ItemStatus,
  type PromptContentFormat,
  type PromptCreateDTO,
  type PromptDomain,
  type PromptKind,
  type PromptTaskType,
  type SourceType,
} from "@/types/library";

const ALLOWED_STATUSES = new Set<ItemStatus>(["DRAFT", "ACTIVE"]);
const ALLOWED_CREATED_BY = new Set<CreatedByType>(["USER", "AGENT", "LIBRARIAN"]);
const ALLOWED_SOURCE = new Set<SourceType>(["USER_CREATED", "AGENT_SUBMITTED", "LIBRARIAN_CREATED", "IMPORTED"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nullableString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string").map((item) => item.trim()).filter(Boolean);
}

function enumValue<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value) ? value as T : fallback;
}

function promptVariables(value: unknown): PromptCreateDTO["inputVariables"] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  return value
    .filter(isRecord)
    .map((variable) => ({
      name: nullableString(variable.name) ?? "",
      required: typeof variable.required === "boolean" ? variable.required : true,
      description: nullableString(variable.description),
      defaultValue: nullableString(variable.defaultValue),
      example: nullableString(variable.example),
      inputType: nullableString(variable.inputType) ?? "text",
    }))
    .filter((variable) => {
      if (!variable.name || seen.has(variable.name)) return false;
      seen.add(variable.name);
      return true;
    });
}

export async function POST(request: Request) {
  try {
    const rawBody = await request.json();
    if (!isRecord(rawBody)) {
      return NextResponse.json({ message: "프롬프트 정보를 다시 확인하세요." }, { status: 400 });
    }

    const title = nullableString(rawBody.title) ?? "";
    const content = typeof rawBody.content === "string" ? rawBody.content.trim() : "";
    if (!title || !content) {
      return NextResponse.json({ message: "프롬프트 제목과 본문을 입력하세요." }, { status: 400 });
    }

    const createdByType = typeof rawBody.createdByType === "string" && ALLOWED_CREATED_BY.has(rawBody.createdByType as CreatedByType)
      ? rawBody.createdByType as CreatedByType
      : "USER";
    const sourceType = typeof rawBody.sourceType === "string" && ALLOWED_SOURCE.has(rawBody.sourceType as SourceType)
      ? rawBody.sourceType as SourceType
      : "USER_CREATED";
    const status = typeof rawBody.status === "string" && ALLOWED_STATUSES.has(rawBody.status as ItemStatus)
      ? rawBody.status as Extract<ItemStatus, "DRAFT" | "ACTIVE">
      : "DRAFT";

    const payload: PromptCreateDTO = {
      title,
      summary: nullableString(rawBody.summary),
      content,
      categoryId: nullableString(rawBody.categoryId),
      tags: stringList(rawBody.tags),
      contentFormat: enumValue(rawBody.contentFormat, PROMPT_CONTENT_FORMATS, "MARKDOWN") as PromptContentFormat,
      promptKind: enumValue(rawBody.promptKind, PROMPT_KINDS, "USER_TEMPLATE") as PromptKind,
      promptDomain: enumValue(rawBody.promptDomain, PROMPT_DOMAINS, "GENERAL") as PromptDomain,
      promptTaskType: enumValue(rawBody.promptTaskType, PROMPT_TASK_TYPES, "GENERAL_TASK") as PromptTaskType,
      inputVariables: promptVariables(rawBody.inputVariables),
      outputFormat: nullableString(rawBody.outputFormat),
      targetActor: nullableString(rawBody.targetActor),
      targetModelFamily: nullableString(rawBody.targetModelFamily),
      language: nullableString(rawBody.language),
      relatedItemIds: stringList(rawBody.relatedItemIds),
      safetyNotes: nullableString(rawBody.safetyNotes),
      version: nullableString(rawBody.version) ?? "1.0.0",
      changeSummary: nullableString(rawBody.changeSummary),
      createdByName: nullableString(rawBody.createdByName) ?? "library-user",
      createdByType,
      sourceType,
      status,
    };

    const prompt = await createPromptInBackend(payload);
    return NextResponse.json(prompt, { status: 201 });
  } catch {
    return NextResponse.json(
      { message: "프롬프트를 등록하지 못했습니다. 입력값을 확인하세요." },
      { status: 502 },
    );
  }
}
