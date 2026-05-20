"""Native Typer commands for execution harness management."""

from __future__ import annotations

import typer
from app.cli_support.contracts.memory_command_contracts import (
    ContextIdCommand,
    HarnessCaptureCommand,
    HarnessListCommand,
)
from app.cli_support.handlers.harness import (
    handle_harness_archive,
    handle_harness_capture,
    handle_harness_check,
    handle_harness_get,
    handle_harness_list,
)
from app.cli_support.typer_commands.typer_runtime import run_client, values
from app.memory.domain.event_enum.context_enums import ContextScope

harness_app = typer.Typer(help="Manage reusable execution harnesses")


def _capture_command(
    *,
    task_goal: str,
    reusable_procedure: str | None,
    reusable_procedure_file: str | None,
    summary: str | None,
    project: str | None,
    scope: ContextScope,
    source_agent: str,
    environment: str | None,
    trigger_context: str | None,
    step: list[str] | None,
    command: list[str] | None,
    test: list[str] | None,
    failure: list[str] | None,
    fix: list[str] | None,
    artifact: list[str] | None,
    recall_keyword: list[str] | None,
    safety_note: list[str] | None,
) -> HarnessCaptureCommand:
    return HarnessCaptureCommand(
        task_goal=task_goal,
        reusable_procedure=reusable_procedure,
        reusable_procedure_file=reusable_procedure_file,
        summary=summary,
        project=project,
        scope=scope,
        source_agent=source_agent,
        environment=environment,
        trigger_context=trigger_context,
        steps=values(step),
        commands=values(command),
        tests=values(test),
        failures=values(failure),
        fixes=values(fix),
        artifacts=values(artifact),
        recall_keywords=values(recall_keyword),
        safety_notes=values(safety_note),
    )


@harness_app.command("list")
def harness_list(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project"),
    scope: ContextScope | None = typer.Option(None, "--scope"),
    source_agent: str | None = typer.Option(None, "--source-agent"),
    tag: str | None = typer.Option(None, "--tag"),
    limit: int = typer.Option(50, "--limit", min=1, max=1000),
    offset: int = typer.Option(0, "--offset", min=0),
    include_archived: bool = typer.Option(False, "--include-archived"),
) -> None:
    """List saved execution harnesses.

    Args:
        ctx: Typer context.
        project: Optional project filter.
        scope: Optional recall scope filter.
        source_agent: Optional producing-agent filter.
        tag: Optional tag filter.
        limit: Maximum harnesses to return.
        offset: Pagination offset.
        include_archived: Whether archived harnesses are included.

    Returns:
        None.
    """
    run_client(
        ctx,
        HarnessListCommand(
            project=project,
            scope=scope,
            source_agent=source_agent,
            tag=tag,
            limit=limit,
            offset=offset,
            include_archived=include_archived,
        ),
        handle_harness_list,
    )


@harness_app.command("get")
def harness_get(ctx: typer.Context, harness_id: str) -> None:
    """Read one saved execution harness.

    Args:
        ctx: Typer context.
        harness_id: Harness context identifier.

    Returns:
        None.
    """
    run_client(ctx, ContextIdCommand(context_id=harness_id), handle_harness_get)


