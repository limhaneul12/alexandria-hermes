import { NextResponse } from "next/server";

import {
  deleteAgentInBackend,
  loadAgentFromBackend,
  updateAgentInBackend,
} from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../_shared/backend-error-response";
import { isAgentRequestRecord, updateAgentPayload } from "../agent-route-payload";

export async function GET(
  _request: Request,
  context: { params: Promise<{ agentId: string }> },
) {
  const { agentId } = await context.params;
  try {
    return NextResponse.json(await loadAgentFromBackend(agentId));
  } catch (error) {
    return backendFailureResponse(error, "에이전트 설정을 불러오지 못했습니다.");
  }
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ agentId: string }> },
) {
  const { agentId } = await context.params;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ message: "에이전트 설정을 확인하세요." }, { status: 400 });
  }
  if (!isAgentRequestRecord(body)) {
    return NextResponse.json({ message: "에이전트 설정을 확인하세요." }, { status: 400 });
  }
  const payload = updateAgentPayload(body);
  if (!payload.ok) {
    return NextResponse.json({ message: payload.message }, { status: 400 });
  }
  try {
    return NextResponse.json(await updateAgentInBackend(agentId, payload.payload));
  } catch (error) {
    return backendFailureResponse(error, "에이전트 설정을 수정하지 못했습니다.");
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ agentId: string }> },
) {
  const { agentId } = await context.params;
  try {
    await deleteAgentInBackend(agentId);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return backendFailureResponse(error, "에이전트 설정을 삭제하지 못했습니다.");
  }
}
