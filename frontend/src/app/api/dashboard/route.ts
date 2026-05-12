import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";
import { ensureDatabaseSeeded } from "@/server/seed";
import { serializeSkill } from "@/server/serializers";

export async function GET() {
  await ensureDatabaseSeeded();

  const [skillsCount, workflowsCount, docsCount, categoriesCount] = await Promise.all([
    prisma.skill.count(),
    prisma.workflow.count(),
    prisma.knowledgeDocument.count(),
    prisma.category.count(),
  ]);

  const [recentSkills, recommendations, categories, usage] = await Promise.all([
    prisma.skill.findMany({
      include: { category: true, tags: true, _count: { select: { usageHistory: true } } },
      orderBy: { lastAccessedAt: "desc" },
      take: 5,
    }),
    prisma.recommendation.findMany({ orderBy: { usageCount: "desc" }, take: 6 }),
    prisma.category.findMany({ include: { _count: { select: { skills: true } } } }),
    prisma.usageHistory.findMany({ orderBy: { accessedAt: "asc" } }),
  ]);

  const trend = new Map<string, number>();
  const formatter = new Intl.DateTimeFormat("en", { weekday: "short" });
  for (let index = 6; index >= 0; index -= 1) {
    const day = new Date(Date.now() - index * 24 * 3600 * 1000);
    trend.set(formatter.format(day), 0);
  }
  for (const entry of usage) {
    const label = formatter.format(entry.accessedAt);
    if (trend.has(label)) trend.set(label, (trend.get(label) ?? 0) + 1);
  }

  return NextResponse.json({
    stats: [
      { label: "Total Archives", value: skillsCount + workflowsCount + docsCount, hint: "indexed capabilities" },
      { label: "Skills", value: skillsCount, hint: "callable agent capabilities" },
      { label: "Workflows", value: workflowsCount, hint: "repeatable procedures" },
      { label: "Knowledge Documents", value: docsCount, hint: "deep reference notes" },
      { label: "Categories", value: categoriesCount, hint: "curated shelves" },
    ],
    recentlyUsed: recentSkills.map(serializeSkill),
    recommendations,
    categoryActivity: categories
      .map((category) => ({ name: category.name, value: category._count.skills }))
      .filter((item) => item.value > 0),
    usageTrend: Array.from(trend.entries()).map(([day, count]) => ({ day, usage: count })),
  });
}
