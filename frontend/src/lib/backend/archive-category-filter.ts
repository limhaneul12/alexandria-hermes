type CategoryTreeNode = {
  id: string;
  children?: CategoryTreeNode[];
};

export function collectCategoryTreeIds(
  categories: readonly CategoryTreeNode[],
  categoryId: string,
): Set<string> {
  const ids = new Set<string>();

  function collect(node: CategoryTreeNode): void {
    ids.add(node.id);
    for (const child of node.children ?? []) {
      collect(child);
    }
  }

  function visit(nodes: readonly CategoryTreeNode[]): boolean {
    for (const node of nodes) {
      if (node.id === categoryId) {
        collect(node);
        return true;
      }
      if (visit(node.children ?? [])) return true;
    }
    return false;
  }

  visit(categories);
  return ids;
}
