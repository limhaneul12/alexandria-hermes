"""Context metadata boundary mapping."""

from __future__ import annotations

from collections.abc import Mapping

from app.memory.domain.types.context_payload_types import ContextMetadataPayload
from app.shared.types.extra_types import JSONValue


def metadata_payload(metadata: Mapping[str, JSONValue]) -> ContextMetadataPayload:
    """Normalize arbitrary context metadata from the request boundary.

    Args:
        metadata: Caller-owned arbitrary JSON metadata from the API request.

    Returns:
        Typed metadata payload for context application contracts.
    """
    # Metadata keys are caller-defined; only the JSON value shape is knowable here.
    payload: ContextMetadataPayload = {}
    payload.update(metadata.items())
    return payload
