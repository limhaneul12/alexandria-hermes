"""Test helpers for overriding dependency-injector library providers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from app.main import app
from dependency_injector import providers

_LIBRARY_PROVIDER_NAMES: Final[set[str]] = {
    "agent_service",
    "category_service",
    "context_service",
    "item_service",
    "knowledge_service",
    "prompt_service",
    "librarian_service",
    "skill_service",
    "usage_service",
    "workflow_service",
}


@contextmanager
def override_library_provider(provider_name: str, value: object) -> Iterator[None]:
    """Temporarily override one library provider for route contract tests."""
    if provider_name not in _LIBRARY_PROVIDER_NAMES:
        raise ValueError(f"unsupported library provider override: {provider_name}")
    provider = getattr(app.state.container.library, provider_name)
    with provider.override(providers.Object(value)):
        yield
