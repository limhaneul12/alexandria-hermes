import type {
  CategoryCreateDTO,
  CategoryNode,
} from "@/types/library";

export type CategoryOption = {
  id: string;
  label: string;
};

export function flattenCategoryOptions(categories: CategoryNode[], depth = 0): CategoryOption[] {
  return categories.flatMap((category) => [
    { id: category.id, label: `${"　".repeat(depth)}${category.name}` },
    ...flattenCategoryOptions(category.children, depth + 1),
  ]);
}

export function buildCategoryCreatePayload(name: string, parentId: string): CategoryCreateDTO {
  return {
    name: name.trim(),
    parentId: parentId || null,
  };
}
