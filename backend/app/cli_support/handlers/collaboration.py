"""CLI handlers for Hermes collaboration, usage, and librarian commands."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from app.cli_support.contracts.command_contracts import (
    LibrarianAskCommand,
    LibrarianJobStatusCommand,
    LibrarianOAuthCommand,
    LibrarianProfileActionCommand,
    LibrarianProfileCreateCommand,
    LibrarianProfileUpdateCommand,
    LibrarianProviderActionCommand,
    LibrarianProviderConnectCodexOAuthCommand,
    LibrarianProviderCreateCommand,
    LibrarianRoutePreviewCommand,
    UsageRecordCliCommand,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import print_json, text_field
from app.cli_support.routing.url_paths import quote_path
from app.cli_support.transport.backend_api_client import CliBackendApiClient
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.util.oauth_redaction import without_oauth_sensitive_fields

_DEFAULT_OPENAI_CODEX_OAUTH_CONFIG: JSONObject = {
    "device_authorization_url": "https://auth.openai.com/api/accounts/deviceauth/usercode",
    "device_token_url": "https://auth.openai.com/api/accounts/deviceauth/token",
    "client_id": "codex-cli",
}


def handle_usage_record(
    command: UsageRecordCliCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the usage record CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post("/library/usage", _usage_record_body(command))
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        usage_id = text_field(payload, "id")
        print(f"recorded usage {usage_id}", file=context.stdout)
    return 0


def handle_librarian_ask(
    command: LibrarianAskCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the librarian ask CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post("/librarians/ask", _librarian_ask_body(command))
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        decision = text_field(payload, "decision")
        job_id = text_field(payload, "job_id")
        print(f"librarian {decision}: {job_id}", file=context.stdout)
    return 0


def handle_librarian_route_preview(
    command: LibrarianRoutePreviewCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the librarian route-preview CLI command.

    Args:
        command: Typed CLI command contract for route preview.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post("/librarians/route-preview", _librarian_route_body(command))
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        decision = text_field(payload, "decision")
        print(f"librarian route preview: {decision}", file=context.stdout)
    return 0


def handle_librarian_job_status(
    command: LibrarianJobStatusCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the librarian job-status CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get(f"/librarians/jobs/{quote_path(command.job_id)}")
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        status = text_field(payload, "status")
        print(f"librarian job {command.job_id}: {status}", file=context.stdout)
    return 0


def handle_librarian_providers_list(
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run provider list CLI command.

    Args:
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get("/settings/connections")
    _print_json_or_summary(payload, context, "librarian providers")
    return 0


def handle_librarian_provider_get(
    command: LibrarianProviderActionCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run provider get CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get(f"/settings/connections/{quote_path(command.provider_id)}")
    _print_json_or_summary(payload, context, "librarian provider")
    return 0


def handle_librarian_provider_delete(
    command: LibrarianProviderActionCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run provider delete CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    client.delete(f"/settings/connections/{quote_path(command.provider_id)}")
    if not context.json_output:
        print(f"deleted librarian provider {command.provider_id}", file=context.stdout)
    return 0


def handle_librarian_provider_test(
    command: LibrarianProviderActionCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run provider test CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post(
        f"/settings/connections/{quote_path(command.provider_id)}/test",
        {"test_query": command.test_query or "ping"},
    )
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        ok = text_field(payload, "ok")
        message = text_field(payload, "message")
        print(
            f"librarian provider {command.provider_id}: ok={ok} {message}",
            file=context.stdout,
        )
    return 0


def handle_librarian_provider_create(
    command: LibrarianProviderCreateCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run provider create CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = _provider_create_body(command)
    result = client.post("/settings/connections", payload)
    _print_json_or_summary(result, context, "created librarian provider")
    return 0


def handle_librarian_provider_connect_codex_oauth(
    command: LibrarianProviderConnectCodexOAuthCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Create a Codex OAuth provider and start OAuth device flow.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    provider_payload = LibrarianProviderCreateCommand(
        name=command.name,
        provider_type="OPENAI_CODEX",
        auth_type="OAUTH",
        enabled=command.enabled,
        config=command.config,
        api_key_env=None,
        access_key_env=None,
        secret_key_env=None,
    )
    provider = client.post(
        "/settings/connections", _provider_create_body(provider_payload)
    )
    provider_id = text_field(provider, "id")
    oauth_payload = client.post(_oauth_path(provider_id, "start"), {})
    safe_payload = without_oauth_sensitive_fields(
        oauth_payload,
        keep_device_user_instructions=True,
    )
    if context.json_output:
        combined: JSONObject = {"provider": provider, "oauth": safe_payload}
        print_json(combined, context.stdout)
    else:
        status = text_field(safe_payload, "status")
        verification_uri = text_field(safe_payload, "verification_uri")
        user_code = text_field(safe_payload, "user_code")
        print(
            f"created provider {provider_id}; oauth {status}; "
            f"open {verification_uri}; code {user_code}",
            file=context.stdout,
        )
    return 0


def handle_librarian_profiles_list(
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run profile list CLI command.

    Args:
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get("/librarians/profiles")
    _print_json_or_summary(payload, context, "librarian profiles")
    return 0


def handle_librarian_profile_get(
    command: LibrarianProfileActionCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run profile get CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get(f"/librarians/profiles/{quote_path(command.profile_id)}")
    _print_json_or_summary(payload, context, "librarian profile")
    return 0


def handle_librarian_profile_delete(
    command: LibrarianProfileActionCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run profile delete CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    client.delete(f"/librarians/profiles/{quote_path(command.profile_id)}")
    if not context.json_output:
        print(f"deleted librarian profile {command.profile_id}", file=context.stdout)
    return 0


def handle_librarian_profile_create(
    command: LibrarianProfileCreateCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run profile create CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post("/librarians/profiles", _profile_create_body(command))
    _print_json_or_summary(payload, context, "created librarian profile")
    return 0


def handle_librarian_profile_update(
    command: LibrarianProfileUpdateCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run profile update CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    current: JSONObject | None = None
    if command.add_specialties or command.remove_specialties:
        raw_current = client.get(
            f"/librarians/profiles/{quote_path(command.profile_id)}"
        )
        current = raw_current if isinstance(raw_current, dict) else None
    payload = _profile_update_body(command, current)
    updated = client.patch(
        f"/librarians/profiles/{quote_path(command.profile_id)}",
        payload,
    )
    _print_json_or_summary(updated, context, "updated librarian profile")
    return 0


def handle_librarian_profile_enable(
    command: LibrarianProfileActionCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Enable one librarian profile.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.patch(
        f"/librarians/profiles/{quote_path(command.profile_id)}",
        {"librarian_enabled": True},
    )
    _print_json_or_summary(payload, context, "enabled librarian profile")
    return 0


def handle_librarian_profile_disable(
    command: LibrarianProfileActionCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Disable one librarian profile.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.patch(
        f"/librarians/profiles/{quote_path(command.profile_id)}",
        {"librarian_enabled": False},
    )
    _print_json_or_summary(payload, context, "disabled librarian profile")
    return 0


def handle_librarian_oauth_start(
    command: LibrarianOAuthCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the librarian oauth-start CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post(_oauth_path(command.provider_id, "start"), {})
    safe_payload = without_oauth_sensitive_fields(
        payload,
        keep_device_user_instructions=True,
    )
    if context.json_output:
        print_json(safe_payload, context.stdout)
    else:
        status = text_field(safe_payload, "status")
        verification_uri = text_field(safe_payload, "verification_uri")
        verification_uri_complete = text_field(
            safe_payload,
            "verification_uri_complete",
        )
        user_code = text_field(safe_payload, "user_code")
        target_url = verification_uri_complete or verification_uri
        suffix_parts = []
        if target_url:
            suffix_parts.append(f"open {target_url}")
        if user_code:
            suffix_parts.append(f"code {user_code}")
        suffix = f"; {'; '.join(suffix_parts)}" if suffix_parts else ""
        print(
            f"librarian oauth {command.provider_id}: {status}{suffix}",
            file=context.stdout,
        )
    return 0


def handle_librarian_oauth_poll(
    command: LibrarianOAuthCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the librarian oauth-poll CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post(_oauth_path(command.provider_id, "poll"), {})
    _print_oauth_status(command.provider_id, payload, context)
    return 0


def handle_librarian_oauth_status(
    command: LibrarianOAuthCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the librarian oauth-status CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get(_oauth_path(command.provider_id, "status"))
    _print_oauth_status(command.provider_id, payload, context)
    return 0


def handle_librarian_oauth_refresh(
    command: LibrarianOAuthCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the librarian oauth-refresh CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post(_oauth_path(command.provider_id, "refresh"), {})
    _print_oauth_status(command.provider_id, payload, context)
    return 0


def _usage_record_body(command: UsageRecordCliCommand) -> JSONObject:
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
    feedback = _usage_feedback(command)
    if feedback is not None:
        body["feedback"] = feedback
    return body


def _usage_feedback(command: UsageRecordCliCommand) -> JSONObject | str | None:
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


def _librarian_ask_body(command: LibrarianAskCommand) -> JSONObject:
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


def _librarian_route_body(command: LibrarianRoutePreviewCommand) -> JSONObject:
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


def _provider_create_body(command: LibrarianProviderCreateCommand) -> JSONObject:
    body: JSONObject = {
        "name": command.name,
        "provider_type": command.provider_type,
        "auth_type": command.auth_type,
        "enabled": command.enabled,
        "config": cast(JSONValue, command.config),
    }
    if command.api_key_env is not None:
        api_key = os.environ.get(command.api_key_env)
        if api_key:
            body["api_key"] = api_key
    if command.access_key_env is not None and command.secret_key_env is not None:
        access_key = os.environ.get(command.access_key_env)
        secret_key = os.environ.get(command.secret_key_env)
        if access_key and secret_key:
            body["api_key"] = f"{access_key}:{secret_key}"
    return body


def _profile_create_body(command: LibrarianProfileCreateCommand) -> JSONObject:
    role_prompt = _role_prompt_text(command.role_prompt, command.role_prompt_file)
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


def _profile_update_body(
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
    role_prompt = _role_prompt_text(command.role_prompt, command.role_prompt_file)
    if role_prompt is not None:
        body["description"] = role_prompt
        body["librarian_role_prompt"] = role_prompt
    if command.add_specialties or command.remove_specialties:
        specialties = _updated_specialties(command, current)
        body["capabilities"] = specialties
        body["librarian_specialties"] = specialties
    return body


def _updated_specialties(
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


def _role_prompt_text(
    role_prompt: str | None,
    role_prompt_file: str | None,
) -> str | None:
    if role_prompt_file is not None:
        return Path(role_prompt_file).read_text(encoding="utf-8").strip()
    if role_prompt is not None:
        return role_prompt
    return None


def _print_json_or_summary(
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


def _oauth_path(provider_id: str, action: str) -> str:
    return f"/settings/connections/{quote_path(provider_id)}/oauth/{action}"


def _print_oauth_status(
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
