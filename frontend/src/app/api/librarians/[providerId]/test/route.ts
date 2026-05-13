import { NextResponse } from "next/server";

import { testLibrarianProviderInBackend } from "@/lib/backend/librarians";

export async function POST(
  request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  try {
    const body = (await request.json()) as { testQuery?: unknown };
    const testQuery = typeof body.testQuery === "string" && body.testQuery.trim()
      ? body.testQuery.trim()
      : "ping";

    return NextResponse.json(await testLibrarianProviderInBackend(providerId, testQuery));
  } catch {
    return NextResponse.json(
      { message: "사서 인증 검증을 완료하지 못했습니다." },
      { status: 502 },
    );
  }
}
