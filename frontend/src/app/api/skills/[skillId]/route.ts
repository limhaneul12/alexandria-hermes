import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";
import { ensureDatabaseSeeded } from "@/server/seed";
import { serializeSkillDetail } from "@/server/serializers";

export async function GET(
  _request: Request,
  context: { params: Promise<{ skillId: string }> },
) {
  await ensureDatabaseSeeded();
  const { skillId } = await context.params;
  const id = Number(skillId);
  if (!Number.isInteger(id)) {
    return NextResponse.json({ message: "Invalid skill id" }, { status: 400 });
  }

  const skill = await prisma.skill.findUnique({
    where: { id },
    include: {
      category: true,
      tags: true,
      usageHistory: { orderBy: { accessedAt: "desc" }, take: 12 },
      _count: { select: { usageHistory: true } },
    },
  });

  if (!skill) {
    return NextResponse.json({ message: "Skill not found" }, { status: 404 });
  }

  return NextResponse.json(serializeSkillDetail(skill));
}
