import { NextResponse } from "next/server";

import { loadAgentsFromBackend } from "@/lib/backend/librarians";

export async function GET() {
  try {
    return NextResponse.json(await loadAgentsFromBackend());
  } catch {
    return NextResponse.json(
      { message: "에이전트 목록을 불러오지 못했습니다." },
      { status: 502 },
    );
  }
}
