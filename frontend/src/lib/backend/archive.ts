import { BackendRequestError, backendFetch } from "@/lib/backend/client";
import { isItemType } from "@/types/library";
import type {
  CategoryCreateDTO,
  CategoryDTO,
  CategoryNode,
  CreatedByType,
  DashboardDTO,
  ItemStatus,
  ItemType,
  LibraryDTO,
  SelectionSource,
  LibraryUsageRecordCreateDTO,
  LibraryUsageRecordDTO,
  LibraryItemCardDTO,
  LibraryItemDetailDTO,
  PromptContentFormat,
  PromptDomain,
  PromptKind,
  PromptTaskType,
  SkillAcquisitionMetadataDTO,
  SkillCandidateHarnessDTO,
  SkillCandidateHarnessStatus,
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

type BackendSearchHit = {
  id: string;
  item_type: ItemType;
  title: string;
  summary: string | null;
  tags: string[];
  status: ItemStatus;
  category_id: string | null;
  score: number;
  why_matched: string[];
  highlights: string[];
  details_preview: Record<string, unknown>;
  content_char_count: number;
  updated_at: string;
};

type BackendSearchResponse = {
  items: BackendSearchHit[];
  total: number;
  limit: number;
  offset: number;
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


const VISIBLE_ITEM_TYPES = new Set<ItemType>(["SKILL", "PROMPT"]);

function isVisibleItem(item: BackendItem): boolean {
  return VISIBLE_ITEM_TYPES.has(item.item_type);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function detailString(details: Record<string, unknown>, key: string): string | null {
  const value = details[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function detailStringList(details: Record<string, unknown>, key: string): string[] {
  const value = details[key];
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function toPromptMetadata(details: Record<string, unknown>) {
  const rawVariables = details.input_variables;
  const inputVariables = Array.isArray(rawVariables)
    ? rawVariables.flatMap((item) => {
        if (!isRecord(item)) return [];
        return [
          {
            name: typeof item.name === "string" ? item.name : "variable",
            required: typeof item.required === "boolean" ? item.required : true,
            description:
              typeof item.description === "string" ? item.description : null,
            defaultValue:
              typeof item.default_value === "string" ? item.default_value : null,
            example: typeof item.example === "string" ? item.example : null,
            inputType: typeof item.input_type === "string" ? item.input_type : "text",
          },
        ];
      })
    : [];
  return {
    contentFormat: (detailString(details, "content_format") ?? "MARKDOWN") as PromptContentFormat,
    promptKind: (detailString(details, "prompt_kind") ?? "USER_TEMPLATE") as PromptKind,
    promptDomain: (detailString(details, "prompt_domain") ?? "GENERAL") as PromptDomain,
    promptTaskType: (detailString(details, "prompt_task_type") ?? "GENERAL_TASK") as PromptTaskType,
    inputVariables,
    outputFormat: detailString(details, "output_format"),
    targetActor: detailString(details, "target_actor"),
    targetModelFamily: detailString(details, "target_model_family"),
    language: detailString(details, "language"),
    relatedItemIds: detailStringList(details, "related_item_ids"),
    safetyNotes: detailString(details, "safety_notes"),
    changeSummary: detailString(details, "change_summary"),
  };
}

function isHarnessStatus(value: string): value is SkillCandidateHarnessStatus {
  return value === "PASSED" || value === "NEEDS_REVIEW";
}

function toCandidateHarness(details: Record<string, unknown>): SkillCandidateHarnessDTO | null {
  const rawHarness = details.harness;
  if (!isRecord(rawHarness)) return null;
  const status = typeof rawHarness.status === "string" && isHarnessStatus(rawHarness.status)
    ? rawHarness.status
    : null;
  const rawChecks = rawHarness.checks;
  if (!status || !Array.isArray(rawChecks)) return null;
  return {
    status,
    checks: rawChecks
      .filter(isRecord)
      .map((check) => ({
        name: typeof check.name === "string" ? check.name : "candidate_check",
        passed: typeof check.passed === "boolean" ? check.passed : false,
        message: typeof check.message === "string" ? check.message : "",
      })),
  };
}

function toSkillAcquisitionMetadata(details: Record<string, unknown>): SkillAcquisitionMetadataDTO | null {
  const acquisitionMethod = detailString(details, "acquisition_method");
  const evidenceUrls = detailStringList(details, "evidence_urls");
  const sourceSummary = detailString(details, "source_summary");
  const harness = toCandidateHarness(details);
  if (!acquisitionMethod && evidenceUrls.length === 0 && !sourceSummary && !harness) return null;
  return {
    acquisitionMethod: acquisitionMethod ?? "SELF_ACQUISITION",
    evidenceUrls,
    sourceSummary,
    harness,
  };
}

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
): LibraryItemCardDTO {
  const category = item.category_id ? categoriesById.get(item.category_id) : undefined;
  return {
    id: item.id,
    title: item.title,
    slug: item.id,
    description: item.summary ?? "No summary recorded yet.",
    content: item.content,
    type: item.item_type === "PROMPT" ? "PROMPT" : "SKILL",
    version: typeof item.details.version === "string" ? item.details.version : "1.0.0",
    author: item.created_by_name,
    category: category
      ? { id: category.id, name: category.name, slug: categorySlug(category) }
      : { id: null, name: "Uncategorized", slug: "uncategorized" },
    tags: item.tags,
    updatedAt: item.updated_at,
    lastAccessedAt: recentUsage.get(item.id) ?? null,
    usageCount: usageCounts.get(item.id) ?? 0,
    prompt: item.item_type === "PROMPT" ? toPromptMetadata(item.details) : null,
  };
}

function candidateToCard(
  item: BackendSearchHit,
  categoriesById: Map<string, BackendCategory>,
  usageCounts: Map<string, number>,
  recentUsage: Map<string, string>,
): LibraryItemCardDTO {
  const category = item.category_id ? categoriesById.get(item.category_id) : undefined;
  const visibleType = item.item_type === "PROMPT" ? "PROMPT" : "SKILL";
  return {
    id: item.id,
    title: item.title,
    slug: item.id,
    description: item.summary ?? "No summary recorded yet.",
    content: "",
    type: visibleType,
    version: typeof item.details_preview.version === "string" ? item.details_preview.version : "1.0.0",
    author: "Alexandria",
    category: category
      ? { id: category.id, name: category.name, slug: categorySlug(category) }
      : { id: null, name: "Uncategorized", slug: "uncategorized" },
    tags: item.tags,
    updatedAt: item.updated_at,
    lastAccessedAt: recentUsage.get(item.id) ?? null,
    usageCount: usageCounts.get(item.id) ?? 0,
    prompt: visibleType === "PROMPT" ? toPromptMetadata(item.details_preview) : null,
  };
}

function toCategoryDTO(category: BackendCategory & { created_at?: string; updated_at?: string }): CategoryDTO {
  return {
    id: category.id,
    name: category.name,
    parentId: category.parent_id,
    position: category.position,
    createdAt: category.created_at ?? "",
    updatedAt: category.updated_at ?? "",
  };
}


function toUsageRecordDTO(usage: BackendUsage): LibraryUsageRecordDTO {
  return {
    id: usage.id,
    accessedAt: usage.used_at,
    agentName: usage.agent_name,
    accessMethod: usage.selection_source,
  };
}

export async function createCategoryInBackend(payload: CategoryCreateDTO): Promise<CategoryDTO> {
  const category = await backendFetch<BackendCategory & { created_at: string; updated_at: string }>(
    "/library/categories",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: payload.name, parent_id: payload.parentId }),
    },
  );
  return toCategoryDTO(category);
}

export async function deleteCategoryInBackend(categoryId: string): Promise<void> {
  await backendFetch<void>(`/library/categories/${encodeURIComponent(categoryId)}`, { method: "DELETE" });
}

export async function deleteSkillInBackend(skillId: string): Promise<void> {
  await backendFetch<void>(`/library/skills/${encodeURIComponent(skillId)}`, { method: "DELETE" });
}

export async function deletePromptInBackend(promptId: string): Promise<void> {
  await backendFetch<void>(`/library/prompts/${encodeURIComponent(promptId)}`, { method: "DELETE" });
}

export async function deleteLibraryItemInBackend(item: LibraryItemCardDTO): Promise<void> {
  if (item.type === "PROMPT") {
    await deletePromptInBackend(item.id);
    return;
  }
  await deleteSkillInBackend(item.id);
}

export async function recordLibraryUsageInBackend(
  payload: LibraryUsageRecordCreateDTO,
): Promise<LibraryUsageRecordDTO> {
  const usage = await backendFetch<BackendUsage>("/library/usage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      item_id: payload.itemId,
      item_type: payload.itemType,
      agent_name: payload.agentName,
      librarian_provider: payload.librarianProvider ?? null,
      query: payload.query ?? null,
      selection_source: payload.selectionSource,
      success: payload.success,
      feedback: payload.feedback ?? null,
    }),
  });
  return toUsageRecordDTO(usage);
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
  const [dbItems, categories, popular, recent] = await Promise.all([
    backendFetch<BackendItem[]>("/library/items?limit=200"),
    backendFetch<BackendCategory[]>("/library/categories/tree"),
    backendFetch<BackendPopular[]>("/library/usage/popular?limit=100"),
    backendFetch<BackendUsage[]>("/library/usage/recent?limit=200"),
  ]);
  const items = dbItems.filter(isVisibleItem);
  const categoriesById = buildCategoryLookup(categories);
  const usageCounts = new Map(popular.map((entry) => [entry.item_id, entry.count]));
  const recentUsage = new Map(recent.map((entry) => [entry.item_id, entry.used_at]));
  return { items, categories, categoriesById, usageCounts, recentUsage, recent };
}

