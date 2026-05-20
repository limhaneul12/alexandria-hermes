"""Native Typer commands for Hermes collaboration workflows."""

from __future__ import annotations

import typer
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
from app.cli_support.handlers.collaboration import (
    handle_librarian_ask,
    handle_librarian_brief_preview,
    handle_librarian_job_status,
    handle_librarian_oauth_poll,
    handle_librarian_oauth_refresh,
    handle_librarian_oauth_start,
    handle_librarian_oauth_status,
    handle_librarian_profile_create,
    handle_librarian_profile_delete,
    handle_librarian_profile_disable,
    handle_librarian_profile_enable,
    handle_librarian_profile_get,
    handle_librarian_profile_update,
    handle_librarian_profiles_list,
    handle_librarian_provider_connect_codex_oauth,
    handle_librarian_provider_create,
    handle_librarian_provider_delete,
    handle_librarian_provider_get,
    handle_librarian_provider_test,
    handle_librarian_providers_list,
    handle_librarian_route_preview,
    handle_usage_record,
)
from app.cli_support.typer_commands.typer_runtime import run_client, run_context, values
from app.library.domain.event_enum.usage_enums import SelectionSource

librarian_app = typer.Typer(help="Collaborate with the configured librarian")
providers_app = typer.Typer(help="Manage librarian provider connections")
profiles_app = typer.Typer(help="Manage librarian routing profiles")
usage_app = typer.Typer(help="Record Hermes usage history")

librarian_app.add_typer(providers_app, name="providers")
librarian_app.add_typer(profiles_app, name="profiles")


def _codex_oauth_config() -> dict[str, str | int | bool]:
    return {
        "device_authorization_url": "https://auth.openai.com/api/accounts/deviceauth/usercode",
        "device_token_url": "https://auth.openai.com/api/accounts/deviceauth/token",
    }


@librarian_app.command("brief-preview")
def librarian_brief_preview(
    ctx: typer.Context,
    prompt: str,
    project: str | None = typer.Option(None, "--project"),
    max_input_chars: int = typer.Option(12_000, "--max-input-chars"),
    max_source_refs: int = typer.Option(20, "--max-source-refs"),
) -> None:
    """Compile a budgeted librarian knowledge packet without delegation.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianBriefPreviewCommand(
            prompt=prompt,
            project=project,
            max_input_chars=max_input_chars,
            max_source_refs=max_source_refs,
        ),
        handle_librarian_brief_preview,
    )


@librarian_app.command("ask")
def librarian_ask(
    ctx: typer.Context,
    prompt: str,
    delegate_to_librarian: bool = typer.Option(
        False,
        "--delegate-to-librarian",
        "--delegate",
        help="Ask for profile-backed librarian delegation.",
    ),
    provider_id: str | None = typer.Option(None, "--provider-id"),
    librarian_profile_id: str | None = typer.Option(None, "--librarian-profile-id"),
    librarian_model: str | None = typer.Option(None, "--librarian-model"),
    librarian_role_prompt: str | None = typer.Option(None, "--librarian-role-prompt"),
    max_librarian_agents: int | None = typer.Option(
        None,
        "--max-librarian-agents",
        "--delegate-limit",
    ),
    specialty: list[str] | None = typer.Option(None, "--specialty"),
    agent_name: str = typer.Option("Hermes", "--agent-name"),
    project: str | None = typer.Option(None, "--project"),
    task_summary: str | None = typer.Option(None, "--task-summary"),
) -> None:
    """Ask for self-acquisition or profile-backed librarian guidance.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianAskCommand(
            prompt=prompt,
            delegate_to_librarian=delegate_to_librarian,
            provider_id=provider_id,
            agent_name=agent_name,
            project=project,
            task_summary=task_summary,
            librarian_profile_id=librarian_profile_id,
            librarian_model=librarian_model,
            librarian_role_prompt=librarian_role_prompt,
            max_librarian_agents=max_librarian_agents,
            routing_specialties=values(specialty),
        ),
        handle_librarian_ask,
    )


