"""Test helpers for overriding dependency-injector providers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from app.main import app
from dependency_injector import providers

_PROVIDER_CONTAINER_BY_NAME: Final[dict[str, str]] = {
    "agent_service": "librarian",
    "context_service": "memory",
    "hermes_collaboration_service": "librarian",
    "memory_compact_service": "memory",
    "obsidian_service": "obsidian",
    "librarian_oauth_service": "connections",
    "skill_acquisition_service": "librarian",
    "librarian_service": "connections",
}


@contextmanager
def override_library_provider(provider_name: str, value: object) -> Iterator[None]:
    """Temporarily override one app provider for route contract tests."""
    container_name = _PROVIDER_CONTAINER_BY_NAME.get(provider_name)
    if container_name is None:
        raise ValueError(f"unsupported provider override: {provider_name}")
    root_container = app.state.container
    if container_name == "connections":
        provider = root_container.connections.providers[provider_name]
    elif container_name == "librarian":
        provider = root_container.librarian.providers[provider_name]
    elif container_name == "memory":
        provider = root_container.memory.providers[provider_name]
    elif container_name == "obsidian":
        provider = root_container.obsidian.providers[provider_name]
    with provider.override(providers.Object(value)):
        yield