function searchParamValues(searchParams: URLSearchParams, key: string): string[] {
  const value = searchParams.get(key);
  return value ? [value] : [];
}

async function loadLibraryCandidateContext(searchParams: URLSearchParams) {
  const [categories, popular, recent] = await Promise.all([
    backendFetch<BackendCategory[]>("/library/categories/tree"),
    backendFetch<BackendPopular[]>("/library/usage/popular?limit=100"),
    backendFetch<BackendUsage[]>("/library/usage/recent?limit=200"),
  ]);
  const categoriesById = buildCategoryLookup(categories);
  const q = searchParams.get("q")?.trim() ?? "";
  const categorySlugParam = searchParams.get("category");
  const typeParam = searchParams.get("type");
  const type = typeParam && isItemType(typeParam) ? typeParam : null;
  const updatedAfter = searchParams.get("updated_after");
  const updatedBefore = searchParams.get("updated_before");
  const limit = Math.min(Math.max(Number(searchParams.get("limit") ?? 48), 1), 60);
  const backendLimit = Math.max(limit, 100);
  const selectedCategory = categorySlugParam
    ? Array.from(categoriesById.values()).find((category) => categorySlug(category) === categorySlugParam)
    : undefined;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (type) {
    params.set("item_type", type);
  } else {
    params.append("item_types", "SKILL");
    params.append("item_types", "PROMPT");
  }
  if (selectedCategory) {
    params.set("category_id", selectedCategory.id);
    params.set("include_descendant_categories", "true");
  }
  for (const tagValue of searchParamValues(searchParams, "tag")) {
    params.append("tags_any", tagValue);
  }
  if (updatedAfter) params.set("updated_after", updatedAfter);
  if (updatedBefore) params.set("updated_before", updatedBefore);
  params.set("limit", String(Math.min(backendLimit, 100)));
  params.set("offset", "0");
  params.set("content_mode", "candidate");
  const response = await backendFetch<BackendSearchResponse>(`/library/search?${params.toString()}`);
  const usageCounts = new Map(popular.map((entry) => [entry.item_id, entry.count]));
  const recentUsage = new Map(recent.map((entry) => [entry.item_id, entry.used_at]));
  return {
    items: response.items,
    total: response.total,
    categories,
    categoriesById,
    usageCounts,
    recentUsage,
    limit,
  };
}

