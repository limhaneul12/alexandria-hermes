import type {
  CategoryCreateDTO,
  CategoryNode,
  CreatedByType,
  PromptContentFormat,
  PromptCreateDTO,
  PromptDomain,
  PromptKind,
  PromptTaskType,
  SourceType,
  SkillCreateDTO,
} from "@/types/library";

export type CategoryOption = {
  id: string;
  label: string;
};

export type SkillDraft = {
  title: string;
  summary: string;
  content: string;
  purpose: string;
  categoryId: string;
  tags: string;
  activate: boolean;
};

export type PromptDraft = {
  title: string;
  summary: string;
  content: string;
  categoryId: string;
  tags: string;
  contentFormat: PromptContentFormat;
  promptKind: PromptKind;
  promptDomain: PromptDomain;
  promptTaskType: PromptTaskType;
  variables: string;
  outputFormat: string;
  targetActor: string;
  targetModelFamily: string;
  language: string;
  relatedItemIds: string;
  safetyNotes: string;
  changeSummary: string;
  createdByName: string;
  createdByType: CreatedByType;
  sourceType: SourceType;
  activate: boolean;
};

export const initialSkillDraft = (): SkillDraft => ({
  title: "",
  summary: "",
  content: "",
  purpose: "",
  categoryId: "",
  tags: "",
  activate: false,
});

export const initialPromptDraft = (): PromptDraft => ({
  title: "",
  summary: "",
  content: "",
  categoryId: "",
  tags: "",
  contentFormat: "MARKDOWN",
  promptKind: "USER_TEMPLATE",
  promptDomain: "GENERAL",
  promptTaskType: "GENERAL_TASK",
  variables: "",
  outputFormat: "",
  targetActor: "",
  targetModelFamily: "",
  language: "",
  relatedItemIds: "",
  safetyNotes: "",
  changeSummary: "",
  createdByName: "library-user",
  createdByType: "USER",
  sourceType: "USER_CREATED",
  activate: false,
});

export function flattenCategoryOptions(categories: CategoryNode[], depth = 0): CategoryOption[] {
  return categories.flatMap((category) => [
    { id: category.id, label: `${"　".repeat(depth)}${category.name}` },
    ...flattenCategoryOptions(category.children, depth + 1),
  ]);
}

export function commaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function variableList(value: string): PromptCreateDTO["inputVariables"] {
  const seen = new Set<string>();
  return value
    .split(",")
    .map((raw) => raw.trim())
    .filter(Boolean)
    .map((raw) => {
      const [namePart, requiredPart, ...descriptionParts] = raw.split(":");
      const name = namePart.trim();
      const required = requiredPart?.trim() !== "optional";
      return {
        name,
        required,
        description: descriptionParts.join(":").trim() || null,
        defaultValue: null,
        example: null,
        inputType: "text",
      };
    })
    .filter((variable) => {
      if (!variable.name || seen.has(variable.name)) return false;
      seen.add(variable.name);
      return true;
    });
}

export function buildCategoryCreatePayload(name: string, parentId: string): CategoryCreateDTO {
  return {
    name: name.trim(),
    parentId: parentId || null,
  };
}

export function buildSkillCreatePayload(draft: SkillDraft): SkillCreateDTO {
  return {
    title: draft.title.trim(),
    summary: draft.summary.trim() || null,
    content: draft.content.trim(),
    categoryId: draft.categoryId || null,
    tags: commaList(draft.tags),
    purpose: draft.purpose.trim(),
    usageExample: null,
    requiredTools: [],
    riskLevel: "LOW",
    version: "1.0.0",
    createdByName: "library-user",
    status: draft.activate ? "ACTIVE" : "DRAFT",
  };
}

export function buildPromptCreatePayload(draft: PromptDraft): PromptCreateDTO {
  return {
    title: draft.title.trim(),
    summary: draft.summary.trim() || null,
    content: draft.content.trim(),
    categoryId: draft.categoryId || null,
    tags: commaList(draft.tags),
    contentFormat: draft.contentFormat,
    promptKind: draft.promptKind,
    promptDomain: draft.promptDomain,
    promptTaskType: draft.promptTaskType,
    inputVariables: variableList(draft.variables),
    outputFormat: draft.outputFormat.trim() || null,
    targetActor: draft.targetActor.trim() || null,
    targetModelFamily: draft.targetModelFamily.trim() || null,
    language: draft.language.trim() || null,
    relatedItemIds: commaList(draft.relatedItemIds),
    safetyNotes: draft.safetyNotes.trim() || null,
    version: "1.0.0",
    changeSummary: draft.changeSummary.trim() || null,
    createdByName: draft.createdByName.trim() || "library-user",
    createdByType: draft.createdByType,
    sourceType: draft.sourceType,
    status: draft.activate ? "ACTIVE" : "DRAFT",
  };
}
