"""Read models for canonical managed-note data-integrity diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.operations.domain.event_enum.operational_data_integrity_enums import (
    OperationalDataIntegrityStatus,
    OperationalDataIntegrityWarningCode,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationalDataIntegrityWarning:
    """One aggregated integrity problem suitable for operator reporting."""

    code: OperationalDataIntegrityWarningCode
    count: int
    note_paths: tuple[str, ...] = field(default_factory=tuple)
    fields: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationalDataIntegritySnapshot:
    """Read-only integrity status independent of infrastructure readiness."""

    status: OperationalDataIntegrityStatus
    scanned_notes: int
    warnings: tuple[OperationalDataIntegrityWarning, ...] = field(default_factory=tuple)


def unchecked_data_integrity_snapshot() -> OperationalDataIntegritySnapshot:
    """Return the compatibility default when inventory is unavailable.

    Returns:
        Unchecked data-integrity snapshot.
    """
    return OperationalDataIntegritySnapshot(
        status=OperationalDataIntegrityStatus.NOT_CHECKED,
        scanned_notes=0,
    )
