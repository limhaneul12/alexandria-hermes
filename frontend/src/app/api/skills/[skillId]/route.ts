import { NextResponse } from "next/server";

import { deleteSkillInBackend, loadSkillDetailFromBackend } from "@/lib/backend/archive";
import { BackendRequestError } from "@/lib/backend/client";

export async function GET(
  _request: Request,
  context: { params: Promise<{ skillId: string }> },
) {
  const { skillId } = await context.params;
  const skill = await loadSkillDetailFromBackend(skillId);

  if (!skill) {
    return NextResponse.json({ message: "Skill not found" }, { status: 404 });
  }

  return NextResponse.json(skill);
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ skillId: string }> },
) {
  const { skillId } = await context.params;
  try {
    await deleteSkillInBackend(skillId);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return NextResponse.json(
      { message: "Skill delete failed" },
      { status: error instanceof BackendRequestError ? error.status : 502 },
    );
  }
}