export async function loadLibraryFromBackend(searchParams: URLSearchParams): Promise<LibraryDTO> {
  const {
    items,
    total,
    categories,
    categoriesById,
    usageCounts,
    recentUsage,
    limit,
  } = await loadLibraryCandidateContext(searchParams);
  const categorySlugParam = searchParams.get("category");
  const sort = searchParams.get("sort") ?? "recent";
  const filtered = items.filter(isVisibleSearchHit);
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
      .map((item) => candidateToCard(item, categoriesById, usageCounts, recentUsage)),
    categories: buildCategoryNodes(categories, itemCounts),
    tags: Array.from(new Set(items.flatMap((item) => item.tags))).sort(),
    total: categorySlugParam ? filtered.length : total,
  };
}

function isVisibleSearchHit(item: BackendSearchHit): boolean {
  return item.item_type === "SKILL" || item.item_type === "PROMPT";
}


export async function loadDashboardFromBackend(): Promise<DashboardDTO> {
  const [
    { items, categories, categoriesById, usageCounts, recentUsage, recent },
    categoryPopularity,
  ] = await Promise.all([
    loadArchiveContext(),
    backendFetch<BackendCategoryPopularity[]>("/library/usage/popular/by-category?limit=12"),
  ]);
  const cards = items.map((item) => toSkillCard(item, categoriesById, usageCounts, recentUsage));
  const skillsCount = items.filter((item) => item.item_type === "SKILL").length;
  const promptsCount = items.filter((item) => item.item_type === "PROMPT").length;

  return {
    stats: [
      { label: "Total Volumes", value: items.length, hint: "skills and prompts in the archive" },
      { label: "Skills", value: skillsCount, hint: "callable agent capabilities" },
      { label: "Prompts", value: promptsCount, hint: "reusable agent instructions" },
      { label: "Categories", value: flattenCategories(categories).length, hint: "curated shelves" },
      { label: "Recent Uses", value: recent.length, hint: "latest library circulation" },
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

async function loadItemCategory(item: BackendItem): Promise<BackendCategory | null> {
  if (!item.category_id) return null;
  const encodedCategoryId = encodeURIComponent(item.category_id);
  return backendFetch<BackendCategory>(`/library/categories/${encodedCategoryId}`).catch((error: unknown) => {
    if (error instanceof BackendRequestError && error.status === 404) return null;
    throw error;
  });
}


export async function loadLibraryItemDetailFromBackend(skillId: string): Promise<LibraryItemDetailDTO | null> {
  const encodedSkillId = encodeURIComponent(skillId);
  const persistedItem = await backendFetch<BackendItem>(`/library/items/${encodedSkillId}`).catch((error: unknown) => {
    if (error instanceof BackendRequestError && error.status === 404) return null;
    throw error;
  });
  const item = persistedItem;
  if (!item) return null;
  const usagePromise = backendFetch<BackendUsage[]>(`/library/usage/library/items/${encodedSkillId}`);
  const [usage, category] = await Promise.all([
    usagePromise,
    loadItemCategory(item),
  ]);
  const categoriesById = new Map<string, BackendCategory>(
    category ? [[category.id, category]] : [],
  );
  const usageCounts = new Map([[item.id, usage.length]]);
  const recentUsage = new Map<string, string>(
    usage[0] ? [[item.id, usage[0].used_at]] : [],
  );
  const base = toSkillCard(item, categoriesById, usageCounts, recentUsage);
  const skillAcquisition = item.item_type === "SKILL"
    ? toSkillAcquisitionMetadata(item.details)
    : null;
  return {
    ...base,
    skillAcquisition,
    usageHistory: usage.map((entry) => ({
      id: entry.id,
      accessedAt: entry.used_at,
      agentName: entry.agent_name,
      accessMethod: entry.selection_source,
    })),
    tableOfContents: item.item_type === "PROMPT"
      ? [
          { id: "overview", label: "Prompt body" },
          { id: "variables", label: "Fill variables" },
          { id: "history", label: "Usage history" },
          { id: "archive-controls", label: "Archive controls" },
        ]
      : [
          { id: "overview", label: "Overview" },
          ...(skillAcquisition
            ? [{ id: "self-acquisition", label: "Self-acquisition" }]
            : []),
          { id: "usage-guide", label: "Usage guide" },
          { id: "examples", label: "Code examples" },
          { id: "history", label: "Usage history" },
          { id: "archive-controls", label: "Archive controls" },
        ],
    codeExamples: extractCodeExamples(item.content),
  };
}

export async function loadSkillDetailFromBackend(skillId: string): Promise<SkillDetailDTO | null> {
  return loadLibraryItemDetailFromBackend(skillId);
}
