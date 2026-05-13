export type ItemType = "SKILL" | "WORKFLOW" | "KNOWLEDGE";
export type ArchiveType = ItemType;

export type ItemStatus = "DRAFT" | "ACTIVE" | "ARCHIVED" | "DEPRECATED";
export type SourceType =
  | "USER_CREATED"
  | "AGENT_SUBMITTED"
  | "LIBRARIAN_CREATED"
  | "IMPORTED";
export type CreatedByType = "USER" | "AGENT" | "LIBRARIAN";
export type SelectionSource = "RECOMMENDATION" | "MANUAL_BROWSE" | "SEARCH" | "DIRECT_LINK";
export type ProviderType = "OPENAI" | "OPENROUTER" | "ANTHROPIC" | "HERMES" | "LOCAL" | "CUSTOM";
export type AuthType = "API_KEY" | "OAUTH" | "NONE";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export const ITEM_TYPES = ["SKILL", "WORKFLOW", "KNOWLEDGE"] as const satisfies readonly ItemType[];
export const PROVIDER_TYPES = ["OPENAI", "OPENROUTER", "ANTHROPIC", "HERMES", "LOCAL", "CUSTOM"] as const satisfies readonly ProviderType[];
export const LIBRARIAN_AUTH_TYPES = ["API_KEY"] as const satisfies readonly AuthType[];

export function isItemType(value: string): value is ItemType {
  return (ITEM_TYPES as readonly string[]).includes(value);
}

export type CategoryNode = {
  id: string;
  name: string;
  slug: string;
  parentId: string | null;
  children: CategoryNode[];
  skillCount: number;
};

export type SkillCardDTO = {
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
};

export type SkillDetailDTO = SkillCardDTO & {
  usageHistory: Array<{
    id: string;
    accessedAt: string;
    agentName: string;
    accessMethod: SelectionSource;
  }>;
  tableOfContents: Array<{ id: string; label: string }>;
  codeExamples: Array<{ language: string; title: string; code: string }>;
};

export type DashboardDTO = {
  stats: Array<{ label: string; value: number; hint: string }>;
  recentlyUsed: SkillCardDTO[];
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
  items: SkillCardDTO[];
  categories: CategoryNode[];
  tags: string[];
  total: number;
};

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

export type AgentDTO = {
  id: string;
  name: string;
  provider: string;
  description: string | null;
  capabilities: string[];
  preferredLibrarianProvider: string | null;
  createdAt: string;
  updatedAt: string;
};
