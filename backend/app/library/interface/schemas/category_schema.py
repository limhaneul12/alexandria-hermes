"""Pydantic schemas for category endpoints."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.entities.read_models import Category
from app.library.interface.schemas._types import StrictSchema
from pydantic import ConfigDict, Field


class CategoryCreateRequest(StrictSchema):
    """Payload for creating a category node."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"name": "Backend", "parent_id": None}]}
    )

    name: str = Field(min_length=1)
    parent_id: str | None = None


class CategoryUpdateRequest(StrictSchema):
    """Payload for category rename."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "FastAPI"}]})

    name: str = Field(min_length=1)


class CategoryMoveRequest(StrictSchema):
    """Payload for move and reorder operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "parent_id": "00000000-0000-4000-8000-000000000001",
                    "position": 0,
                }
            ]
        }
    )

    parent_id: str | None
    position: int = Field(ge=0)


class CategoryResponse(StrictSchema):
    """Category API response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000002",
                    "name": "FastAPI",
                    "parent_id": "00000000-0000-4000-8000-000000000001",
                    "position": 0,
                    "created_at": "2026-05-12T10:00:00Z",
                    "updated_at": "2026-05-12T10:05:00Z",
                }
            ]
        },
    )

    id: str
    name: str
    parent_id: str | None
    position: int
    created_at: datetime
    updated_at: datetime


class CategoryTreeNode(StrictSchema):
    """Tree-shaped category response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000001",
                    "name": "Backend",
                    "parent_id": None,
                    "position": 0,
                    "children": [
                        {
                            "id": "00000000-0000-4000-8000-000000000002",
                            "name": "FastAPI",
                            "parent_id": "00000000-0000-4000-8000-000000000001",
                            "position": 0,
                            "children": [],
                        }
                    ],
                }
            ]
        }
    )

    id: str
    name: str
    parent_id: str | None
    position: int
    children: list[CategoryTreeNode]

    @classmethod
    def from_orm_node(
        cls,
        node: Category,
        *,
        children: list[CategoryTreeNode],
    ) -> CategoryTreeNode:
        """Build response node from ORM row.

        Args:
            node: ORM node.
            children: Child nodes.

        Return:
            Tree node schema.
        """
        return cls(
            id=node.id,
            name=node.name,
            parent_id=node.parent_id,
            position=node.position,
            children=children,
        )


CategoryTreeNode.model_rebuild()
