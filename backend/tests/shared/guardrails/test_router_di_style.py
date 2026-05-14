"""Architecture guardrails for FastAPI router DI style."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3]
ROUTERS_DIR = BACKEND_ROOT / "app" / "library" / "interface" / "routers"

ROUTER_METHODS = {"get", "post", "patch", "put", "delete"}


def _router_files() -> list[Path]:
    return sorted(
        path
        for path in ROUTERS_DIR.rglob("*_router.py")
        if path.name != "minio_archive_router.py"
    )


def _route_functions(path: Path) -> list[ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(), filename=str(path))
    route_functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and _has_router_decorator(node)
    ]
    return route_functions


def _has_router_decorator(node: ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "router"
        and decorator.func.attr in ROUTER_METHODS
        for decorator in node.decorator_list
    )


def _has_inject_decorator(node: ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(decorator, ast.Name) and decorator.id == "inject"
        for decorator in node.decorator_list
    )


def _depends_uses_provide(default: ast.expr | None) -> bool:
    if not isinstance(default, ast.Call):
        return False
    if not isinstance(default.func, ast.Name) or default.func.id != "Depends":
        return False
    return any(_contains_provide(arg) for arg in default.args) or any(
        keyword.value is not None and _contains_provide(keyword.value)
        for keyword in default.keywords
    )


def _contains_provide(node: ast.AST) -> bool:
    if isinstance(node, ast.Subscript):
        return isinstance(node.value, ast.Name) and node.value.id == "Provide"
    return any(_contains_provide(child) for child in ast.iter_child_nodes(node))


def test_library_route_handlers_use_dependency_injector_provide() -> None:
    offenders: list[str] = []
    for path in _router_files():
        for node in _route_functions(path):
            defaults = [
                *node.args.defaults,
                *(default for default in node.args.kw_defaults if default is not None),
            ]
            if not any(_depends_uses_provide(default) for default in defaults):
                offenders.append(f"{path.name}:{node.name}")

    assert offenders == []


def test_library_route_handlers_are_injected() -> None:
    offenders: list[str] = []
    for path in _router_files():
        offenders.extend(
            f"{path.name}:{node.name}"
            for node in _route_functions(path)
            if not _has_inject_decorator(node)
        )

    assert offenders == []


def test_library_routers_import_dependency_helpers_from_interface_dependencies() -> (
    None
):
    offenders: list[str] = []
    for path in _router_files():
        source = path.read_text()
        if "app.library.interface.routers.dependencies" in source:
            offenders.append(path.name)

    assert offenders == []
