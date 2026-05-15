import { BackendRequestError, backendFetch } from "@/lib/backend/client";
import { isItemType } from "@/types/library";
import type {
  CategoryCreateDTO,
  CategoryDTO,
  CategoryNode,
  CreatedByType,
  DashboardDTO,
  ExternalArchiveCandidateDTO,
  ExternalArchiveImportResultDTO,
  ItemStatus,
  ItemType,
  LibraryDTO,
  SelectionSource,
  LibraryItemCardDTO,
  LibraryItemDetailDTO,
  PromptContentFormat,
  PromptCreateDTO,
  PromptCreateResultDTO,
  PromptDomain,
  PromptKind,
  PromptTaskType,
  SkillCreateDTO,
  SkillAcquisitionMetadataDTO,
  SkillCandidateHarnessDTO,
  SkillCandidateHarnessStatus,
  SkillCreateResultDTO,
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

type BackendExternalArchiveCandidate = {
  id: string;
  provider_id: string;
  bucket: string;
  object_key: string;
  title: string;
  summary: string;
  content_preview: string;
  item_type: ItemType;
  tags: string[];
  details: Record<string, unknown>;
  confidence: number;
  needs_review: boolean;
};

type BackendExternalArchiveImportResult = {
  imported_count: number;
  skipped_count: number;
  item_ids: string[];
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
    ? rawVariables.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null && !Array.isArray(item)).map((item) => ({
        name: typeof item.name === "string" ? item.name : "variable",
        required: typeof item.required === "boolean" ? item.required : true,
        description: typeof item.description === "string" ? item.description : null,
        defaultValue: typeof item.default_value === "string" ? item.default_value : null,
        example: typeof item.example === "string" ? item.example : null,
        inputType: typeof item.input_type === "string" ? item.input_type : "text",
      }))
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

function toExternalArchiveCandidateDTO(
  candidate: BackendExternalArchiveCandidate,
): ExternalArchiveCandidateDTO {
  return {
    id: candidate.id,
    providerId: candidate.provider_id,
    bucket: candidate.bucket,
    objectKey: candidate.object_key,
    title: candidate.title,
    summary: candidate.summary,
    contentPreview: candidate.content_preview,
    itemType: candidate.item_type,
    tags: candidate.tags,
    details: candidate.details,
    confidence: candidate.confidence,
    needsReview: candidate.needs_review,
  };
}

function toExternalArchiveImportResultDTO(
  result: BackendExternalArchiveImportResult,
): ExternalArchiveImportResultDTO {
  return {
    importedCount: result.imported_count,
    skippedCount: result.skipped_count,
    itemIds: result.item_ids,
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

export async function createSkillInBackend(payload: SkillCreateDTO): Promise<SkillCreateResultDTO> {
  const item = await backendFetch<BackendItem>("/library/skills", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title,
      summary: payload.summary,
      content: payload.content,
      category_id: payload.categoryId,
      tags: payload.tags,
      purpose: payload.purpose,
      input_schema: {},
      output_schema: {},
      usage_example: payload.usageExample,
      required_tools: payload.requiredTools,
      risk_level: payload.riskLevel,
      version: payload.version,
      created_by_name: payload.createdByName,
      status: payload.status,
    }),
  });
  return toSkillCard(
    item,
    new Map<string, BackendCategory>(),
    new Map<string, number>(),
    new Map<string, string>(),
  );
}

export async function createPromptInBackend(payload: PromptCreateDTO): Promise<PromptCreateResultDTO> {
  const item = await backendFetch<BackendItem>("/library/prompts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: payload.title,
      summary: payload.summary,
      content: payload.content,
      category_id: payload.categoryId,
      tags: payload.tags,
      content_format: payload.contentFormat,
      prompt_kind: payload.promptKind,
      prompt_domain: payload.promptDomain,
      prompt_task_type: payload.promptTaskType,
      input_variables: payload.inputVariables.map((variable) => ({
        name: variable.name,
        required: variable.required,
        description: variable.description,
        default_value: variable.defaultValue,
        example: variable.example,
        input_type: variable.inputType,
      })),
      output_format: payload.outputFormat,
      target_actor: payload.targetActor,
      target_model_family: payload.targetModelFamily,
      language: payload.language,
      related_item_ids: payload.relatedItemIds,
      safety_notes: payload.safetyNotes,
      version: payload.version,
      change_summary: payload.changeSummary,
      created_by_name: payload.createdByName,
      created_by_type: payload.createdByType,
      source_type: payload.sourceType,
      status: payload.status,
    }),
  });
  return toSkillCard(
    item,
    new Map<string, BackendCategory>(),
    new Map<string, number>(),
    new Map<string, string>(),
  );
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
  const [dbItems, minioItems, categories, popular, recent] = await Promise.all([
    backendFetch<BackendItem[]>("/library/items?limit=200"),
    backendFetch<BackendItem[]>("/archive/minio/library/items?limit=200").catch(
      (error: unknown) => {
        if (error instanceof BackendRequestError) return [];
        throw error;
      },
    ),
    backendFetch<BackendCategory[]>("/library/categories/tree"),
    backendFetch<BackendPopular[]>("/library/usage/popular?limit=100"),
    backendFetch<BackendUsage[]>("/library/usage/recent?limit=200"),
  ]);
  const items = [...dbItems, ...minioItems].filter(isVisibleItem);
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

export async function loadExternalArchiveCandidatesFromBackend(
  limit = 48,
): Promise<ExternalArchiveCandidateDTO[]> {
  const boundedLimit = Math.min(Math.max(limit, 1), 1000);
  const candidates = await backendFetch<BackendExternalArchiveCandidate[]>(
    `/archive/minio/import-candidates?limit=${boundedLimit}`,
  );
  return candidates.map(toExternalArchiveCandidateDTO);
}

export async function importExternalArchiveCandidatesInBackend(
  limit = 48,
): Promise<ExternalArchiveImportResultDTO> {
  const boundedLimit = Math.min(Math.max(limit, 1), 1000);
  const result = await backendFetch<BackendExternalArchiveImportResult>(
    "/archive/minio/import",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: boundedLimit }),
    },
  );
  return toExternalArchiveImportResultDTO(result);
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

async function loadMinioItemById(skillId: string): Promise<BackendItem | null> {
  if (!skillId.startsWith("minio:")) return null;
  const minioItems = await backendFetch<BackendItem[]>("/archive/minio/library/items?limit=1000").catch(
    (error: unknown) => {
      if (error instanceof BackendRequestError) return [];
      throw error;
    },
  );
  return minioItems.find((item) => item.id === skillId) ?? null;
}

export async function loadLibraryItemDetailFromBackend(skillId: string): Promise<LibraryItemDetailDTO | null> {
  const encodedSkillId = encodeURIComponent(skillId);
  const persistedItem = await backendFetch<BackendItem>(`/library/items/${encodedSkillId}`).catch((error: unknown) => {
    if (error instanceof BackendRequestError && error.status === 404) return null;
    throw error;
  });
  const item = persistedItem ?? await loadMinioItemById(skillId);
  if (!item) return null;
  const usagePromise = item.id.startsWith("minio:")
    ? Promise.resolve<BackendUsage[]>([])
    : backendFetch<BackendUsage[]>(`/library/usage/library/items/${encodedSkillId}`);
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
