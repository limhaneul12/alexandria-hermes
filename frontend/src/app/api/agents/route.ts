import { NextResponse } from "next/server";

import { createAgentInBackend, loadAgentsFromBackend } from "@/lib/backend/librarians";
import { backendFailureResponse } from "../_shared/backend-error-response";
import { createAgentPayload, isAgentRequestRecord } from "./agent-route-payload";

export async function GET() {
  try {
    return NextResponse.json(await loadAgentsFromBackend());
  } catch (error) {
    return backendFailureResponse(error, "에이전트 목록을 불러오지 못했습니다.");
  }
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ message: "에이전트 설정을 확인하세요." }, { status: 400 });
  }
  if (!isAgentRequestRecord(body)) {
    return NextResponse.json({ message: "에이전트 설정을 확인하세요." }, { status: 400 });
  }
  const payload = createAgentPayload(body);
  if (!payload.ok) {
    return NextResponse.json({ message: payload.message }, { status: 400 });
  }
  try {
    return NextResponse.json(await createAgentInBackend(payload.payload), { status: 201 });
  } catch (error) {
    return backendFailureResponse(error, "에이전트 설정을 저장하지 못했습니다.");
  }
}
