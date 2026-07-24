"""Guardrails for repository agent rule entrypoints."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CANONICAL_RULE_DIRECTORY = Path("backend/.agents/docs/rule")
CANONICAL_RULE_ENTRYPOINTS = (
    CANONICAL_RULE_DIRECTORY / "규칙.md",
    CANONICAL_RULE_DIRECTORY / "README.md",
)
ENTRYPOINT_DOCUMENTS = (
    Path("AGENTS.md"),
    Path("backend/AGENTS.md"),
    Path("CONTRIBUTING.md"),
    CANONICAL_RULE_DIRECTORY / "15-agent-execution-rules.md",
)
STALE_RULE_PATHS = (
    ".agent/docs/ruls",
    ".agent/docs/rule",
    "backend/.agent/docs/ruls",
    "backend/.agent/docs/rule",
    "backend/.agents/rule",
)


def test_canonical_agent_rule_entrypoints_exist() -> None:
    """Ensure the declared canonical rule entrypoints exist."""
    missing = [
        str(path)
        for path in CANONICAL_RULE_ENTRYPOINTS
        if not (REPOSITORY_ROOT / path).is_file()
    ]

    assert missing == []


def test_agent_entrypoint_documents_reference_only_canonical_rule_directory() -> None:
    """Ensure agent entrypoints do not direct agents to stale rule paths."""
    failures: list[str] = []
    canonical_text = str(CANONICAL_RULE_DIRECTORY)

    for relative_path in ENTRYPOINT_DOCUMENTS:
        document = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        if canonical_text not in document:
            failures.append(f"{relative_path}: missing {canonical_text}")
        for stale_path in STALE_RULE_PATHS:
            if stale_path in document:
                failures.append(f"{relative_path}: stale {stale_path}")

    assert failures == []
