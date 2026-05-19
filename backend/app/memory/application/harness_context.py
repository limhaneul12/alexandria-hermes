"""Builders for agent-owned execution harness contexts."""

from __future__ import annotations

from app.memory.domain.contracts.harness_contracts import HarnessCapture
from app.memory.domain.types.context_payload_types import ContextMetadataPayload
from app.memory.domain.types.harness_payload_types import (
    HarnessExecutionMetadataPayload,
)
from app.shared.types.extra_types import JSONObject


def build_harness_context_content(payload: HarnessCapture) -> str:
    """Build Markdown content for an agent-owned execution harness.

    Args:
        payload: Harness capture command.

    Returns:
        Markdown content that satisfies Context Harness lint requirements.
    """
    summary = _summary(payload)
    content = "\n\n".join(
        [
            f"# Harness: {payload.task_goal.strip()}",
            f"## Summary\n{summary}",
            f"## Environment\n{_optional_text(payload.environment)}",
            f"## Trigger Context\n{_optional_text(payload.trigger_context)}",
            f"## Execution Trace\n{_bullet_list(payload.steps)}",
            f"## Commands\n{_bullet_list(payload.commands)}",
            f"## Tests\n{_bullet_list(payload.tests)}",
            _failures_and_fixes(payload),
            f"## Artifacts\n{_bullet_list(payload.artifacts)}",
            f"## Reusable Procedure\n{payload.reusable_procedure.strip()}",
            f"## Recall Keywords\n{_bullet_list(payload.recall_keywords)}",
            f"## Safety Notes\n{_bullet_list(payload.safety_notes)}",
            f"## Restore Prompt\n{_restore_prompt(payload)}",
        ]
    )
    return content


def harness_context_metadata(
    payload: HarnessCapture,
) -> ContextMetadataPayload:
    """Return persistent metadata for a harness context.

    Args:
        payload: Harness capture command.

    Returns:
        Context metadata containing the structured harness contract.
    """
    harness_metadata = HarnessExecutionMetadataPayload(
        task_goal=payload.task_goal.strip(),
        environment=_optional_value(payload.environment),
        trigger_context=_optional_value(payload.trigger_context),
        steps=_clean_items(payload.steps),
        commands=_clean_items(payload.commands),
        tests=_clean_items(payload.tests),
        failures=_clean_items(payload.failures),
        fixes=_clean_items(payload.fixes),
        artifacts=_clean_items(payload.artifacts),
        reusable_procedure=payload.reusable_procedure.strip(),
        recall_keywords=_clean_items(payload.recall_keywords),
        safety_notes=_clean_items(payload.safety_notes),
    )
    context_metadata = ContextMetadataPayload()
    context_metadata.update(payload.metadata.items())
    context_metadata["harness"] = _harness_metadata_json(harness_metadata)
    return context_metadata


def _harness_metadata_json(payload: HarnessExecutionMetadataPayload) -> JSONObject:
    return {
        "task_goal": payload["task_goal"],
        "environment": payload["environment"],
        "trigger_context": payload["trigger_context"],
        "steps": payload["steps"],
        "commands": payload["commands"],
        "tests": payload["tests"],
        "failures": payload["failures"],
        "fixes": payload["fixes"],
        "artifacts": payload["artifacts"],
        "reusable_procedure": payload["reusable_procedure"],
        "recall_keywords": payload["recall_keywords"],
        "safety_notes": payload["safety_notes"],
    }


def _summary(payload: HarnessCapture) -> str:
    if payload.summary is not None and payload.summary.strip():
        return payload.summary.strip()
    return f"Execution harness for: {payload.task_goal.strip()}."


def _restore_prompt(payload: HarnessCapture) -> str:
    keywords = ", ".join(_clean_items(payload.recall_keywords))
    if keywords:
        return (
            "Recall this HARNESS when a future task matches these signals: "
            f"{keywords}. Reuse the procedure and review the safety notes."
        )
    return (
        "Recall this HARNESS when a future task has a similar goal: "
        f"{payload.task_goal.strip()}. Reuse the procedure and review the safety notes."
    )


def _failures_and_fixes(payload: HarnessCapture) -> str:
    return "\n\n".join(
        [
            "## Failures and Fixes",
            f"### Failures\n{_bullet_list(payload.failures)}",
            f"### Fixes\n{_bullet_list(payload.fixes)}",
        ]
    )


def _optional_text(value: str | None) -> str:
    normalized = _optional_value(value)
    if normalized is None:
        return "- Not recorded."
    return normalized


def _optional_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    return normalized


def _bullet_list(values: list[str]) -> str:
    items = _clean_items(values)
    if not items:
        return "- Not recorded."
    return "\n".join(f"- {item}" for item in items)


def _clean_items(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]
