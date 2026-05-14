"""Response schemas for skill-specific endpoints."""

from __future__ import annotations

from app.library.interface.schemas._types import StrictSchema
from app.library.interface.schemas.skill.examples import SKILL_RESPONSE_EXAMPLE
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict


class SkillResponse(StrictSchema):
    """Skill payload with normalized type fields."""

    model_config = ConfigDict(json_schema_extra={"examples": [SKILL_RESPONSE_EXAMPLE]})

    id: str
    item_type: str
    title: str
    summary: str | None
    content: str
    details: dict[str, JSONValue]
    category_id: str | None
    status: str
    source_type: str
    created_by_type: str
    created_by_name: str
