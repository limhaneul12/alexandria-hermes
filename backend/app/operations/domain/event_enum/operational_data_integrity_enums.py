"""Data-integrity states and stable diagnostic warning codes."""

from __future__ import annotations

from enum import StrEnum


class OperationalDataIntegrityStatus(StrEnum):
    """Health of canonical managed-note metadata."""

    NOT_CHECKED = "NOT_CHECKED"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"


class OperationalDataIntegrityWarningCode(StrEnum):
    """Stable warning codes emitted by the read-only integrity scan."""

    LEGACY_TUPLE_COLLECTION = "LEGACY_TUPLE_COLLECTION"
    EMPTY_COLLECTION_SCALAR = "EMPTY_COLLECTION_SCALAR"
    INVALID_COLLECTION_TYPE = "INVALID_COLLECTION_TYPE"
    STRING_BOOLEAN = "STRING_BOOLEAN"
    INVALID_BOOLEAN_VALUE = "INVALID_BOOLEAN_VALUE"
    UNRECOVERABLE_REDACTED_URL = "UNRECOVERABLE_REDACTED_URL"
    EXISTING_INDEX_ERRORS = "EXISTING_INDEX_ERRORS"
    INVENTORY_SCAN_ERROR = "INVENTORY_SCAN_ERROR"
