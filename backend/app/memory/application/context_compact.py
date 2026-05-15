"""Compact context construction helpers."""

from __future__ import annotations


def build_compact_context_content(
    current_goal: str,
    completed: list[str],
    in_progress: list[str],
    key_decisions: list[str],
    next_actions: list[str],
    risks: list[str],
) -> str:
    """Build a compact handoff Markdown document.

    Args:
        current_goal: Current work goal.
        completed: Completed work bullets.
        in_progress: Active work bullets.
        key_decisions: Decision bullets.
        next_actions: Next action bullets.
        risks: Risk/watchout bullets.

    Returns:
        Markdown compact context content.
    """
    content = "\n\n".join(
        [
            "# Compact Context",
            "## Summary\nCompact handoff prepared for Alexandria-Hermes.",
            f"## Current State\n- Goal: {current_goal}",
            _section("Completed", completed),
            _section("In Progress", in_progress),
            _section("Key Decisions", key_decisions),
            _section("Next Actions", next_actions),
            _section("Risks / Watchouts", risks),
            "## Restore Prompt\nContinue from this Alexandria-Hermes compact context.",
        ]
    )
    return content


def _section(title: str, values: list[str]) -> str:
    if not values:
        return f"## {title}\n- None"
    section = f"## {title}\n" + "\n".join(f"- {value}" for value in values)
    return section
