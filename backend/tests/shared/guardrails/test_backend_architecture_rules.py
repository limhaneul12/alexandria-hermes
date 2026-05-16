"""Architecture guardrails for backend rule compliance."""

from __future__ import annotations

import ast
from pathlib import Path

from app.shared.guardrails import (
    check_broad_types,
    check_getattr_usage,
    check_lazy_import_usage,
)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = BACKEND_ROOT / "app"
LIBRARY_INTERFACE = APP_ROOT / "library" / "interface"
BOUNDED_INTERFACE_ROOTS = tuple(
    sorted(path for path in APP_ROOT.glob("*/interface") if path.is_dir())
)
SHARED_EXCEPTIONS = APP_ROOT / "shared" / "exceptions"

MODULE_LINE_BUDGET = 450
OVERSIZED_MODULE_ALLOWLIST = {
    "archive/application/minio/use_cases/import_archive_items.py": (
        "Archive import use case still coordinates object reads, mapping, and writes; "
        "split into provider config/content reader/import persister next."
    ),
    "cli_support/contracts/command_contracts.py": (
        "CLI command dataclass catalog is intentionally centralized until command "
        "groups receive package-local contract modules."
    ),
    "cli_support/handlers/collaboration.py": (
        "Collaboration CLI remains a route-handler facade after helper extraction; "
        "split provider/profile/oauth handlers by command group next."
    ),
    "cli_support/handlers/library.py": (
        "Library CLI handler combines legacy folders/items/skills flows; split by "
        "resource family when touching those commands."
    ),
    "cli_support/hermes/integration_files.py": (
        "Hermes install-file generation owns several template renderers; split into "
        "per-target writer modules before adding new templates."
    ),
    "cli_support/typer_commands/collaboration.py": (
        "Typer collaboration command tree spans provider/profile/oauth verbs; split "
        "into command-group modules before adding more verbs."
    ),
    "cli_support/typer_commands/context.py": (
        "Context CLI command tree covers lint/save/search/compact flows; split by "
        "Context Vault operation family on next CLI expansion."
    ),
    "connections/application/librarians/oauth_service.py": (
        "OAuth service owns the full device-flow lifecycle; extract token storage and "
        "status projection before adding new OAuth providers."
    ),
    "connections/infrastructure/librarians/openai_codex_oauth_adapter.py": (
        "OpenAI Codex OAuth adapter includes endpoint discovery and token mapping; "
        "split discovery/client DTO mapping before expanding providers."
    ),
    "mcp_server/backend_tool_gateway.py": (
        "MCP gateway aggregates backend tool adapters; split by tool namespace before "
        "adding new MCP write tools."
    ),
    "mcp_server/server_runtime.py": (
        "MCP server runtime still combines protocol registration and process runtime; "
        "extract transport/bootstrap before adding transports."
    ),
    "memory/application/context_service.py": (
        "Context service coordinates lint/save/search/archive lifecycle; extract recall "
        "and archive operations before adding memory features."
    ),
    "memory/interface/routers/context_router.py": (
        "Context router exposes the full Context Vault surface; split route modules by "
        "lint/save/search/archive when changing context routes."
    ),
    "memory/interface/schemas/context/context_schema.py": (
        "Context API schema catalog covers all Context Vault I/O contracts; split by "
        "operation family before adding schema groups."
    ),
}


def _python_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts
    )


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
    return imports


def _router_decorators(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(), filename=str(path))
    calls: list[ast.Call] = [
        decorator
        for node in ast.walk(tree)
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call) and _is_router_operation(decorator.func)
    ]
    return calls


def _is_router_operation(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "router"
        and node.attr in {"get", "post", "patch", "put", "delete"}
    )


def _has_keyword(call: ast.Call, name: str) -> bool:
    return any(keyword.arg == name for keyword in call.keywords)


def _is_model_validate_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "model_validate"
    )


def _is_list_type_expression(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "list"
    )


def _router_function_nodes(path: Path) -> list[ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and any(
            isinstance(decorator, ast.Call) and _is_router_operation(decorator.func)
            for decorator in node.decorator_list
        )
    ]


def _router_response_model_keyword(node: ast.AsyncFunctionDef) -> ast.AST | None:
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call) or not _is_router_operation(
            decorator.func
        ):
            continue
        for keyword in decorator.keywords:
            if keyword.arg == "response_model":
                return keyword.value
    return None