@librarian_app.command("route-preview")
def librarian_route_preview(
    ctx: typer.Context,
    prompt: str,
    provider_id: str | None = typer.Option(None, "--provider-id"),
    librarian_profile_id: str | None = typer.Option(None, "--librarian-profile-id"),
    librarian_model: str | None = typer.Option(None, "--librarian-model"),
    librarian_role_prompt: str | None = typer.Option(None, "--librarian-role-prompt"),
    max_librarian_agents: int | None = typer.Option(
        None,
        "--max-librarian-agents",
        "--delegate-limit",
    ),
    specialty: list[str] | None = typer.Option(None, "--specialty"),
    agent_name: str = typer.Option("Hermes", "--agent-name"),
    project: str | None = typer.Option(None, "--project"),
    task_summary: str | None = typer.Option(None, "--task-summary"),
) -> None:
    """Preview which librarian route would be used before delegation.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianRoutePreviewCommand(
            prompt=prompt,
            provider_id=provider_id,
            agent_name=agent_name,
            project=project,
            task_summary=task_summary,
            librarian_profile_id=librarian_profile_id,
            librarian_model=librarian_model,
            librarian_role_prompt=librarian_role_prompt,
            max_librarian_agents=max_librarian_agents,
            routing_specialties=values(specialty),
        ),
        handle_librarian_route_preview,
    )


@librarian_app.command("job-status")
def librarian_job_status(ctx: typer.Context, job_id: str) -> None:
    """Read status for a librarian job.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianJobStatusCommand(job_id=job_id),
        handle_librarian_job_status,
    )


@librarian_app.command("oauth-start")
def librarian_oauth_start(ctx: typer.Context, provider_id: str) -> None:
    """Start OAuth authorization for a librarian provider.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianOAuthCommand(provider_id=provider_id),
        handle_librarian_oauth_start,
    )


@librarian_app.command("oauth-poll")
def librarian_oauth_poll(ctx: typer.Context, provider_id: str) -> None:
    """Poll OAuth authorization for a librarian provider.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianOAuthCommand(provider_id=provider_id),
        handle_librarian_oauth_poll,
    )


@librarian_app.command("oauth-status")
def librarian_oauth_status(ctx: typer.Context, provider_id: str) -> None:
    """Read OAuth status for a librarian provider.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianOAuthCommand(provider_id=provider_id),
        handle_librarian_oauth_status,
    )


@librarian_app.command("oauth-refresh")
def librarian_oauth_refresh(ctx: typer.Context, provider_id: str) -> None:
    """Refresh OAuth credentials for a librarian provider when needed.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianOAuthCommand(provider_id=provider_id),
        handle_librarian_oauth_refresh,
    )


@providers_app.command("list")
def providers_list(ctx: typer.Context) -> None:
    """List librarian providers.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_context(ctx, handle_librarian_providers_list)


@providers_app.command("get")
def providers_get(ctx: typer.Context, provider_id: str) -> None:
    """Read one librarian provider.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProviderActionCommand(provider_id=provider_id),
        handle_librarian_provider_get,
    )


@providers_app.command("delete")
def providers_delete(ctx: typer.Context, provider_id: str) -> None:
    """Delete one librarian provider.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProviderActionCommand(provider_id=provider_id),
        handle_librarian_provider_delete,
    )


@providers_app.command("test")
def providers_test(
    ctx: typer.Context,
    provider_id: str,
    test_query: str = typer.Option("ping", "--test-query"),
) -> None:
    """Test one librarian provider without exposing credential material.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProviderActionCommand(provider_id=provider_id, test_query=test_query),
        handle_librarian_provider_test,
    )


@providers_app.command("create-codex-oauth")
def providers_create_codex_oauth(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    enabled: bool = typer.Option(True, "--enabled/--disabled"),
) -> None:
    """Create a pending OpenAI Codex OAuth provider.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProviderCreateCommand(
            name=name,
            provider_type="OPENAI_CODEX",
            auth_type="OAUTH",
            enabled=enabled,
            config=_codex_oauth_config(),
            api_key_env=None,
        ),
        handle_librarian_provider_create,
    )


@providers_app.command("connect-codex-oauth")
def providers_connect_codex_oauth(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    enabled: bool = typer.Option(True, "--enabled/--disabled"),
) -> None:
    """Create a Codex OAuth provider and start device authorization.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProviderConnectCodexOAuthCommand(
            name=name,
            enabled=enabled,
            config=_codex_oauth_config(),
        ),
        handle_librarian_provider_connect_codex_oauth,
    )


@providers_app.command("create-openai")
def providers_create_openai(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    api_key_env: str = typer.Option(..., "--api-key-env"),
    model: str = typer.Option("gpt-5.5", "--model"),
    enabled: bool = typer.Option(True, "--enabled/--disabled"),
) -> None:
    """Create an OpenAI API-key provider using an environment variable.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProviderCreateCommand(
            name=name,
            provider_type="OPENAI",
            auth_type="API_KEY",
            enabled=enabled,
            config={"model": model},
            api_key_env=api_key_env,
        ),
        handle_librarian_provider_create,
    )


@profiles_app.command("list")
def profiles_list(ctx: typer.Context) -> None:
    """List librarian profiles.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_context(ctx, handle_librarian_profiles_list)


