"""CLI-only prompt command response schemas."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.types.extra_types import JSONValue


class PromptUsageResult(StrictSchemaModel):
    """JSON output contract for prompt rendering plus usage recording."""

    prompt: JSONValue
    usage: JSONValue
