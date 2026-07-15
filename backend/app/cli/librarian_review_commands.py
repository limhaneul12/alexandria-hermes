"""Typer commands for librarian review queue and vault move workflows."""

from __future__ import annotations

import typer

from app.cli.librarian_command_context import build_librarian_gateway
from app.cli.output import run_json_command
from app.cli.type_validate.command_options import (
    ConfirmApplyOption,
    LibrarianReviewOptions,
    LimitOption,
    NoReindexOption,
    ProjectOption,
    ReportPathOption,
    ReviewApplyOptions,
    ScopePathOption,
    SummaryOption,
    VerificationQueryOption,
)
from app.cli.type_validate.librarian_payload_views import (
    confirmation_required,
    review_queue_summary,
)
from app.shared.types.extra_types import JSONValue


def register_librarian_review_commands(app: typer.Typer) -> None:
    """Register review-related librarian commands on the parent Typer app.

    Args:
        app: Parent librarian Typer app.
    """
    app.command("review-queue")(_review_queue)
    app.command("review-move-plan")(_review_move_plan)
    app.command("review-apply-moves")(_review_apply_moves)


def _review_queue(
    project: ProjectOption = None,
    scope_path: ScopePathOption = None,
    limit: LimitOption = 20,
    summary: SummaryOption = False,
) -> int:
    """List notes waiting for librarian curation."""
    options = LibrarianReviewOptions(
        project=project, scope_path=scope_path, limit=limit
    )

    async def operation() -> JSONValue:
        payload = await build_librarian_gateway().review_queue(options)
        if summary:
            return review_queue_summary(payload)
        return payload

    exit_code = run_json_command(operation, error_prefix="Alexandria API error")
    return exit_code


def _review_move_plan(
    project: ProjectOption = None,
    scope_path: ScopePathOption = None,
    limit: LimitOption = 20,
) -> int:
    """Build a dry-run safe move plan from review queue candidates."""
    options = LibrarianReviewOptions(
        project=project, scope_path=scope_path, limit=limit
    )

    async def operation() -> JSONValue:
        return await build_librarian_gateway().review_move_plan(options)

    exit_code = run_json_command(operation, error_prefix="Alexandria API error")
    return exit_code


def _review_apply_moves(
    project: ProjectOption = None,
    scope_path: ScopePathOption = None,
    limit: LimitOption = 20,
    report_path: ReportPathOption = None,
    confirm_apply: ConfirmApplyOption = False,
    no_reindex: NoReindexOption = False,
    verification_query: VerificationQueryOption = None,
) -> int:
    """Apply safe moves from review queue candidates and write a report."""
    options = ReviewApplyOptions(
        review=LibrarianReviewOptions(
            project=project,
            scope_path=scope_path,
            limit=limit,
        ),
        report_path=report_path,
        reindex=not no_reindex,
        verification_query=verification_query,
        confirm_apply=confirm_apply,
    )

    async def operation() -> JSONValue:
        return await build_librarian_gateway().review_apply_moves(options)

    exit_code = run_json_command(
        operation,
        error_prefix="Alexandria API error",
        attention_required=confirmation_required,
    )
    return exit_code
