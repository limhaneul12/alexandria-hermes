import { BackendRequestError, backendFetch } from "@/lib/backend/client";
import { isItemType } from "@/types/library";
import type {
  CategoryNode,
  CreatedByType,
  DashboardDTO,
  ItemStatus,
  ItemType,
  LibraryDTO,
  SelectionSource,
  SkillCardDTO,
  SkillDetailDTO,
  SourceType,
} from "@/types/library";

type BackendItem = {
  id: string;
  item_type: ItemType;
  title: string;
  summary: string | null;
  content: string;
  category_id: string | null;
  tags: string[];
  status: ItemStatus;
  source_type: SourceType;
  created_by_type: CreatedByType;
  created_by_name: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

type BackendCategory = {
  id: string;
  name: string;
  parent_id: string | null;
  position: number;
  children?: BackendCategory[];
};

type BackendUsage = {
  id: string;
  item_id: string;
  item_type: ItemType;
  agent_name: string;
  librarian_provider: string | null;
  selection_source: SelectionSource;
  used_at: string;
  success: boolean;
};

type BackendPopular = {
  item_id: string;
  count: number;
};

type BackendCategoryPopularity = {
  category_id: string;
  item_type: ItemType;
  count: number;
};

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9가-힣]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function categorySlug(category: BackendCategory): string {
  const slug = slugify(category.name);
  return slug ? `${slug}-${category.id.slice(0, 8)}` : category.id;
}

function flattenCategories(categories: BackendCategory[]): BackendCategory[] {
  return categories.flatMap((category) => [
    category,
    ...flattenCategories(category.children ?? []),
  ]);
}

function buildCategoryNodes(categories: BackendCategory[], itemCounts: Map<string, number>): CategoryNode[] {
  return categories.map((category) => {
    const children = buildCategoryNodes(category.children ?? [], itemCounts);
    const childCount = children.reduce((total, child) => total + child.skillCount, 0);
    return {
      id: category.id,
      name: category.name,
      slug: categorySlug(category),
      parentId: category.parent_id,
      children,
      skillCount: (itemCounts.get(category.id) ?? 0) + childCount,
    };
  });
}

function buildCategoryLookup(categories: BackendCategory[]) {
  return new Map(flattenCategories(categories).map((category) => [category.id, category]));
}

