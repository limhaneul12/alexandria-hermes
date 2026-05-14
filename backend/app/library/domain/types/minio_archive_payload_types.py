"""MINIO archive domain payload contracts."""

from __future__ import annotations

from app.shared.types.extra_types import JSONValue
from typing_extensions import TypedDict


class MinioArchiveDetailsPayload(TypedDict, extra_items=JSONValue):
    """Arbitrary details object for a MINIO-backed archive item."""
