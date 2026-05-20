"""CLI handlers for Hermes collaboration, usage, and librarian commands."""

from __future__ import annotations

from app.cli_support.backend_api_client import CliBackendApiClient
from app.cli_support.contracts.librarian_command_contracts import (
    LibrarianAskCommand,
    LibrarianBriefPreviewCommand,
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
from app.cli_support.handlers.collaboration_helpers import (
    librarian_ask_body,
    librarian_route_body,
    oauth_path,
    print_oauth_status,
    profile_create_body,
    profile_update_body,
    provider_create_body,
    usage_record_body,
)
from app.cli_support.presentation.output_renderers import (
    print_json,
    print_json_or_summary,
    text_field,
)
from app.cli_support.url_paths import quote_path
from app.shared.types.extra_types import JSONObject
from app.shared.utils.oauth_redaction import without_oauth_sensitive_fields


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
    payload = client.post("/library/usage", usage_record_body(command))
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        usage_id = text_field(payload, "id")
        print(f"recorded usage {usage_id}", file=context.stdout)
    return 0


def handle_librarian_brief_preview(
    command: LibrarianBriefPreviewCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the librarian brief-preview CLI command.

    Args:
        command: Typed CLI command contract for brief preview.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body: JSONObject = {
        "prompt": command.prompt,
        "budget": {
            "max_input_chars": command.max_input_chars,
            "max_source_refs": command.max_source_refs,
        },
    }
    if command.project is not None:
        body["project"] = command.project
    payload = client.post("/librarians/brief-preview", body)
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print("librarian brief preview compiled", file=context.stdout)
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
    payload = client.post("/librarians/ask", librarian_ask_body(command))
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
    payload = client.post("/librarians/route-preview", librarian_route_body(command))
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
    print_json_or_summary(payload, context, "librarian providers")
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
    print_json_or_summary(payload, context, "librarian provider")
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
    payload = provider_create_body(command)
    result = client.post("/settings/connections", payload)
    print_json_or_summary(result, context, "created librarian provider")
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
    )
    provider = client.post(
        "/settings/connections", provider_create_body(provider_payload)
    )
    provider_id = text_field(provider, "id")
    oauth_payload = client.post(oauth_path(provider_id, "start"), {})
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
    print_json_or_summary(payload, context, "librarian profiles")
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
    print_json_or_summary(payload, context, "librarian profile")
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
    payload = client.post("/librarians/profiles", profile_create_body(command))
    print_json_or_summary(payload, context, "created librarian profile")
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
    payload = profile_update_body(command, current)
    updated = client.patch(
        f"/librarians/profiles/{quote_path(command.profile_id)}",
        payload,
    )
    print_json_or_summary(updated, context, "updated librarian profile")
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
    print_json_or_summary(payload, context, "enabled librarian profile")
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
    print_json_or_summary(payload, context, "disabled librarian profile")
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
    payload = client.post(oauth_path(command.provider_id, "start"), {})
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
    payload = client.post(oauth_path(command.provider_id, "poll"), {})
    print_oauth_status(command.provider_id, payload, context)
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
    payload = client.get(oauth_path(command.provider_id, "status"))
    print_oauth_status(command.provider_id, payload, context)
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
    payload = client.post(oauth_path(command.provider_id, "refresh"), {})
    print_oauth_status(command.provider_id, payload, context)
    return 0
