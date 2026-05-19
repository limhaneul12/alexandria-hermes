"""Payload builders and presentation helpers for collaboration CLI handlers."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from app.cli_support.contracts.command_contracts import (
    LibrarianAskCommand,
    LibrarianProfileCreateCommand,
    LibrarianProfileUpdateCommand,
    LibrarianProviderCreateCommand,
    LibrarianRoutePreviewCommand,
    UsageRecordCliCommand,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.environment import cli_secret_value
from app.cli_support.presentation.output_renderers import print_json, text_field
from app.cli_support.url_paths import quote_path
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.utils.oauth_redaction import without_oauth_sensitive_fields


def usage_record_body(command: UsageRecordCliCommand) -> JSONObject:
    body: JSONObject = {
        "item_id": command.item_id,
        "item_type": command.item_type,
        "agent_name": command.agent_name,
        "selection_source": command.selection_source.value,
        "success": command.success,
    }
    if command.query is not None:
        body["query"] = command.query
    if command.librarian_provider is not None:
        body["librarian_provider"] = command.librarian_provider
    feedback = usage_feedback(command)
    if feedback is not None:
        body["feedback"] = feedback
    return body


def usage_feedback(command: UsageRecordCliCommand) -> JSONObject | str | None:
    if command.project is None and command.task_summary is None:
        return command.feedback
    payload: JSONObject = {}
    if command.project is not None:
        payload["project"] = command.project
    if command.task_summary is not None:
        payload["task_summary"] = command.task_summary
    if command.feedback is not None:
        payload["comment"] = command.feedback
    return payload


def librarian_ask_body(command: LibrarianAskCommand) -> JSONObject:
    body: JSONObject = {
        "prompt": command.prompt,
        "agent_name": command.agent_name,
        "delegate_to_librarian": command.delegate_to_librarian,
    }
    if command.provider_id is not None:
        body["provider_id"] = command.provider_id
    if command.librarian_profile_id is not None:
        body["librarian_profile_id"] = command.librarian_profile_id
    if command.librarian_model is not None:
        body["librarian_model"] = command.librarian_model
    if command.librarian_role_prompt is not None:
        body["librarian_role_prompt"] = command.librarian_role_prompt
    if command.max_librarian_agents is not None:
        body["max_librarian_agents"] = command.max_librarian_agents
    if command.routing_specialties:
        body["routing_specialties"] = command.routing_specialties
    if command.project is not None:
        body["project"] = command.project
    if command.task_summary is not None:
        body["task_summary"] = command.task_summary
    return body


def librarian_route_body(command: LibrarianRoutePreviewCommand) -> JSONObject:
    body: JSONObject = {
        "prompt": command.prompt,
        "agent_name": command.agent_name,
        "delegate_to_librarian": False,
    }
    if command.provider_id is not None:
        body["provider_id"] = command.provider_id
    if command.librarian_profile_id is not None:
        body["librarian_profile_id"] = command.librarian_profile_id
    if command.librarian_model is not None:
        body["librarian_model"] = command.librarian_model
    if command.librarian_role_prompt is not None:
        body["librarian_role_prompt"] = command.librarian_role_prompt
    if command.max_librarian_agents is not None:
        body["max_librarian_agents"] = command.max_librarian_agents
    if command.routing_specialties:
        body["routing_specialties"] = command.routing_specialties
    if command.project is not None:
        body["project"] = command.project
    if command.task_summary is not None:
        body["task_summary"] = command.task_summary
    return body


def provider_create_body(command: LibrarianProviderCreateCommand) -> JSONObject:
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
    body: JSONObject = {}
    if command.name is not None:
        body["name"] = command.name
    if command.role is not None:
        body["librarian_role"] = command.role
    if command.provider_id is not None:
        body["preferred_librarian_provider"] = command.provider_id
    if command.model is not None:
        body["preferred_librarian_model"] = command.model
    if command.delegate_limit is not None:
        body["max_librarian_agents"] = command.delegate_limit
    if command.routing_priority is not None:
        body["librarian_routing_priority"] = command.routing_priority
    if command.enabled is not None:
        body["librarian_enabled"] = command.enabled
    role_prompt = role_prompt_text(command.role_prompt, command.role_prompt_file)
    if role_prompt is not None:
        body["description"] = role_prompt
        body["librarian_role_prompt"] = role_prompt
    if command.add_specialties or command.remove_specialties:
        specialties = updated_specialties(command, current)
        body["capabilities"] = specialties
        body["librarian_specialties"] = specialties
    return body


def updated_specialties(
    command: LibrarianProfileUpdateCommand,
    current: JSONObject | None,
) -> list[str]:
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
    if role_prompt_file is not None:
        return Path(role_prompt_file).read_text(encoding="utf-8").strip()
    if role_prompt is not None:
        return role_prompt
    return None


def print_json_or_summary(
    payload: JSONValue,
    context: CommandContext,
    label: str,
) -> None:
    if context.json_output:
        print_json(payload, context.stdout)
        return
    if isinstance(payload, list):
        print(f"{label}: {len(payload)}", file=context.stdout)
        return
    item_id = text_field(payload, "id")
    suffix = f" {item_id}" if item_id else ""
    print(f"{label}{suffix}", file=context.stdout)


def oauth_path(provider_id: str, action: str) -> str:
    return f"/settings/connections/{quote_path(provider_id)}/oauth/{action}"


def print_oauth_status(
    provider_id: str,
    payload: JSONValue,
    context: CommandContext,
) -> None:
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
