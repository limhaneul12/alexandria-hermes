"""Guardrail integration for broad types and local import exceptions."""

from __future__ import annotations

from app.shared.guardrails.check_broad_types import collect_failures as broad_failures
from app.shared.guardrails.check_lazy_import_usage import (
    collect_failures as lazy_import_failures,
)


def test_production_annotations_avoid_unjustified_broad_types() -> None:
    """Ensure production type annotations satisfy the broad-type harness."""
    assert broad_failures() == []


def test_local_imports_have_explicit_boundary_justification() -> None:
    """Ensure production local imports are explicitly justified."""
    assert lazy_import_failures() == []
