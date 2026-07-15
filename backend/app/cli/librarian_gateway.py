"""Gateway wrapper for librarian CLI backend calls."""

from __future__ import annotations

from typing import Any

from app.cli.type_validate.command_options import (
    CompactRefreshOptions,
    LibrarianReadinessOptions,
    LibrarianReviewOptions,
    ReviewApplyOptions,
)
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.shared.types.extra_types import JSONValue


class _BackendToolGatewayProxy:
    """Lazily resolve backend MCP tool gateway functions for command execution."""

    def __getattr__(self, name: str) -> Any:
        from app.mcp_server import backend_tool_gateway as real_gateway

        return getattr(real_gateway, name)


backend_tool_gateway = _BackendToolGatewayProxy()


class LibrarianGateway:
    """Call librarian MCP gateway functions with shared client state."""

    def __init__(self, client: AlexandriaApiClient) -> None:
        self._client = client

    async def readiness(self, options: LibrarianReadinessOptions) -> JSONValue:
        """Return librarian readiness for the configured project scope.

        Args:
            options: Readiness command options.

        Returns:
            JSON-compatible readiness payload.
        """
        return await backend_tool_gateway.alexandria_librarian_readiness(
            self._client,
            project=options.project,
            max_compact_age_days=options.max_compact_age_days,
        )

    async def review_queue(self, options: LibrarianReviewOptions) -> JSONValue:
        """Return notes waiting for librarian review.

        Args:
            options: Review queue command options.

        Returns:
            JSON-compatible review queue payload.
        """
        return await backend_tool_gateway.alexandria_librarian_review_queue(
            self._client,
            project=options.project,
            scope_path=options.scope_path,
            limit=options.limit,
        )

    async def review_move_plan(self, options: LibrarianReviewOptions) -> JSONValue:
        """Return a dry-run move plan for safe review queue candidates.

        Args:
            options: Review move-plan command options.

        Returns:
            JSON-compatible move-plan payload.
        """
        return await backend_tool_gateway.alexandria_librarian_review_move_plan(
            self._client,
            project=options.project,
            scope_path=options.scope_path,
            limit=options.limit,
        )

    async def review_apply_moves(self, options: ReviewApplyOptions) -> JSONValue:
        """Apply confirmed safe review queue moves.

        Args:
            options: Review apply command options.

        Returns:
            JSON-compatible apply result payload.
        """
        return await backend_tool_gateway.alexandria_librarian_review_apply_moves(
            self._client,
            project=options.review.project,
            scope_path=options.review.scope_path,
            limit=options.review.limit,
            report_path=options.report_path,
            reindex=options.reindex,
            verification_query=options.verification_query,
            confirm_apply=options.confirm_apply,
        )

    async def refresh_current_compact(
        self, options: CompactRefreshOptions
    ) -> JSONValue:
        """Plan or apply a CURRENT Memory Compact refresh.

        Args:
            options: Compact refresh command options.

        Returns:
            JSON-compatible compact refresh payload.
        """
        return await backend_tool_gateway.alexandria_librarian_refresh_current_compact(
            self._client,
            project=options.project,
            max_compact_age_days=options.max_compact_age_days,
            apply=options.apply,
            force=options.force,
            covered_to=options.covered_to,
        )
