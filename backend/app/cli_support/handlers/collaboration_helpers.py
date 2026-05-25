"""Payload builders and presentation helpers for collaboration CLI handlers."""

from __future__ import annotations

from os import environ as process_environment
from pathlib import Path
from typing import cast

from app.cli_support.contracts.librarian_command_contracts import (
    LibrarianAskCommand,
    LibrarianProfileCreateCommand,
    LibrarianProfileUpdateCommand,
    LibrarianProviderCreateCommand,
    LibrarianRoutePreviewCommand,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import print_json, text_field
from app.cli_support.schemas.collaboration_payload_schemas import (
    LibrarianAskBody,
    LibrarianProfilePatchBody,
)
from app.cli_support.url_paths import quote_path
from app.shared.serialization.model_codec import schema_payload
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.utils.oauth_redaction import without_oauth_sensitive_fields


def cli_secret_value(env_name: str) -> str | None:
    """Return one CLI-provided secret environment value.

    Args:
        env_name: Environment variable name supplied by an operator CLI option.

    Returns:
        Non-empty environment value, or None.
    """
    value = process_environment.get(env_name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def librarian_ask_body(command: LibrarianAskCommand) -> JSONObject:
    """Build the ask-librarian backend body from a CLI command.

    Args:
        command: Typed CLI ask command.

    Returns:
        JSONObject: Backend request body with empty optionals omitted.
    """
    body = LibrarianAskBody(
        prompt=command.prompt,
        agent_name=command.agent_name,
        delegate_to_librarian=command.delegate_to_librarian,
        provider_id=command.provider_id,
        librarian_profile_id=command.librarian_profile_id,
        librarian_model=command.librarian_model,
        librarian_role_prompt=command.librarian_role_prompt,
        max_librarian_agents=command.max_librarian_agents,
        routing_specialties=command.routing_specialties or None,
        project=command.project,
        task_summary=command.task_summary,
    )
    return schema_payload(body, exclude_none=True)


def librarian_route_body(command: LibrarianRoutePreviewCommand) -> JSONObject:
    """Build the route-preview backend body from a CLI command.

    Args:
        command: Typed CLI route-preview command.

    Returns:
        JSONObject: Backend request body with delegation disabled.
    """
    body = LibrarianAskBody(
        prompt=command.prompt,
        agent_name=command.agent_name,
        delegate_to_librarian=False,
        provider_id=command.provider_id,
        librarian_profile_id=command.librarian_profile_id,
        librarian_model=command.librarian_model,
        librarian_role_prompt=command.librarian_role_prompt,
        max_librarian_agents=command.max_librarian_agents,
        routing_specialties=command.routing_specialties or None,
        project=command.project,
        task_summary=command.task_summary,
    )
    return schema_payload(body, exclude_none=True)


def provider_create_body(command: LibrarianProviderCreateCommand) -> JSONObject:
    """Build the provider-create backend body from a CLI command.

    Args:
        command: Typed CLI provider-create command.

    Returns:
        JSONObject: Backend request body with secret material read from env.
    """
    body: JSONObject = {
        "name": command.name,
        "provider_type": command.provider_type,
        "auth_type": command.auth_type,
        "enabled": command.enabled,
        "config": cast(JSONValue, command.config),
    }
    if command.api_key_env is not None:
        api_key = cli_secret_value(command.api_key_env)
        if api_key:
            body["api_key"] = api_key
    return body


def profile_create_body(command: LibrarianProfileCreateCommand) -> JSONObject:
    """Build the profile-create backend body from a CLI command.

    Args:
        command: Typed CLI profile-create command.

    Returns:
        JSONObject: Backend request body for a new librarian profile.
    """
    role_prompt = role_prompt_text(command.role_prompt, command.role_prompt_file)
    specialties = command.specialties
    body: JSONObject = {
        "name": command.name,
        "provider": "OPENAI_CODEX",
        "description": role_prompt,
        "capabilities": specialties,
        "preferred_librarian_provider": command.provider_id,
        "preferred_librarian_model": command.model,
        "max_librarian_agents": command.delegate_limit,
        "librarian_role_prompt": role_prompt,
        "librarian_role": command.role,
        "librarian_specialties": specialties,
        "librarian_routing_priority": command.routing_priority,
        "librarian_enabled": command.enabled,
    }
    return body


def profile_update_body(
    command: LibrarianProfileUpdateCommand,
    current: JSONObject | None,
) -> JSONObject:
    """Build the profile-patch backend body from a CLI command.

    Args:
        command: Typed CLI profile-update command.
        current: Current backend profile payload used for specialty diffs.

    Returns:
        JSONObject: Backend patch body with empty optionals omitted.
    """
    role_prompt = role_prompt_text(command.role_prompt, command.role_prompt_file)
    specialties = (
        updated_specialties(command, current)
        if command.add_specialties or command.remove_specialties
        else None
    )
    body = LibrarianProfilePatchBody(
        name=command.name,
        librarian_role=command.role,
        preferred_librarian_provider=command.provider_id,
        preferred_librarian_model=command.model,
        max_librarian_agents=command.delegate_limit,
        librarian_routing_priority=command.routing_priority,
        librarian_enabled=command.enabled,
        description=role_prompt,
        librarian_role_prompt=role_prompt,
        capabilities=specialties,
        librarian_specialties=specialties,
    )
    return schema_payload(body, exclude_none=True)


def updated_specialties(
    command: LibrarianProfileUpdateCommand,
    current: JSONObject | None,
) -> list[str]:
    """Apply CLI add/remove specialty edits to the current profile payload.

    Args:
        command: Typed CLI profile-update command.
        current: Current backend profile payload.

    Returns:
        list[str]: Updated specialty list preserving existing order.
    """
    specialties: list[str] = []
    if current is not None:
        raw_specialties = current.get("librarian_specialties")
        if isinstance(raw_specialties, list):
            specialties = [item for item in raw_specialties if isinstance(item, str)]
    remove = {item.lower() for item in command.remove_specialties}
    kept = [item for item in specialties if item.lower() not in remove]
    for specialty in command.add_specialties:
        if specialty.lower() not in {item.lower() for item in kept}:
            kept.append(specialty)
    return kept


def role_prompt_text(
    role_prompt: str | None,
    role_prompt_file: str | None,
) -> str | None:
    """Resolve inline or file-backed role prompt text.

    Args:
        role_prompt: Inline prompt text.
        role_prompt_file: Optional file path containing prompt text.

    Returns:
        str | None: Resolved role prompt text, or none when omitted.
    """
    if role_prompt_file is not None:
        return Path(role_prompt_file).read_text(encoding="utf-8").strip()
    if role_prompt is not None:
        return role_prompt
    return None


def oauth_path(provider_id: str, action: str) -> str:
    """Build a provider OAuth action path.

    Args:
        provider_id: Provider identifier.
        action: OAuth lifecycle action.

    Returns:
        str: URL path for the provider OAuth action.
    """
    return f"/settings/connections/{quote_path(provider_id)}/oauth/{action}"


def print_oauth_status(
    provider_id: str,
    payload: JSONValue,
    context: CommandContext,
) -> None:
    """Print a redacted OAuth status response.

    Args:
        provider_id: Provider identifier.
        payload: Backend OAuth status response.
        context: CLI runtime context.
    """
    safe_payload = without_oauth_sensitive_fields(payload)
    if context.json_output:
        print_json(safe_payload, context.stdout)
        return
    status = text_field(safe_payload, "status")
    connected = text_field(safe_payload, "connected")
    refresh_required = text_field(safe_payload, "refresh_required")
    detail = " ".join(
        part
        for part in (
            f"connected={connected}" if connected else "",
            f"refresh_required={refresh_required}" if refresh_required else "",
        )
        if part
    )
    suffix = f" {detail}" if detail else ""
    print(f"librarian oauth {provider_id}: {status}{suffix}", file=context.stdout)
