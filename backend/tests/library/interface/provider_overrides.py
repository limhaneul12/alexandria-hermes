"""Test helpers for overriding dependency-injector providers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from app.main import app
from dependency_injector import providers

_PROVIDER_CONTAINER_BY_NAME: Final[dict[str, str]] = {
    "agent_service": "librarian",
    "category_service": "library",
    "context_service": "memory",
    "hermes_collaboration_service": "librarian",
    "item_service": "library",
    "knowledge_service": "library",
    "librarian_oauth_service": "connections",
    "librarian_service": "connections",
    "prompt_service": "library",
    "skill_service": "library",
    "usage_service": "library",
    "workflow_service": "library",
}


@contextmanager
def override_library_provider(provider_name: str, value: object) -> Iterator[None]:
    """Temporarily override one app provider for route contract tests."""
    container_name = _PROVIDER_CONTAINER_BY_NAME.get(provider_name)
    if container_name is None:
        raise ValueError(f"unsupported provider override: {provider_name}")
    root_container = app.state.container
    if container_name == "archive":
        provider = root_container.archive.providers[provider_name]
    elif container_name == "connections":
        provider = root_container.connections.providers[provider_name]
    elif container_name == "librarian":
        provider = root_container.librarian.providers[provider_name]
    elif container_name == "memory":
        provider = root_container.memory.providers[provider_name]
    else:
        provider = root_container.library.providers[provider_name]
    with provider.override(providers.Object(value)):
        yield
