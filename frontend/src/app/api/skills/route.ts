import { NextResponse } from "next/server";

import { createSkillInBackend } from "@/lib/backend/archive";
import type { ItemStatus, RiskLevel, SkillCreateDTO } from "@/types/library";

const ALLOWED_STATUSES = new Set<ItemStatus>(["DRAFT", "ACTIVE"]);
const ALLOWED_RISK_LEVELS = new Set<RiskLevel>(["LOW", "MEDIUM", "HIGH"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string").map((item) => item.trim()).filter(Boolean);
}

function nullableString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export async function POST(request: Request) {
  try {
    const rawBody = await request.json();
    if (!isRecord(rawBody)) {
      return NextResponse.json({ message: "스킬 정보를 다시 확인하세요." }, { status: 400 });
    }

    const title = typeof rawBody.title === "string" ? rawBody.title.trim() : "";
    const content = typeof rawBody.content === "string" ? rawBody.content.trim() : "";
    const purpose = typeof rawBody.purpose === "string" ? rawBody.purpose.trim() : "";
    const status = typeof rawBody.status === "string" && ALLOWED_STATUSES.has(rawBody.status as ItemStatus)
      ? rawBody.status as Extract<ItemStatus, "DRAFT" | "ACTIVE">
      : "DRAFT";
    const riskLevel = typeof rawBody.riskLevel === "string" && ALLOWED_RISK_LEVELS.has(rawBody.riskLevel as RiskLevel)
      ? rawBody.riskLevel as RiskLevel
      : "LOW";

    if (!title || !content || !purpose) {
      return NextResponse.json(
        { message: "스킬 제목, 목적, 본문을 입력하세요." },
        { status: 400 },
      );
    }

    const payload: SkillCreateDTO = {
      title,
      summary: nullableString(rawBody.summary),
      content,
      categoryId: nullableString(rawBody.categoryId),
      tags: stringList(rawBody.tags),
      purpose,
      usageExample: nullableString(rawBody.usageExample),
      requiredTools: stringList(rawBody.requiredTools),
      riskLevel,
      version: nullableString(rawBody.version) ?? "1.0.0",
      createdByName: nullableString(rawBody.createdByName) ?? "library-user",
      status,
    };

    const skill = await createSkillInBackend(payload);
    return NextResponse.json(skill, { status: 201 });
  } catch {
    return NextResponse.json(
      { message: "스킬을 등록하지 못했습니다. 입력값을 확인하세요." },
      { status: 502 },
    );
  }
}
