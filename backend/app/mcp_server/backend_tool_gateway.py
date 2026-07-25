"""MCP tool gateway backed exclusively by Alexandria-Hermes HTTP APIs."""

from __future__ import annotations

from app.mcp_server.tools.backend_gateway_policy import (
    _bounded_search_limit as _gateway_bounded_search_limit,
)
from app.mcp_server.tools.context_backend_gateway import (
    alexandria_archive_context,
    alexandria_delete_context,
    alexandria_rag_context,
    alexandria_rag_status,
    alexandria_recall_context,
    alexandria_search,
    alexandria_supersede_context,
)
from app.mcp_server.tools.librarian_readiness_tools import (
    alexandria_librarian_readiness as _alexandria_librarian_readiness,
    alexandria_librarian_refresh_current_compact as _alexandria_librarian_refresh_current_compact,
)
from app.mcp_server.tools.librarian_vault_backend_gateway import (
    alexandria_librarian_review_apply_moves,
    alexandria_librarian_review_move_plan,
    alexandria_librarian_review_queue,
    alexandria_librarian_vault_apply_moves,
    alexandria_librarian_vault_inventory,
    alexandria_librarian_vault_move_plan,
    alexandria_librarian_vault_path_search,
    alexandria_reindex_vault,
)
from app.mcp_server.tools.memory_compact_tools import (
    alexandria_archive_memory_compact as _alexandria_archive_memory_compact,
    alexandria_create_memory_compact as _alexandria_create_memory_compact,
    alexandria_delete_memory_compact as _alexandria_delete_memory_compact,
    alexandria_get_current_memory_compact as _alexandria_get_current_memory_compact,
    alexandria_get_memory_compact as _alexandria_get_memory_compact,
    alexandria_list_memory_compact_artifacts as _alexandria_list_memory_compact_artifacts,
    alexandria_mark_memory_compact_current as _alexandria_mark_memory_compact_current,
    alexandria_review_memory_compact as _alexandria_review_memory_compact,
)
from app.mcp_server.tools.memory_reconciliation_tools import (
    alexandria_apply_existing_memory_reconciliation as _alexandria_apply_existing_memory_reconciliation,
    alexandria_apply_memory_reconciliation as _alexandria_apply_memory_reconciliation,
    alexandria_get_memory_conflict as _alexandria_get_memory_conflict,
    alexandria_get_memory_reconciliation_plan as _alexandria_get_memory_reconciliation_plan,
    alexandria_get_memory_reconciliation_result as _alexandria_get_memory_reconciliation_result,
    alexandria_list_memory_conflicts as _alexandria_list_memory_conflicts,
    alexandria_list_memory_reconciliation_review_queue as _alexandria_list_memory_reconciliation_review_queue,
    alexandria_mark_memory_conflict_reviewing as _alexandria_mark_memory_conflict_reviewing,
    alexandria_preview_existing_memory_reconciliation as _alexandria_preview_existing_memory_reconciliation,
    alexandria_preview_memory_reconciliation as _alexandria_preview_memory_reconciliation,
    alexandria_preview_reconciliation_memory_compact as _alexandria_preview_reconciliation_memory_compact,
    alexandria_recall_memory_temporally as _alexandria_recall_memory_temporally,
    alexandria_resolve_memory_conflict as _alexandria_resolve_memory_conflict,
)
from app.mcp_server.tools.oauth_backend_gateway import (
    alexandria_librarian_oauth_poll,
    alexandria_librarian_oauth_refresh,
    alexandria_librarian_oauth_start,
    alexandria_librarian_oauth_status,
)
from app.mcp_server.tools.obsidian_backend_gateway import (
    alexandria_ask_obsidian_librarian,
    alexandria_get_related_notes,
    alexandria_read_note,
    alexandria_save_note,
    alexandria_search_vault,
)
from app.mcp_server.tools.operations_backend_gateway import (
    alexandria_operational_readiness,
    alexandria_recovery_plan,
    alexandria_recovery_quarantine,
    alexandria_recovery_retry,
    alexandria_recovery_run,
    alexandria_recovery_run_status,
)
from app.mcp_server.tools.skill_backend_gateway import (
    alexandria_ask_librarian,
    alexandria_complete_skill_acquisition,
    alexandria_librarian_brief_preview,
    alexandria_librarian_job_status,
    alexandria_librarian_route_preview,
    alexandria_search_skills,
    alexandria_skill_acquisition_job_status,
    alexandria_start_skill_acquisition,
)
from app.memory.domain.event_enum.context_enums import (
    RagStrategy,
)

_bounded_search_limit = _gateway_bounded_search_limit

DEFAULT_CONTEXT_SEARCH_LIMIT = 5

DEFAULT_CONTEXT_SEARCH_STRATEGY = RagStrategy.HYBRID

DEFAULT_SOURCE_AGENT = "Hermes"

