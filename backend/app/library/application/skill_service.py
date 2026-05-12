"""Skill-specific application services."""

from __future__ import annotations

from collections.abc import Mapping

from app.library.application.item_service import ItemService
from app.library.domain.entities.enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONValue


class SkillService:
    """Service for skill registration and generation workflows."""

    def __init__(self, item_service: ItemService) -> None:
        """Initialize service.

        Args:
            item_service: Shared item service.
        """
        self.item_service = item_service

    def _normalize_details(
        self,
        *,
        purpose: str,
        input_schema: dict[str, JSONValue],
        output_schema: dict[str, JSONValue],
        usage_example: str | None,
        required_tools: list[str],
        risk_level: str,
        version: str,
    ) -> dict[str, JSONValue]:
        """Build skill payload details used in persistent model.

        Args:
            purpose: Skill purpose statement.
            input_schema: Expected input data shape.
            output_schema: Expected output data shape.
            usage_example: Example run.
            required_tools: Required tools list.
            risk_level: Risk classification.
            version: Version string.

        Return:
            Persistent details dictionary.
        """
        return {
            "purpose": purpose,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "usage_example": usage_example,
            "required_tools": required_tools,
            "risk_level": risk_level,
            "version": version,
        }

    @staticmethod
    def _as_dict_value(payload: dict[str, JSONValue], key: str) -> dict[str, JSONValue]:
        value = payload.get(key, {})
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_list_value(payload: dict[str, JSONValue], key: str) -> list[str | int]:
        value = payload.get(key, [])
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str | int)]

    @staticmethod
    def _as_str_value(
        payload: dict[str, JSONValue], key: str, default: str = ""
    ) -> str:
        value = payload.get(key, default)
        return value if isinstance(value, str) else default

    async def create_skill(
        self,
        *,
        title: str,
        summary: str | None,
        content: str,
        category_id: int | None,
        tags: list[str],
        purpose: str,
        input_schema: dict[str, JSONValue],
        output_schema: dict[str, JSONValue],
        usage_example: str | None,
        required_tools: list[str],
        risk_level: str,
        version: str,
        created_by_name: str,
        activate: bool = False,
        status: ItemStatus | None = None,
    ) -> dict[str, JSONValue]:
        """Create one user-submitted skill.

        Args:
            title: Skill title.
            summary: Optional summary.
            content: Long-form content.
            category_id: Optional category.
            tags: Tag list.
            purpose: Problem statement.
            input_schema: Input JSON schema.
            output_schema: Output JSON schema.
            usage_example: Example run.
            required_tools: Tool dependency names.
            risk_level: Risk label.
            version: Version text.
            created_by_name: Human-readable source identifier.
            activate: Whether to mark active.
            status: Desired initial status.

        Return:
            Item payload.
        """
        if status is None:
            status = ItemStatus.ACTIVE if activate else ItemStatus.DRAFT

        if not purpose.strip():
            raise ValidationError("purpose is required")
        if not created_by_name.strip():
            raise ValidationError("created_by_name is required")
        return await self.item_service.create_item(
            item_type=ItemType.SKILL,
            title=title,
            summary=summary,
            content=content,
            category_id=category_id,
            tags=tags,
            status=status,
            source_type=SourceType.USER_CREATED,
            created_by_type=CreatedByType.USER,
            created_by_name=created_by_name,
            details=self._normalize_details(
                purpose=purpose,
                input_schema=input_schema,
                output_schema=output_schema,
                usage_example=usage_example,
                required_tools=required_tools,
                risk_level=risk_level,
                version=version,
            ),
        )

    async def create_skill_by_agent(
        self,
        *,
        title: str,
        content: str,
        summary: str | None,
        category_id: int | None,
        tags: list[str],
        purpose: str,
        input_schema: dict[str, JSONValue],
        output_schema: dict[str, JSONValue],
        usage_example: str | None,
        required_tools: list[str],
        risk_level: str,
        version: str,
        created_by_name: str,
        activate: bool,
        status: ItemStatus | None = None,
    ) -> dict[str, JSONValue]:
        """Create skill payload from a structured agent candidate.

        Args:
            title: Candidate title.
            content: Content body.
            summary: Optional summary.
            category_id: Optional category.
            tags: Tag list.
            purpose: Skill purpose.
            input_schema: Input schema.
            output_schema: Output schema.
            usage_example: Example.
            required_tools: Tool list.
            risk_level: Risk level.
            version: Semantic version.
            created_by_name: Source name.
            activate: Whether to activate directly.
            status: Optional forced status.

        Return:
            Item payload.
        """
        if status is None:
            status = ItemStatus.ACTIVE if activate else ItemStatus.DRAFT
        return await self.item_service.create_item(
            item_type=ItemType.SKILL,
            title=title,
            summary=summary,
            content=content,
            category_id=category_id,
            tags=tags,
            status=status,
            source_type=SourceType.AGENT_SUBMITTED,
            created_by_type=CreatedByType.AGENT,
            created_by_name=created_by_name,
            details=self._normalize_details(
                purpose=purpose,
                input_schema=input_schema,
                output_schema=output_schema,
                usage_example=usage_example,
                required_tools=required_tools,
                risk_level=risk_level,
                version=version,
            ),
        )

    async def create_from_librarian_candidate(
        self,
        *,
        generated: dict[str, JSONValue],
        category_id: int | None,
        tags: list[str],
        created_by_name: str,
    ) -> dict[str, JSONValue]:
        """Create a librarian produced candidate into a library draft item.

        Args:
            generated: Candidate payload from provider adapter.
            category_id: Optional category.
            tags: Tag list.
            created_by_name: Source display name.

        Return:
            Item payload.
        """
        return await self.item_service.create_item(
            item_type=ItemType.SKILL,
            title=self._as_str_value(generated, "title", "untitled"),
            summary=self._as_str_value(generated, "summary", ""),
            content=self._as_str_value(generated, "content", ""),
            category_id=category_id,
            tags=tags,
            status=ItemStatus.DRAFT,
            source_type=SourceType.LIBRARIAN_CREATED,
            created_by_type=CreatedByType.LIBRARIAN,
            created_by_name=created_by_name,
            details={
                "purpose": self._as_str_value(generated, "purpose", ""),
                "input_schema": self._as_dict_value(generated, "input_schema"),
                "output_schema": self._as_dict_value(generated, "output_schema"),
                "usage_example": generated.get("usage_example"),
                "required_tools": self._as_list_value(generated, "required_tools"),
                "risk_level": self._as_str_value(generated, "risk_level", "LOW"),
                "version": self._as_str_value(generated, "version", "1.0.0"),
                "librarian_provider_id": generated.get("provider_id"),
                "prompt": generated.get("prompt"),
            },
        )

    async def list_skills(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, JSONValue]], int]:
        """List skill items.

        Args:
            limit: Page size.
            offset: Page offset.

        Return:
            Tuple of payload list and total.
        """
        return await self.item_service.list_items(
            item_type=ItemType.SKILL,
            limit=limit,
            offset=offset,
        )

    async def patch_skill(
        self,
        *,
        item_id: int,
        payload: Mapping[str, JSONValue],
    ) -> dict[str, JSONValue]:
        """Patch one skill item.

        Args:
            item_id: Target item id.
            payload: Patch payload map.

        Return:
            Patched item payload.
        """
        item = await self.item_service.get_item(item_id)
        if item["item_type"] != ItemType.SKILL:
            raise ValidationError("Not a skill item")

        base_fields: dict[str, JSONValue] = {
            key: value
            for key, value in payload.items()
            if key
            in {
                "title",
                "summary",
                "content",
                "category_id",
                "tags",
                "status",
            }
        }

        detail_updates: dict[str, JSONValue] = {}
        for key in [
            "purpose",
            "input_schema",
            "output_schema",
            "usage_example",
            "required_tools",
            "risk_level",
            "version",
        ]:
            if key in payload:
                detail_updates[key] = payload[key]

        if detail_updates:
            existing_details_raw = item.get("details", {})
            existing_details = (
                existing_details_raw if isinstance(existing_details_raw, dict) else {}
            )
            existing_details.update(detail_updates)
            base_fields["details"] = existing_details

        if not base_fields:
            raise ValidationError("No fields provided")

        updated = await self.item_service.update_item(item_id, payload=base_fields)
        return updated
