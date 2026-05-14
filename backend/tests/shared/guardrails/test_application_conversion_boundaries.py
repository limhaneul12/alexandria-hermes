"""Guardrails for library application conversion boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = BACKEND_ROOT / "app"
APPLICATION_ROOT = APP_ROOT / "library" / "application"
PROVIDER_PAYLOAD_MAPPER = APPLICATION_ROOT / "librarians" / "provider_payload_mapper.py"

CONVERSION_HELPER_NAMES = frozenset(
    {
        "_required_datetime",
        "_string_list",
        "_selection_source",
        "_as_string",
        "_as_bool",
        "_as_dict_value",
        "_as_list_value",
        "_as_str_value",
    }
)


def _application_python_files() -> list[Path]:
    return sorted(APPLICATION_ROOT.rglob("*.py"))


def _app_python_files() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _meaningful_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = [
        arg.arg for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs
    ]
    return [arg for arg in args if arg not in {"self", "cls"}]


def _returns_meaningful_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.returns is None:
        return True
    return not (isinstance(node.returns, ast.Constant) and node.returns.value is None)


def _annotation_name(node: ast.expr | None) -> str:
    if node is None:
        return ""
    return ast.unparse(node)


def test_application_common_module_is_removed() -> None:
    """Ensure shared conversion and mapping helpers are not hidden in common.py."""
    assert not (APPLICATION_ROOT / "common.py").exists()


def test_application_services_do_not_keep_local_conversion_helpers() -> None:
    """Ensure interface payload conversion helpers live under app.shared.types."""
    failures: list[str] = []
    for path in _application_python_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name in CONVERSION_HELPER_NAMES
            ):
                failures.append(
                    f"{path.relative_to(BACKEND_ROOT)}:{node.lineno}:{node.name}"
                )
    assert failures == []


def test_application_functions_do_not_use_keyword_only_separator_by_default() -> None:
    """Ensure application functions reserve keyword-only signatures for real need."""
    failures: list[str] = []
    for path in _application_python_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.args.kwonlyargs:
                failures.append(
                    f"{path.relative_to(BACKEND_ROOT)}:{node.lineno}:{node.name}"
                )

    assert failures == []


def test_librarian_provider_payload_mapper_returns_named_contract() -> None:
    """Ensure provider response payloads do not leak broad dict contracts."""
    tree = ast.parse(PROVIDER_PAYLOAD_MAPPER.read_text())
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build_provider_payload"
    ]
    assert len(functions) == 1

    annotation = _annotation_name(functions[0].returns)
    assert annotation == "LibrarianProviderPayload"


def test_librarian_config_credential_keys_are_enum_members() -> None:
    """Ensure credential config keys are modeled as provider enum values."""
    policy_path = APPLICATION_ROOT / "librarians" / "credential_policy.py"
    enum_path = APP_ROOT / "library" / "domain" / "event_enum" / "provider_enums.py"
    policy_tree = ast.parse(policy_path.read_text())
    enum_tree = ast.parse(enum_path.read_text())
    class_names = {
        node.name for node in ast.walk(enum_tree) if isinstance(node, ast.ClassDef)
    }
    constant_names = {
        target.id
        for node in ast.walk(policy_tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    assert "ConfigCredentialKey" in class_names
    assert "CONFIG_CREDENTIAL_KEYS" not in constant_names


def test_backend_app_docstrings_with_public_function_contracts_use_google_sections() -> (
    None
):
    """Ensure app public function docstrings use Args and Returns sections."""
    failures: list[str] = []
    for path in _app_python_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue
            docstring = ast.get_docstring(node)
            if docstring is None:
                continue
            needs_args = bool(_meaningful_args(node))
            needs_returns = _returns_meaningful_value(node)
            missing_sections = []
            if needs_args and "Args:" not in docstring:
                missing_sections.append("Args")
            if (
                needs_returns
                and "Returns:" not in docstring
                and "Yields:" not in docstring
            ):
                missing_sections.append("Returns")
            if missing_sections:
                failures.append(
                    f"{path.relative_to(BACKEND_ROOT)}:{node.lineno}:{node.name}:"
                    f"missing {','.join(missing_sections)}"
                )
    assert failures == []
