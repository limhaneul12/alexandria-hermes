import { NextResponse } from "next/server";

import { importExternalArchiveCandidatesInBackend } from "@/lib/backend/archive";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function POST(request: Request) {
  try {
    const rawBody = await request.json().catch(() => ({}));
    const limitValue = isRecord(rawBody) ? rawBody.limit : undefined;
    const limit = typeof limitValue === "number" && Number.isFinite(limitValue) ? limitValue : 48;
    const result = await importExternalArchiveCandidatesInBackend(limit);
    return NextResponse.json(result, { status: 201 });
  } catch {
    return NextResponse.json(
      { message: "MINIO 아카이브를 서재에 등록하지 못했습니다." },
      { status: 502 },
    );
  }
}
