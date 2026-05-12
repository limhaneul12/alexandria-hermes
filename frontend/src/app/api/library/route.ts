import { NextResponse } from "next/server";
import type { Prisma } from "@prisma/client";

import { prisma } from "@/lib/prisma";
import { ensureDatabaseSeeded } from "@/server/seed";
import { buildCategoryTree, collectCategoryIds, serializeSkill } from "@/server/serializers";

export async function GET(request: Request) {
  await ensureDatabaseSeeded();

  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim();
  const category = searchParams.get("category");
  const tag = searchParams.get("tag");
  const type = searchParams.get("type");
  const sort = searchParams.get("sort") ?? "recent";
  const limit = Math.min(Math.max(Number(searchParams.get("limit") ?? 30), 1), 60);

  const categories = await prisma.category.findMany({
    include: { _count: { select: { skills: true } } },
    orderBy: { name: "asc" },
  });
  const categoryIds = collectCategoryIds(categories, category);

  const where: Prisma.SkillWhereInput = {
    ...(categoryIds ? { categoryId: { in: categoryIds } } : {}),
    ...(tag ? { tags: { some: { name: tag } } } : {}),
    ...(type ? { type } : {}),
    ...(q
      ? {
          OR: [
            { title: { contains: q } },
            { description: { contains: q } },
            { content: { contains: q } },
            { tags: { some: { name: { contains: q } } } },
          ],
        }
      : {}),
  };

  const [skills, tags, total] = await Promise.all([
    prisma.skill.findMany({
      where,
      include: {
        category: true,
        tags: true,
        _count: { select: { usageHistory: true } },
      },
      orderBy: sort === "title" ? { title: "asc" } : { updatedAt: "desc" },
      take: 200,
    }),
    prisma.tag.findMany({ orderBy: { name: "asc" } }),
    prisma.skill.count({ where }),
  ]);

  const sorted = [...skills].sort((a, b) => {
    if (sort === "popular") return b._count.usageHistory - a._count.usageHistory;
    if (sort === "title") return a.title.localeCompare(b.title);
    return (b.lastAccessedAt?.getTime() ?? 0) - (a.lastAccessedAt?.getTime() ?? 0);
  });

  return NextResponse.json({
    items: sorted.slice(0, limit).map(serializeSkill),
    categories: buildCategoryTree(categories),
    tags: tags.map((item) => item.name),
    total,
  });
}
