"""Typer commands for librarian readiness and compact freshness workflows."""

from __future__ import annotations

import typer

from app.cli.librarian_command_context import build_librarian_gateway
from app.cli.mcp_server_commands import _mcp_smoke_tools
from app.cli.output import run_json_command
from app.cli.type_validate.command_options import (
    DEFAULT_REQUIRED_MCP_TOOLS,
    ApplyOption,
    CompactRefreshOptions,
    CoveredToOption,
    ForceOption,
    ForceRefreshOption,
    LibrarianReadinessOptions,
    MaxCompactAgeDaysOption,
    ProjectOption,
    RefreshCompactOption,
    SummaryOption,
)
from app.cli.type_validate.librarian_payload_schemas import LibrarianCheckPayload
from app.cli.type_validate.librarian_payload_views import (
    check_ok,
    check_summary,
    preflight_ready,
)
from app.mcp_server.backend_api_client import AlexandriaApiSettings
from app.shared.types.extra_types import JSONValue


def register_librarian_readiness_commands(app: typer.Typer) -> None:
    """Register readiness-related librarian commands on the parent Typer app.

    Args:
        app: Parent librarian Typer app.
    """
    app.command("readiness")(_readiness)
    app.command("refresh-current-compact")(_refresh_current_compact)
    app.command("preflight")(_preflight)
    app.command("check")(_check)


def _readiness(
    project: ProjectOption = None,
    max_compact_age_days: MaxCompactAgeDaysOption = 30,
) -> int:
    """Check librarian/second-brain readiness."""
    options = LibrarianReadinessOptions(
        project=project,
        max_compact_age_days=max_compact_age_days,
    )

    async def operation() -> JSONValue:
        return await build_librarian_gateway().readiness(options)

    exit_code = run_json_command(operation, error_prefix="Alexandria API error")
    return exit_code


def _refresh_current_compact(
    project: ProjectOption = None,
    max_compact_age_days: MaxCompactAgeDaysOption = 30,
    apply: ApplyOption = False,
    force: ForceOption = False,
    covered_to: CoveredToOption = None,
) -> int:
    """Plan or apply a CURRENT Memory Compact refresh."""
    options = CompactRefreshOptions(
        project=project,
        max_compact_age_days=max_compact_age_days,
        apply=apply,
        force=force,
        covered_to=covered_to,
    )

    async def operation() -> JSONValue:
        return await build_librarian_gateway().refresh_current_compact(options)

    exit_code = run_json_command(operation, error_prefix="Alexandria API error")
    return exit_code


def _preflight(
    project: ProjectOption = None,
    max_compact_age_days: MaxCompactAgeDaysOption = 30,
    refresh_compact: RefreshCompactOption = False,
    force_refresh: ForceRefreshOption = False,
    covered_to: CoveredToOption = None,
) -> int:
    """Check librarian readiness and fail non-zero when attention is needed."""
    options = CompactRefreshOptions(
        project=project,
        max_compact_age_days=max_compact_age_days,
        apply=refresh_compact,
        force=force_refresh,
        covered_to=covered_to,
    )

    async def operation() -> JSONValue:
        return await build_librarian_gateway().refresh_current_compact(options)

    exit_code = run_json_command(
        operation,
        error_prefix="Alexandria API error",
        attention_required=lambda payload: not preflight_ready(payload),
    )
    return exit_code


def _check(
    project: ProjectOption = None,
    max_compact_age_days: MaxCompactAgeDaysOption = 30,
    refresh_compact: RefreshCompactOption = False,
    force_refresh: ForceRefreshOption = False,
    covered_to: CoveredToOption = None,
    summary: SummaryOption = False,
) -> int:
    """Run MCP tool smoke and librarian preflight as one JSON check."""
    options = CompactRefreshOptions(
        project=project,
        max_compact_age_days=max_compact_age_days,
        apply=refresh_compact,
        force=force_refresh,
        covered_to=covered_to,
    )

    async def operation() -> JSONValue:
        mcp_smoke = await _mcp_smoke_tools(
            settings=AlexandriaApiSettings.from_env(),
            mcp_url=None,
            required_tools=DEFAULT_REQUIRED_MCP_TOOLS,
        )
        preflight_payload = await build_librarian_gateway().refresh_current_compact(
            options
        )
        if summary:
            return check_summary(mcp_smoke=mcp_smoke, preflight=preflight_payload)
        check_payload = LibrarianCheckPayload(
            ok=check_ok(
                check_summary(mcp_smoke=mcp_smoke, preflight=preflight_payload)
            ),
            mcp_smoke=mcp_smoke,
            preflight=preflight_payload,
        )
        return check_payload.model_dump(mode="json")

    exit_code = run_json_command(
        operation,
        error_prefix="Alexandria API error",
        attention_required=lambda payload: not check_ok(payload),
    )
    return exit_code
