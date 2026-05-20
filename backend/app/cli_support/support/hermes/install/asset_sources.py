"""Hermes awareness asset source loading for Alexandria integration."""

from __future__ import annotations

from pathlib import Path

SKILL_SOURCE_RELATIVE_PATH = Path("alexandria-library") / "SKILL.md"
PROMPTS_SOURCE_RELATIVE_DIR = Path("prompts")
SOURCE_ROOT_NAME = "skills_alexandria"


def load_alexandria_skill_source() -> str:
    """Load the Alexandria Hermes skill source bundle.

    Returns:
        Markdown content for the source skill.
    """
    return (
        _source_root().joinpath(SKILL_SOURCE_RELATIVE_PATH).read_text(encoding="utf-8")
    )


def load_alexandria_prompt_sources() -> dict[str, str]:
    """Load bundled prompt source files keyed by file name.

    Returns:
        Mapping of prompt file name to Markdown content.
    """
    prompts_dir = _source_root() / PROMPTS_SOURCE_RELATIVE_DIR
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(prompts_dir.glob("*.md"))
    }


def _source_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / SOURCE_ROOT_NAME
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Could not locate {SOURCE_ROOT_NAME} source bundle")
