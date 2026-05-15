"""Typed command contracts passed from Typer callbacks to CLI handlers."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.event_enum.context_enums import (
    ContextImportance,
    ContextKind,
    ContextSourceType,
    RagStrategy,
)
from app.library.domain.event_enum.item_enums import CreatedByType, ItemType, SourceType
from app.library.domain.event_enum.prompt_enums import (
    PromptContentFormat,
    PromptDomain,
    PromptKind,
    PromptTaskType,
)
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.mcp_server.mcp_protocol_enums import McpTransport


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
class FoldersListCommand:
    """Parameters for listing folders."""

    tree: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldersCreateCommand:
    """Parameters for creating a folder."""

    name: str
    parent_id: str | None


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


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextIdCommand:
    """Parameters for commands targeting one context."""

    context_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesBundleCommand:
    """Shared parameters for Hermes bundle installation commands."""

    hermes_home: str | None
    api_url: str | None
    api_token: str
    dry_run: bool
    overwrite: bool


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
class HermesDoctorCommand:
    """Parameters for Hermes diagnostics."""

    hermes_home: str | None
    api_url: str | None
    api_token: str
    require_home: bool


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
