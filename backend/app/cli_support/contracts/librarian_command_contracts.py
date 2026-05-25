"""Librarian CLI command contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianBriefPreviewCommand:
    """Parameters for compiling a librarian brief preview."""

    prompt: str
    project: str | None
    max_input_chars: int
    max_source_refs: int


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianAskCommand:
    """Parameters for asking or delegating work to the librarian."""

    prompt: str
    delegate_to_librarian: bool
    provider_id: str | None
    agent_name: str
    project: str | None
    task_summary: str | None
    librarian_profile_id: str | None
    librarian_model: str | None
    librarian_role_prompt: str | None
    max_librarian_agents: int | None
    routing_specialties: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianRoutePreviewCommand:
    """Parameters for previewing librarian routing before delegation."""

    prompt: str
    provider_id: str | None
    agent_name: str
    project: str | None
    task_summary: str | None
    librarian_profile_id: str | None
    librarian_model: str | None
    librarian_role_prompt: str | None
    max_librarian_agents: int | None
    routing_specialties: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianProviderCreateCommand:
    """Parameters for creating a librarian provider from the CLI."""

    name: str
    provider_type: str
    auth_type: str
    enabled: bool
    config: dict[str, str | int | bool]
    api_key_env: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianProviderActionCommand:
    """Parameters for reading, deleting, testing, or connecting one provider."""

    provider_id: str
    test_query: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianProviderConnectCodexOAuthCommand:
    """Parameters for creating and starting a Codex OAuth provider."""

    name: str
    enabled: bool
    config: dict[str, str | int | bool]


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianProfileCreateCommand:
    """Parameters for creating a librarian profile from the CLI."""

    name: str
    role: str
    specialties: list[str]
    provider_id: str | None
    model: str | None
    delegate_limit: int
    role_prompt: str | None
    role_prompt_file: str | None
    routing_priority: int
    enabled: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianProfileUpdateCommand:
    """Parameters for patching a librarian profile from the CLI."""

    profile_id: str
    name: str | None
    role: str | None
    add_specialties: list[str]
    remove_specialties: list[str]
    provider_id: str | None
    model: str | None
    delegate_limit: int | None
    role_prompt: str | None
    role_prompt_file: str | None
    routing_priority: int | None
    enabled: bool | None


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianProfileActionCommand:
    """Parameters for reading, deleting, enabling, or disabling one profile."""

    profile_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianJobStatusCommand:
    """Parameters for reading librarian job status."""

    job_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianOAuthCommand:
    """Parameters for librarian OAuth lifecycle commands."""

    provider_id: str
