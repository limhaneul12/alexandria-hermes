import { NextResponse } from "next/server";

import { testLibrarianProviderInBackend } from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../../_shared/backend-error-response";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function POST(
  request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ message: "사서 인증 정보를 다시 확인하세요." }, { status: 400 });
  }
  if (!isRecord(body)) {
    return NextResponse.json({ message: "사서 인증 정보를 다시 확인하세요." }, { status: 400 });
  }
  const testQuery = typeof body.testQuery === "string" && body.testQuery.trim()
    ? body.testQuery.trim()
    : "ping";

  try {
    return NextResponse.json(await testLibrarianProviderInBackend(providerId, testQuery));
  } catch (error) {
    return backendFailureResponse(error, "사서 인증 검증을 완료하지 못했습니다.");
  }
}
