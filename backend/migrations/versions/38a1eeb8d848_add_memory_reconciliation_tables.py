"""add memory reconciliation tables.

Revision ID: 38a1eeb8d848
Revises: 202606021145_add_skill_acquisition_search_audit_fields
Create Date: 2026-07-25 02:17:09.479525
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "38a1eeb8d848"
down_revision: str | None = "202606021145_add_skill_acquisition_search_audit_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create reconciliation audit, relation, conflict, and temporal tables."""
    op.create_table(
        "memory_reconciliation_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("primary_decision", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_memory_reconciliation_plans_candidate_id",
        "memory_reconciliation_plans",
        ["candidate_id"],
    )
    op.create_index(
        "ix_memory_reconciliation_plans_idempotency_key",
        "memory_reconciliation_plans",
        ["idempotency_key"],
    )
    op.create_index(
        "ix_memory_reconciliation_plans_primary_decision",
        "memory_reconciliation_plans",
        ["primary_decision"],
    )
    op.create_index(
        "ix_memory_reconciliation_plans_status",
        "memory_reconciliation_plans",
        ["status"],
    )

    op.create_table(
        "memory_reconciliation_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plan_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("hard_delete_performed", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["memory_reconciliation_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id"),
    )
    op.create_index(
        "ix_memory_reconciliation_results_failure_code",
        "memory_reconciliation_results",
        ["failure_code"],
    )
    op.create_index(
        "ix_memory_reconciliation_results_plan_id",
        "memory_reconciliation_results",
        ["plan_id"],
    )
    op.create_index(
        "ix_memory_reconciliation_results_status",
        "memory_reconciliation_results",
        ["status"],
    )

    op.create_table(
        "memory_relations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_context_id", sa.String(length=512), nullable=False),
        sa.Column("target_context_id", sa.String(length=512), nullable=False),
        sa.Column("candidate_id", sa.String(length=255), nullable=False),
        sa.Column("relation", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decision_source", sa.String(length=32), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_context_id",
            "target_context_id",
            "relation",
            name="uq_memory_relation_identity",
        ),
    )
    op.create_index(
        "ix_memory_relations_candidate_id",
        "memory_relations",
        ["candidate_id"],
    )
    op.create_index(
        "ix_memory_relations_relation",
        "memory_relations",
        ["relation"],
    )
    op.create_index(
        "ix_memory_relations_source_context_id",
        "memory_relations",
        ["source_context_id"],
    )
    op.create_index(
        "ix_memory_relations_target_context_id",
        "memory_relations",
        ["target_context_id"],
    )

    op.create_table(
        "memory_conflict_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=255), nullable=False),
        sa.Column("subject_key", sa.String(length=512), nullable=False),
        sa.Column("claim_key", sa.String(length=1024), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("validity_overlap", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id",
            "claim_key",
            name="uq_memory_conflict_candidate_claim",
        ),
    )
    op.create_index(
        "ix_memory_conflict_sets_candidate_id",
        "memory_conflict_sets",
        ["candidate_id"],
    )
    op.create_index(
        "ix_memory_conflict_sets_scope",
        "memory_conflict_sets",
        ["scope"],
    )
    op.create_index(
        "ix_memory_conflict_sets_status",
        "memory_conflict_sets",
        ["status"],
    )
    op.create_index(
        "ix_memory_conflict_sets_subject_key",
        "memory_conflict_sets",
        ["subject_key"],
    )

    op.create_table(
        "context_temporal_states",
        sa.Column("context_id", sa.String(length=512), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("context_id"),
    )
    op.create_index(
        "ix_context_temporal_states_is_current",
        "context_temporal_states",
        ["is_current"],
    )
    op.create_index(
        "ix_context_temporal_states_valid_from",
        "context_temporal_states",
        ["valid_from"],
    )
    op.create_index(
        "ix_context_temporal_states_valid_to",
        "context_temporal_states",
        ["valid_to"],
    )


def downgrade() -> None:
    """Drop reconciliation audit, relation, conflict, and temporal tables."""
    op.drop_index(
        "ix_context_temporal_states_valid_to",
        table_name="context_temporal_states",
    )
    op.drop_index(
        "ix_context_temporal_states_valid_from",
        table_name="context_temporal_states",
    )
    op.drop_index(
        "ix_context_temporal_states_is_current",
        table_name="context_temporal_states",
    )
    op.drop_table("context_temporal_states")
    op.drop_index(
        "ix_memory_conflict_sets_subject_key",
        table_name="memory_conflict_sets",
    )
    op.drop_index(
        "ix_memory_conflict_sets_status",
        table_name="memory_conflict_sets",
    )
    op.drop_index(
        "ix_memory_conflict_sets_scope",
        table_name="memory_conflict_sets",
    )
    op.drop_index(
        "ix_memory_conflict_sets_candidate_id",
        table_name="memory_conflict_sets",
    )
    op.drop_table("memory_conflict_sets")
    op.drop_index(
        "ix_memory_relations_target_context_id",
        table_name="memory_relations",
    )
    op.drop_index(
        "ix_memory_relations_source_context_id",
        table_name="memory_relations",
    )
    op.drop_index(
        "ix_memory_relations_relation",
        table_name="memory_relations",
    )
    op.drop_index(
        "ix_memory_relations_candidate_id",
        table_name="memory_relations",
    )
    op.drop_table("memory_relations")
    op.drop_index(
        "ix_memory_reconciliation_results_status",
        table_name="memory_reconciliation_results",
    )
    op.drop_index(
        "ix_memory_reconciliation_results_plan_id",
        table_name="memory_reconciliation_results",
    )
    op.drop_index(
        "ix_memory_reconciliation_results_failure_code",
        table_name="memory_reconciliation_results",
    )
    op.drop_table("memory_reconciliation_results")
    op.drop_index(
        "ix_memory_reconciliation_plans_status",
        table_name="memory_reconciliation_plans",
    )
    op.drop_index(
        "ix_memory_reconciliation_plans_primary_decision",
        table_name="memory_reconciliation_plans",
    )
    op.drop_index(
        "ix_memory_reconciliation_plans_idempotency_key",
        table_name="memory_reconciliation_plans",
    )
    op.drop_index(
        "ix_memory_reconciliation_plans_candidate_id",
        table_name="memory_reconciliation_plans",
    )
    op.drop_table("memory_reconciliation_plans")