function toSkillCard(
  item: BackendItem,
  categoriesById: Map<string, BackendCategory>,
  usageCounts: Map<string, number>,
  recentUsage: Map<string, string>,
): SkillCardDTO {
  const category = item.category_id ? categoriesById.get(item.category_id) : undefined;
  return {
    id: item.id,
    title: item.title,
    slug: item.id,
    description: item.summary ?? "No summary recorded yet.",
    content: item.content,
    type: item.item_type,
    version: typeof item.details.version === "string" ? item.details.version : "1.0.0",
    author: item.created_by_name,
    category: category
      ? { id: category.id, name: category.name, slug: categorySlug(category) }
      : { id: null, name: "Uncategorized", slug: "uncategorized" },
    tags: item.tags,
    updatedAt: item.updated_at,
    lastAccessedAt: recentUsage.get(item.id) ?? null,
    usageCount: usageCounts.get(item.id) ?? 0,
  };
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

function usageTrend(usages: BackendUsage[]) {
  const trend = new Map<string, number>();
  const formatter = new Intl.DateTimeFormat("en", { weekday: "short" });
  for (let index = 6; index >= 0; index -= 1) {
    const day = new Date(Date.now() - index * 24 * 3600 * 1000);
    trend.set(formatter.format(day), 0);
  }
  for (const usage of usages) {
    const label = formatter.format(new Date(usage.used_at));
    if (trend.has(label)) trend.set(label, (trend.get(label) ?? 0) + 1);
  }
  return Array.from(trend.entries()).map(([day, usage]) => ({ day, usage }));
}

async function loadArchiveContext() {
  const [items, categories, popular, recent] = await Promise.all([
    backendFetch<BackendItem[]>("/items?limit=200"),
    backendFetch<BackendCategory[]>("/categories/tree"),
    backendFetch<BackendPopular[]>("/usage/popular?limit=100"),
    backendFetch<BackendUsage[]>("/usage/recent?limit=200"),
  ]);
  const categoriesById = buildCategoryLookup(categories);
  const usageCounts = new Map(popular.map((entry) => [entry.item_id, entry.count]));
  const recentUsage = new Map(recent.map((entry) => [entry.item_id, entry.used_at]));
  return { items, categories, categoriesById, usageCounts, recentUsage, recent };
}

export async function loadLibraryFromBackend(searchParams: URLSearchParams): Promise<LibraryDTO> {
  const { items, categories, categoriesById, usageCounts, recentUsage } = await loadArchiveContext();
  const q = searchParams.get("q")?.trim().toLowerCase() ?? "";
  const categorySlugParam = searchParams.get("category");
  const tag = searchParams.get("tag");
  const typeParam = searchParams.get("type");
  const type = typeParam && isItemType(typeParam) ? typeParam : null;
  const sort = searchParams.get("sort") ?? "recent";
  const limit = Math.min(Math.max(Number(searchParams.get("limit") ?? 48), 1), 60);
  const selectedCategory = categorySlugParam
    ? Array.from(categoriesById.values()).find((category) => categorySlug(category) === categorySlugParam)
    : undefined;

  const filtered = items.filter((item) => {
    const matchesText =
      !q ||
      [item.title, item.summary ?? "", item.content, item.tags.join(" ")]
        .join(" ")
        .toLowerCase()
        .includes(q);
    const matchesCategory = !categorySlugParam || item.category_id === selectedCategory?.id;
    const matchesTag = !tag || item.tags.includes(tag);
    const matchesType = !type || item.item_type === type;
    return matchesText && matchesCategory && matchesTag && matchesType;
  });

  filtered.sort((left, right) => {
    if (sort === "title") return left.title.localeCompare(right.title);
    if (sort === "popular") {
      return (usageCounts.get(right.id) ?? 0) - (usageCounts.get(left.id) ?? 0);
    }
    return new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime();
  });

  const itemCounts = new Map<string, number>();
  for (const item of items) {
    if (item.category_id) itemCounts.set(item.category_id, (itemCounts.get(item.category_id) ?? 0) + 1);
  }

  return {
    items: filtered
      .slice(0, limit)
      .map((item) => toSkillCard(item, categoriesById, usageCounts, recentUsage)),
    categories: buildCategoryNodes(categories, itemCounts),
    tags: Array.from(new Set(items.flatMap((item) => item.tags))).sort(),
    total: filtered.length,
  };
}

export async function loadDashboardFromBackend(): Promise<DashboardDTO> {
  const { items, categories, categoriesById, usageCounts, recentUsage, recent } =
    await loadArchiveContext();
  const cards = items.map((item) => toSkillCard(item, categoriesById, usageCounts, recentUsage));
  const skillsCount = items.filter((item) => item.item_type === "SKILL").length;
  const workflowsCount = items.filter((item) => item.item_type === "WORKFLOW").length;
  const docsCount = items.filter((item) => item.item_type === "KNOWLEDGE").length;
  const categoryPopularity = await backendFetch<BackendCategoryPopularity[]>(
    "/usage/popular/by-category?limit=12",
  );

  return {
    stats: [
      { label: "Total Archives", value: items.length, hint: "backend-owned records" },
      { label: "Skills", value: skillsCount, hint: "callable agent capabilities" },
      { label: "Workflows", value: workflowsCount, hint: "repeatable procedures" },
      { label: "Knowledge Documents", value: docsCount, hint: "deep reference notes" },
      { label: "Categories", value: flattenCategories(categories).length, hint: "curated shelves" },
    ],
    recentlyUsed: cards
      .filter((item) => item.lastAccessedAt)
      .sort(
        (left, right) =>
          new Date(right.lastAccessedAt ?? 0).getTime() -
          new Date(left.lastAccessedAt ?? 0).getTime(),
      )
      .slice(0, 5),
    recommendations: cards
      .filter((item) => item.usageCount > 0)
      .sort((left, right) => right.usageCount - left.usageCount)
      .slice(0, 6)
      .map((item) => ({
        id: item.id,
        title: item.title,
        description: item.description,
        type: item.type,
        usageCount: item.usageCount,
      })),
    categoryActivity: categoryPopularity
      .map((entry) => ({
        name: categoriesById.get(entry.category_id)?.name ?? entry.category_id,
        value: entry.count,
      }))
      .filter((item) => item.value > 0),
    usageTrend: usageTrend(recent),
  };
}

export async function loadSkillDetailFromBackend(skillId: string): Promise<SkillDetailDTO | null> {
  const { categoriesById, usageCounts, recentUsage } = await loadArchiveContext();
  const encodedSkillId = encodeURIComponent(skillId);
  const item = await backendFetch<BackendItem>(`/items/${encodedSkillId}`).catch((error: unknown) => {
    if (error instanceof BackendRequestError && error.status === 404) return null;
    throw error;
  });
  if (!item) return null;
  const usage = await backendFetch<BackendUsage[]>(`/usage/items/${encodedSkillId}`);
  const base = toSkillCard(item, categoriesById, usageCounts, recentUsage);
  return {
    ...base,
    usageHistory: usage.map((entry) => ({
      id: entry.id,
      accessedAt: entry.used_at,
      agentName: entry.agent_name,
      accessMethod: entry.selection_source,
    })),
    tableOfContents: [
      { id: "overview", label: "Overview" },
      { id: "usage-guide", label: "Usage guide" },
      { id: "examples", label: "Code examples" },
      { id: "history", label: "Usage history" },
    ],
    codeExamples: extractCodeExamples(item.content),
  };
}