@profiles_app.command("get")
def profiles_get(ctx: typer.Context, profile_id: str) -> None:
    """Read one librarian profile.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProfileActionCommand(profile_id=profile_id),
        handle_librarian_profile_get,
    )


@profiles_app.command("delete")
def profiles_delete(ctx: typer.Context, profile_id: str) -> None:
    """Delete one librarian profile.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProfileActionCommand(profile_id=profile_id),
        handle_librarian_profile_delete,
    )


@profiles_app.command("create")
def profiles_create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    role: str = typer.Option("DEFAULT_SEARCH", "--role"),
    specialty: list[str] | None = typer.Option(None, "--specialty"),
    provider_id: str | None = typer.Option(None, "--provider-id"),
    model: str | None = typer.Option(None, "--model"),
    delegate_limit: int = typer.Option(1, "--delegate-limit"),
    role_prompt: str | None = typer.Option(None, "--role-prompt"),
    role_prompt_file: str | None = typer.Option(None, "--role-prompt-file"),
    routing_priority: int = typer.Option(100, "--routing-priority"),
    enabled: bool = typer.Option(True, "--enabled/--disabled"),
) -> None:
    """Create a librarian profile with role and specialties.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProfileCreateCommand(
            name=name,
            role=role,
            specialties=values(specialty),
            provider_id=provider_id,
            model=model,
            delegate_limit=delegate_limit,
            role_prompt=role_prompt,
            role_prompt_file=role_prompt_file,
            routing_priority=routing_priority,
            enabled=enabled,
        ),
        handle_librarian_profile_create,
    )


@profiles_app.command("update")
def profiles_update(
    ctx: typer.Context,
    profile_id: str,
    name: str | None = typer.Option(None, "--name"),
    role: str | None = typer.Option(None, "--role"),
    add_specialty: list[str] | None = typer.Option(None, "--add-specialty"),
    remove_specialty: list[str] | None = typer.Option(None, "--remove-specialty"),
    provider_id: str | None = typer.Option(None, "--provider-id"),
    model: str | None = typer.Option(None, "--model"),
    delegate_limit: int | None = typer.Option(None, "--delegate-limit"),
    role_prompt: str | None = typer.Option(None, "--role-prompt"),
    role_prompt_file: str | None = typer.Option(None, "--role-prompt-file"),
    routing_priority: int | None = typer.Option(None, "--routing-priority"),
) -> None:
    """Patch a librarian profile.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProfileUpdateCommand(
            profile_id=profile_id,
            name=name,
            role=role,
            add_specialties=values(add_specialty),
            remove_specialties=values(remove_specialty),
            provider_id=provider_id,
            model=model,
            delegate_limit=delegate_limit,
            role_prompt=role_prompt,
            role_prompt_file=role_prompt_file,
            routing_priority=routing_priority,
            enabled=None,
        ),
        handle_librarian_profile_update,
    )


@profiles_app.command("enable")
def profiles_enable(ctx: typer.Context, profile_id: str) -> None:
    """Enable one librarian profile.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProfileActionCommand(profile_id=profile_id),
        handle_librarian_profile_enable,
    )


@profiles_app.command("disable")
def profiles_disable(ctx: typer.Context, profile_id: str) -> None:
    """Disable one librarian profile.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        LibrarianProfileActionCommand(profile_id=profile_id),
        handle_librarian_profile_disable,
    )


@usage_app.command("record")
def usage_record(
    ctx: typer.Context,
    item_id: str = typer.Option(..., "--item"),
    item_type: str = typer.Option(..., "--type"),
    selection_source: SelectionSource = typer.Option(
        SelectionSource.SEARCH,
        "--selection-source",
    ),
    agent_name: str = typer.Option("Hermes", "--agent-name"),
    success: bool = typer.Option(True, "--success/--failure"),
    query: str | None = typer.Option(None, "--query"),
    librarian_provider: str | None = typer.Option(None, "--librarian-provider"),
    project: str | None = typer.Option(None, "--project"),
    task_summary: str | None = typer.Option(None, "--task-summary"),
    feedback: str | None = typer.Option(None, "--feedback"),
) -> None:
    """Record one Hermes usage event.

    Args:
        ctx: Typer callback context and command-line option values.
    """
    run_client(
        ctx,
        UsageRecordCliCommand(
            item_id=item_id,
            item_type=item_type,
            selection_source=selection_source,
            agent_name=agent_name,
            success=success,
            query=query,
            librarian_provider=librarian_provider,
            project=project,
            task_summary=task_summary,
            feedback=feedback,
        ),
        handle_usage_record,
    )
