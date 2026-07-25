"""Safe Markdown and wikilink target normalization for graph relations."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.obsidian.application.graph.obsidian_graph_relation_contracts import (
    _ROOT_RELATIVE_LINK_PREFIXES,
    _WIKILINK_RE,
)


def _wikilink_targets(
    body: str,
    *,
    relative_path: str,
    alexandria_root: str,
) -> list[str]:
    targets: list[str] = []
    for match in _WIKILINK_RE.finditer(body):
        target = _normalize_wikilink_target_path(
            match.group(1),
            relative_path=relative_path,
            alexandria_root=alexandria_root,
        )
        if target is not None:
            targets.append(target)
    return targets


def _normalize_wikilink_target_path(
    path: str | None,
    *,
    relative_path: str,
    alexandria_root: str,
) -> str | None:
    normalized = _normalize_markdown_target(path)
    if normalized is None:
        return None
    root = alexandria_root.strip().strip("/") or "."
    first_segment = normalized.split("/", maxsplit=1)[0]
    if root != "." and normalized.startswith(f"{root}/"):
        return normalized
    if first_segment in _ROOT_RELATIVE_LINK_PREFIXES:
        return normalized if root == "." else f"{root}/{normalized}"
    source_parent = PurePosixPath(relative_path).parent
    return str(source_parent / normalized)


def _normalize_target_path(path: str | None, *, alexandria_root: str) -> str | None:
    normalized = _normalize_markdown_target(path)
    if normalized is None:
        return None
    root = alexandria_root.strip().strip("/") or "."
    if root == ".":
        return normalized
    if "/" in normalized:
        if normalized.startswith(f"{root}/"):
            return normalized
        return f"{root}/{normalized}"
    return f"{root}/{normalized}"


def _normalize_markdown_target(path: str | None) -> str | None:
    if path is None:
        return None
    normalized = path.strip().removeprefix("./")
    if not normalized or "://" in normalized or normalized.startswith("#"):
        return None
    normalized = normalized.removesuffix(".md") + ".md"
    if normalized.startswith("/") or ".." in normalized.split("/"):
        return None
    return normalized