def _list_model_validate_comprehensions(
    node: ast.AsyncFunctionDef,
) -> list[ast.ListComp]:
    return [
        child
        for child in ast.walk(node)
        if isinstance(child, ast.ListComp) and _is_model_validate_call(child.elt)
    ]


def _direct_model_validate_returns(node: ast.AsyncFunctionDef) -> list[ast.Return]:
    return [
        child
        for child in ast.walk(node)
        if (
            isinstance(child, ast.Return)
            and child.value is not None
            and _is_model_validate_call(child.value)
        )
    ]


def _router_files() -> list[Path]:
    return sorted(
        router
        for interface_root in BOUNDED_INTERFACE_ROOTS
        for router in (interface_root / "routers").rglob("*_router.py")
    )


def _schema_roots() -> list[Path]:
    return sorted(
        interface_root / "schemas"
        for interface_root in BOUNDED_INTERFACE_ROOTS
        if (interface_root / "schemas").exists()
    )


def _root_python_modules(path: Path) -> list[Path]:
    return sorted(
        module
        for module in path.glob("*.py")
        if module.name not in {"__init__.py"} and not module.name.startswith("_")
    )


def test_shared_exception_catalog_has_route_mapping_and_decorator_modules() -> None:
    expected = {
        "route_exceptions.py",
        "exception_decorators.py",
        "common_exceptions.py",
    }

    missing = sorted(
        name for name in expected if not (SHARED_EXCEPTIONS / name).exists()
    )

    assert missing == []


def test_library_routers_use_shared_exception_decorator_surface() -> None:
    router_files = _router_files()
    offenders = [
        path.name
        for path in router_files
        if "app.shared.exceptions.exception_decorators" not in _module_imports(path)
        or "router_exception_status" not in path.read_text()
        or "ErrorDecorator" in path.read_text()
    ]

    assert offenders == []


def test_library_router_operations_have_descriptions() -> None:
    offenders: list[str] = []
    for path in _router_files():
        for call in _router_decorators(path):
            if not _has_keyword(call, "description"):
                lineno = getattr(call, "lineno", 0)
                offenders.append(f"{path.name}:{lineno}")

    assert offenders == []


def test_library_routers_name_model_validate_before_return() -> None:
    offenders: list[str] = []
    for path in _router_files():
        for node in _router_function_nodes(path):
            offenders.extend(
                f"{path.name}:{return_node.lineno}:{node.name}"
                for return_node in _direct_model_validate_returns(node)
            )

    assert offenders == []


def test_library_routers_use_named_root_schemas_for_list_responses() -> None:
    offenders: list[str] = []
    for path in _router_files():
        for node in _router_function_nodes(path):
            response_model = _router_response_model_keyword(node)
            returns_list = node.returns is not None and _is_list_type_expression(
                node.returns
            )
            if _is_list_type_expression(response_model) or returns_list:
                lineno = getattr(response_model or node.returns, "lineno", node.lineno)
                offenders.append(f"{path.name}:{lineno}:{node.name}")

    assert offenders == []


def test_library_routers_do_not_validate_response_lists_with_comprehensions() -> None:
    offenders: list[str] = []
    for path in _router_files():
        for node in _router_function_nodes(path):
            offenders.extend(
                f"{path.name}:{list_comp.lineno}:{node.name}"
                for list_comp in _list_model_validate_comprehensions(node)
            )

    assert offenders == []


def test_library_router_dependencies_import_from_interface_dependencies() -> None:
    router_files = _router_files()
    offenders = [
        path.name
        for path in router_files
        if "app.library.interface.routers.dependencies" in _module_imports(path)
    ]

    assert offenders == []


def test_library_interface_has_no_dependency_helper_modules() -> None:
    dependencies_dir = LIBRARY_INTERFACE / "dependencies"
    dependency_modules = (
        []
        if not dependencies_dir.exists()
        else sorted(path.name for path in dependencies_dir.glob("*.py"))
    )

    assert dependency_modules == []


def test_backend_app_does_not_use_unjustified_broad_types() -> None:
    check_broad_types.ensure_clean(BACKEND_ROOT)


def test_backend_app_does_not_use_dynamic_attribute_access_or_writes() -> None:
    check_getattr_usage.ensure_clean(BACKEND_ROOT)


def test_backend_app_does_not_use_unjustified_lazy_imports() -> None:
    check_lazy_import_usage.ensure_clean(BACKEND_ROOT)


def test_library_interface_router_folders_are_only_for_multi_module_concepts() -> None:
    routers_root = LIBRARY_INTERFACE / "routers"
    offenders = sorted(
        path.name
        for path in routers_root.iterdir()
        if path.is_dir()
        and path.name != "__pycache__"
        and len(_root_python_modules(path)) < 2
    )

    assert offenders == []


