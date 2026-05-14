import { NextResponse } from "next/server";

import { loadExternalArchiveCandidatesFromBackend } from "@/lib/backend/archive";

export async function GET(request: Request) {
  const limit = Number(new URL(request.url).searchParams.get("limit") ?? 48);
  try {
    const candidates = await loadExternalArchiveCandidatesFromBackend(Number.isFinite(limit) ? limit : 48);
    return NextResponse.json(candidates);
  } catch {
    return NextResponse.json(
      { message: "MINIO 아카이브 후보를 스캔하지 못했습니다." },
      { status: 502 },
    );
  }
}
