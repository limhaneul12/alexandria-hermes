import { NextResponse } from "next/server";

import { loadSkillDetailFromBackend } from "@/lib/backend/archive";

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
