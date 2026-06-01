"""Skill-acquisition artifact payload contracts."""

from __future__ import annotations

from app.shared.types.extra_types import JSONValue
from typing_extensions import TypedDict


class SkillSchemaPayload(TypedDict, extra_items=JSONValue):
    """Arbitrary JSON schema object owned by a generated skill artifact."""
