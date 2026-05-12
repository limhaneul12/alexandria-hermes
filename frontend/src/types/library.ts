export type ArchiveType = "SKILL" | "WORKFLOW" | "KNOWLEDGE" | "CHECKLIST" | "POLICY";

export type CategoryNode = {
  id: number;
  name: string;
  slug: string;
  parentId: number | null;
  children: CategoryNode[];
  skillCount: number;
};

export type SkillCardDTO = {
  id: number;
  title: string;
  slug: string;
  description: string;
  content: string;
  type: ArchiveType | string;
  version: string;
  author: string;
  category: { id: number; name: string; slug: string };
  tags: string[];
  updatedAt: string;
  lastAccessedAt: string | null;
  usageCount: number;
};

export type SkillDetailDTO = SkillCardDTO & {
  usageHistory: Array<{
    id: number;
    accessedAt: string;
    agentName: string;
    accessMethod: string;
  }>;
  tableOfContents: Array<{ id: string; label: string }>;
  codeExamples: Array<{ language: string; title: string; code: string }>;
};

export type DashboardDTO = {
  stats: Array<{ label: string; value: number; hint: string }>;
  recentlyUsed: SkillCardDTO[];
  recommendations: Array<{ id: number; title: string; description: string; type: string; usageCount: number }>;
  categoryActivity: Array<{ name: string; value: number }>;
  usageTrend: Array<{ day: string; usage: number }>;
};

export type LibraryDTO = {
  items: SkillCardDTO[];
  categories: CategoryNode[];
  tags: string[];
  total: number;
};
