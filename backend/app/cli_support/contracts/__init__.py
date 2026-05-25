"""Package-level exports for CLI command contracts.

Prefer importing from the concept-owned modules when a caller only needs one
command family; use this package namespace for broad CLI contract surfaces.
"""

from __future__ import annotations

from app.cli_support.contracts.codex_command_contracts import CodexMcpInstallCommand
from app.cli_support.contracts.hermes_command_contracts import (
    HermesBundleCommand,
    HermesConfigureCommand,
    HermesDoctorCommand,
    HermesInstallCommand,
    HermesOnboardCommand,
    HermesPolicyCommand,
    HermesScanCommand,
    HermesSyncCommand,
)
from app.cli_support.contracts.librarian_command_contracts import (
    LibrarianAskCommand,
    LibrarianBriefPreviewCommand,
    LibrarianJobStatusCommand,
    LibrarianOAuthCommand,
    LibrarianProfileActionCommand,
    LibrarianProfileCreateCommand,
    LibrarianProfileUpdateCommand,
    LibrarianProviderActionCommand,
    LibrarianProviderConnectCodexOAuthCommand,
    LibrarianProviderCreateCommand,
    LibrarianRoutePreviewCommand,
)
from app.cli_support.contracts.memory_command_contracts import (
    ContextCurateCommand,
    ContextIdCommand,
    ContextMemoryMapCommand,
    ContextRecallCommand,
    ContextReindexCommand,
    MemoryCompactIdCommand,
    MemoryCompactListCommand,
)
from app.cli_support.contracts.runtime_command_contracts import (
    DaemonCommand,
    McpServeCommand,
    NoArgsCommand,
    ServeCommand,
    SetupCommand,
    SetupRuntimeMode,
)

__all__ = [
    "CodexMcpInstallCommand",
    "ContextCurateCommand",
    "ContextIdCommand",
    "ContextMemoryMapCommand",
    "ContextRecallCommand",
    "ContextReindexCommand",
    "DaemonCommand",
    "HermesBundleCommand",
    "HermesConfigureCommand",
    "HermesDoctorCommand",
    "HermesInstallCommand",
    "HermesOnboardCommand",
    "HermesPolicyCommand",
    "HermesScanCommand",
    "HermesSyncCommand",
    "LibrarianAskCommand",
    "LibrarianBriefPreviewCommand",
    "LibrarianJobStatusCommand",
    "LibrarianOAuthCommand",
    "LibrarianProfileActionCommand",
    "LibrarianProfileCreateCommand",
    "LibrarianProfileUpdateCommand",
    "LibrarianProviderActionCommand",
    "LibrarianProviderConnectCodexOAuthCommand",
    "LibrarianProviderCreateCommand",
    "LibrarianRoutePreviewCommand",
    "McpServeCommand",
    "MemoryCompactIdCommand",
    "MemoryCompactListCommand",
    "NoArgsCommand",
    "ServeCommand",
    "SetupCommand",
    "SetupRuntimeMode",
]