DEFAULT_CANDIDATE_AUTHOR = "Hermes"

alexandria_get_current_memory_compact = _alexandria_get_current_memory_compact

alexandria_get_memory_compact = _alexandria_get_memory_compact

alexandria_create_memory_compact = _alexandria_create_memory_compact

alexandria_mark_memory_compact_current = _alexandria_mark_memory_compact_current

alexandria_archive_memory_compact = _alexandria_archive_memory_compact

alexandria_review_memory_compact = _alexandria_review_memory_compact

alexandria_librarian_readiness = _alexandria_librarian_readiness

alexandria_librarian_refresh_current_compact = (
    _alexandria_librarian_refresh_current_compact
)

alexandria_delete_memory_compact = _alexandria_delete_memory_compact

alexandria_list_memory_compact_artifacts = _alexandria_list_memory_compact_artifacts

alexandria_preview_memory_reconciliation = _alexandria_preview_memory_reconciliation

alexandria_preview_existing_memory_reconciliation = (
    _alexandria_preview_existing_memory_reconciliation
)

alexandria_apply_existing_memory_reconciliation = (
    _alexandria_apply_existing_memory_reconciliation
)

alexandria_recall_memory_temporally = _alexandria_recall_memory_temporally

alexandria_preview_reconciliation_memory_compact = (
    _alexandria_preview_reconciliation_memory_compact
)

alexandria_get_memory_reconciliation_plan = _alexandria_get_memory_reconciliation_plan

alexandria_apply_memory_reconciliation = _alexandria_apply_memory_reconciliation

alexandria_get_memory_reconciliation_result = (
    _alexandria_get_memory_reconciliation_result
)

alexandria_list_memory_reconciliation_review_queue = (
    _alexandria_list_memory_reconciliation_review_queue
)

alexandria_list_memory_conflicts = _alexandria_list_memory_conflicts

alexandria_get_memory_conflict = _alexandria_get_memory_conflict

alexandria_mark_memory_conflict_reviewing = _alexandria_mark_memory_conflict_reviewing

alexandria_resolve_memory_conflict = _alexandria_resolve_memory_conflict

__all__ = [
    "alexandria_apply_existing_memory_reconciliation",
    "alexandria_apply_memory_reconciliation",
    "alexandria_archive_context",
    "alexandria_archive_memory_compact",
    "alexandria_ask_librarian",
    "alexandria_ask_obsidian_librarian",
    "alexandria_complete_skill_acquisition",
    "alexandria_create_memory_compact",
    "alexandria_delete_context",
    "alexandria_delete_memory_compact",
    "alexandria_get_current_memory_compact",
    "alexandria_get_memory_compact",
    "alexandria_get_memory_conflict",
    "alexandria_get_memory_reconciliation_plan",
    "alexandria_get_memory_reconciliation_result",
    "alexandria_get_related_notes",
    "alexandria_librarian_brief_preview",
    "alexandria_librarian_job_status",
    "alexandria_librarian_oauth_poll",
    "alexandria_librarian_oauth_refresh",
    "alexandria_librarian_oauth_start",
    "alexandria_librarian_oauth_status",
    "alexandria_librarian_readiness",
    "alexandria_librarian_refresh_current_compact",
    "alexandria_librarian_review_apply_moves",
    "alexandria_librarian_review_move_plan",
    "alexandria_librarian_review_queue",
    "alexandria_librarian_route_preview",
    "alexandria_librarian_vault_apply_moves",
    "alexandria_librarian_vault_inventory",
    "alexandria_librarian_vault_move_plan",
    "alexandria_librarian_vault_path_search",
    "alexandria_list_memory_compact_artifacts",
    "alexandria_list_memory_conflicts",
    "alexandria_list_memory_reconciliation_review_queue",
    "alexandria_mark_memory_compact_current",
    "alexandria_mark_memory_conflict_reviewing",
    "alexandria_operational_readiness",
    "alexandria_preview_existing_memory_reconciliation",
    "alexandria_preview_memory_reconciliation",
    "alexandria_preview_reconciliation_memory_compact",
    "alexandria_rag_context",
    "alexandria_rag_status",
    "alexandria_read_note",
    "alexandria_recall_context",
    "alexandria_recall_memory_temporally",
    "alexandria_recovery_plan",
    "alexandria_recovery_quarantine",
    "alexandria_recovery_retry",
    "alexandria_recovery_run",
    "alexandria_recovery_run_status",
    "alexandria_reindex_vault",
    "alexandria_resolve_memory_conflict",
    "alexandria_review_memory_compact",
    "alexandria_save_note",
    "alexandria_search",
    "alexandria_search_skills",
    "alexandria_search_vault",
    "alexandria_skill_acquisition_job_status",
    "alexandria_start_skill_acquisition",
    "alexandria_supersede_context",
]
