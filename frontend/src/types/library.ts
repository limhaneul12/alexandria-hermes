export type ItemType = "SKILL" | "KNOWLEDGE" | "PROMPT";
export type VisibleItemType = "SKILL" | "PROMPT";
export type ArchiveType = VisibleItemType;

export type ItemStatus = "DRAFT" | "ACTIVE" | "ARCHIVED" | "DEPRECATED";
export type SourceType =
  | "USER_CREATED"
  | "AGENT_SUBMITTED"
  | "LIBRARIAN_CREATED"
  | "IMPORTED";
export type CreatedByType = "USER" | "AGENT" | "LIBRARIAN";
export type SelectionSource =
  | "RECOMMENDATION"
  | "MANUAL_BROWSE"
  | "SEARCH"
  | "DIRECT_LINK"
  | "UI_VIEW"
  | "CONTEXT_RECALL"
  | "SELF_ACQUISITION"
  | "LIBRARIAN_DELEGATION";
export type ProviderType = "OPENAI" | "OPENAI_CODEX" | "MINIO";
export type AuthType = "API_KEY" | "OAUTH" | "NONE";
export type LibrarianProfileRole =
  | "DEFAULT_SEARCH"
  | "SPECIALIST"
  | "QUALITY_REVIEWER"
  | "ARCHIVIST_CURATOR";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type SkillCandidateHarnessStatus = "PASSED" | "NEEDS_REVIEW";

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
export const BACKEND_ITEM_TYPES = ["SKILL", "KNOWLEDGE", "PROMPT"] as const satisfies readonly ItemType[];
export const PROMPT_CONTENT_FORMATS = ["MARKDOWN", "XML", "JSON", "TEXT"] as const satisfies readonly PromptContentFormat[];
export const PROMPT_KINDS = ["SYSTEM", "DEVELOPER", "USER_TEMPLATE", "EVAL", "TOOL_GUIDE", "CHAIN"] as const satisfies readonly PromptKind[];
export const PROMPT_DOMAINS = ["DEVELOPMENT", "DESIGN", "WRITING", "RESEARCH", "ANALYSIS", "PLANNING", "REVIEW", "TESTING", "DEBUGGING", "OPERATIONS", "DATA", "EDUCATION", "MARKETING", "PRODUCT", "SECURITY", "GENERAL"] as const satisfies readonly PromptDomain[];
export const PROMPT_TASK_TYPES = ["CODE_GENERATION", "CODE_REVIEW", "TEST_GENERATION", "BUG_DIAGNOSIS", "FEATURE_PLANNING", "UI_COPYWRITING", "DOCUMENT_SUMMARY", "DOCUMENT_CREATION", "REQUIREMENTS_ANALYSIS", "RESEARCH_SYNTHESIS", "IMAGE_PROMPTING", "AGENT_INSTRUCTION", "TOOL_USAGE_GUIDE", "EVALUATION", "GENERAL_TASK"] as const satisfies readonly PromptTaskType[];
export const PROVIDER_TYPES = ["OPENAI", "OPENAI_CODEX", "MINIO"] as const satisfies readonly ProviderType[];
export const LIBRARIAN_AUTH_TYPES = ["API_KEY", "OAUTH"] as const satisfies readonly AuthType[];

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

export type SkillCandidateHarnessCheckDTO = {
  name: string;
  passed: boolean;
  message: string;
};

export type SkillCandidateHarnessDTO = {
  status: SkillCandidateHarnessStatus;
  checks: SkillCandidateHarnessCheckDTO[];
};

