import type { CategoryCreateDTO, CategoryNode, LibraryDTO, SkillCardDTO, SkillCreateDTO } from "@/types/library";

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9가-힣]+/g, "-")
    .replace(/^-+|-+$/g, "") || "folder";
}

function appendChild(categories: CategoryNode[], parentId: string, child: CategoryNode): CategoryNode[] {
  return categories.map((category) => {
    if (category.id === parentId) {
      return { ...category, children: [...category.children, child] };
    }
    return { ...category, children: appendChild(category.children, parentId, child) };
  });
}

function incrementSkillCount(categories: CategoryNode[], categoryId: string): [CategoryNode[], boolean] {
  let changed = false;
  const nextCategories = categories.map((category) => {
    const [children, childChanged] = incrementSkillCount(category.children, categoryId);
    const selfChanged = category.id === categoryId;

    if (!selfChanged && !childChanged) return category;
    changed = true;
    return {
      ...category,
      children,
      skillCount: category.skillCount + 1,
    };
  });

  return [changed ? nextCategories : categories, changed];
}

function getLibraryQueryParams(queryKey?: readonly unknown[]): URLSearchParams {
  const query = typeof queryKey?.[1] === "string" ? queryKey[1] : "";
  return new URLSearchParams(query);
}

function matchesSearch(skill: SkillCardDTO, query: string): boolean {
  if (!query) return true;
  return [skill.title, skill.description, skill.content, skill.tags.join(" ")]
    .join(" ")
    .toLowerCase()
    .includes(query.toLowerCase());
}

function matchesLibraryQuery(skill: SkillCardDTO, queryKey?: readonly unknown[]): boolean {
  const params = getLibraryQueryParams(queryKey);
  const categorySlug = params.get("category");
  const tag = params.get("tag");
  const type = params.get("type");
  const search = params.get("q")?.trim() ?? "";

  return (
    (!categorySlug || skill.category.slug === categorySlug) &&
    (!tag || skill.tags.includes(tag)) &&
    (!type || skill.type === type) &&
    matchesSearch(skill, search)
  );
}

function getLibraryQueryLimit(queryKey: readonly unknown[] | undefined, fallback: number): number {
  const limit = Number(getLibraryQueryParams(queryKey).get("limit"));
  return Number.isFinite(limit) && limit > 0 ? limit : fallback;
}

export function buildOptimisticCategory(payload: CategoryCreateDTO): CategoryNode {
  return {
    id: `optimistic-category-${Date.now()}`,
    name: payload.name,
    slug: slugify(payload.name),
    parentId: payload.parentId,
    children: [],
    skillCount: 0,
  };
}

export function withOptimisticCategory(library: LibraryDTO, category: CategoryNode): LibraryDTO {
  const categories = category.parentId
    ? appendChild(library.categories, category.parentId, category)
    : [...library.categories, category];
  return { ...library, categories };
}

export function buildOptimisticSkill(
  payload: SkillCreateDTO,
  categories: CategoryNode[],
  optimisticId = `optimistic-skill-${Date.now()}`,
  updatedAt = new Date().toISOString(),
): SkillCardDTO {
  const flatCategories = flattenCategories(categories);
  const category = flatCategories.find((item) => item.id === payload.categoryId);
  return {
    id: optimisticId,
    title: payload.title,
    slug: slugify(payload.title),
    description: payload.summary ?? payload.purpose,
    content: payload.content,
    type: "SKILL",
    version: payload.version,
    author: payload.createdByName,
    category: {
      id: category?.id ?? null,
      name: category?.name ?? "미분류",
      slug: category?.slug ?? "uncategorized",
    },
    tags: payload.tags,
    updatedAt,
    lastAccessedAt: null,
    usageCount: 0,
    prompt: null,
  };
}

export function withOptimisticSkill(library: LibraryDTO, skill: SkillCardDTO, queryKey?: readonly unknown[]): LibraryDTO {
  const [categories] = skill.category.id ? incrementSkillCount(library.categories, skill.category.id) : [library.categories];
  const shouldIncludeSkill = matchesLibraryQuery(skill, queryKey);
  const limit = getLibraryQueryLimit(queryKey, library.items.length + 1);

  return {
    ...library,
    categories,
    items: shouldIncludeSkill ? [skill, ...library.items].slice(0, limit) : library.items,
    tags: Array.from(new Set([...library.tags, ...skill.tags])).sort(),
    total: shouldIncludeSkill ? library.total + 1 : library.total,
  };
}

function flattenCategories(categories: CategoryNode[]): CategoryNode[] {
  return categories.flatMap((category) => [category, ...flattenCategories(category.children)]);
}
