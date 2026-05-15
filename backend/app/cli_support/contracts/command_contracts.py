"""Typed command contracts passed from Typer callbacks to CLI handlers."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.event_enum.item_enums import CreatedByType, ItemType, SourceType
from app.library.domain.event_enum.prompt_enums import (
    PromptContentFormat,
    PromptDomain,
    PromptKind,
    PromptTaskType,
)
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.mcp_server.mcp_protocol_enums import McpTransport
from app.memory.domain.event_enum.context_enums import (
    ContextImportance,
    ContextKind,
    ContextScope,
    ContextSourceType,
    RagStrategy,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class NoArgsCommand:
    """Parameters for commands without command-specific inputs."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillsListCommand:
    """Parameters for listing skills."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemIdCommand:
    """Parameters for commands targeting one library item."""

    item_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillsCreateCommand:
    """Parameters for creating a manual skill."""

    title: str
    purpose: str
    content: str | None
    content_file: str | None
    summary: str | None
    category_id: str | None
    tag: list[str]
    tool: list[str]
    usage_example: str | None
    risk_level: RiskLevel
    version: str
    created_by: str
    active: bool
    source_agent: str | None
    evidence_url: list[str]
    source_summary: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptsListCommand:
    """Parameters for listing prompts."""

    limit: int
    offset: int
    kind: PromptKind | None
    tag: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptsCreateCommand:
    """Parameters for creating a prompt."""

    title: str
    summary: str | None
    content: str | None
    content_file: str | None
    kind: PromptKind
    domain: PromptDomain
    task_type: PromptTaskType
    content_format: PromptContentFormat
    var: list[str]
    output_format: str | None
    target_actor: str | None
    target_model_family: str | None
    language: str | None
    related_item_id: list[str]
    category_id: str | None
    tag: list[str]
    version: str
    created_by: str
    created_by_type: CreatedByType
    source_type: SourceType
    active: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptsUseCommand:
    """Parameters for rendering and recording prompt usage."""

    item_id: str
    actor_id: str | None
    actor_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptsSearchCommand:
    """Parameters for searching prompt library items."""

    query: str
    limit: int
    offset: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptVersionCommand:
    """Parameters for updating a prompt version and optional change summary."""

    item_id: str
    version: str
    change_summary: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptDeprecateCommand:
    """Parameters for deprecating one prompt."""

    item_id: str
    reason: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptDiffCommand:
    """Parameters for diffing two prompt records."""

    left_item_id: str
    right_item_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldersListCommand:
    """Parameters for listing folders."""

    tree: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldersCreateCommand:
    """Parameters for creating a folder."""

    name: str
    parent_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldersEnsureCommand:
    """Parameters for ensuring a nested folder path."""

    path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FolderIdCommand:
    """Parameters for commands targeting one folder."""

    folder_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LibraryListCommand:
    """Parameters for listing all library items."""

    limit: int
    offset: int
    item_type: ItemType | None
    folder_id: str | None
    query: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarySearchCommand:
    """Parameters for searching library items."""

    query: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UsageRecordCliCommand:
    """Parameters for recording usage from the CLI."""

    item_id: str
    item_type: str
    selection_source: SelectionSource
    agent_name: str
    success: bool
    query: str | None
    librarian_provider: str | None
    project: str | None
    task_summary: str | None
    feedback: str | None


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
    access_key_env: str | None = None
    secret_key_env: str | None = None


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


@dataclass(frozen=True, slots=True, kw_only=True)
class MinioCommand:
    """Parameters for MINIO scan/import operations."""

    limit: int
    item_type: ItemType | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextMetadataCommand:
    """Shared context metadata parameters."""

    title: str
    kind: ContextKind
    summary: str | None
    project: str | None
    scope: ContextScope
    workspace_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None
    visibility: ContextScope
    source_agent: str
    tag: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextLintCommand(ContextMetadataCommand):
    """Parameters for linting context Markdown."""

    content_file: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextSaveCommand(ContextMetadataCommand):
    """Parameters for saving context Markdown."""

    content: str | None
    content_file: str | None
    source_type: ContextSourceType
    importance: ContextImportance


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextRecallCommand:
    """Parameters for context recall/RAG search."""

    query: str
    strategy: RagStrategy
    limit: int
    project: str | None
    kind: ContextKind | None
    include_scopes: list[ContextScope]
    workspace_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextIdCommand:
    """Parameters for commands targeting one context."""

    context_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextCompactCommand:
    """Parameters for preparing a compact handoff context."""

    current_goal: str
    completed: list[str]
    in_progress: list[str]
    key_decisions: list[str]
    next_actions: list[str]
    risks: list[str]
    project: str | None
    scope: ContextScope
    workspace_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None
    visibility: ContextScope
    source_agent: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextMemoryMapCommand:
    """Parameters for building a project memory map."""

    project: str | None
    limit: int
    include_archived: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextCurateCommand:
    """Parameters for listing curation candidates."""

    project: str | None
    stale_after_days: int
    limit: int


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesBundleCommand:
    """Shared parameters for Hermes bundle installation commands."""

    hermes_home: str | None
    api_url: str | None
    api_token: str
    dry_run: bool
    overwrite: bool
    apply: bool
    restart_hint: bool
    print_first_prompt: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesConfigureCommand:
    """Parameters for saving Hermes path configuration."""

    hermes_home: str | None
    api_url: str | None
    api_token: str
    dry_run: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesOnboardCommand(HermesBundleCommand):
    """Parameters for Hermes onboarding."""

    install_prompts: bool
    install_mcp: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesInstallCommand(HermesBundleCommand):
    """Parameters for one-command Hermes installation."""


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesDoctorCommand:
    """Parameters for Hermes diagnostics."""

    hermes_home: str | None
    api_url: str | None
    api_token: str
    require_home: bool
    deep: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesScanCommand:
    """Parameters for scanning Hermes Alexandria files."""

    path: str | None
    hermes_home: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesSyncCommand(HermesBundleCommand):
    """Parameters for syncing Hermes prompt assets."""

    path: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class McpServeCommand:
    """Parameters for running the MCP server."""

    transport: McpTransport