export type SkillAcquisitionMetadataDTO = {
  acquisitionMethod: string;
  evidenceUrls: string[];
  sourceSummary: string | null;
  harness: SkillCandidateHarnessDTO | null;
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

export type LibrarySearchHitDTO = {
  id: string;
  itemType: ItemType;
  title: string;
  summary: string | null;
  tags: string[];
  status: ItemStatus;
  categoryId: string | null;
  score: number;
  whyMatched: string[];
  highlights: string[];
  detailsPreview: Record<string, unknown>;
  contentCharCount: number;
  updatedAt: string;
};

export type LibrarySearchDTO = {
  items: LibrarySearchHitDTO[];
  total: number;
  limit: number;
  offset: number;
};

export type LibraryItemDetailDTO = LibraryItemCardDTO & {
  skillAcquisition: SkillAcquisitionMetadataDTO | null;
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

export type LibraryUsageRecordCreateDTO = {
  itemId: string;
  itemType: ItemType;
  agentName: string;
  selectionSource: SelectionSource;
  success: boolean;
  query?: string | null;
  librarianProvider?: string | null;
  feedback?: Record<string, unknown> | string | null;
};

export type LibraryUsageRecordDTO = LibraryItemDetailDTO["usageHistory"][number];

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

export type LibrarianProviderCredentialMode = Extract<AuthType, "API_KEY" | "OAUTH">;

export type LibrarianProviderCreateDTO = {
  name: string;
  providerType: ProviderType;
  authType: LibrarianProviderCredentialMode;
  enabled: boolean;
  config: Record<string, unknown>;
  credential?: string;
};

export type LibrarianProviderUpdateDTO = Partial<
  Omit<LibrarianProviderCreateDTO, "credential"> & { credential: string }
>;

export type LibrarianProviderTestDTO = {
  providerId: string;
  ok: boolean;
  message: string;
};

export type LibrarianOAuthStartDTO = {
  providerId: string;
  status: string;
  userCode: string;
  verificationUri: string;
  verificationUriComplete: string | null;
  expiresAt: string;
  intervalSeconds: number;
};

export type LibrarianOAuthStatusDTO = {
  providerId: string;
  status: string;
  authorized: boolean;
  expiresAt: string | null;
  refreshRequired: boolean;
  message: string | null;
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
  preferredLibrarianProvider: string | null;
  preferredLibrarianModel: string | null;
  maxLibrarianAgents: number;
  librarianRolePrompt: string | null;
  librarianRole: LibrarianProfileRole;
  librarianSpecialties: string[];
  librarianRoutingPriority: number;
  librarianEnabled: boolean;
  createdAt: string;
  updatedAt: string;
};

export type AgentCreateDTO = {
  name: string;
  provider: string;
  description: string | null;
  capabilities: string[];
  preferredLibrarianProvider: string | null;
  preferredLibrarianModel: string | null;
  maxLibrarianAgents: number;
  librarianRolePrompt: string | null;
  librarianRole: LibrarianProfileRole;
  librarianSpecialties: string[];
  librarianRoutingPriority: number;
  librarianEnabled: boolean;
};

export type AgentUpdateDTO = Partial<AgentCreateDTO>;

export type LibrarianAskRequestDTO = {
  prompt: string;
  agentName?: string;
  project?: string | null;
  taskSummary?: string | null;
  delegateToLibrarian?: boolean;
  providerId?: string | null;
  librarianProfileId?: string | null;
  librarianModel?: string | null;
  librarianRolePrompt?: string | null;
  maxLibrarianAgents?: number | null;
  routingSpecialties?: string[];
  sourceRefs?: LibrarianSourceRefDTO[];
  contextCompact?: {
    markdownBody: string;
    sourceRefs: LibrarianSourceRefDTO[];
  } | null;
};

export type LibrarianSourceRefDTO = {
  sourceType: "CONTEXT" | "MEMORY_COMPACT" | "LIBRARY_ITEM" | "SKILL" | "PROMPT" | "KNOWLEDGE";
  sourceId: string;
  title: string;
  detailPath: string;
  preview: string | null;
};

export type LibrarianDelegateDTO = {
  profileId: string;
  providerId: string | null;
  status: string;
  delegateType: string;
  summary: string;
  matchedSpecialties: string[];
};

export type LibrarianAskResponseDTO = {
  jobId: string;
  status: string;
  decision: string;
  librarianAvailable: boolean;
  selfAcquisitionAllowed: boolean;
  recommendation: string;
  providerId: string | null;
  candidateId: string | null;
  librarianProfileId: string | null;
  librarianModel: string | null;
  librarianRolePrompt: string | null;
  maxLibrarianAgents: number | null;
  routePreview: string[];
  selectedProfiles: string[];
  matchedSpecialties: string[];
  qualityReviewAdded: boolean;
  routingReason: string;
  delegates: LibrarianDelegateDTO[];
};

export type LibrarianChatMode = "DIRECT_SEARCH" | "DELEGATE" | "SEARCH_AND_DELEGATE";
export type LibrarianChatTarget = "SKILL" | "PROMPT" | "CONTEXT" | "MEMORY_COMPACT";

export type LibrarianChatRequestDTO = {
  prompt: string;
  mode: LibrarianChatMode;
  targets: LibrarianChatTarget[];
  limit: number;
};

export type LibrarianDirectHitDTO = {
  id: string;
  sourceType: LibrarianSourceRefDTO["sourceType"];
  title: string;
  preview: string;
  detailPath: string;
  score: number;
};

export type LibrarianChatResponseDTO = {
  answer: string;
  directHits: LibrarianDirectHitDTO[];
  delegatedJobId: string | null;
  sourceRefs: LibrarianSourceRefDTO[];
  executionSummary: string[];
  askResponse: LibrarianAskResponseDTO | null;
};

export type ContextKind =
  | "HANDOFF"
  | "COMPACT"
  | "DECISION"
  | "BUG_ROOT_CAUSE"
  | "PLAN"
  | "RESEARCH"
  | "USAGE"
  | "MEMORY"
  | "HARNESS";
export type ContextSourceType = "AGENT" | "USER" | "SYSTEM" | "IMPORTED";
export type ContextImportance = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ContextStorageStatus =
  | "SAVED"
  | "SAVED_WITH_WARNINGS"
  | "REDACTED_AND_SAVED"
  | "BLOCKED_SECRET_RISK"
  | "PENDING_REVIEW";
export type RagStrategy = "FTS_ONLY" | "VECTOR_ONLY" | "HYBRID";
export type RagHealthState = "HEALTHY" | "DEGRADED" | "DISABLED";

export const CONTEXT_KINDS = [
  "HANDOFF",
  "COMPACT",
  "DECISION",
  "BUG_ROOT_CAUSE",
  "PLAN",
  "RESEARCH",
  "USAGE",
  "MEMORY",
  "HARNESS",
] as const satisfies readonly ContextKind[];
export const RAG_STRATEGIES = ["HYBRID", "FTS_ONLY", "VECTOR_ONLY"] as const satisfies readonly RagStrategy[];

export type ContextDTO = {
  id: string;
  kind: ContextKind;
  title: string;
  summary: string;
  content: string;
  contentFormat: string;
  project: string | null;
  sourceAgent: string;
  sourceType: ContextSourceType;
  importance: ContextImportance;
  tags: string[];
  status: ContextStorageStatus;
  qualityScore: number;
  warnings: string[];
  restorePrompt: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  lastAccessedAt: string | null;
  expiresAt: string | null;
  archivedAt: string | null;
  accessCount: number;
  isArchived: boolean;
};

export type ContextAccessActorType = "UI" | "AGENT" | "LIBRARIAN" | "SYSTEM";
export type ContextAccessMethod = "DETAIL_VIEW" | "RECALL" | "RAG_SEARCH" | "MCP_TOOL";

export type ContextAccessEventDTO = {
  id: string;
  contextId: string;
  accessedAt: string;
  actorName: string;
  actorType: ContextAccessActorType;
  accessMethod: ContextAccessMethod;
  sourceSurface: string | null;
};

export type ContextAccessEventCreateDTO = {
  actorName: string;
  actorType: ContextAccessActorType;
  accessMethod: ContextAccessMethod;
  sourceSurface: string | null;
};

export type ContextChunkDTO = {
  id: string;
  contextId: string;
  chunkIndex: number;
  heading: string | null;
  content: string;
  tokenCount: number;
  contentHash: string;
  metadata: Record<string, unknown>;
  createdAt: string;
};

export type ContextListDTO = {
  items: ContextDTO[];
  total: number;
};

export type ContextSearchDTO = {
  query: string;
  strategy: RagStrategy;
  limit: number;
  project: string | null;
  kind: ContextKind | null;
};

export type ContextSearchMatchDTO = {
  context: ContextDTO;
  chunk: ContextChunkDTO;
  score: number;
  ftsScore: number | null;
  vectorScore: number | null;
  whyRetrieved: string;
};

export type ContextPackDTO = {
  query: string;
  strategy: RagStrategy;
  effectiveStrategy: RagStrategy;
  warnings: string[];
  matches: ContextSearchMatchDTO[];
  contextPack: string;
};

export type RagStatusDTO = {
  fts: RagHealthState;
  vector: RagHealthState;
  embedding: RagHealthState;
  defaultStrategy: RagStrategy;
  modelName: string;
  dimensions: number;
  warnings: string[];
};

export type ContextPrepareCompactDTO = {
  project: string | null;
  sourceAgent: string;
  currentGoal: string;
  completed: string[];
  inProgress: string[];
  keyDecisions: string[];
  nextActions: string[];
  risks: string[];
};

export type MemoryCompactStatus = "DRAFT" | "CURRENT" | "SUPERSEDED" | "ARCHIVED";

export const MEMORY_COMPACT_STATUSES = [
  "CURRENT",
  "SUPERSEDED",
  "ARCHIVED",
  "DRAFT",
] as const satisfies readonly MemoryCompactStatus[];

export type MemoryCompactSourceRefDTO = {
  id: string;
  compactId: string;
  sourceType: string;
  sourceId: string;
  title: string;
  detailPath: string;
};

export type MemoryCompactDTO = {
  id: string;
  project: string | null;
  coveredFrom: string;
  coveredTo: string;
  markdownBody: string;
  status: MemoryCompactStatus;
  sourceRefs: MemoryCompactSourceRefDTO[];
  createdAt: string;
  updatedAt: string;
  archivedAt: string | null;
};

export type MemoryCompactListDTO = {
  items: MemoryCompactDTO[];
  total: number;
};
