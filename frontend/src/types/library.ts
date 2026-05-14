export type ItemType = "SKILL" | "WORKFLOW" | "KNOWLEDGE" | "PROMPT";
export type VisibleItemType = "SKILL" | "PROMPT";
export type ArchiveType = VisibleItemType;

export type ItemStatus = "DRAFT" | "ACTIVE" | "ARCHIVED" | "DEPRECATED";
export type SourceType =
  | "USER_CREATED"
  | "AGENT_SUBMITTED"
  | "LIBRARIAN_CREATED"
  | "IMPORTED";
export type CreatedByType = "USER" | "AGENT" | "LIBRARIAN";
export type SelectionSource = "RECOMMENDATION" | "MANUAL_BROWSE" | "SEARCH" | "DIRECT_LINK";
export type ProviderType = "OPENAI" | "MINIO";
export type AuthType = "API_KEY" | "OAUTH" | "NONE";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export type PromptContentFormat = "MARKDOWN" | "XML" | "JSON" | "TEXT";
export type PromptKind = "SYSTEM" | "DEVELOPER" | "USER_TEMPLATE" | "EVAL" | "TOOL_GUIDE" | "CHAIN";
export type PromptDomain =
  | "DEVELOPMENT"
  | "DESIGN"
  | "WRITING"
  | "RESEARCH"
  | "ANALYSIS"
  | "PLANNING"
  | "REVIEW"
  | "TESTING"
  | "DEBUGGING"
  | "OPERATIONS"
  | "DATA"
  | "EDUCATION"
  | "MARKETING"
  | "PRODUCT"
  | "SECURITY"
  | "GENERAL";
export type PromptTaskType =
  | "CODE_GENERATION"
  | "CODE_REVIEW"
  | "TEST_GENERATION"
  | "BUG_DIAGNOSIS"
  | "FEATURE_PLANNING"
  | "UI_COPYWRITING"
  | "DOCUMENT_SUMMARY"
  | "DOCUMENT_CREATION"
  | "REQUIREMENTS_ANALYSIS"
  | "RESEARCH_SYNTHESIS"
  | "IMAGE_PROMPTING"
  | "AGENT_INSTRUCTION"
  | "TOOL_USAGE_GUIDE"
  | "EVALUATION"
  | "GENERAL_TASK";

export const ITEM_TYPES = ["SKILL", "PROMPT"] as const satisfies readonly VisibleItemType[];
export const BACKEND_ITEM_TYPES = ["SKILL", "WORKFLOW", "KNOWLEDGE", "PROMPT"] as const satisfies readonly ItemType[];
export const PROMPT_CONTENT_FORMATS = ["MARKDOWN", "XML", "JSON", "TEXT"] as const satisfies readonly PromptContentFormat[];
export const PROMPT_KINDS = ["SYSTEM", "DEVELOPER", "USER_TEMPLATE", "EVAL", "TOOL_GUIDE", "CHAIN"] as const satisfies readonly PromptKind[];
export const PROMPT_DOMAINS = ["DEVELOPMENT", "DESIGN", "WRITING", "RESEARCH", "ANALYSIS", "PLANNING", "REVIEW", "TESTING", "DEBUGGING", "OPERATIONS", "DATA", "EDUCATION", "MARKETING", "PRODUCT", "SECURITY", "GENERAL"] as const satisfies readonly PromptDomain[];
export const PROMPT_TASK_TYPES = ["CODE_GENERATION", "CODE_REVIEW", "TEST_GENERATION", "BUG_DIAGNOSIS", "FEATURE_PLANNING", "UI_COPYWRITING", "DOCUMENT_SUMMARY", "DOCUMENT_CREATION", "REQUIREMENTS_ANALYSIS", "RESEARCH_SYNTHESIS", "IMAGE_PROMPTING", "AGENT_INSTRUCTION", "TOOL_USAGE_GUIDE", "EVALUATION", "GENERAL_TASK"] as const satisfies readonly PromptTaskType[];
export const PROVIDER_TYPES = ["OPENAI", "MINIO"] as const satisfies readonly ProviderType[];
export const LIBRARIAN_AUTH_TYPES = ["API_KEY"] as const satisfies readonly AuthType[];

export function isItemType(value: string): value is VisibleItemType {
  return (ITEM_TYPES as readonly string[]).includes(value);
}

export function isBackendItemType(value: string): value is ItemType {
  return (BACKEND_ITEM_TYPES as readonly string[]).includes(value);
}

export type CategoryNode = {
  id: string;
  name: string;
  slug: string;
  parentId: string | null;
  children: CategoryNode[];
  skillCount: number;
};

export type PromptVariableDTO = {
  name: string;
  required: boolean;
  description: string | null;
  defaultValue: string | null;
  example: string | null;
  inputType: string;
};