@harness_app.command("capture")
def harness_capture(
    ctx: typer.Context,
    task_goal: str = typer.Option(..., "--task-goal"),
    reusable_procedure: str | None = typer.Option(None, "--procedure"),
    reusable_procedure_file: str | None = typer.Option(None, "--procedure-file"),
    summary: str | None = typer.Option(None, "--summary"),
    project: str | None = typer.Option(None, "--project"),
    scope: ContextScope = typer.Option(ContextScope.PROJECT, "--scope"),
    source_agent: str = typer.Option("Hermes", "--source-agent"),
    environment: str | None = typer.Option(None, "--environment"),
    trigger_context: str | None = typer.Option(None, "--trigger-context"),
    step: list[str] | None = typer.Option(None, "--step"),
    command: list[str] | None = typer.Option(None, "--command"),
    test: list[str] | None = typer.Option(None, "--test"),
    failure: list[str] | None = typer.Option(None, "--failure"),
    fix: list[str] | None = typer.Option(None, "--fix"),
    artifact: list[str] | None = typer.Option(None, "--artifact"),
    recall_keyword: list[str] | None = typer.Option(None, "--keyword"),
    safety_note: list[str] | None = typer.Option(None, "--safety-note"),
) -> None:
    """Capture a reusable execution harness.

    Args:
        ctx: Typer context.
        task_goal: Goal this harness solves.
        reusable_procedure: Inline reusable procedure content.
        reusable_procedure_file: File path or '-' for reusable procedure content.
        summary: Optional human summary.
        project: Optional project scope.
        scope: Recall-routing scope.
        source_agent: Agent creating the harness.
        environment: Optional runtime environment note.
        trigger_context: Optional reason this harness was created.
        step: Repeatable execution step.
        command: Repeatable command run by the agent.
        test: Repeatable verification item.
        failure: Repeatable failure encountered.
        fix: Repeatable fix applied.
        artifact: Repeatable related artifact reference.
        recall_keyword: Repeatable recall keyword.
        safety_note: Repeatable safety note.

    Returns:
        None.
    """
    run_client(
        ctx,
        _capture_command(
            task_goal=task_goal,
            reusable_procedure=reusable_procedure,
            reusable_procedure_file=reusable_procedure_file,
            summary=summary,
            project=project,
            scope=scope,
            source_agent=source_agent,
            environment=environment,
            trigger_context=trigger_context,
            step=step,
            command=command,
            test=test,
            failure=failure,
            fix=fix,
            artifact=artifact,
            recall_keyword=recall_keyword,
            safety_note=safety_note,
        ),
        handle_harness_capture,
    )


@harness_app.command("check")
def harness_check(
    ctx: typer.Context,
    task_goal: str = typer.Option(..., "--task-goal"),
    reusable_procedure: str | None = typer.Option(None, "--procedure"),
    reusable_procedure_file: str | None = typer.Option(None, "--procedure-file"),
    summary: str | None = typer.Option(None, "--summary"),
    project: str | None = typer.Option(None, "--project"),
    scope: ContextScope = typer.Option(ContextScope.PROJECT, "--scope"),
    source_agent: str = typer.Option("Hermes", "--source-agent"),
    environment: str | None = typer.Option(None, "--environment"),
    trigger_context: str | None = typer.Option(None, "--trigger-context"),
    step: list[str] | None = typer.Option(None, "--step"),
    command: list[str] | None = typer.Option(None, "--command"),
    test: list[str] | None = typer.Option(None, "--test"),
    failure: list[str] | None = typer.Option(None, "--failure"),
    fix: list[str] | None = typer.Option(None, "--fix"),
    artifact: list[str] | None = typer.Option(None, "--artifact"),
    recall_keyword: list[str] | None = typer.Option(None, "--keyword"),
    safety_note: list[str] | None = typer.Option(None, "--safety-note"),
) -> None:
    """Validate a reusable execution harness without saving it.

    Args:
        ctx: Typer context.
        task_goal: Goal this harness solves.
        reusable_procedure: Inline reusable procedure content.
        reusable_procedure_file: File path or '-' for reusable procedure content.
        summary: Optional human summary.
        project: Optional project scope.
        scope: Recall-routing scope.
        source_agent: Agent creating the harness.
        environment: Optional runtime environment note.
        trigger_context: Optional reason this harness was created.
        step: Repeatable execution step.
        command: Repeatable command run by the agent.
        test: Repeatable verification item.
        failure: Repeatable failure encountered.
        fix: Repeatable fix applied.
        artifact: Repeatable related artifact reference.
        recall_keyword: Repeatable recall keyword.
        safety_note: Repeatable safety note.

    Returns:
        None.
    """
    run_client(
        ctx,
        _capture_command(
            task_goal=task_goal,
            reusable_procedure=reusable_procedure,
            reusable_procedure_file=reusable_procedure_file,
            summary=summary,
            project=project,
            scope=scope,
            source_agent=source_agent,
            environment=environment,
            trigger_context=trigger_context,
            step=step,
            command=command,
            test=test,
            failure=failure,
            fix=fix,
            artifact=artifact,
            recall_keyword=recall_keyword,
            safety_note=safety_note,
        ),
        handle_harness_check,
    )


@harness_app.command("archive")
def harness_archive(ctx: typer.Context, harness_id: str) -> None:
    """Archive one saved execution harness.

    Args:
        ctx: Typer context.
        harness_id: Harness context identifier.

    Returns:
        None.
    """
    run_client(ctx, ContextIdCommand(context_id=harness_id), handle_harness_archive)
