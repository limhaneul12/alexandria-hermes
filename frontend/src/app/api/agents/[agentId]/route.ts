import { NextResponse } from "next/server";

import { updateAgentLibrarianProviderInBackend } from "@/lib/backend/librarians";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ agentId: string }> },
) {
  const { agentId } = await context.params;
  try {
    const body = (await request.json()) as { preferredLibrarianProvider?: unknown } | null;

    if (typeof body !== "object" || body === null || Array.isArray(body)) {
      return NextResponse.json({ message: "사서 배정 값을 다시 확인하세요." }, { status: 400 });
    }

    if (!("preferredLibrarianProvider" in body)) {
      return NextResponse.json({ message: "사서 배정 값이 필요합니다." }, { status: 400 });
    }

    const providerId = body.preferredLibrarianProvider;
    if (providerId !== null && typeof providerId !== "string") {
      return NextResponse.json({ message: "사서 배정 값을 다시 확인하세요." }, { status: 400 });
    }

    return NextResponse.json(await updateAgentLibrarianProviderInBackend(agentId, providerId || null));
  } catch {
    return NextResponse.json(
      { message: "에이전트 사서 배정을 저장하지 못했습니다." },
      { status: 502 },
    );
  }
}