export type PromptMetadataDTO = {
  contentFormat: PromptContentFormat;
  promptKind: PromptKind;
  promptDomain: PromptDomain;
  promptTaskType: PromptTaskType;
  inputVariables: PromptVariableDTO[];
  outputFormat: string | null;
  targetActor: string | null;
  targetModelFamily: string | null;
  language: string | null;
  relatedItemIds: string[];
  safetyNotes: string | null;
  changeSummary: string | null;
};

export type LibraryItemCardDTO = {
  id: string;
  title: string;
  slug: string;
  description: string;
  content: string;
  type: ArchiveType;
  version: string;
  author: string;
  category: { id: string | null; name: string; slug: string };
  tags: string[];
  updatedAt: string;
  lastAccessedAt: string | null;
  usageCount: number;
  prompt: PromptMetadataDTO | null;
};

export type SkillCardDTO = LibraryItemCardDTO;

export type LibraryItemDetailDTO = LibraryItemCardDTO & {
  usageHistory: Array<{
    id: string;
    accessedAt: string;
    agentName: string;
    accessMethod: SelectionSource;
  }>;
  tableOfContents: Array<{ id: string; label: string }>;
  codeExamples: Array<{ language: string; title: string; code: string }>;
};

export type SkillDetailDTO = LibraryItemDetailDTO;

export type DashboardDTO = {
  stats: Array<{ label: string; value: number; hint: string }>;
  recentlyUsed: LibraryItemCardDTO[];
  recommendations: Array<{
    id: string;
    title: string;
    description: string;
    type: ArchiveType;
    usageCount: number;
  }>;
  categoryActivity: Array<{ name: string; value: number }>;
  usageTrend: Array<{ day: string; usage: number }>;
};

export type LibraryDTO = {
  items: LibraryItemCardDTO[];
  categories: CategoryNode[];
  tags: string[];
  total: number;
};

export type CategoryCreateDTO = {
  name: string;
  parentId: string | null;
};

export type CategoryDTO = {
  id: string;
  name: string;
  parentId: string | null;
  position: number;
  createdAt: string;
  updatedAt: string;
};

export type SkillCreateDTO = {
  title: string;
  summary: string | null;
  content: string;
  categoryId: string | null;
  tags: string[];
  purpose: string;
  usageExample: string | null;
  requiredTools: string[];
  riskLevel: RiskLevel;
  version: string;
  createdByName: string;
  status: Extract<ItemStatus, "DRAFT" | "ACTIVE">;
};

export type PromptCreateDTO = {
  title: string;
  summary: string | null;
  content: string;
  categoryId: string | null;
  tags: string[];
  contentFormat: PromptContentFormat;
  promptKind: PromptKind;
  promptDomain: PromptDomain;
  promptTaskType: PromptTaskType;
  inputVariables: PromptVariableDTO[];
  outputFormat: string | null;
  targetActor: string | null;
  targetModelFamily: string | null;
  language: string | null;
  relatedItemIds: string[];
  safetyNotes: string | null;
  version: string;
  changeSummary: string | null;
  createdByName: string;
  createdByType: CreatedByType;
  sourceType: SourceType;
  status: Extract<ItemStatus, "DRAFT" | "ACTIVE">;
};

export type SkillCreateResultDTO = LibraryItemCardDTO;
export type PromptCreateResultDTO = LibraryItemCardDTO;

export type LibrarianProviderDTO = {
  id: string;
  name: string;
  providerType: ProviderType;
  authType: AuthType;
  enabled: boolean;
  config: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
};

export type LibrarianProviderCredentialMode = Extract<AuthType, "API_KEY">;

export type LibrarianProviderCreateDTO = {
  name: string;
  providerType: ProviderType;
  authType: LibrarianProviderCredentialMode;
  enabled: boolean;
  config: Record<string, unknown>;
  credential: string;
};

export type LibrarianProviderUpdateDTO = Partial<
  Omit<LibrarianProviderCreateDTO, "credential"> & { credential: string }
>;

export type LibrarianProviderTestDTO = {
  providerId: string;
  ok: boolean;
  message: string;
};

export type ExternalArchiveCandidateDTO = {
  id: string;
  providerId: string;
  bucket: string;
  objectKey: string;
  title: string;
  summary: string;
  contentPreview: string;
  itemType: ItemType;
  tags: string[];
  details: Record<string, unknown>;
  confidence: number;
  needsReview: boolean;
};

export type ExternalArchiveImportResultDTO = {
  importedCount: number;
  skippedCount: number;
  itemIds: string[];
};

export type AgentDTO = {
  id: string;
  name: string;
  provider: string;
  description: string | null;
  capabilities: string[];
  createdAt: string;
  updatedAt: string;
};
