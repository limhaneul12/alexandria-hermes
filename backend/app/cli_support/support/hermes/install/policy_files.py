"""Hermes Alexandria usage policy file helpers."""

from __future__ import annotations

from pathlib import Path

from app.cli_support.support.hermes.install.schemas import HermesPolicyResult

POLICY_RELATIVE_PATH = "alexandria-hermes/policy.yaml"
DEFAULT_POLICY_MODE = "local_first_library_when_needed"


def policy_path(hermes_home: Path) -> Path:
    """Return the Alexandria policy path under a Hermes home.

    Args:
        hermes_home: Target Hermes home directory.

    Returns:
        Absolute policy file path.
    """
    return hermes_home / POLICY_RELATIVE_PATH


def default_policy_yaml(enabled: bool = True) -> str:
    """Return the default Alexandria-Hermes usage policy YAML.

    Args:
        enabled: Whether Hermes should use Alexandria by default.

    Returns:
        YAML text for the policy contract.
    """
    enabled_text = "true" if enabled else "false"
    return f"""# Alexandria-Hermes usage policy for Hermes.
# This file is installed by `alexandria-hermes hermes onboard`.
# Default is ON and local-first: Hermes should use local/current context first,
# then Alexandria when local memory, skills, prompts, or project context are insufficient.
enabled: {enabled_text}
mode: local_first_library_when_needed

read:
  search_library: true
  recall_context: true
  get_skill: true
  get_prompt: true

write:
  auto_capture_context: true
  auto_submit_skill_candidates: true
  auto_capture_prompt_candidates: true
  default_state: DRAFT
  allow_active_without_review: false

self_acquisition:
  enabled: true
  hermes_can_research_directly: true
  self_acquisition_enabled: true

librarian:
  enabled: true
  optional: true
  hermes_self_acquisition_fallback: true
  delegate_when_busy: false
  delegate_when_self_acquisition_cost_high: false
  require_explicit_user_request_for_librarian: true

safety:
  secret_lint_required: true
  reject_raw_secrets: true
  redact_before_store: true
  store_full_conversation: false
  store_temporary_todos: false

user_interruption:
  ask_before_routine_curation: false
  report_saved_assets_in_final_summary: true
"""


def write_policy(hermes_home: Path, enabled: bool) -> HermesPolicyResult:
    """Set the top-level enabled flag without resetting custom policy settings.

    Args:
        hermes_home: Target Hermes home directory.
        enabled: Whether Alexandria usage should be enabled.

    Returns:
        Policy status after writing.
    """
    target = policy_path(hermes_home)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = (
        _replace_top_level_enabled(target.read_text(encoding="utf-8"), enabled=enabled)
        if target.exists()
        else default_policy_yaml(enabled=enabled)
    )
    target.write_text(content, encoding="utf-8")
    return read_policy(hermes_home)


def read_policy(hermes_home: Path) -> HermesPolicyResult:
    """Read policy status, treating a missing file as default-on.

    Args:
        hermes_home: Target Hermes home directory.

    Returns:
        Typed policy status for CLI output.
    """
    target = policy_path(hermes_home)
    exists = target.exists()
    content = target.read_text(encoding="utf-8") if exists else ""
    self_acquisition_enabled = _parse_bool_path(
        content,
        path=("self_acquisition", "self_acquisition_enabled"),
        default=_parse_bool_path(
            content,
            path=("self_acquisition", "enabled"),
            default=True,
        ),
    )
    return HermesPolicyResult(
        hermes_home=str(hermes_home),
        policy_path=str(target),
        exists=exists,
        enabled=_parse_bool_path(content, path=("enabled",), default=True),
        mode=_parse_string_path(content, path=("mode",), default=DEFAULT_POLICY_MODE),
        self_acquisition_enabled=self_acquisition_enabled,
        librarian_enabled=_parse_bool_path(
            content,
            path=("librarian", "enabled"),
            default=True,
        ),
        librarian_optional=_parse_bool_path(
            content,
            path=("librarian", "optional"),
            default=True,
        ),
        hermes_self_acquisition_fallback=_parse_bool_path(
            content,
            path=("librarian", "hermes_self_acquisition_fallback"),
            default=True,
        ),
        autonomous_curation_enabled=_parse_bool_path(
            content,
            path=("write", "auto_capture_context"),
            default=True,
        ),
    )


def _replace_top_level_enabled(content: str, *, enabled: bool) -> str:
    """Replace or insert only the top-level enabled flag.

    Args:
        content: Existing policy text.
        enabled: Desired top-level enabled value.

    Returns:
        Policy text with custom nested settings preserved.
    """
    enabled_line = f"enabled: {'true' if enabled else 'false'}"
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("enabled:"):
            lines[index] = enabled_line
            return "\n".join(lines) + ("\n" if content.endswith("\n") else "")
    insert_at = 0
    while insert_at < len(lines) and (
        lines[insert_at].startswith("#") or not lines[insert_at].strip()
    ):
        insert_at += 1
    lines.insert(insert_at, enabled_line)
    return "\n".join(lines) + "\n"


def _parse_bool_path(content: str, *, path: tuple[str, ...], default: bool) -> bool:
    """Parse a boolean value from the generated YAML subset.

    Args:
        content: Policy YAML text.
        path: Top-level key or section/key pair.
        default: Fallback value when missing or malformed.

    Returns:
        Parsed boolean value.
    """
    value = _parse_scalar_path(content, path=path)
    if value is None:
        return default
    normalized = value.strip().strip("\"'").lower()
    if normalized == "false":
        return False
    if normalized == "true":
        return True
    return default


def _parse_string_path(content: str, *, path: tuple[str, ...], default: str) -> str:
    """Parse a string value from the generated YAML subset.

    Args:
        content: Policy YAML text.
        path: Top-level key or section/key pair.
        default: Fallback value when missing.

    Returns:
        Parsed string value.
    """
    value = _parse_scalar_path(content, path=path)
    if value is None:
        return default
    stripped = value.strip().strip("\"'")
    return stripped or default


def _parse_scalar_path(content: str, *, path: tuple[str, ...]) -> str | None:
    """Parse scalar values from the simple generated policy YAML shape.

    Args:
        content: Policy YAML text.
        path: Top-level key or section/key pair.

    Returns:
        The raw scalar text when found.
    """
    if len(path) == 1:
        prefix = f"{path[0]}:"
        for line in content.splitlines():
            if line.startswith(prefix):
                return line.removeprefix(prefix).split("#", 1)[0].strip()
        return None
    if len(path) != 2:
        return None
    section, key = path
    in_section = False
    key_prefix = f"  {key}:"
    for line in content.splitlines():
        if line.startswith(f"{section}:"):
            in_section = True
            continue
        if in_section and line and not line.startswith(" "):
            return None
        if in_section and line.startswith(key_prefix):
            return line.removeprefix(key_prefix).split("#", 1)[0].strip()
    return None