def test_interface_schema_modules_are_split_by_concept_folder() -> None:
    offenders = [
        str(path.relative_to(APP_ROOT))
        for schemas_root in _schema_roots()
        for path in _root_python_modules(schemas_root)
    ]

    assert offenders == []


def test_skill_schema_contracts_do_not_use_reexport_packages() -> None:
    schemas_root = LIBRARY_INTERFACE / "schemas"

    assert not (schemas_root / "skill_schema.py").exists()
    assert not (schemas_root / "skill" / "__init__.py").exists()


def test_interface_schema_folders_do_not_use_init_files() -> None:
    offenders = sorted(
        str(path.relative_to(APP_ROOT))
        for schemas_root in _schema_roots()
        for path in schemas_root.rglob("__init__.py")
    )

    assert offenders == []


def test_backend_app_does_not_use_protocol() -> None:
    offenders: list[str] = []
    for path in _python_files(APP_ROOT):
        source = path.read_text()
        if "Protocol" in source:
            offenders.append(str(path.relative_to(APP_ROOT)))

    assert offenders == []


def test_library_orm_model_files_use_feature_models_suffix() -> None:
    models_dir = APP_ROOT / "library" / "infrastructure" / "models"
    offenders = sorted(
        path.name
        for path in models_dir.glob("*.py")
        if path.name != "__init__.py" and not path.name.endswith("_models.py")
    )

    assert offenders == []


def test_library_interface_has_no_stale_shared_schema_base_module() -> None:
    assert not (LIBRARY_INTERFACE / "schemas" / "_types.py").exists()


def test_library_has_no_stale_split_context_modules() -> None:
    stale_patterns = (
        "*context*",
        "*librarian*",
        "*agent*",
        "*minio*",
    )
    ignored_parts = {"__pycache__"}
    offenders = sorted(
        str(path.relative_to(APP_ROOT / "library"))
        for pattern in stale_patterns
        for path in (APP_ROOT / "library").rglob(pattern)
        if path.is_file() and ignored_parts.isdisjoint(path.parts)
    )

    assert offenders == []


def test_backend_tree_has_no_local_duplicate_copy_artifacts() -> None:
    offenders = sorted(
        str(path.relative_to(BACKEND_ROOT))
        for path in BACKEND_ROOT.rglob("* 2*")
        if ".venv" not in path.parts
    )

    assert offenders == []


def test_shared_layer_does_not_import_platform_layer() -> None:
    shared_root = APP_ROOT / "shared"
    offenders = sorted(
        str(path.relative_to(APP_ROOT))
        for path in _python_files(shared_root)
        if any(module.startswith("app.platform") for module in _module_imports(path))
    )

    assert offenders == []


def test_split_context_tests_do_not_live_under_library_suite() -> None:
    stale_markers = (
        "context",
        "minio",
        "librarian",
        "agent",
        "provider_connection",
        "openai_codex",
        "chunker",
        "embedding",
    )
    library_tests = BACKEND_ROOT / "tests" / "library"
    offenders = sorted(
        str(path.relative_to(BACKEND_ROOT / "tests"))
        for path in library_tests.rglob("test_*.py")
        if any(marker in path.name for marker in stale_markers)
    )

    assert offenders == []


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_backend_app_modules_stay_under_line_budget_or_are_justified() -> None:
    oversized: list[str] = []
    for path in _python_files(APP_ROOT):
        relative = str(path.relative_to(APP_ROOT))
        line_count = _line_count(path)
        if (
            line_count > MODULE_LINE_BUDGET
            and relative not in OVERSIZED_MODULE_ALLOWLIST
        ):
            oversized.append(f"{relative}:{line_count}")

    stale_or_invalid_allowlist: list[str] = []
    for relative, reason in OVERSIZED_MODULE_ALLOWLIST.items():
        path = APP_ROOT / relative
        if not path.exists():
            stale_or_invalid_allowlist.append(f"{relative}:missing")
            continue
        line_count = _line_count(path)
        if line_count <= MODULE_LINE_BUDGET:
            stale_or_invalid_allowlist.append(
                f"{relative}:{line_count}:remove allowlist"
            )
        if len(reason.strip()) < 40:
            stale_or_invalid_allowlist.append(f"{relative}:reason too short")

    assert oversized == []
    assert stale_or_invalid_allowlist == []
