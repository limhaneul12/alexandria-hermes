import type { Prisma } from "@prisma/client";
import type { CategoryNode, SkillCardDTO, SkillDetailDTO } from "@/types/library";

export type SkillListRecord = Prisma.SkillGetPayload<{
  include: {
    category: true;
    tags: true;
    _count: { select: { usageHistory: true } };
  };
}>;

export type SkillDetailRecord = Prisma.SkillGetPayload<{
  include: {
    category: true;
    tags: true;
    usageHistory: { orderBy: { accessedAt: "desc" } };
    _count: { select: { usageHistory: true } };
  };
}>;

export type CategoryRecord = Prisma.CategoryGetPayload<{
  include: { _count: { select: { skills: true } } };
}>;

export function serializeSkill(skill: SkillListRecord): SkillCardDTO {
  return {
    id: skill.id,
    title: skill.title,
    slug: skill.slug,
    description: skill.description,
    content: skill.content,
    type: skill.type,
    version: skill.version,
    author: skill.author,
    category: {
      id: skill.category.id,
      name: skill.category.name,
      slug: skill.category.slug,
    },
    tags: skill.tags.map((tag) => tag.name),
    updatedAt: skill.updatedAt.toISOString(),
    lastAccessedAt: skill.lastAccessedAt?.toISOString() ?? null,
    usageCount: skill._count.usageHistory,
  };
}

export function serializeSkillDetail(skill: SkillDetailRecord): SkillDetailDTO {
  const base = serializeSkill(skill);
  return {
    ...base,
    usageHistory: skill.usageHistory.map((usage) => ({
      id: usage.id,
      accessedAt: usage.accessedAt.toISOString(),
      agentName: usage.agentName,
      accessMethod: usage.accessMethod,
    })),
    tableOfContents: [
      { id: "overview", label: "Overview" },
      { id: "usage-guide", label: "Usage guide" },
      { id: "examples", label: "Code examples" },
      { id: "history", label: "Usage history" },
    ],
    codeExamples: extractCodeExamples(skill.content),
  };
}

export function buildCategoryTree(categories: CategoryRecord[]): CategoryNode[] {
  const nodes = new Map<number, CategoryNode>();
  for (const category of categories) {
    nodes.set(category.id, {
      id: category.id,
      name: category.name,
      slug: category.slug,
      parentId: category.parentId,
      children: [],
      skillCount: category._count.skills,
    });
  }

  const roots: CategoryNode[] = [];
  for (const node of nodes.values()) {
    if (node.parentId === null) {
      roots.push(node);
      continue;
    }
    const parent = nodes.get(node.parentId);
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  const sortNodes = (items: CategoryNode[]) => {
    items.sort((a, b) => a.name.localeCompare(b.name));
    for (const item of items) sortNodes(item.children);
  };

  const aggregateSkillCounts = (item: CategoryNode): number => {
    item.skillCount += item.children.reduce(
      (total, child) => total + aggregateSkillCounts(child),
      0,
    );
    return item.skillCount;
  };

  for (const root of roots) aggregateSkillCounts(root);
  sortNodes(roots);
  return roots;
}

export function collectCategoryIds(categories: CategoryRecord[], slug?: string | null) {
  if (!slug) return undefined;
  const target = categories.find((category) => category.slug === slug);
  if (!target) return [];
  const ids = new Set<number>([target.id]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const category of categories) {
      if (category.parentId !== null && ids.has(category.parentId) && !ids.has(category.id)) {
        ids.add(category.id);
        changed = true;
      }
    }
  }
  return Array.from(ids);
}

function extractCodeExamples(content: string) {
  const matches = [...content.matchAll(/```(\w+)?\n([\s\S]*?)```/g)];
  if (matches.length === 0) {
    return [
      {
        language: "text",
        title: "Operational note",
        code: content.split("\n").slice(0, 4).join("\n"),
      },
    ];
  }
  return matches.map((match, index) => ({
    language: match[1] ?? "text",
    title: index === 0 ? "Primary example" : `Example ${index + 1}`,
    code: match[2].trim(),
  }));
}
