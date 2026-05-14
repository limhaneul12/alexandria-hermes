"""Category hierarchy traversal helpers."""

from __future__ import annotations

from collections import deque

from app.library.domain.entities.read_models import Category


def descendants_of(nodes: list[Category], category_id: str) -> list[Category]:
    """Return descendants using ordered adjacency traversal.

    Args:
        nodes: Categories already ordered by parent and position.
        category_id: Ancestor id.

    Returns:
        Descendant categories in breadth-first ordered-adjacency order.
    """
    children_by_parent = _children_by_parent(nodes)
    descendants: list[Category] = []
    queue: deque[str] = deque([category_id])
    while queue:
        current = queue.popleft()
        direct_children = children_by_parent.get(current, [])
        descendants.extend(direct_children)
        queue.extend(node.id for node in direct_children)

    ordered_descendants = descendants
    return ordered_descendants


def max_depth(nodes: list[Category], category_id: str) -> int:
    """Compute zero-based depth from the root node.

    Args:
        nodes: Categories available for parent traversal.
        category_id: Target id.

    Returns:
        Zero-based depth. Missing nodes have depth 0.
    """
    node_by_id = {node.id: node for node in nodes}
    depth = 0
    node = node_by_id.get(category_id)
    while node is not None and node.parent_id is not None:
        depth += 1
        node = node_by_id.get(node.parent_id)

    resolved_depth = depth
    return resolved_depth


def has_descendant(nodes: list[Category], ancestor_id: str, node_id: str) -> bool:
    """Return true when ``node_id`` is in ``ancestor_id`` subtree.

    Args:
        nodes: Categories already ordered by parent and position.
        ancestor_id: Candidate ancestor.
        node_id: Node id to check.

    Returns:
        ``True`` when node is descendant.
    """
    descendants = descendants_of(nodes, ancestor_id)
    descendant_found = any(item.id == node_id for item in descendants)
    return descendant_found


def _children_by_parent(nodes: list[Category]) -> dict[str | None, list[Category]]:
    children_by_parent: dict[str | None, list[Category]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_id, []).append(node)

    grouped_children = children_by_parent
    return grouped_children
